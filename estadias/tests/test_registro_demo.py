"""Registro de cuentas de prueba (solo con MODO_DEMO=true)."""
import pytest
from sqlalchemy import select

from app.config import settings
from app.models import Alumno, Grupo, Usuario


@pytest.fixture()
def demo(monkeypatch):
    monkeypatch.setattr(settings, "MODO_DEMO", True)


def _registrar(cliente, **datos):
    base = {"nombre": "Persona Demo", "password": "Demo12345", "confirmar": "Demo12345"}
    return cliente.post_form("/registro", {**base, **datos})


def test_registro_apagado_por_defecto(cliente):
    assert cliente.get("/registro").status_code == 404
    assert _registrar(cliente, email="x@estadias.test", rol="alumno").status_code in (403, 404)
    assert "Crear cuenta de prueba" not in cliente.get("/login").text


@pytest.mark.parametrize("rol,inicio", [("alumno", "/alumno"), ("profesor", "/profesor"), ("admin", "/admin")])
def test_registro_por_rol_y_entra(cliente, db, demo, rol, inicio):
    assert "Crear cuenta de prueba" in cliente.get("/login").text
    r = _registrar(cliente, email=f"demo.{rol}@estadias.test", rol=rol)
    assert r.status_code == 303 and r.headers["location"] == inicio
    assert cliente.get(inicio).status_code == 200  # ya quedó con la sesión iniciada
    u = db.scalar(select(Usuario).where(Usuario.email == f"demo.{rol}@estadias.test"))
    assert u.rol == rol and u.password_hash.startswith("$2")
    assert (u.alumno is not None) == (rol == "alumno")


def test_registro_alumno_con_grupo_ve_sus_requisitos(cliente, db, demo):
    g = db.scalar(select(Grupo).where(Grupo.nombre == "Grupo B"))
    _registrar(cliente, email="demo.b@estadias.test", rol="alumno", grupo_id=g.id, matricula="")
    a = db.scalar(select(Alumno).join(Usuario, Alumno.usuario_id == Usuario.id).where(Usuario.email == "demo.b@estadias.test"))
    assert a.matricula.startswith("DEMO") and a.grupo_id == g.id
    assert "Seguro facultativo" in cliente.get("/alumno/expediente").text


def test_registro_valida_datos(cliente, db, demo):
    assert _registrar(cliente, email="admin@estadias.test", rol="alumno").status_code == 400  # correo repetido
    assert _registrar(cliente, email="n1@estadias.test", rol="alumno", confirmar="otra").status_code == 400
    assert _registrar(cliente, email="n2@estadias.test", rol="alumno", password="corta", confirmar="corta").status_code == 400
    assert _registrar(cliente, email="n3@estadias.test", rol="superusuario").status_code == 400
    assert db.scalar(select(Usuario).where(Usuario.email.like("n_@estadias.test"))) is None
