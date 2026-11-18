"""Panel del profesor: solo alumnos que el administrador le asignó."""
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import APROBADO, CORRECCION, EN_REVISION, RECHAZADO, Alumno, ProyectoEntrega, Revision, Usuario
from app.security import registrar, solo_profesor, verificar_csrf
from app.servicios import ultimo_proyecto
from app.web import flash, redirigir, render

router = APIRouter(prefix="/profesor", dependencies=[Depends(verificar_csrf)])


def _alumno_asignado(db: Session, profesor: Usuario, alumno_id: int) -> Alumno:
    a = db.get(Alumno, alumno_id)
    # 404 en vez de 403 para no revelar qué alumnos existen
    if not a or a.profesor_id != profesor.id:
        raise HTTPException(404, "Alumno no encontrado entre tus asignados.")
    return a


@router.get("")
def panel(request: Request, estado: str = "", profesor: Usuario = Depends(solo_profesor), db: Session = Depends(get_db)):
    alumnos = db.scalars(
        select(Alumno)
        .join(Usuario, Alumno.usuario_id == Usuario.id)
        .where(Alumno.profesor_id == profesor.id, Usuario.activo.is_(True))
        .options(selectinload(Alumno.usuario), selectinload(Alumno.grupo), selectinload(Alumno.proyecto_entregas))
        .order_by(Usuario.nombre)
    ).all()
    filas = [(a, ultimo_proyecto(a)) for a in alumnos]
    conteo = {k: sum(1 for _, p in filas if p and p.estado == k) for k in (EN_REVISION, APROBADO, CORRECCION, RECHAZADO)}
    conteo["sin_entrega"] = sum(1 for _, p in filas if not p)
    if estado == "sin_entrega":
        filas = [f for f in filas if not f[1]]
    elif estado:
        filas = [f for f in filas if f[1] and f[1].estado == estado]
    # Los pendientes de revisión primero
    filas.sort(key=lambda f: (0 if f[1] and f[1].estado == EN_REVISION else 1))
    return render(request, "profesor/panel.html", filas=filas, conteo=conteo, total=len(alumnos), estado=estado)


@router.get("/alumnos/{alumno_id}")
def alumno(request: Request, alumno_id: int, profesor: Usuario = Depends(solo_profesor), db: Session = Depends(get_db)):
    a = _alumno_asignado(db, profesor, alumno_id)
    historial = db.scalars(
        select(ProyectoEntrega)
        .where(ProyectoEntrega.alumno_id == a.id)
        .order_by(ProyectoEntrega.version.desc())
        .options(selectinload(ProyectoEntrega.revisiones).selectinload(Revision.revisor))
    ).all()
    return render(request, "profesor/alumno.html", a=a, historial=historial, actual=historial[0] if historial else None)


@router.post("/proyectos/{proyecto_id}/revisar")
def revisar(
    request: Request,
    proyecto_id: int,
    resultado: str = Form(...),
    observacion: str = Form(""),
    profesor: Usuario = Depends(solo_profesor),
    db: Session = Depends(get_db),
):
    p = db.get(ProyectoEntrega, proyecto_id)
    if not p:
        raise HTTPException(404, "Entrega no encontrada.")
    a = _alumno_asignado(db, profesor, p.alumno_id)
    ultima = db.scalar(select(func.max(ProyectoEntrega.version)).where(ProyectoEntrega.alumno_id == a.id))
    if p.version != ultima:
        flash(request, "Solo se puede dictaminar la versión más reciente.", "error")
        return redirigir(f"/profesor/alumnos/{a.id}")
    if resultado not in (APROBADO, CORRECCION, RECHAZADO):
        raise HTTPException(400, "Resultado no válido.")
    observacion = observacion.strip()
    if resultado != APROBADO and not observacion:
        flash(request, "Escribe una observación para el alumno.", "error")
        return redirigir(f"/profesor/alumnos/{a.id}")
    p.estado = resultado
    db.add(Revision(proyecto_entrega_id=p.id, revisor_id=profesor.id, resultado=resultado, observacion=observacion or None))
    registrar(db, request, profesor, f"proyecto_{resultado}", f"proyecto {p.id} alumno {a.id}")
    db.commit()
    flash(request, "Revisión guardada.")
    return redirigir(f"/profesor/alumnos/{a.id}")
