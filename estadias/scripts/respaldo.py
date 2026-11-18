"""Copia de seguridad: volcado de la base de datos + ZIP de los archivos privados.

Uso:  python -m scripts.respaldo
Programarlo a diario con el Programador de tareas de Windows (ver README).
"""
import subprocess
import zipfile
from datetime import datetime
from urllib.parse import unquote, urlparse

from app.config import settings


def main() -> None:
    marca = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino = settings.BACKUP_DIR
    destino.mkdir(parents=True, exist_ok=True)

    url = urlparse(settings.DATABASE_URL.replace("mysql+pymysql", "mysql"))
    sql = destino / f"bd_{marca}.sql"
    cmd = [
        settings.MYSQLDUMP,
        f"--host={url.hostname or '127.0.0.1'}",
        f"--port={url.port or 3306}",
        f"--user={unquote(url.username or 'root')}",
        "--single-transaction",
        "--routines",
        "--default-character-set=utf8mb4",
        url.path.lstrip("/"),
    ]
    entorno = None
    if url.password:
        import os

        entorno = {**os.environ, "MYSQL_PWD": unquote(url.password)}  # evita exponerla en la línea de comandos
    with open(sql, "wb") as f:
        subprocess.run(cmd, stdout=f, check=True, env=entorno)

    zip_path = destino / f"archivos_{marca}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        if settings.STORAGE_DIR.exists():
            for p in settings.STORAGE_DIR.rglob("*"):
                if p.is_file():
                    z.write(p, p.relative_to(settings.STORAGE_DIR))

    # Conservar solo los N respaldos más recientes de cada tipo
    for patron in ("bd_*.sql", "archivos_*.zip"):
        viejos = sorted(destino.glob(patron), reverse=True)[settings.BACKUP_CONSERVAR:]
        for v in viejos:
            v.unlink()
    print(f"Respaldo creado: {sql.name}, {zip_path.name}")


if __name__ == "__main__":
    main()
