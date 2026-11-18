"""Criterios de aceptación 1–15 del proyecto (sección 16 del prompt maestro)."""
from sqlalchemy import select

from app.config import settings
from app.models import Alumno, Entrega, Grupo, ProyectoEntrega, Requisito, Revision, Usuario
from tests.conftest import PDF, PNG, login_como


def _alumno(db, matricula) -> Alumno:
    return db.scalar(select(Alumno).where(Alumno.matricula == matricula))


def _req(db, nombre) -> Requisito:
    return db.scalar(select(Requisito).where(Requisito.nombre == nombre))


# 1. El administrador puede crear cuentas
def test_01_admin_crea_cuentas(cliente, db):
    login_como(cliente, "admin")
    g = db.scalar(select(Grupo).where(Grupo.nombre == "Grupo B"))
    r = cliente.post_form("/admin/alumnos/nuevo", {
        "nombre": "Nuevo Alumno", "email": "nuevo@estadias.test", "matricula": "N0001",
        "carrera": "Sistemas", "grupo_id": g.id, "profesor_id": 0, "password": "Clave1234",
    })
    assert r.status_code == 303
    r = cliente.post_form("/admin/usuarios/nuevo", {
        "nombre": "Profe Nuevo", "email": "profe.nuevo@estadias.test", "rol": "profesor", "password": "",
    })
    assert r.status_code == 303
    db.expire_all()
    nuevo = _alumno(db, "N0001")
    assert nuevo.usuario.rol == "alumno" and nuevo.grupo_id == g.id
    assert nuevo.usuario.password_hash.startswith("$2")  # bcrypt, nunca en texto plano
    assert db.scalar(select(Usuario).where(Usuario.email == "profe.nuevo@estadias.test")).rol == "profesor"
    # la cuenta nueva puede iniciar sesión
    cliente.post_form("/logout")
    cliente.entrar("nuevo@estadias.test", "Clave1234")


def test_01b_no_hay_registro_publico(cliente):
    assert cliente.get("/registro").status_code == 404
    assert cliente.get("/admin/alumnos/nuevo", follow_redirects=False).headers["location"] == "/login"


# 2. El alumno puede iniciar sesión (y credenciales incorrectas no)
def test_02_login_alumno(cliente):
    r = cliente.post_form("/login", {"email": "alumno1@estadias.test", "password": "incorrecta"})
    assert r.status_code == 400
    login_como(cliente, "alumno1")
    r = cliente.get("/")
    assert r.status_code == 200 and "Avance documental" in r.text


# 3. El alumno solo consulta su expediente
def test_03_alumno_solo_su_expediente(cliente, db):
    login_como(cliente, "alumno1")
    otro = _alumno(db, "B0001")
    ajena = db.scalar(select(Entrega).where(Entrega.alumno_id == otro.id))
    assert cliente.get(f"/archivos/entrega/{ajena.id}").status_code == 404
    assert cliente.get("/admin").status_code == 403
    assert cliente.get(f"/admin/alumnos/{otro.id}").status_code == 403
    assert cliente.get("/profesor").status_code == 403
    html = cliente.get("/alumno/expediente").text
    assert "A0001" in html and "B0001" not in html


# 4 y 5. Generales para todos; específicos solo para su grupo
def test_04_05_requisitos_generales_y_especificos(cliente):
    login_como(cliente, "alumno1")  # Grupo A
    html_a = cliente.get("/alumno/expediente").text
    cliente.post_form("/logout")
    login_como(cliente, "alumno3")  # Grupo B
    html_b = cliente.get("/alumno/expediente").text
    for general in ("Identificación oficial", "Comprobante de domicilio", "Historial académico", "Carta de aceptación"):
        assert general in html_a and general in html_b
    assert "Convenio de estadía" in html_a and "Convenio de estadía" not in html_b
    assert "Seguro facultativo" in html_b and "Seguro facultativo" not in html_a


