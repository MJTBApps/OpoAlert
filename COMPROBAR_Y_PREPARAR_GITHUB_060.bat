@echo off
setlocal
cd /d "%~dp0"
title OpoAlert 0.6 - Preparar publicacion GitHub
if not exist ".venv\Scripts\python.exe" (
  echo No se encuentra el Python de OpoAlert.
  echo Ejecuta antes PROBAR_LECTOR_BOP.bat para preparar el entorno.
  pause
  exit /b 1
)
if not exist "data\convocatorias.json" (
  echo Falta data\convocatorias.json.
  echo Hay un feed inicial validado en docs\convocatorias.json.
  echo Si quieres usar tu archivo local, copialo primero a data\convocatorias.json.
  pause
  exit /b 1
)
echo ================================================
echo  OpoAlert 0.6 - Preparar feed GitHub
echo ================================================
echo.
echo [1/4] Comprobando las pruebas del proyecto...
".venv\Scripts\python.exe" -m unittest discover -s backend\tests -q > "backend\pruebas_060.log" 2>&1
if errorlevel 1 (
  echo Pruebas fallidas. Abre backend\pruebas_060.log.
  type "backend\pruebas_060.log"
  pause
  exit /b 1
)
echo.
echo [2/4] Validando tu historico real de 30 dias...
".venv\Scripts\python.exe" backend\validar_feed.py --input data\convocatorias.json
if errorlevel 1 (
  echo El JSON local no es publicable. No se ha tocado docs\convocatorias.json.
  pause
  exit /b 1
)
echo.
echo [3/4] Preparando el feed publico...
".venv\Scripts\python.exe" backend\publicar_feed.py --input data\convocatorias.json --output docs\convocatorias.json --require-history
if errorlevel 1 (
  echo Error al preparar el archivo. No publiques el feed.
  pause
  exit /b 1
)
echo.
echo [4/4] Validando la copia que se va a publicar...
".venv\Scripts\python.exe" backend\validar_feed.py --input docs\convocatorias.json
if errorlevel 1 (
  echo Archivo publico no validado. No lo subas.
  pause
  exit /b 1
)
echo.
echo CORRECTO: docs\convocatorias.json esta listo para GitHub.
echo Lee INSTRUCCIONES_GITHUB_060.txt para conectarlo y publicarlo.
pause
exit /b 0
