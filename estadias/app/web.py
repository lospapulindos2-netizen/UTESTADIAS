"""Utilidades compartidas por las vistas: plantillas, mensajes flash y redirecciones."""
from fastapi import Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import BASE_DIR, settings
from app.models import ESTADOS, ROLES
from app.security import csrf_token

templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))
templates.env.globals.update(settings=settings, ESTADOS=ESTADOS, ROLES=ROLES)

COLOR_ESTADO = {
    "pendiente": "badge-gris",
    "en_revision": "badge-azul",
    "aprobado": "badge-verde",
    "correccion": "badge-ambar",
    "rechazado": "badge-rojo",
}
templates.env.globals["COLOR_ESTADO"] = COLOR_ESTADO

# Versión de css/js para que el navegador no use copias viejas tras un cambio
_static = BASE_DIR / "app" / "static"
templates.env.globals["VER"] = str(int(max(
    (_static / "css" / "app.css").stat().st_mtime, (_static / "js" / "app.js").stat().st_mtime
)))


def _fecha(valor, formato="%d/%m/%Y %H:%M"):
    return valor.strftime(formato) if valor else "—"


def _tamano(n: int) -> str:
    return f"{n / 1024 / 1024:.1f} MB" if n >= 1024 * 1024 else f"{max(1, n // 1024)} KB"


templates.env.filters.update(fecha=_fecha, tamano=_tamano)


def flash(request: Request, mensaje: str, tipo: str = "ok") -> None:
    request.session.setdefault("flash", []).append({"tipo": tipo, "msg": mensaje})


def render(request: Request, plantilla: str, status_code: int = 200, **contexto):
    contexto.setdefault("usuario", getattr(request.state, "usuario", None))
    contexto["csrf"] = csrf_token(request)
    contexto["mensajes"] = request.session.pop("flash", [])
    return templates.TemplateResponse(request, plantilla, contexto, status_code=status_code)


def redirigir(url: str) -> RedirectResponse:
    return RedirectResponse(url, status_code=303)
