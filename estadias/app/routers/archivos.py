"""Única puerta de salida de archivos: verifica permisos antes de entregar el contenido."""
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.archivos import ArchivoInvalido, ruta_absoluta
from app.database import get_db
from app.models import ROL_ADMIN, ROL_ALUMNO, ROL_PROFESOR, Entrega, ProyectoEntrega, Usuario
from app.security import registrar, usuario_actual

router = APIRouter(prefix="/archivos")


def _responder(request: Request, db: Session, usuario: Usuario, obj, descargar: int):
    try:
        ruta = ruta_absoluta(obj.ruta)
    except ArchivoInvalido:
        raise HTTPException(404, "Archivo no disponible.")
    if not ruta.is_file():
        raise HTTPException(404, "El archivo no se encuentra en el servidor.")
    if descargar:
        registrar(db, request, usuario, "archivo_descargado", f"{type(obj).__name__} {obj.id}")
        db.commit()
    disposicion = "attachment" if descargar else "inline"
    resp = FileResponse(ruta, media_type=obj.mime)
    resp.headers["Content-Disposition"] = f"{disposicion}; filename*=UTF-8''{quote(obj.nombre_original)}"
    return resp


@router.get("/entrega/{entrega_id}")
def entrega(request: Request, entrega_id: int, descargar: int = 0, usuario: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    e = db.get(Entrega, entrega_id)
    permitido = e is not None and (
        usuario.rol == ROL_ADMIN
        or (usuario.rol == ROL_ALUMNO and usuario.alumno is not None and e.alumno_id == usuario.alumno.id)
    )
    if not permitido:
        raise HTTPException(404, "Archivo no encontrado.")
    return _responder(request, db, usuario, e, descargar)


@router.get("/proyecto/{proyecto_id}")
def proyecto(request: Request, proyecto_id: int, descargar: int = 0, usuario: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    p = db.get(ProyectoEntrega, proyecto_id)
    permitido = p is not None and (
        usuario.rol == ROL_ADMIN
        or (usuario.rol == ROL_ALUMNO and usuario.alumno is not None and p.alumno_id == usuario.alumno.id)
        or (usuario.rol == ROL_PROFESOR and p.alumno.profesor_id == usuario.id)
    )
    if not permitido:
        raise HTTPException(404, "Archivo no encontrado.")
    return _responder(request, db, usuario, p, descargar)
