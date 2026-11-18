"""Modelo de datos.

Decisiones 80/20:
- Rol como columna en `usuarios` (tres roles fijos, sin tabla de permisos).
- Cada alumno tiene un solo grupo y un solo profesor: columnas en `alumnos`.
- Cada fila de `entregas` / `proyecto_entregas` es una versión de archivo.
- Nada se borra físicamente: requisitos, grupos, categorías y usuarios se desactivan.
"""
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# --- Catálogos de valores -------------------------------------------------
ROL_ADMIN, ROL_PROFESOR, ROL_ALUMNO = "admin", "profesor", "alumno"
ROLES = {ROL_ADMIN: "Administrador", ROL_PROFESOR: "Profesor", ROL_ALUMNO: "Alumno"}

TIPO_GENERAL, TIPO_ESPECIFICO = "general", "especifico"

PENDIENTE = "pendiente"          # sin entrega (no se guarda, se calcula)
EN_REVISION = "en_revision"
APROBADO = "aprobado"
CORRECCION = "correccion"
RECHAZADO = "rechazado"          # solo proyectos
ESTADOS = {
    PENDIENTE: "Pendiente",
    EN_REVISION: "En revisión",
    APROBADO: "Aprobado",
    CORRECCION: "Requiere corrección",
    RECHAZADO: "Rechazado",
}


def ahora() -> datetime:
    return datetime.now().replace(microsecond=0)


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(150))
    email: Mapped[str] = mapped_column(String(190), unique=True)
    password_hash: Mapped[str] = mapped_column(String(100))
    rol: Mapped[str] = mapped_column(String(20), index=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=ahora)

    alumno: Mapped["Alumno | None"] = relationship(
        back_populates="usuario", foreign_keys="Alumno.usuario_id", uselist=False
    )
    alumnos_asignados: Mapped[list["Alumno"]] = relationship(
        back_populates="profesor", foreign_keys="Alumno.profesor_id"
    )

    __table_args__ = (CheckConstraint("rol IN ('admin','profesor','alumno')", name="ck_usuarios_rol"),)


class Grupo(Base):
    __tablename__ = "grupos"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), unique=True)
    descripcion: Mapped[str | None] = mapped_column(String(255))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)

    alumnos: Mapped[list["Alumno"]] = relationship(back_populates="grupo")


class Alumno(Base):
    __tablename__ = "alumnos"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), unique=True)
    matricula: Mapped[str] = mapped_column(String(30), unique=True)
    carrera: Mapped[str] = mapped_column(String(150))
    telefono: Mapped[str | None] = mapped_column(String(30))
    grupo_id: Mapped[int | None] = mapped_column(ForeignKey("grupos.id"), index=True)
    profesor_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), index=True)

    usuario: Mapped[Usuario] = relationship(back_populates="alumno", foreign_keys=[usuario_id])
    profesor: Mapped[Usuario | None] = relationship(
        back_populates="alumnos_asignados", foreign_keys=[profesor_id]
    )
    grupo: Mapped[Grupo | None] = relationship(back_populates="alumnos")
    entregas: Mapped[list["Entrega"]] = relationship(back_populates="alumno")
    proyecto_entregas: Mapped[list["ProyectoEntrega"]] = relationship(
        back_populates="alumno", order_by="ProyectoEntrega.version.desc()"
    )


class Categoria(Base):
    __tablename__ = "categorias"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), unique=True)
    orden: Mapped[int] = mapped_column(Integer, default=0)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)

    requisitos: Mapped[list["Requisito"]] = relationship(back_populates="categoria")


requisito_grupo = Table(
    "requisito_grupo",
    Base.metadata,
    Column("requisito_id", ForeignKey("requisitos.id"), primary_key=True),
    Column("grupo_id", ForeignKey("grupos.id"), primary_key=True),
)


class Requisito(Base):
    __tablename__ = "requisitos"

    id: Mapped[int] = mapped_column(primary_key=True)
    categoria_id: Mapped[int] = mapped_column(ForeignKey("categorias.id"), index=True)
    nombre: Mapped[str] = mapped_column(String(150))
    descripcion: Mapped[str | None] = mapped_column(String(500))
    tipo: Mapped[str] = mapped_column(String(20), default=TIPO_GENERAL)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=ahora)

    categoria: Mapped[Categoria] = relationship(back_populates="requisitos")
    grupos: Mapped[list[Grupo]] = relationship(secondary=requisito_grupo)

    __table_args__ = (
        CheckConstraint("tipo IN ('general','especifico')", name="ck_requisitos_tipo"),
    )


