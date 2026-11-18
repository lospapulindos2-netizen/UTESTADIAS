"""Panel del administrador / encargado de estadías."""
import re
import secrets

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import (
    APROBADO,
    CORRECCION,
    EN_REVISION,
    ROL_ADMIN,
    ROL_ALUMNO,
    ROL_PROFESOR,
    TIPO_ESPECIFICO,
    TIPO_GENERAL,
    Alumno,
    Bitacora,
    Categoria,
    Entrega,
    Grupo,
    Requisito,
    Revision,
    Usuario,
)
from app.security import hash_password, registrar, solo_admin, validar_password_nueva, verificar_csrf
from app.servicios import armar_expediente, resumen_alumnos, ultimas_entregas_subq, ultimo_proyecto
from app.web import flash, redirigir, render

router = APIRouter(prefix="/admin", dependencies=[Depends(verificar_csrf), Depends(solo_admin)])

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _obtener(db: Session, modelo, id_: int):
    obj = db.get(modelo, id_)
    if not obj:
        raise HTTPException(404, "Registro no encontrado.")
    return obj


def _password_inicial(password: str) -> tuple[str, str | None]:
    """Devuelve (password, error). Si viene vacía se genera una aleatoria."""
    if not password:
        return secrets.token_urlsafe(8) + "7a", None
    return password, validar_password_nueva(password)


def _validar_usuario(db: Session, nombre: str, email: str, excluir_id: int | None = None) -> str | None:
    if not nombre.strip():
        return "El nombre es obligatorio."
    if not EMAIL_RE.match(email):
        return "Correo electrónico no válido."
    q = select(Usuario.id).where(Usuario.email == email)
    if excluir_id:
        q = q.where(Usuario.id != excluir_id)
    if db.scalar(q):
        return "Ya existe una cuenta con ese correo."
    return None


def _validar_asignacion(db: Session, grupo_id: int, profesor_id: int) -> str | None:
    if grupo_id and not db.get(Grupo, grupo_id):
        return "El grupo seleccionado no existe."
    if profesor_id:
        p = db.get(Usuario, profesor_id)
        if not p or p.rol != ROL_PROFESOR:
            return "El profesor seleccionado no es válido."
    return None


def _grupos(db: Session, solo_activos=True):
    q = select(Grupo).order_by(Grupo.nombre)
    if solo_activos:
        q = q.where(Grupo.activo.is_(True))
    return db.scalars(q).all()


def _profesores(db: Session):
    return db.scalars(
        select(Usuario).where(Usuario.rol == ROL_PROFESOR, Usuario.activo.is_(True)).order_by(Usuario.nombre)
    ).all()


# ---------------------------------------------------------------- Panel
@router.get("")
def panel(request: Request, db: Session = Depends(get_db)):
    alumnos = db.scalars(
        select(Alumno).join(Usuario, Alumno.usuario_id == Usuario.id).where(Usuario.activo.is_(True))
    ).all()
    resumen = resumen_alumnos(db, alumnos)
    totales = {k: sum(r[k] for r in resumen.values()) for k in ("pendiente", EN_REVISION, APROBADO, CORRECCION)}
    completos = sum(1 for r in resumen.values() if r["completo"])
    grupos = db.scalars(
        select(Grupo).where(Grupo.activo.is_(True)).order_by(Grupo.nombre).options(selectinload(Grupo.alumnos))
    ).all()
    por_grupo = []
    for g in grupos:
        ids = [a.id for a in g.alumnos if a.id in resumen]
        prom = round(sum(resumen[i]["avance"] for i in ids) / len(ids)) if ids else 0
        por_grupo.append({"grupo": g, "alumnos": len(ids), "avance": prom})
    sin_grupo = sum(1 for a in alumnos if not a.grupo_id)
    sin_profesor = sum(1 for a in alumnos if not a.profesor_id)
    return render(
        request,
        "admin/panel.html",
        total_alumnos=len(alumnos),
        total_grupos=len(grupos),
        totales=totales,
        completos=completos,
        incompletos=len(alumnos) - completos,
        por_grupo=por_grupo,
        sin_grupo=sin_grupo,
        sin_profesor=sin_profesor,
    )


