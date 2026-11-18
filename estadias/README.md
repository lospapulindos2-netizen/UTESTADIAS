# Plataforma de Gestión de Estadías

Aplicación web para recibir, organizar y revisar los documentos de estadía de alumnos foráneos, más un módulo independiente para entregar y revisar el proyecto de estadía.

**Tecnologías:** Python 3.12+ · FastAPI · Jinja2 · SQLAlchemy 2 · Alembic · MySQL/MariaDB · Tailwind CSS 3 · JavaScript sin frameworks.
Es un monolito modular: una sola aplicación, una base de datos y un sistema de autenticación.

---

## 1. Requisitos

| Software | Versión probada | Notas |
|---|---|---|
| Python | 3.14 (sirve ≥ 3.12) | |
| MySQL o MariaDB | MariaDB 10.4 (XAMPP) | |
| Node.js | 24 | Solo para recompilar los estilos (`app.css` ya viene compilado) |

## 2. Instalación

```bash
cd estadias
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt
```

1. Inicia MySQL/MariaDB (en XAMPP: botón **Start** de MySQL).
2. Crea la base de datos:
   ```bash
   C:\xampp\mysql\bin\mysql.exe -u root -e "CREATE DATABASE estadias CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
   ```
3. Copia `.env.example` como `.env` y define `SECRET_KEY`:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```
   Ajusta también `DATABASE_URL` si MySQL tiene contraseña, y `INSTITUCION` con el nombre de la universidad.
4. Crea las tablas (migraciones):
   ```bash
   alembic upgrade head
   ```
5. (Opcional) Carga los datos de prueba:
   ```bash
   python -m scripts.semilla
   ```

## 3. Ejecución

**Forma fácil (Windows):** doble clic en `iniciar.bat`. Enciende MySQL de XAMPP si está apagado, arranca el servidor y abre el navegador. Deja la ventana abierta mientras uses la plataforma.

**Desde una terminal**, siempre dentro de la carpeta `estadias`:

```bash
cd C:\SKUL\AUTOMATIZACIÓN\estadias
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Abre <http://127.0.0.1:8000>. Para desarrollo agrega `--reload`.

**Producción (resumen):** usar HTTPS detrás de un proxy (Nginx/IIS), `COOKIE_SEGURA=true`, un usuario de MySQL con contraseña y permisos solo sobre la BD `estadias`, y varios workers: `uvicorn app.main:app --workers 4`.
El bloqueo por intentos fallidos se guarda en memoria de cada proceso, así que con varios workers el límite efectivo se multiplica.

## 4. Modo demostración (crear cuentas de prueba)

Con `MODO_DEMO=true` en `.env`, la pantalla de inicio muestra el botón **«Crear cuenta de prueba»**. Ahí cualquiera elige si quiere ser **Alumno**, **Profesor** o **Revisor** (encargado de estadías, con permisos de administrador) y entra directamente.
Si eliges Alumno, también puedes indicar grupo y profesor.

> ⚠️ El modo demostración contradice el requisito «sin registro público» y deja que cualquiera se haga administrador. Úsalo solo para probar. **Pon `MODO_DEMO=false` y reinicia el servidor antes de entregar o de usar datos reales.** Con `false` (el valor por defecto), la ruta `/registro` no existe.

## 5. Usuarios de prueba

Los crea `python -m scripts.semilla` (solo para pruebas locales; cámbialos o desactívalos en producción).

| Rol | Correo | Contraseña |
|---|---|---|
| Administrador | admin@estadias.test | Admin2026 |
| Profesor 1 (asesora a A0001 y A0002) | profesor1@estadias.test | Profesor2026 |
| Profesor 2 (asesora a B0001) | profesor2@estadias.test | Profesor2026 |
| Alumno Grupo A (con entregas de ejemplo) | alumno1@estadias.test | Alumno2026 |
| Alumno Grupo A | alumno2@estadias.test | Alumno2026 |
| Alumno Grupo B | alumno3@estadias.test | Alumno2026 |
| Alumno Grupo C (sin profesor) | alumno4@estadias.test | Alumno2026 |