# 6. El administrador agrega y modifica requisitos (sin desarrollador)
def test_06_admin_agrega_y_modifica_requisitos(cliente, db):
    login_como(cliente, "admin")
    g_c = db.scalar(select(Grupo).where(Grupo.nombre == "Grupo C"))
    cat = _req(db, "Convenio de estadía").categoria_id
    r = cliente.post_form("/admin/requisitos/nuevo", {
        "nombre": "Constancia de vigencia", "descripcion": "", "categoria_id": cat, "tipo": "especifico", "grupos": [g_c.id],
    })
    assert r.status_code == 303
    nuevo = _req(db, "Constancia de vigencia")
    assert [g.nombre for g in nuevo.grupos] == ["Grupo C"]
    # modificarlo a general
    r = cliente.post_form(f"/admin/requisitos/{nuevo.id}/editar", {
        "nombre": "Constancia de vigencia de derechos", "descripcion": "IMSS", "categoria_id": cat, "tipo": "general",
    })
    assert r.status_code == 303
    db.expire_all()
    assert nuevo.tipo == "general" and nuevo.grupos == [] and nuevo.nombre.endswith("derechos")
    cliente.post_form("/logout")
    login_como(cliente, "alumno1")
    assert "Constancia de vigencia de derechos" in cliente.get("/alumno/expediente").text


def test_06b_desactivar_requisito_conserva_historial(cliente, db):
    login_como(cliente, "admin")
    req = _req(db, "Identificación oficial")
    a1 = _alumno(db, "A0001")
    antes = db.scalar(select(Entrega).where(Entrega.alumno_id == a1.id, Entrega.requisito_id == req.id))
    cliente.post_form(f"/admin/requisitos/{req.id}/estado")
    html = cliente.get(f"/admin/alumnos/{a1.id}").text
    assert "ya no aplican" in html  # se muestra como historial
    assert cliente.get(f"/archivos/entrega/{antes.id}").status_code == 200
    assert (settings.STORAGE_DIR / antes.ruta).exists()


# 7. Los archivos se cargan y se almacenan en el servidor (carpeta privada)
def test_07_carga_y_almacenamiento(cliente, db):
    login_como(cliente, "alumno1")
    req = _req(db, "Carta de aceptación")
    r = cliente.post_form(f"/alumno/requisitos/{req.id}/entregar", files={"archivo": ("carta.pdf", PDF, "application/pdf")})
    assert r.status_code == 303
    e = db.scalar(select(Entrega).where(Entrega.requisito_id == req.id))
    assert e.estado == "en_revision" and e.nombre_original == "carta.pdf"
    ruta = settings.STORAGE_DIR / e.ruta
    assert ruta.read_bytes() == PDF
    assert "carta" not in ruta.name  # nombre interno aleatorio
    # imágenes también se aceptan
    req2 = _req(db, "Convenio de estadía")
    r = cliente.post_form(f"/alumno/requisitos/{req2.id}/entregar", files={"archivo": ("convenio.png", PNG, "image/png")})
    assert r.status_code == 303


def test_07b_rechaza_archivos_invalidos(cliente, db):
    login_como(cliente, "alumno1")
    req = _req(db, "Carta de aceptación")
    casos = [
        ("virus.exe", b"MZ\x90\x00", "application/octet-stream"),       # extensión no permitida
        ("falso.pdf", b"MZ\x90\x00 no soy pdf", "application/pdf"),      # extensión engañosa
        ("activo.pdf", b"%PDF-1.4 /JavaScript (alert(1))", "application/pdf"),  # PDF con JS
        ("grande.pdf", b"%PDF-" + b"0" * (settings.MAX_MB * 1024 * 1024 + 1), "application/pdf"),
    ]
    for nombre, datos, mime in casos:
        cliente.post_form(f"/alumno/requisitos/{req.id}/entregar", files={"archivo": (nombre, datos, mime)})
    assert db.scalar(select(Entrega).where(Entrega.requisito_id == req.id)) is None