# ---------------------------------------------------------------- Bandeja de revisión
@router.get("/revision")
def bandeja(request: Request, grupo: int = 0, q: str = "", db: Session = Depends(get_db)):
    sub = ultimas_entregas_subq()
    consulta = (
        select(Entrega)
        .join(Alumno)
        .join(Usuario, Alumno.usuario_id == Usuario.id)
        .where(Entrega.id.in_(select(sub.c.id)), Entrega.estado == EN_REVISION)
        .options(selectinload(Entrega.alumno).selectinload(Alumno.usuario), selectinload(Entrega.requisito))
        .order_by(Entrega.creado_en)
    )
    if grupo:
        consulta = consulta.where(Alumno.grupo_id == grupo)
    if q.strip():
        like = f"%{q.strip()}%"
        consulta = consulta.where(or_(Usuario.nombre.like(like), Alumno.matricula.like(like)))
    entregas = db.scalars(consulta).all()
    return render(request, "admin/revision.html", entregas=entregas, grupos=_grupos(db), grupo=grupo, q=q)


@router.get("/entregas/{entrega_id}")
def ver_entrega(request: Request, entrega_id: int, db: Session = Depends(get_db)):
    e = _obtener(db, Entrega, entrega_id)
    historial = db.scalars(
        select(Entrega)
        .where(Entrega.alumno_id == e.alumno_id, Entrega.requisito_id == e.requisito_id)
        .order_by(Entrega.version.desc())
        .options(selectinload(Entrega.revisiones).selectinload(Revision.revisor))
    ).all()
    # Siguiente pendiente en la bandeja, para revisar en cadena
    sub = ultimas_entregas_subq()
    siguiente = db.scalar(
        select(Entrega.id)
        .where(Entrega.id.in_(select(sub.c.id)), Entrega.estado == EN_REVISION, Entrega.id != e.id)
        .order_by(Entrega.creado_en)
        .limit(1)
    )
    return render(
        request,
        "admin/entrega.html",
        e=e,
        historial=historial,
        es_ultima=historial[0].id == e.id,
        siguiente=siguiente,
    )


@router.post("/entregas/{entrega_id}/revisar")
def revisar_entrega(
    request: Request,
    entrega_id: int,
    resultado: str = Form(...),
    observacion: str = Form(""),
    siguiente: int = Form(0),
    db: Session = Depends(get_db),
):
    usuario = request.state.usuario
    e = _obtener(db, Entrega, entrega_id)
    ultima = db.scalar(
        select(func.max(Entrega.version)).where(
            Entrega.alumno_id == e.alumno_id, Entrega.requisito_id == e.requisito_id
        )
    )
    if e.version != ultima:
        flash(request, "Solo se puede dictaminar la versión más reciente.", "error")
        return redirigir(f"/admin/entregas/{e.id}")
    if resultado not in (APROBADO, CORRECCION):
        raise HTTPException(400, "Resultado no válido.")
    observacion = observacion.strip()
    if resultado == CORRECCION and not observacion:
        flash(request, "Escribe una observación indicando qué debe corregir el alumno.", "error")
        return redirigir(f"/admin/entregas/{e.id}")
    e.estado = resultado
    db.add(Revision(entrega_id=e.id, revisor_id=usuario.id, resultado=resultado, observacion=observacion or None))
    registrar(db, request, usuario, f"documento_{resultado}", f"entrega {e.id} alumno {e.alumno_id}")
    db.commit()
    flash(request, f"Documento marcado como «{'Aprobado' if resultado == APROBADO else 'Requiere corrección'}».")
    if siguiente:
        return redirigir(f"/admin/entregas/{siguiente}")
    return redirigir("/admin/revision")


# ---------------------------------------------------------------- Alumnos
@router.get("/alumnos")
def alumnos(
    request: Request,
    q: str = "",
    grupo: int = 0,
    profesor: int = 0,
    estado: str = "",
    inactivos: int = 0,
    db: Session = Depends(get_db),
):
    consulta = (
        select(Alumno)
        .join(Usuario, Alumno.usuario_id == Usuario.id)
        .options(selectinload(Alumno.usuario), selectinload(Alumno.grupo), selectinload(Alumno.profesor))
        .order_by(Usuario.nombre)
    )
    if not inactivos:
        consulta = consulta.where(Usuario.activo.is_(True))
    if q.strip():
        like = f"%{q.strip()}%"
        consulta = consulta.where(or_(Usuario.nombre.like(like), Alumno.matricula.like(like), Usuario.email.like(like)))
    if grupo == -1:
        consulta = consulta.where(Alumno.grupo_id.is_(None))
    elif grupo:
        consulta = consulta.where(Alumno.grupo_id == grupo)
    if profesor == -1:
        consulta = consulta.where(Alumno.profesor_id.is_(None))
    elif profesor:
        consulta = consulta.where(Alumno.profesor_id == profesor)
    lista = db.scalars(consulta).all()
    resumen = resumen_alumnos(db, lista)
    if estado == "completo":
        lista = [a for a in lista if resumen[a.id]["completo"]]
    elif estado == "incompleto":
        lista = [a for a in lista if not resumen[a.id]["completo"]]
    return render(
        request,
        "admin/alumnos.html",
        alumnos=lista,
        resumen=resumen,
        grupos=_grupos(db),
        profesores=_profesores(db),
        f={"q": q, "grupo": grupo, "profesor": profesor, "estado": estado, "inactivos": inactivos},
    )


