from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import BASE_DIR, settings
from app.routers import admin, alumno, archivos, auth, profesor
from app.security import NoAutenticado
from app.web import redirigir, render

app = FastAPI(title=settings.APP_NOMBRE, docs_url=None, redoc_url=None, openapi_url=None)


@app.middleware("http")
async def cabeceras_seguridad(request: Request, call_next):
    resp = await call_next(request)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "SAMEORIGIN"
    resp.headers["Referrer-Policy"] = "same-origin"
    resp.headers["Content-Security-Policy"] = (
        "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; "
        "frame-src 'self'; frame-ancestors 'self'; object-src 'none'; base-uri 'self'; form-action 'self'"
    )
    if request.url.path.startswith(("/admin", "/alumno", "/profesor", "/archivos", "/cuenta")):
        resp.headers["Cache-Control"] = "no-store"
    return resp


# Va después para quedar por fuera: la sesión ya está disponible en el middleware anterior
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    session_cookie="estadias_sesion",
    max_age=settings.SESION_HORAS * 3600,
    same_site="lax",
    https_only=settings.COOKIE_SEGURA,
)

app.mount("/static", StaticFiles(directory=BASE_DIR / "app" / "static"), name="static")

for r in (auth.router, admin.router, alumno.router, profesor.router, archivos.router):
    app.include_router(r)


@app.exception_handler(NoAutenticado)
async def _no_autenticado(request: Request, exc: NoAutenticado):
    return redirigir("/login")


@app.exception_handler(HTTPException)
async def _http_error(request: Request, exc: HTTPException):
    titulos = {403: "Acceso denegado", 404: "No encontrado"}
    return render(
        request,
        "error.html",
        status_code=exc.status_code,
        titulo=titulos.get(exc.status_code, "Error"),
        detalle=exc.detail,
    )


@app.exception_handler(404)
async def _404(request: Request, exc):
    return render(request, "error.html", status_code=404, titulo="No encontrado", detalle="La página no existe.")
