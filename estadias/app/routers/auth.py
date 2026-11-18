from fastapi import APIRouter, Depends, Form, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import ROL_ADMIN, ROL_ALUMNO, ROL_PROFESOR, Alumno, Grupo, Usuario
from app.security import (
    NoAutenticado,
    hash_password,
    limpiar_fallos,
    login_bloqueado,
    registrar,
    registrar_fallo,
    usuario_actual,
    validar_password_nueva,
    verificar_csrf,
    verificar_password,
)
from app.web import flash, redirigir, render

router = APIRouter(dependencies=[Depends(verificar_csrf)])

INICIO = {ROL_ADMIN: "/admin", ROL_PROFESOR: "/profesor", ROL_ALUMNO: "/alumno"}


@router.get("/")
def inicio(request: Request, db: Session = Depends(get_db)):
    try:
        u = usuario_actual(request, db)
    except NoAutenticado:
        return redirigir("/login")
    return redirigir(INICIO[u.rol])


@router.get("/login")
def login_form(request: Request):
    if request.session.get("uid"):
        return redirigir("/")
    return render(request, "login.html")


@router.post("/login")
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    email = email.strip().lower()
    clave = f"{request.client.host if request.client else ''}|{email}"
    if login_bloqueado(clave):
        return render(request, "login.html", 429, error="Demasiados intentos. Espera 5 minutos.", email=email)

    u = db.scalar(select(Usuario).where(Usuario.email == email))
    if not u or not u.activo or not verificar_password(password, u.password_hash):
        registrar_fallo(clave)
        registrar(db, request, u, "login_fallido", email)
        db.commit()
        return render(request, "login.html", 400, error="Correo o contraseña incorrectos.", email=email)

    limpiar_fallos(clave)
    request.session.clear()  # evita fijación de sesión
    request.session["uid"] = u.id
    registrar(db, request, u, "login")
    db.commit()
    return redirigir(INICIO[u.rol])


ROLES_DEMO = {ROL_ALUMNO: "Alumno", ROL_PROFESOR: "Profesor", ROL_ADMIN: "Revisor / encargado de estadías"}


def _form_registro(request: Request, db: Session, status: int = 200, **ctx):
    if not settings.MODO_DEMO:
        raise HTTPException(404, "La página no existe.")
    grupos = db.scalars(select(Grupo).where(Grupo.activo.is_(True)).order_by(Grupo.nombre)).all()
    profesores = db.scalars(
        select(Usuario).where(Usuario.rol == ROL_PROFESOR, Usuario.activo.is_(True)).order_by(Usuario.nombre)
    ).all()
    ctx.setdefault("d", {"rol": ROL_ALUMNO})
    return render(request, "registro.html", status, roles=ROLES_DEMO, grupos=grupos, profesores=profesores, **ctx)


@router.get("/registro")
def registro_form(request: Request, db: Session = Depends(get_db)):
    return _form_registro(request, db)


@router.post("/registro")
def registro(
    request: Request,
    nombre: str = Form(""),
    email: str = Form(""),
    rol: str = Form(ROL_ALUMNO),
    password: str = Form(""),
    confirmar: str = Form(""),
    matricula: str = Form(""),
    carrera: str = Form(""),
    grupo_id: int = Form(0),
    profesor_id: int = Form(0),
    db: Session = Depends(get_db),
):
    from app.routers.admin import _validar_asignacion, _validar_usuario

    if not settings.MODO_DEMO:
        raise HTTPException(404, "La página no existe.")
    email = email.strip().lower()
    matricula = matricula.strip()
    d = dict(nombre=nombre, email=email, rol=rol, matricula=matricula, carrera=carrera, grupo_id=grupo_id, profesor_id=profesor_id)
    error = None
    if rol not in ROLES_DEMO:
        error = "Elige un tipo de cuenta."
    error = error or _validar_usuario(db, nombre, email)
    if not error and password != confirmar:
        error = "Las contraseñas no coinciden."
    error = error or (validar_password_nueva(password) if not error else None)
    if not error and rol == ROL_ALUMNO:
        if matricula and db.scalar(select(Alumno.id).where(Alumno.matricula == matricula)):
            error = "Ya existe un alumno con esa matrícula."
        error = error or _validar_asignacion(db, grupo_id, profesor_id)
    if error:
        return _form_registro(request, db, 400, error=error, d=d)

    u = Usuario(nombre=nombre.strip(), email=email, password_hash=hash_password(password), rol=rol)
    db.add(u)
    db.flush()
    if rol == ROL_ALUMNO:
        db.add(Alumno(
            usuario_id=u.id,
            matricula=matricula or f"DEMO{u.id:04d}",
            carrera=carrera.strip() or "Sin especificar",
            grupo_id=grupo_id or None,
            profesor_id=profesor_id or None,
        ))
    registrar(db, request, u, "registro_demo", f"usuario {u.id} rol {rol}")
    db.commit()

    request.session.clear()
    request.session["uid"] = u.id
    flash(request, f"Cuenta de prueba creada como «{ROLES_DEMO[rol]}». ¡Bienvenido!")
    return redirigir(INICIO[rol])


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return redirigir("/login")


@router.get("/cuenta/password")
def password_form(request: Request, usuario: Usuario = Depends(usuario_actual)):
    return render(request, "cuenta_password.html")


@router.post("/cuenta/password")
def password_cambiar(
    request: Request,
    actual: str = Form(...),
    nueva: str = Form(...),
    confirmar: str = Form(...),
    usuario: Usuario = Depends(usuario_actual),
    db: Session = Depends(get_db),
):
    error = None
    if not verificar_password(actual, usuario.password_hash):
        error = "La contraseña actual no es correcta."
    elif nueva != confirmar:
        error = "La confirmación no coincide."
    else:
        error = validar_password_nueva(nueva)
    if error:
        return render(request, "cuenta_password.html", 400, error=error)
    usuario.password_hash = hash_password(nueva)
    registrar(db, request, usuario, "cambio_password")
    db.commit()
    flash(request, "Contraseña actualizada.")
    return redirigir("/")