@router.post("/alumnos/asignar")
def asignar_masivo(
    request: Request,
    ids: list[int] = Form([]),
    grupo_id: str = Form(""),
    profesor_id: str = Form(""),
    db: Session = Depends(get_db),
):
    if not ids:
        flash(request, "Selecciona al menos un alumno.", "error")
        return redirigir("/admin/alumnos")
    error = _validar_asignacion(
        db,
        int(grupo_id) if grupo_id.isdigit() else 0,
        int(profesor_id) if profesor_id.isdigit() else 0,
    )
    if error:
        flash(request, error, "error")
        return redirigir("/admin/alumnos")
    cambios = []
    for a in db.scalars(select(Alumno).where(Alumno.id.in_(ids))).all():
        if grupo_id:
            a.grupo_id = int(grupo_id) if grupo_id.isdigit() else None
        if profesor_id:
            a.profesor_id = int(profesor_id) if profesor_id.isdigit() else None
        cambios.append(str(a.id))
    registrar(db, request, request.state.usuario, "asignacion_masiva", f"alumnos {','.join(cambios)} grupo={grupo_id} profesor={profesor_id}")
    db.commit()
    flash(request, f"Asignación aplicada a {len(cambios)} alumno(s).")
    return redirigir("/admin/alumnos")


def _form_alumno(request, db, alumno=None, error=None, datos=None, status=200):
    return render(
        request,
        "admin/alumno_form.html",
        status,
        alumno=alumno,
        error=error,
        d=datos or {},
        grupos=_grupos(db),
        profesores=_profesores(db),
    )


@router.get("/alumnos/nuevo")
def alumno_nuevo_form(request: Request, db: Session = Depends(get_db)):
    return _form_alumno(request, db)


@router.post("/alumnos/nuevo")
def alumno_nuevo(
    request: Request,
    nombre: str = Form(""),
    email: str = Form(""),
    matricula: str = Form(""),
    carrera: str = Form(""),
    telefono: str = Form(""),
    grupo_id: int = Form(0),
    profesor_id: int = Form(0),
    password: str = Form(""),
    db: Session = Depends(get_db),
):
    datos = dict(nombre=nombre, email=email.strip().lower(), matricula=matricula.strip(), carrera=carrera,
                 telefono=telefono, grupo_id=grupo_id, profesor_id=profesor_id)
    error = _validar_usuario(db, nombre, datos["email"])
    if not error and (not datos["matricula"] or not carrera.strip()):
        error = "Matrícula y carrera son obligatorias."
    if not error and db.scalar(select(Alumno.id).where(Alumno.matricula == datos["matricula"])):
        error = "Ya existe un alumno con esa matrícula."
    error = error or _validar_asignacion(db, grupo_id, profesor_id)
    password, err_pw = _password_inicial(password)
    error = error or err_pw
    if error:
        return _form_alumno(request, db, error=error, datos=datos, status=400)

    u = Usuario(nombre=nombre.strip(), email=datos["email"], password_hash=hash_password(password), rol=ROL_ALUMNO)
    a = Alumno(
        usuario=u,
        matricula=datos["matricula"],
        carrera=carrera.strip(),
        telefono=telefono.strip() or None,
        grupo_id=grupo_id or None,
        profesor_id=profesor_id or None,
    )
    db.add(a)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        return _form_alumno(request, db, error="Correo o matrícula duplicados.", datos=datos, status=400)
    registrar(db, request, request.state.usuario, "alumno_creado", f"alumno {a.id} {a.matricula}")
    db.commit()
    flash(request, f"Alumno creado. Usuario: {u.email} — Contraseña inicial: {password}  (cópiala ahora, no se volverá a mostrar)")
    return redirigir(f"/admin/alumnos/{a.id}")


