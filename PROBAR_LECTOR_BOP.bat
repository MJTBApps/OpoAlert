@echo off
setlocal
cd /d "%~dp0"
echo.
echo ==============================================
echo    OpoAlert - Auditoria de todo el BOP Valencia
echo ==============================================
echo.
where py >nul 2>&1
if not errorlevel 1 (
    set "PYRUN=py -3"
) else (
    where python >nul 2>&1
    if errorlevel 1 (
        echo ERROR: Falta Python 3. Instalalo antes de continuar.
        echo Comando opcional: winget install --id Python.Python.3.13 -e
        pause
        exit /b 1
    )
    set "PYRUN=python"
)
if not exist .venv\Scripts\python.exe (
    echo Preparando entorno Python local...
    %PYRUN% -m venv .venv || goto :error
)
call .venv\Scripts\activate.bat || goto :error
echo Instalando dependencias de lectura...
python -m pip install -r backend\requirements.txt || goto :error
echo Preparando navegador Chromium para lectura automatica...
python -m playwright install chromium || goto :error
echo Ejecutando pruebas...
python -m unittest discover -s backend\tests -v || goto :error
echo.
echo Consultando el BOP real. No cierres esta ventana.
python backend\bop_full.py --output data\convocatorias.json || goto :error
echo.
echo OK. Revisa data\convocatorias.json, apartado coverage.
pause
exit /b 0
:error
echo.
echo ATENCION: No se ha confirmado cobertura del boletin completo.
echo Si se creo, mira backend\diagnostico_bop.html y backend\diagnostico_bop.png.
echo No publicar datos sin verificar.
pause
exit /b 1
