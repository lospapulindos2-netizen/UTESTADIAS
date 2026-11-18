"""Las pruebas usan una BD SQLite y una carpeta de archivos temporales (no tocan MySQL)."""
import os
import re
import shutil
import tempfile
from pathlib import Path

import pytest

_TMP = Path(tempfile.mkdtemp(prefix="estadias_test_"))
os.environ.update(
    DATABASE_URL=f"sqlite:///{(_TMP / 'test.db').as_posix()}",
    STORAGE_DIR=str(_TMP / "privado"),
    SECRET_KEY="clave-solo-para-pruebas-1234567890",
    BCRYPT_ROUNDS="4",
    MODO_DEMO="false",  # las pruebas que lo necesitan lo activan explícitamente
)

from fastapi.testclient import TestClient  # noqa: E402

from app import security  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from scripts import semilla  # noqa: E402

CSRF_RE = re.compile(r'name="_csrf" value="([^"]+)"')


@pytest.fixture()
def db_limpia():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    shutil.rmtree(_TMP / "privado", ignore_errors=True)
    security._INTENTOS.clear()
    semilla.main()
    yield
    engine.dispose()


@pytest.fixture()
def db(db_limpia):
    s = SessionLocal()
    yield s
    s.close()


class Cliente(TestClient):
    """TestClient con ayudas para CSRF e inicio de sesión."""

    def csrf(self) -> str:
        html = self.get("/login" if not self.cookies.get("estadias_sesion") else "/cuenta/password").text
        return CSRF_RE.search(html).group(1)

    def post_form(self, url, data=None, files=None, **kw):
        data = dict(data or {})
        data["_csrf"] = self.csrf()
        return self.post(url, data=data, files=files, follow_redirects=kw.pop("follow_redirects", False), **kw)

    def entrar(self, email, password):
        r = self.post_form("/login", {"email": email, "password": password})
        assert r.status_code == 303, r.text[:500]
        return r


@pytest.fixture()
def cliente(db_limpia):
    with Cliente(app) as c:
        yield c


def login_como(cliente: Cliente, quien: str) -> Cliente:
    if quien in semilla.USUARIOS_PRUEBA:
        _, email, pw = semilla.USUARIOS_PRUEBA[quien]
    else:  # alumno1..alumno4
        email, pw = f"{quien}@estadias.test", semilla.PASSWORD_ALUMNO
    cliente.entrar(email, pw)
    return cliente


PDF = semilla.pdf_minimo("archivo de prueba")
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