@router.get("/alumnos/{alumno_id}")
def expediente(request: Request, alumno_id: int, db: Session = Depends(get_db)):
    a = _obtener(db, Alumno, alumno_id)
    exp = armar_expediente(db, a)
    return render(request, "admin/expediente.html", a=a, exp=exp, proyecto=ultimo_proyecto(a))


@router.get("/alumnos/{alumno_id}/editar")
def alumno_editar_form(request: Request, alumno_id: int, db: Session = Depends(get_db)):
    a = _obtener(db, Alumno, alumno_id)
    datos = dict(nombre=a.usuario.nombre, email=a.usuario.email, matricula=a.matricula, carrera=a.carrera,
                 telefono=a.telefono or "", grupo_id=a.grupo_id or 0, profesor_id=a.profesor_id or 0)
    return _form_alumno(request, db, alumno=a, datos=datos)


@router.post("/alumnos/{alumno_id}/editar")
def alumno_editar(
    request: Request,
    alumno_id: int,
    nombre: str = Form(""),
    email: str = Form(""),
    matricula: str = Form(""),
    carrera: str = Form(""),
    telefono: str = Form(""),
    grupo_id: int = Form(0),
    profesor_id: int = Form(0),
    password: str = Form(""),
    db: Session = Depends(get_db),
):
    a = _obtener(db, Alumno, alumno_id)
    datos = dict(nombre=nombre, email=email.strip().lower(), matricula=matricula.strip(), carrera=carrera,
                 telefono=telefono, grupo_id=grupo_id, profesor_id=profesor_id)
    error = _validar_usuario(db, nombre, datos["email"], excluir_id=a.usuario_id)
    if not error and (not datos["matricula"] or not carrera.strip()):
        error = "Matrícula y carrera son obligatorias."
    if not error and db.scalar(select(Alumno.id).where(Alumno.matricula == datos["matricula"], Alumno.id != a.id)):
        error = "Ya existe un alumno con esa matrícula."
    error = error or _validar_asignacion(db, grupo_id, profesor_id)
    if not error and password:
        error = validar_password_nueva(password)
    if error:
        return _form_alumno(request, db, alumno=a, error=error, datos=datos, status=400)

    cambios = []
    if a.grupo_id != (grupo_id or None):
        cambios.append(f"grupo {a.grupo_id}->{grupo_id or None}")
    if a.profesor_id != (profesor_id or None):
        cambios.append(f"profesor {a.profesor_id}->{profesor_id or None}")
    a.usuario.nombre, a.usuario.email = nombre.strip(), datos["email"]
    a.matricula, a.carrera, a.telefono = datos["matricula"], carrera.strip(), telefono.strip() or None
    a.grupo_id, a.profesor_id = grupo_id or None, profesor_id or None
    if password:
        a.usuario.password_hash = hash_password(password)
        cambios.append("password restablecida")
    registrar(db, request, request.state.usuario, "alumno_editado", f"alumno {a.id} {'; '.join(cambios)}")
    db.commit()
    flash(request, "Datos del alumno actualizados.")
    return redirigir(f"/admin/alumnos/{a.id}")


@router.post("/alumnos/{alumno_id}/estado")
def alumno_estado(request: Request, alumno_id: int, db: Session = Depends(get_db)):
    a = _obtener(db, Alumno, alumno_id)
    a.usuario.activo = not a.usuario.activo
    registrar(db, request, request.state.usuario, "alumno_" + ("activado" if a.usuario.activo else "desactivado"), f"alumno {a.id}")
    db.commit()
    flash(request, "Cuenta " + ("activada." if a.usuario.activo else "desactivada. El alumno ya no puede iniciar sesión; su expediente se conserva."))
    return redirigir(f"/admin/alumnos/{a.id}")


# ---------------------------------------------------------------- Profesores y administradores
@router.get("/usuarios")
def usuarios(request: Request, db: Session = Depends(get_db)):
    lista = db.scalars(
        select(Usuario)
        .where(Usuario.rol.in_([ROL_PROFESOR, ROL_ADMIN]))
        .order_by(Usuario.rol.desc(), Usuario.nombre)
        .options(selectinload(Usuario.alumnos_asignados))
    ).all()
    return render(request, "admin/usuarios.html", usuarios=lista)


