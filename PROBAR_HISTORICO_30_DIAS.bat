@echo off
setlocal
cd /d "%~dp0"
echo.
echo ===============================================
echo   OpoAlert 0.4 - Historico de 30 dias BOP
 echo ===============================================
echo.
if not exist ".venv\Scripts\python.exe" (
    echo ERROR: Primero ejecuta PROBAR_LECTOR_BOP.bat para instalar Python y Playwright.
    pause
    exit /b 1
)
if not exist "data\convocatorias.json" (
    echo ERROR: Falta data\convocatorias.json. Primero ejecuta PROBAR_LECTOR_BOP.bat.
    pause
    exit /b 1
)
copy /y "data\convocatorias.json" "data\convocatorias_antes_historico.bak" >nul
".venv\Scripts\python.exe" backend\history.py --days 30 --output data\convocatorias.json
if errorlevel 1 (
    echo.
    echo No se ha validado el historico. Se conserva el JSON anterior.
    echo Si falla, envianos backend\diagnostico_historico.json y el error.
    pause
    exit /b 1
)
echo.
echo HISTORICO RECUPERADO Y AUDITADO. Consulta data\convocatorias.json.
pause
