@echo off
setlocal
set "ROOT=%~dp0"
if not exist "%ROOT%.gradle-dist\gradle-8.11.1\bin\gradle.bat" (
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%ROOT%scripts\bootstrap-gradle.ps1"
  if errorlevel 1 (
    echo ERROR: No se ha podido preparar Gradle.
    exit /b 1
  )
)
call "%ROOT%.gradle-dist\gradle-8.11.1\bin\gradle.bat" %*
exit /b %errorlevel%
