"""Pruebas de seguridad complementarias."""
from tests.conftest import login_como


def test_csrf_obligatorio(cliente):
    login_como(cliente, "admin")
    r = cliente.post("/admin/grupos", data={"nombre": "Sin token"}, follow_redirects=False)
    assert r.status_code == 403
    r = cliente.post("/admin/grupos", data={"nombre": "Token falso", "_csrf": "x"}, follow_redirects=False)
    assert r.status_code == 403


def test_bloqueo_por_intentos_fallidos(cliente):
    for _ in range(5):
        cliente.post_form("/login", {"email": "admin@estadias.test", "password": "mal"})
    r = cliente.post_form("/login", {"email": "admin@estadias.test", "password": "Admin2026"})
    assert r.status_code == 429


def test_cuenta_desactivada_pierde_acceso(cliente, db):
    from sqlalchemy import select

    from app.models import Usuario

    login_como(cliente, "alumno2")
    u = db.scalar(select(Usuario).where(Usuario.email == "alumno2@estadias.test"))
    u.activo = False
    db.commit()
    assert cliente.get("/alumno", follow_redirects=False).headers["location"] == "/login"


def test_cabeceras_de_seguridad(cliente):
    r = cliente.get("/login")
    assert "default-src 'self'" in r.headers["content-security-policy"]
    assert r.headers["x-frame-options"] == "SAMEORIGIN"
    cookie = r.headers.get("set-cookie", "").lower()
    assert "httponly" in cookie and "samesite=lax" in cookie


def test_sesion_se_renueva_al_iniciar(cliente):
    cliente.get("/login")
    antes = cliente.cookies.get("estadias_sesion")
    login_como(cliente, "alumno1")
    assert cliente.cookies.get("estadias_sesion") != antes


def test_bitacora_registra_acciones(cliente, db):
    from sqlalchemy import select

    from app.models import Bitacora

    login_como(cliente, "admin")
    cliente.post_form("/admin/grupos", {"nombre": "Grupo D", "descripcion": ""})
    acciones = set(db.scalars(select(Bitacora.accion)).all())
    assert {"login", "grupo_creado"} <= acciones
