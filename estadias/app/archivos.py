"""Validación y almacenamiento privado de archivos."""
import uuid
from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile

from app.config import settings

# extensión -> (MIME, firma de bytes al inicio del archivo)
PERMITIDOS: dict[str, tuple[str, tuple[bytes, ...]]] = {
    ".pdf": ("application/pdf", (b"%PDF-",)),
    ".png": ("image/png", (b"\x89PNG\r\n\x1a\n",)),
    ".jpg": ("image/jpeg", (b"\xff\xd8\xff",)),
    ".jpeg": ("image/jpeg", (b"\xff\xd8\xff",)),
}
# Acciones de PDF que pueden ejecutar código o incrustar otros archivos
PDF_PELIGROSO = (b"/JavaScript", b"/JS ", b"/JS(", b"/Launch", b"/EmbeddedFile", b"/OpenAction /JS")


class ArchivoInvalido(ValueError):
    pass


@dataclass
class ArchivoGuardado:
    ruta: str  # relativa a STORAGE_DIR
    nombre_original: str
    mime: str
    tamano: int


def _nombre_limpio(nombre: str) -> str:
    nombre = Path(nombre or "archivo").name
    return "".join(c for c in nombre if c.isprintable() and c not in '<>:"/\\|?*')[:200] or "archivo"


async def guardar(upload: UploadFile, subcarpeta: str) -> ArchivoGuardado:
    if upload is None or not upload.filename:
        raise ArchivoInvalido("Selecciona un archivo.")
    nombre = _nombre_limpio(upload.filename)
    ext = Path(nombre).suffix.lower()
    if ext not in PERMITIDOS:
        raise ArchivoInvalido("Formato no permitido. Solo PDF, JPG o PNG.")

    limite = settings.MAX_MB * 1024 * 1024
    datos = await upload.read(limite + 1)
    if len(datos) > limite:
        raise ArchivoInvalido(f"El archivo supera el límite de {settings.MAX_MB} MB.")
    if not datos:
        raise ArchivoInvalido("El archivo está vacío.")

    mime, firmas = PERMITIDOS[ext]
    if not datos.startswith(firmas):
        raise ArchivoInvalido("El contenido del archivo no corresponde a su extensión.")
    if ext == ".pdf" and any(p in datos for p in PDF_PELIGROSO):
        raise ArchivoInvalido("El PDF contiene elementos activos (JavaScript o archivos incrustados) y no se acepta.")

    # Nombre interno aleatorio: el nombre original solo se guarda en la BD
    ruta_rel = Path(subcarpeta) / f"{uuid.uuid4().hex}{'.jpg' if ext == '.jpeg' else ext}"
    destino = settings.STORAGE_DIR / ruta_rel
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(datos)
    return ArchivoGuardado(ruta_rel.as_posix(), nombre, mime, len(datos))


def ruta_absoluta(ruta_rel: str) -> Path:
    base = settings.STORAGE_DIR.resolve()
    destino = (base / ruta_rel).resolve()
    if base not in destino.parents:
        raise ArchivoInvalido("Ruta fuera del almacenamiento privado.")
    return destino