def _form_usuario(request, u=None, error=None, datos=None, status=200):
    return render(request, "admin/usuario_form.html", status, u=u, error=error, d=datos or {})


@router.get("/usuarios/nuevo")
def usuario_nuevo_form(request: Request):
    return _form_usuario(request, datos={"rol": ROL_PROFESOR})


@router.post("/usuarios/nuevo")
def usuario_nuevo(
    request: Request,
    nombre: str = Form(""),
    email: str = Form(""),
    rol: str = Form(ROL_PROFESOR),
    password: str = Form(""),
    db: Session = Depends(get_db),
):
    datos = dict(nombre=nombre, email=email.strip().lower(), rol=rol)
    error = _validar_usuario(db, nombre, datos["email"])
    if rol not in (ROL_PROFESOR, ROL_ADMIN):
        error = "Rol no válido."
    password, err_pw = _password_inicial(password)
    error = error or err_pw
    if error:
        return _form_usuario(request, error=error, datos=datos, status=400)
    u = Usuario(nombre=nombre.strip(), email=datos["email"], password_hash=hash_password(password), rol=rol)
    db.add(u)
    db.flush()
    registrar(db, request, request.state.usuario, "usuario_creado", f"usuario {u.id} rol {rol}")
    db.commit()
    flash(request, f"Cuenta creada. Usuario: {u.email} — Contraseña inicial: {password}  (cópiala ahora, no se volverá a mostrar)")
    return redirigir("/admin/usuarios")


@router.get("/usuarios/{usuario_id}/editar")
def usuario_editar_form(request: Request, usuario_id: int, db: Session = Depends(get_db)):
    u = _obtener(db, Usuario, usuario_id)
    if u.rol == ROL_ALUMNO:
        return redirigir(f"/admin/alumnos/{u.alumno.id}/editar")
    return _form_usuario(request, u=u, datos=dict(nombre=u.nombre, email=u.email, rol=u.rol))


@router.post("/usuarios/{usuario_id}/editar")
def usuario_editar(
    request: Request,
    usuario_id: int,
    nombre: str = Form(""),
    email: str = Form(""),
    password: str = Form(""),
    db: Session = Depends(get_db),
):
    u = _obtener(db, Usuario, usuario_id)
    if u.rol == ROL_ALUMNO:
        raise HTTPException(400, "Edita a los alumnos desde su expediente.")
    datos = dict(nombre=nombre, email=email.strip().lower(), rol=u.rol)
    error = _validar_usuario(db, nombre, datos["email"], excluir_id=u.id)
    if not error and password:
        error = validar_password_nueva(password)
    if error:
        return _form_usuario(request, u=u, error=error, datos=datos, status=400)
    u.nombre, u.email = nombre.strip(), datos["email"]
    if password:
        u.password_hash = hash_password(password)
    registrar(db, request, request.state.usuario, "usuario_editado", f"usuario {u.id}")
    db.commit()
    flash(request, "Cuenta actualizada.")
    return redirigir("/admin/usuarios")


@router.post("/usuarios/{usuario_id}/estado")
def usuario_estado(request: Request, usuario_id: int, db: Session = Depends(get_db)):
    u = _obtener(db, Usuario, usuario_id)
    if u.id == request.state.usuario.id:
        flash(request, "No puedes desactivar tu propia cuenta.", "error")
        return redirigir("/admin/usuarios")
    u.activo = not u.activo
    registrar(db, request, request.state.usuario, "usuario_" + ("activado" if u.activo else "desactivado"), f"usuario {u.id}")
    db.commit()
    flash(request, f"Cuenta de {u.nombre} {'activada' if u.activo else 'desactivada'}.")
    return redirigir("/admin/usuarios")


# ---------------------------------------------------------------- Grupos
@router.get("/grupos")
def grupos(request: Request, db: Session = Depends(get_db)):
    lista = db.scalars(select(Grupo).order_by(Grupo.activo.desc(), Grupo.nombre).options(selectinload(Grupo.alumnos))).all()
    return render(request, "admin/grupos.html", grupos=lista)


