"""Configuración leída de variables de entorno (archivo .env)."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _bool(nombre: str, defecto: bool) -> bool:
    return os.getenv(nombre, str(defecto)).strip().lower() in {"1", "true", "si", "sí", "yes"}


def _ruta(nombre: str, defecto: str) -> Path:
    p = Path(os.getenv(nombre, defecto))
    return p if p.is_absolute() else BASE_DIR / p


class Settings:
    APP_NOMBRE: str = os.getenv("APP_NOMBRE", "Gestión de Estadías")
    INSTITUCION: str = os.getenv("INSTITUCION", "[Nombre de la universidad]")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://root:@127.0.0.1:3306/estadias?charset=utf8mb4",
    )
    # Carpeta privada para archivos: NUNCA debe estar dentro de app/static
    STORAGE_DIR: Path = _ruta("STORAGE_DIR", "storage/privado")
    MAX_MB: int = int(os.getenv("MAX_MB", "10"))
    # Cookie de sesión solo por HTTPS (activar en producción)
    COOKIE_SEGURA: bool = _bool("COOKIE_SEGURA", False)
    SESION_HORAS: int = int(os.getenv("SESION_HORAS", "8"))
    # Solo para pruebas: permite que cualquiera cree su cuenta (alumno, profesor o revisor)
    # desde la pantalla de inicio. Apagarlo (false) antes de usar datos reales.
    MODO_DEMO: bool = _bool("MODO_DEMO", False)
    # Respaldos
    MYSQLDUMP: str = os.getenv("MYSQLDUMP", r"C:\xampp\mysql\bin\mysqldump.exe")
    BACKUP_DIR: Path = _ruta("BACKUP_DIR", "respaldos")
    BACKUP_CONSERVAR: int = int(os.getenv("BACKUP_CONSERVAR", "14"))


settings = Settings()

if not settings.SECRET_KEY:
    raise RuntimeError(
        "Falta SECRET_KEY en .env. Genera una con: "
        "python -c \"import secrets; print(secrets.token_urlsafe(48))\""
    )