# 8. Visualización y descarga seguras
def test_08_visualizacion_y_descarga_segura(cliente, db):
    e = db.scalar(select(Entrega).where(Entrega.alumno_id == _alumno(db, "A0001").id))
    assert cliente.get(f"/archivos/entrega/{e.id}", follow_redirects=False).status_code == 303  # sin sesión
    login_como(cliente, "alumno1")
    r = cliente.get(f"/archivos/entrega/{e.id}")
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    assert r.headers["content-disposition"].startswith("inline")
    assert r.headers["x-content-type-options"] == "nosniff"
    r = cliente.get(f"/archivos/entrega/{e.id}?descargar=1")
    assert r.headers["content-disposition"].startswith("attachment")
    # los archivos no están expuestos como estáticos
    assert cliente.get(f"/static/../storage/privado/{e.ruta}").status_code == 404


# 9. El encargado revisa documentos
def test_09_admin_revisa_documentos(cliente, db):
    login_como(cliente, "admin")
    pendiente = db.scalar(select(Entrega).where(Entrega.estado == "en_revision"))
    assert "Bandeja de revisión" in cliente.get("/admin/revision").text
    assert cliente.get(f"/admin/entregas/{pendiente.id}").status_code == 200
    # pedir corrección sin observación no se permite
    cliente.post_form(f"/admin/entregas/{pendiente.id}/revisar", {"resultado": "correccion", "observacion": ""})
    db.expire_all()
    assert pendiente.estado == "en_revision"
    cliente.post_form(f"/admin/entregas/{pendiente.id}/revisar", {"resultado": "aprobado", "observacion": ""})
    db.expire_all()
    assert pendiente.estado == "aprobado"
    assert db.scalar(select(Revision).where(Revision.entrega_id == pendiente.id)).resultado == "aprobado"


# 10. El alumno consulta observaciones y corrige
def test_10_alumno_ve_observacion_y_corrige(cliente, db):
    login_como(cliente, "alumno1")
    req = _req(db, "Comprobante de domicilio")  # en «correccion» según la semilla
    html = cliente.get("/alumno/expediente").text
    assert "más de 3 meses" in html
    r = cliente.post_form(f"/alumno/requisitos/{req.id}/entregar", files={"archivo": ("comprobante.pdf", PDF, "application/pdf")})
    assert r.status_code == 303
    versiones = db.scalars(select(Entrega).where(Entrega.requisito_id == req.id).order_by(Entrega.version)).all()
    assert [v.version for v in versiones] == [1, 2]
    assert versiones[0].estado == "correccion" and versiones[1].estado == "en_revision"


def test_10b_no_reemplaza_documento_aprobado(cliente, db):
    login_como(cliente, "alumno1")
    req = _req(db, "Identificación oficial")  # aprobado en la semilla
    cliente.post_form(f"/alumno/requisitos/{req.id}/entregar", files={"archivo": ("x.pdf", PDF, "application/pdf")})
    assert len(db.scalars(select(Entrega).where(Entrega.requisito_id == req.id, Entrega.alumno_id == _alumno(db, "A0001").id)).all()) == 1


# 11. El administrador asigna profesores
def test_11_admin_asigna_profesor(cliente, db):
    login_como(cliente, "admin")
    a4 = _alumno(db, "C0001")
    prof2 = db.scalar(select(Usuario).where(Usuario.email == "profesor2@estadias.test"))
    r = cliente.post_form("/admin/alumnos/asignar", {"ids": [a4.id], "grupo_id": "", "profesor_id": str(prof2.id)})
    assert r.status_code == 303
    db.expire_all()
    assert a4.profesor_id == prof2.id
    # un alumno no puede asignarse a sí mismo
    cliente.post_form("/logout")
    login_como(cliente, "alumno4")
    assert cliente.post_form("/admin/alumnos/asignar", {"ids": [a4.id], "profesor_id": "ninguno"}).status_code == 403