@router.post("/grupos")
def grupo_crear(request: Request, nombre: str = Form(""), descripcion: str = Form(""), db: Session = Depends(get_db)):
    nombre = nombre.strip()
    if not nombre:
        flash(request, "El nombre del grupo es obligatorio.", "error")
    elif db.scalar(select(Grupo.id).where(Grupo.nombre == nombre)):
        flash(request, "Ya existe un grupo con ese nombre.", "error")
    else:
        g = Grupo(nombre=nombre, descripcion=descripcion.strip() or None)
        db.add(g)
        db.flush()
        registrar(db, request, request.state.usuario, "grupo_creado", f"grupo {g.id} {nombre}")
        db.commit()
        flash(request, f"Grupo «{nombre}» creado.")
    return redirigir("/admin/grupos")


@router.post("/grupos/{grupo_id}")
def grupo_editar(request: Request, grupo_id: int, nombre: str = Form(""), descripcion: str = Form(""), db: Session = Depends(get_db)):
    g = _obtener(db, Grupo, grupo_id)
    nombre = nombre.strip()
    if not nombre or db.scalar(select(Grupo.id).where(Grupo.nombre == nombre, Grupo.id != g.id)):
        flash(request, "Nombre vacío o repetido.", "error")
        return redirigir("/admin/grupos")
    g.nombre, g.descripcion = nombre, descripcion.strip() or None
    registrar(db, request, request.state.usuario, "grupo_editado", f"grupo {g.id}")
    db.commit()
    flash(request, "Grupo actualizado.")
    return redirigir("/admin/grupos")


@router.post("/grupos/{grupo_id}/estado")
def grupo_estado(request: Request, grupo_id: int, db: Session = Depends(get_db)):
    g = _obtener(db, Grupo, grupo_id)
    g.activo = not g.activo
    registrar(db, request, request.state.usuario, "grupo_" + ("activado" if g.activo else "desactivado"), f"grupo {g.id}")
    db.commit()
    flash(request, f"Grupo «{g.nombre}» {'activado' if g.activo else 'desactivado'}.")
    return redirigir("/admin/grupos")


# ---------------------------------------------------------------- Categorías y requisitos
@router.get("/requisitos")
def requisitos(request: Request, db: Session = Depends(get_db)):
    cats = db.scalars(
        select(Categoria)
        .order_by(Categoria.activo.desc(), Categoria.orden, Categoria.nombre)
        .options(selectinload(Categoria.requisitos).selectinload(Requisito.grupos))
    ).all()
    return render(request, "admin/requisitos.html", categorias=cats)


@router.post("/categorias")
def categoria_crear(request: Request, nombre: str = Form(""), orden: int = Form(0), db: Session = Depends(get_db)):
    nombre = nombre.strip()
    if not nombre or db.scalar(select(Categoria.id).where(Categoria.nombre == nombre)):
        flash(request, "Nombre de categoría vacío o repetido.", "error")
    else:
        db.add(Categoria(nombre=nombre, orden=orden))
        registrar(db, request, request.state.usuario, "categoria_creada", nombre)
        db.commit()
        flash(request, f"Categoría «{nombre}» creada.")
    return redirigir("/admin/requisitos")


@router.post("/categorias/{cat_id}")
def categoria_editar(request: Request, cat_id: int, nombre: str = Form(""), orden: int = Form(0), db: Session = Depends(get_db)):
    c = _obtener(db, Categoria, cat_id)
    nombre = nombre.strip()
    if not nombre or db.scalar(select(Categoria.id).where(Categoria.nombre == nombre, Categoria.id != c.id)):
        flash(request, "Nombre de categoría vacío o repetido.", "error")
    else:
        c.nombre, c.orden = nombre, orden
        registrar(db, request, request.state.usuario, "categoria_editada", f"categoria {c.id}")
        db.commit()
        flash(request, "Categoría actualizada.")
    return redirigir("/admin/requisitos")


@router.post("/categorias/{cat_id}/estado")
def categoria_estado(request: Request, cat_id: int, db: Session = Depends(get_db)):
    c = _obtener(db, Categoria, cat_id)
    c.activo = not c.activo
    registrar(db, request, request.state.usuario, "categoria_" + ("activada" if c.activo else "desactivada"), f"categoria {c.id}")
    db.commit()
    flash(request, f"Categoría «{c.nombre}» {'activada' if c.activo else 'desactivada (sus documentos dejan de pedirse; el historial se conserva)'}.")
    return redirigir("/admin/requisitos")


def _form_requisito(request, db, r=None, error=None, datos=None, status=200):
    cats = db.scalars(select(Categoria).where(Categoria.activo.is_(True)).order_by(Categoria.orden, Categoria.nombre)).all()
    return render(request, "admin/requisito_form.html", status, r=r, error=error, d=datos or {}, categorias=cats, grupos=_grupos(db))


