@echo off
setlocal
cd /d "%~dp0"
title OpoAlert 0.5.2 - Historico de 30 dias con calendario oficial
if not exist ".venv\Scripts\python.exe" (
  echo ERROR: No existe el entorno Python .venv.
  echo Primero debes ejecutar PROBAR_LECTOR_BOP.bat.
  pause
  exit /b 1
)
if not exist "data\convocatorias.json" (
  echo ERROR: No existe data\convocatorias.json.
  echo Ejecuta antes PROBAR_LECTOR_BOP.bat.
  pause
  exit /b 1
)
echo ================================================
echo  OpoAlert 0.5.2 - Historico BOP Valencia
echo ================================================
echo.
echo [1/2] Validando 70 pruebas, incluyendo calendario oficial...
".venv\Scripts\python.exe" -m unittest discover -s backend\tests -q > "backend\pruebas_052.log" 2>&1
if errorlevel 1 (
  echo ERROR: Algunas pruebas no pasan. Mira backend\pruebas_052.log
  type "backend\pruebas_052.log"
  pause
  exit /b 1
)
echo Pruebas correctas.
echo.
echo [2/2] Consultando 30 dias usando solo fechas con boletin oficial...
copy /y "data\convocatorias.json" "data\convocatorias_antes_052.bak" >nul
".venv\Scripts\python.exe" -u backend\history.py --days 30 --window-days 5 --output data\convocatorias.json
if errorlevel 1 (
  echo.
  echo HISTORICO NO VALIDADO. JSON anterior conservado.
  echo Adjunta el error y backend\diagnostico_historico.json.
  pause
  exit /b 1
)
echo.
echo EXITO: Historico auditado y guardado en data\convocatorias.json
pause
exit /b 0
