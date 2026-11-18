"""Contraseñas, sesión, CSRF y control de acceso por rol."""
import hmac
import os
import secrets
import time
from collections import defaultdict

import bcrypt
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ROL_ADMIN, ROL_ALUMNO, ROL_PROFESOR, Bitacora, Usuario


# --- Contraseñas (bcrypt) --------------------------------------------------
BCRYPT_ROUNDS = int(os.getenv("BCRYPT_ROUNDS", "12"))  # las pruebas usan menos rondas


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt(rounds=BCRYPT_ROUNDS)).decode()


def verificar_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8")[:72], hashed.encode())
    except ValueError:
        return False


def validar_password_nueva(password: str) -> str | None:
    if len(password) < 8:
        return "La contraseña debe tener al menos 8 caracteres."
    if password.isdigit() or password.isalpha():
        return "La contraseña debe combinar letras y números."
    return None


# --- Bloqueo por intentos fallidos (en memoria) ----------------------------
_INTENTOS: dict[str, list[float]] = defaultdict(list)
MAX_INTENTOS, VENTANA_SEG = 5, 300


def login_bloqueado(clave: str) -> bool:
    ahora = time.monotonic()
    _INTENTOS[clave] = [t for t in _INTENTOS[clave] if ahora - t < VENTANA_SEG]
    return len(_INTENTOS[clave]) >= MAX_INTENTOS


def registrar_fallo(clave: str) -> None:
    _INTENTOS[clave].append(time.monotonic())


def limpiar_fallos(clave: str) -> None:
    _INTENTOS.pop(clave, None)


# --- CSRF (token por sesión) ----------------------------------------------
def csrf_token(request: Request) -> str:
    token = request.session.get("csrf")
    if not token:
        token = secrets.token_urlsafe(32)
        request.session["csrf"] = token
    return token


async def verificar_csrf(request: Request) -> None:
    """Dependencia global: todo POST debe traer el token de la sesión."""
    if request.method != "POST":
        return
    form = await request.form()
    enviado = str(form.get("_csrf", ""))
    esperado = request.session.get("csrf", "")
    if not esperado or not hmac.compare_digest(enviado, esperado):
        raise HTTPException(status_code=403, detail="Token CSRF inválido. Recarga la página.")


# --- Usuario actual y roles -----------------------------------------------
class NoAutenticado(Exception):
    pass


def usuario_actual(request: Request, db: Session = Depends(get_db)) -> Usuario:
    uid = request.session.get("uid")
    if not uid:
        raise NoAutenticado()
    usuario = db.get(Usuario, uid)
    if not usuario or not usuario.activo:
        request.session.clear()
        raise NoAutenticado()
    request.state.usuario = usuario
    return usuario


def requiere_rol(*roles: str):
    def _dep(usuario: Usuario = Depends(usuario_actual)) -> Usuario:
        if usuario.rol not in roles:
            raise HTTPException(status_code=403, detail="No tienes permiso para esta sección.")
        return usuario

    return _dep


solo_admin = requiere_rol(ROL_ADMIN)
solo_alumno = requiere_rol(ROL_ALUMNO)
solo_profesor = requiere_rol(ROL_PROFESOR)


# --- Bitácora --------------------------------------------------------------
def registrar(db: Session, request: Request, usuario: Usuario | None, accion: str, detalle: str = "") -> None:
    db.add(
        Bitacora(
            usuario_id=usuario.id if usuario else None,
            accion=accion,
            detalle=detalle[:500],
            ip=request.client.host if request.client else None,
        )
    )