@router.get("/requisitos/nuevo")
def requisito_nuevo_form(request: Request, categoria: int = 0, db: Session = Depends(get_db)):
    return _form_requisito(request, db, datos={"categoria_id": categoria, "tipo": TIPO_GENERAL, "grupos": []})


def _guardar_requisito(request, db, r, nombre, descripcion, categoria_id, tipo, grupos):
    datos = dict(nombre=nombre, descripcion=descripcion, categoria_id=categoria_id, tipo=tipo, grupos=grupos)
    error = None
    if not nombre.strip():
        error = "El nombre del documento es obligatorio."
    elif not db.get(Categoria, categoria_id):
        error = "Selecciona una categoría."
    elif tipo not in (TIPO_GENERAL, TIPO_ESPECIFICO):
        error = "Tipo no válido."
    elif tipo == TIPO_ESPECIFICO and not grupos:
        error = "Un documento específico debe asignarse al menos a un grupo."
    if error:
        return _form_requisito(request, db, r=r, error=error, datos=datos, status=400)
    nuevo = r is None
    if nuevo:
        r = Requisito()
        db.add(r)
    r.nombre, r.descripcion = nombre.strip(), descripcion.strip() or None
    r.categoria_id, r.tipo = categoria_id, tipo
    r.grupos = db.scalars(select(Grupo).where(Grupo.id.in_(grupos))).all() if tipo == TIPO_ESPECIFICO else []
    db.flush()
    registrar(db, request, request.state.usuario, "requisito_" + ("creado" if nuevo else "editado"), f"requisito {r.id} {r.nombre} tipo={tipo} grupos={grupos}")
    db.commit()
    flash(request, f"Documento requerido «{r.nombre}» {'creado' if nuevo else 'actualizado'}.")
    return redirigir("/admin/requisitos")


@router.post("/requisitos/nuevo")
def requisito_nuevo(
    request: Request,
    nombre: str = Form(""),
    descripcion: str = Form(""),
    categoria_id: int = Form(0),
    tipo: str = Form(TIPO_GENERAL),
    grupos: list[int] = Form([]),
    db: Session = Depends(get_db),
):
    return _guardar_requisito(request, db, None, nombre, descripcion, categoria_id, tipo, grupos)


@router.get("/requisitos/{req_id}/editar")
def requisito_editar_form(request: Request, req_id: int, db: Session = Depends(get_db)):
    r = _obtener(db, Requisito, req_id)
    datos = dict(nombre=r.nombre, descripcion=r.descripcion or "", categoria_id=r.categoria_id, tipo=r.tipo, grupos=[g.id for g in r.grupos])
    return _form_requisito(request, db, r=r, datos=datos)


@router.post("/requisitos/{req_id}/editar")
def requisito_editar(
    request: Request,
    req_id: int,
    nombre: str = Form(""),
    descripcion: str = Form(""),
    categoria_id: int = Form(0),
    tipo: str = Form(TIPO_GENERAL),
    grupos: list[int] = Form([]),
    db: Session = Depends(get_db),
):
    r = _obtener(db, Requisito, req_id)
    return _guardar_requisito(request, db, r, nombre, descripcion, categoria_id, tipo, grupos)


@router.post("/requisitos/{req_id}/estado")
def requisito_estado(request: Request, req_id: int, db: Session = Depends(get_db)):
    r = _obtener(db, Requisito, req_id)
    r.activo = not r.activo
    registrar(db, request, request.state.usuario, "requisito_" + ("activado" if r.activo else "desactivado"), f"requisito {r.id}")
    db.commit()
    flash(request, f"«{r.nombre}» {'activado' if r.activo else 'desactivado. Ya no se pedirá; las entregas anteriores se conservan'}.")
    return redirigir("/admin/requisitos")


# ---------------------------------------------------------------- Bitácora
@router.get("/bitacora")
def bitacora(request: Request, accion: str = "", db: Session = Depends(get_db)):
    q = select(Bitacora).options(selectinload(Bitacora.usuario)).order_by(Bitacora.id.desc()).limit(300)
    if accion:
        q = q.where(Bitacora.accion.like(f"{accion}%"))
    return render(request, "admin/bitacora.html", registros=db.scalars(q).all(), accion=accion)