# 12. El profesor solo accede a sus alumnos asignados
def test_12_profesor_solo_sus_alumnos(cliente, db):
    login_como(cliente, "profesor2")
    a1 = _alumno(db, "A0001")  # asignado a profesor1
    proyecto = db.scalar(select(ProyectoEntrega).where(ProyectoEntrega.alumno_id == a1.id))
    assert "A0001" not in cliente.get("/profesor").text
    assert cliente.get(f"/profesor/alumnos/{a1.id}").status_code == 404
    assert cliente.get(f"/archivos/proyecto/{proyecto.id}").status_code == 404
    assert cliente.post_form(f"/profesor/proyectos/{proyecto.id}/revisar", {"resultado": "aprobado"}).status_code == 404
    assert cliente.get("/admin/requisitos").status_code == 403
    entrega = db.scalar(select(Entrega))
    assert cliente.get(f"/archivos/entrega/{entrega.id}").status_code == 404  # no ve documentos administrativos


# 13. El alumno entrega su proyecto
def test_13_alumno_entrega_proyecto(cliente, db):
    login_como(cliente, "alumno2")
    r = cliente.post_form("/alumno/proyecto/entregar", {"titulo": "App de citas médicas"},
                          files={"archivo": ("proyecto.pdf", PDF, "application/pdf")})
    assert r.status_code == 303
    p = db.scalar(select(ProyectoEntrega).where(ProyectoEntrega.alumno_id == _alumno(db, "A0002").id))
    assert p.version == 1 and p.estado == "en_revision"
    # sin profesor asignado no puede entregar
    cliente.post_form("/logout")
    login_como(cliente, "alumno4")
    cliente.post_form("/alumno/proyecto/entregar", {"titulo": "X"}, files={"archivo": ("p.pdf", PDF, "application/pdf")})
    assert db.scalar(select(ProyectoEntrega).where(ProyectoEntrega.alumno_id == _alumno(db, "C0001").id)) is None


# 14 y 15. El profesor aprueba o pide correcciones; el historial se conserva
def test_14_15_revision_de_proyecto_e_historial(cliente, db):
    a1 = _alumno(db, "A0001")
    v1 = db.scalar(select(ProyectoEntrega).where(ProyectoEntrega.alumno_id == a1.id))
    login_como(cliente, "profesor1")
    assert cliente.get(f"/profesor/alumnos/{a1.id}").status_code == 200
    cliente.post_form(f"/profesor/proyectos/{v1.id}/revisar", {"resultado": "correccion", "observacion": "Falta el marco teórico."})
    cliente.post_form("/logout")

    login_como(cliente, "alumno1")
    assert "Falta el marco teórico." in cliente.get("/alumno/proyecto").text
    cliente.post_form("/alumno/proyecto/entregar", {"titulo": ""}, files={"archivo": ("v2.pdf", PDF, "application/pdf")})
    cliente.post_form("/logout")

    login_como(cliente, "profesor1")
    v2 = db.scalar(select(ProyectoEntrega).where(ProyectoEntrega.alumno_id == a1.id, ProyectoEntrega.version == 2))
    assert v2.titulo == v1.titulo  # conserva el título si no se escribe otro
    # no se puede dictaminar una versión anterior
    cliente.post_form(f"/profesor/proyectos/{v1.id}/revisar", {"resultado": "aprobado"})
    cliente.post_form(f"/profesor/proyectos/{v2.id}/revisar", {"resultado": "aprobado", "observacion": "Excelente."})
    db.expire_all()
    assert v1.estado == "correccion" and v2.estado == "aprobado"
    html = cliente.get(f"/profesor/alumnos/{a1.id}").text
    assert "Versión 1" in html and "Versión 2" in html and "Falta el marco teórico." in html
    assert cliente.get(f"/archivos/proyecto/{v1.id}").status_code == 200  # la versión anterior sigue disponible
