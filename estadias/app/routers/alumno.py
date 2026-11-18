"""Portal del alumno: solo accede a su propio expediente y proyecto."""
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.archivos import ArchivoInvalido, guardar
from app.database import get_db
from app.models import APROBADO, CORRECCION, EN_REVISION, Alumno, Entrega, ProyectoEntrega, Usuario
from app.security import registrar, solo_alumno, verificar_csrf
from app.servicios import armar_expediente, requisitos_vigentes_query, ultimo_proyecto
from app.web import flash, redirigir, render

router = APIRouter(prefix="/alumno", dependencies=[Depends(verificar_csrf)])


def mi_alumno(usuario: Usuario = Depends(solo_alumno)) -> Alumno:
    if not usuario.alumno:
        raise HTTPException(403, "Tu cuenta no tiene expediente. Contacta al encargado de estadías.")
    return usuario.alumno


@router.get("")
def panel(request: Request, a: Alumno = Depends(mi_alumno), db: Session = Depends(get_db)):
    exp = armar_expediente(db, a)
    observaciones = []
    for item in exp.items:
        for e in item.historial[:1]:
            for rev in e.revisiones[:1]:
                if rev.observacion:
                    observaciones.append((item.requisito.nombre, rev))
    proyecto = ultimo_proyecto(a)
    if proyecto and proyecto.revisiones and proyecto.revisiones[0].observacion:
        observaciones.append(("Proyecto de estadía", proyecto.revisiones[0]))
    observaciones.sort(key=lambda x: x[1].creado_en, reverse=True)
    return render(request, "alumno/panel.html", a=a, exp=exp, proyecto=proyecto, observaciones=observaciones[:5])


@router.get("/expediente")
def expediente(request: Request, a: Alumno = Depends(mi_alumno), db: Session = Depends(get_db)):
    return render(request, "alumno/expediente.html", a=a, exp=armar_expediente(db, a))


@router.post("/requisitos/{req_id}/entregar")
async def entregar(
    request: Request,
    req_id: int,
    archivo: UploadFile = File(None),
    a: Alumno = Depends(mi_alumno),
    db: Session = Depends(get_db),
):
    # El requisito debe aplicar a este alumno (general o de su grupo) y estar activo
    ids_vigentes = {r.id for r in db.scalars(requisitos_vigentes_query(a.grupo_id)).all()}
    if req_id not in ids_vigentes:
        raise HTTPException(404, "Ese documento no forma parte de tu expediente.")
    ultima = db.scalar(
        select(Entrega).where(Entrega.alumno_id == a.id, Entrega.requisito_id == req_id).order_by(Entrega.version.desc()).limit(1)
    )
    if ultima and ultima.estado == APROBADO:
        flash(request, "Este documento ya fue aprobado; no es necesario volver a entregarlo.", "error")
        return redirigir("/alumno/expediente")
    try:
        g = await guardar(archivo, f"entregas/{a.id}")
    except ArchivoInvalido as ex:
        flash(request, str(ex), "error")
        return redirigir(f"/alumno/expediente#req-{req_id}")
    e = Entrega(
        alumno_id=a.id,
        requisito_id=req_id,
        version=(ultima.version + 1) if ultima else 1,
        ruta=g.ruta,
        nombre_original=g.nombre_original,
        mime=g.mime,
        tamano=g.tamano,
        estado=EN_REVISION,
    )
    db.add(e)
    db.flush()
    registrar(db, request, a.usuario, "documento_entregado", f"entrega {e.id} requisito {req_id} v{e.version}")
    db.commit()
    flash(request, f"Archivo recibido (versión {e.version}). Quedó «En revisión».")
    return redirigir(f"/alumno/expediente#req-{req_id}")


@router.get("/proyecto")
def proyecto(request: Request, a: Alumno = Depends(mi_alumno)):
    return render(request, "alumno/proyecto.html", a=a, actual=ultimo_proyecto(a), historial=a.proyecto_entregas)


@router.post("/proyecto/entregar")
async def proyecto_entregar(
    request: Request,
    titulo: str = Form(""),
    archivo: UploadFile = File(None),
    a: Alumno = Depends(mi_alumno),
    db: Session = Depends(get_db),
):
    if not a.profesor_id:
        flash(request, "Aún no tienes un profesor asignado. Contacta al encargado de estadías.", "error")
        return redirigir("/alumno/proyecto")
    actual = ultimo_proyecto(a)
    if actual and actual.estado == APROBADO:
        flash(request, "Tu proyecto ya fue aprobado.", "error")
        return redirigir("/alumno/proyecto")
    titulo = titulo.strip() or (actual.titulo if actual else "")
    if not titulo:
        flash(request, "Escribe el título de tu proyecto.", "error")
        return redirigir("/alumno/proyecto")
    try:
        g = await guardar(archivo, f"proyectos/{a.id}")
    except ArchivoInvalido as ex:
        flash(request, str(ex), "error")
        return redirigir("/alumno/proyecto")
    version = (db.scalar(select(func.max(ProyectoEntrega.version)).where(ProyectoEntrega.alumno_id == a.id)) or 0) + 1
    p = ProyectoEntrega(
        alumno_id=a.id, version=version, titulo=titulo[:255], ruta=g.ruta,
        nombre_original=g.nombre_original, mime=g.mime, tamano=g.tamano, estado=EN_REVISION,
    )
    db.add(p)
    db.flush()
    registrar(db, request, a.usuario, "proyecto_entregado", f"proyecto {p.id} v{version}")
    db.commit()
    flash(request, f"Proyecto entregado (versión {version}). Tu profesor lo revisará.")
    return redirigir("/alumno/proyecto")