class Entrega(Base):
    """Una versión de archivo entregada por un alumno para un requisito."""

    __tablename__ = "entregas"

    id: Mapped[int] = mapped_column(primary_key=True)
    alumno_id: Mapped[int] = mapped_column(ForeignKey("alumnos.id"))
    requisito_id: Mapped[int] = mapped_column(ForeignKey("requisitos.id"))
    version: Mapped[int] = mapped_column(Integer)
    ruta: Mapped[str] = mapped_column(String(255))
    nombre_original: Mapped[str] = mapped_column(String(255))
    mime: Mapped[str] = mapped_column(String(50))
    tamano: Mapped[int] = mapped_column(Integer)
    estado: Mapped[str] = mapped_column(String(20), default=EN_REVISION, index=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=ahora)

    alumno: Mapped[Alumno] = relationship(back_populates="entregas")
    requisito: Mapped[Requisito] = relationship()
    revisiones: Mapped[list["Revision"]] = relationship(
        back_populates="entrega", order_by="Revision.id.desc()"
    )

    __table_args__ = (
        UniqueConstraint("alumno_id", "requisito_id", "version", name="uq_entrega_version"),
        Index("ix_entregas_alumno_requisito", "alumno_id", "requisito_id"),
        CheckConstraint(
            "estado IN ('en_revision','aprobado','correccion')", name="ck_entregas_estado"
        ),
    )


class ProyectoEntrega(Base):
    """Una versión del documento de proyecto de estadía."""

    __tablename__ = "proyecto_entregas"

    id: Mapped[int] = mapped_column(primary_key=True)
    alumno_id: Mapped[int] = mapped_column(ForeignKey("alumnos.id"))
    version: Mapped[int] = mapped_column(Integer)
    titulo: Mapped[str] = mapped_column(String(255))
    ruta: Mapped[str] = mapped_column(String(255))
    nombre_original: Mapped[str] = mapped_column(String(255))
    mime: Mapped[str] = mapped_column(String(50))
    tamano: Mapped[int] = mapped_column(Integer)
    estado: Mapped[str] = mapped_column(String(20), default=EN_REVISION, index=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=ahora)

    alumno: Mapped[Alumno] = relationship(back_populates="proyecto_entregas")
    revisiones: Mapped[list["Revision"]] = relationship(
        back_populates="proyecto_entrega", order_by="Revision.id.desc()"
    )

    __table_args__ = (
        UniqueConstraint("alumno_id", "version", name="uq_proyecto_version"),
        CheckConstraint(
            "estado IN ('en_revision','aprobado','correccion','rechazado')",
            name="ck_proyecto_estado",
        ),
    )


class Revision(Base):
    """Dictamen sobre una entrega (documento o proyecto) con su observación."""

    __tablename__ = "revisiones"

    id: Mapped[int] = mapped_column(primary_key=True)
    entrega_id: Mapped[int | None] = mapped_column(ForeignKey("entregas.id"), index=True)
    proyecto_entrega_id: Mapped[int | None] = mapped_column(
        ForeignKey("proyecto_entregas.id"), index=True
    )
    revisor_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    resultado: Mapped[str] = mapped_column(String(20))
    observacion: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=ahora)

    entrega: Mapped[Entrega | None] = relationship(back_populates="revisiones")
    proyecto_entrega: Mapped[ProyectoEntrega | None] = relationship(back_populates="revisiones")
    revisor: Mapped[Usuario] = relationship()

    __table_args__ = (
        # Exactamente una de las dos referencias
        CheckConstraint(
            "(entrega_id IS NULL) <> (proyecto_entrega_id IS NULL)", name="ck_revision_destino"
        ),
    )


class Bitacora(Base):
    __tablename__ = "bitacora"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), index=True)
    accion: Mapped[str] = mapped_column(String(60), index=True)
    detalle: Mapped[str | None] = mapped_column(String(500))
    ip: Mapped[str | None] = mapped_column(String(45))
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=ahora, index=True)

    usuario: Mapped[Usuario | None] = relationship()
