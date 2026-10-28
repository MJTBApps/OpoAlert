@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

rem Elegir Java 17 temporalmente, sin cambiar el Java de Windows.
for /d %%D in ("%ProgramFiles%\Eclipse Adoptium\jdk-17*") do set "JAVA_HOME=%%~fD"
if defined JAVA_HOME set "PATH=%JAVA_HOME%\bin;%PATH%"

echo.
echo ==========================================
echo       OPOALERT - COMPILADOR ANDROID
 echo ==========================================
echo.
java -version
if errorlevel 1 goto :error

rem Si ya existe local.properties, dejar la configuracion del usuario intacta.
if not exist "local.properties" (
    if not defined ANDROID_HOME set "ANDROID_HOME=%LOCALAPPDATA%\Android\Sdk"
    if not exist "!ANDROID_HOME!" (
        echo.
        echo ERROR: No se ha encontrado el SDK de Android.
        echo Revisa local.properties o ANDROID_HOME.
        goto :error
    )
    set "SDK_PATH=!ANDROID_HOME:\=/!"
    call :write_sdk
)

echo.
echo Compilando OpoAlert...
call "%~dp0gradlew.bat" assembleDebug
if errorlevel 1 goto :error

echo.
echo ==========================================
echo            APK GENERADO
 echo ==========================================
echo app\build\outputs\apk\debug\app-debug.apk
echo.
pause
exit /b 0

:write_sdk
> "local.properties" echo sdk.dir=%SDK_PATH%
exit /b 0

:error
echo.
echo No se ha completado la compilacion.
echo Copia las ultimas lineas del error y compartelas para corregirlo.
echo.
pause
exit /b 1
