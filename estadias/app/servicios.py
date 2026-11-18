"""Reglas de negocio: armado del expediente, avance y estadísticas."""
from dataclasses import dataclass, field

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    APROBADO,
    CORRECCION,
    EN_REVISION,
    PENDIENTE,
    TIPO_ESPECIFICO,
    TIPO_GENERAL,
    Alumno,
    Categoria,
    Entrega,
    ProyectoEntrega,
    Requisito,
    requisito_grupo,
)


@dataclass
class ItemExpediente:
    requisito: Requisito
    ultima: Entrega | None
    historial: list[Entrega] = field(default_factory=list)

    @property
    def estado(self) -> str:
        return self.ultima.estado if self.ultima else PENDIENTE

    @property
    def observacion(self) -> str | None:
        if self.ultima and self.ultima.revisiones:
            return self.ultima.revisiones[0].observacion
        return None


@dataclass
class Expediente:
    alumno: Alumno
    categorias: list[tuple[Categoria, list[ItemExpediente]]]
    historicos: list[Entrega]  # entregas de requisitos que ya no aplican

    @property
    def items(self) -> list[ItemExpediente]:
        return [i for _, items in self.categorias for i in items]

    def contar(self, estado: str) -> int:
        return sum(1 for i in self.items if i.estado == estado)

    @property
    def total(self) -> int:
        return len(self.items)

    @property
    def avance(self) -> int:
        return round(100 * self.contar(APROBADO) / self.total) if self.total else 0

    @property
    def completo(self) -> bool:
        return self.total > 0 and self.contar(APROBADO) == self.total


def requisitos_vigentes_query(grupo_id: int | None):
    """RN2: generales activos + específicos activos del grupo del alumno."""
    condicion = Requisito.tipo == TIPO_GENERAL
    if grupo_id:
        condicion = or_(
            condicion,
            (Requisito.tipo == TIPO_ESPECIFICO)
            & Requisito.id.in_(
                select(requisito_grupo.c.requisito_id).where(requisito_grupo.c.grupo_id == grupo_id)
            ),
        )
    return (
        select(Requisito)
        .join(Categoria)
        .where(Requisito.activo.is_(True), Categoria.activo.is_(True), condicion)
        .order_by(Categoria.orden, Categoria.nombre, Requisito.nombre)
        .options(selectinload(Requisito.categoria))
    )


def armar_expediente(db: Session, alumno: Alumno) -> Expediente:
    requisitos = db.scalars(requisitos_vigentes_query(alumno.grupo_id)).all()
    entregas = db.scalars(
        select(Entrega)
        .where(Entrega.alumno_id == alumno.id)
        .order_by(Entrega.version.desc())
        .options(selectinload(Entrega.revisiones), selectinload(Entrega.requisito))
    ).all()
    por_req: dict[int, list[Entrega]] = {}
    for e in entregas:
        por_req.setdefault(e.requisito_id, []).append(e)

    categorias: list[tuple[Categoria, list[ItemExpediente]]] = []
    vigentes = set()
    for r in requisitos:
        vigentes.add(r.id)
        hist = por_req.get(r.id, [])
        item = ItemExpediente(r, hist[0] if hist else None, hist)
        if categorias and categorias[-1][0].id == r.categoria_id:
            categorias[-1][1].append(item)
        else:
            categorias.append((r.categoria, [item]))
    historicos = [e for e in entregas if e.requisito_id not in vigentes]
    return Expediente(alumno, categorias, historicos)


def ultimas_entregas_subq():
    """Subconsulta con el id de la última versión por (alumno, requisito)."""
    return (
        select(func.max(Entrega.id).label("id"))
        .group_by(Entrega.alumno_id, Entrega.requisito_id)
        .subquery()
    )


def ultimo_proyecto(alumno: Alumno) -> ProyectoEntrega | None:
    return alumno.proyecto_entregas[0] if alumno.proyecto_entregas else None


def resumen_alumnos(db: Session, alumnos: list[Alumno]) -> dict[int, dict]:
    """Avance de varios alumnos con pocas consultas (para tablas y panel)."""
    reqs = db.scalars(
        select(Requisito)
        .join(Categoria)
        .where(Requisito.activo.is_(True), Categoria.activo.is_(True))
        .options(selectinload(Requisito.grupos))
    ).all()
    generales = {r.id for r in reqs if r.tipo == TIPO_GENERAL}
    por_grupo: dict[int, set[int]] = {}
    for r in reqs:
        if r.tipo == TIPO_ESPECIFICO:
            for g in r.grupos:
                por_grupo.setdefault(g.id, set()).add(r.id)

    ids = [a.id for a in alumnos]
    estados: dict[tuple[int, int], str] = {}
    if ids:
        sub = ultimas_entregas_subq()
        filas = db.execute(
            select(Entrega.alumno_id, Entrega.requisito_id, Entrega.estado).where(
                Entrega.id.in_(select(sub.c.id)), Entrega.alumno_id.in_(ids)
            )
        ).all()
        estados = {(f[0], f[1]): f[2] for f in filas}

    resultado = {}
    for a in alumnos:
        aplicables = generales | por_grupo.get(a.grupo_id or -1, set())
        conteo = {PENDIENTE: 0, EN_REVISION: 0, APROBADO: 0, CORRECCION: 0}
        for rid in aplicables:
            conteo[estados.get((a.id, rid), PENDIENTE)] += 1
        total = len(aplicables)
        resultado[a.id] = {
            "total": total,
            **conteo,
            "avance": round(100 * conteo[APROBADO] / total) if total else 0,
            "completo": total > 0 and conteo[APROBADO] == total,
        }
    return resultado