## 6. Pruebas

```bash
python -m pytest -v
```

Las pruebas usan SQLite y una carpeta temporal, así que no tocan la base MySQL. Cubren los 15 criterios de aceptación y además CSRF, bloqueo por intentos, cuentas desactivadas, cabeceras de seguridad, renovación de sesión y bitácora.
La evidencia de la última ejecución está en `../docs/evidencia-pruebas.txt`.

## 7. Respaldos

```bash
python -m scripts.respaldo
```

Genera `respaldos/bd_FECHA.sql` (mysqldump) y `respaldos/archivos_FECHA.zip` (los documentos), y conserva los últimos `BACKUP_CONSERVAR`.
Para programarlo a diario en Windows:

```bash
schtasks /Create /SC DAILY /ST 23:00 /TN "Respaldo estadias" /TR "\"C:\ruta\estadias\.venv\Scripts\python.exe\" -m scripts.respaldo" /F
```

(En la tarea, configura «Iniciar en» con la carpeta `estadias`.) Copia la carpeta `respaldos` a otro disco o equipo periódicamente.

## 8. Estructura

```
estadias/
├─ app/
│  ├─ main.py          # aplicación, middlewares de seguridad, manejo de errores
│  ├─ config.py        # configuración desde .env
│  ├─ database.py      # conexión SQLAlchemy
│  ├─ models.py        # modelo de datos (10 tablas + tabla puente)
│  ├─ security.py      # bcrypt, sesión, CSRF, roles, bitácora
│  ├─ archivos.py      # validación y almacenamiento privado
│  ├─ servicios.py     # reglas de negocio (armado de expedientes, avance)
│  ├─ web.py           # plantillas, mensajes, utilidades
│  ├─ routers/         # auth, admin, alumno, profesor, archivos
│  ├─ templates/       # vistas Jinja2 por rol
│  └─ static/          # css (Tailwind compilado), js, imágenes
├─ alembic/            # migraciones
├─ scripts/            # semilla.py (datos de prueba), respaldo.py
├─ tests/              # pruebas automáticas
└─ storage/privado/    # archivos subidos (NO público; se crea solo)
```

Para recompilar los estilos después de cambiar las plantillas:

```bash
npx tailwindcss@3.4.17 -i app/static/css/entrada.css -o app/static/css/app.css --minify
```

## 9. Seguridad implementada

- Contraseñas con **bcrypt** (12 rondas). No hay registro público: solo el administrador crea cuentas.
- Sesión firmada con cookie `HttpOnly` y `SameSite=Lax` (y `Secure` con `COOKIE_SEGURA=true`). Se renueva al iniciar sesión y expira a las 8 h.
- **CSRF**: todos los formularios POST llevan un token de la sesión.
- **Control de acceso por rol** en cada ruta. Además, cada alumno solo puede ver lo suyo y cada profesor solo a sus alumnos asignados.
- Bloqueo temporal tras 5 intentos fallidos de inicio de sesión.
- **Archivos**:
  - Se guardan en `storage/privado`, fuera de `static`, con un nombre interno aleatorio (UUID).
  - Solo se aceptan PDF, JPG y PNG. Se revisan la extensión y la **firma real del contenido**.
  - Límite de 10 MB.
  - Se rechazan los PDF con JavaScript, acciones `/Launch` o archivos incrustados.
  - Solo se sirven por `/archivos/...`, que verifica los permisos antes de entregarlos.
- Cabeceras de seguridad: CSP estricta (sin scripts inline), `X-Frame-Options`, `nosniff`, `Referrer-Policy` y `no-store` en las páginas privadas.
- **Bitácora** de inicios de sesión, revisiones, altas, cambios, asignaciones y descargas.
- **Nada se borra**: usuarios, grupos, categorías y requisitos se desactivan. Cada entrega es una versión nueva y el historial se conserva.

**Limitación conocida:** la revisión de PDFs es heurística. Si un PDF esconde código en flujos comprimidos, no se detecta. Para producción se recomienda añadir un antivirus como ClamAV (está en las mejoras futuras).
