@echo off
rem Inicia la plataforma de estadias: enciende MySQL de XAMPP si hace falta,
rem arranca el servidor y abre el navegador. Se puede ejecutar con doble clic.
chcp 65001 >nul
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] No existe el entorno virtual .venv en esta carpeta.
  echo Sigue la seccion "Instalacion" del README.md
  pause
  exit /b 1
)

rem 1. MySQL / MariaDB
call :puerto 3306
if errorlevel 1 (
  if exist "C:\xampp\mysql\bin\mysqld.exe" (
    echo Iniciando MySQL de XAMPP...
    start "" /min "C:\xampp\mysql\bin\mysqld.exe" --defaults-file=C:\xampp\mysql\bin\my.ini --standalone
    timeout /t 5 /nobreak >nul
  ) else (
    echo [ERROR] MySQL no esta encendido. Inicialo desde el panel de XAMPP.
    pause
    exit /b 1
  )
)

rem 2. Puerto 8000 libre
call :puerto 8000
if not errorlevel 1 (
  echo La plataforma ya esta corriendo. Abriendo el navegador...
  start "" http://127.0.0.1:8000
  exit /b 0
)

rem 3. Servidor + navegador
echo.
echo  Plataforma de estadias en http://127.0.0.1:8000
echo  Deja esta ventana abierta. Para detener el servidor: Ctrl+C
echo.
start "" cmd /c "timeout /t 3 /nobreak >nul & start http://127.0.0.1:8000"
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pause
exit /b 0

rem Devuelve 0 si el puerto local esta abierto, 1 si no (espera maximo 1 s)
:puerto
powershell -NoProfile -Command "$c = New-Object Net.Sockets.TcpClient; try { $ok = $c.ConnectAsync('127.0.0.1', %1).Wait(1000) } catch { $ok = $false }; $c.Close(); if ($ok) { exit 0 } else { exit 1 }"
exit /b %errorlevel%
