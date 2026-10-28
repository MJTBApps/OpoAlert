$ErrorActionPreference = "Stop"
$version = "8.11.1"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$distributionDir = Join-Path $root ".gradle-dist"
$installed = Join-Path $distributionDir "gradle-$version\bin\gradle.bat"
if (Test-Path $installed) { exit 0 }

New-Item -ItemType Directory -Path $distributionDir -Force | Out-Null
$url = "https://services.gradle.org/distributions/gradle-$version-bin.zip"
$archive = Join-Path $env:TEMP "opoalert-gradle-$version-bin.zip"
Write-Host "Descargando Gradle $version de services.gradle.org (solo la primera vez)..."
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
Invoke-WebRequest -Uri $url -OutFile $archive -UseBasicParsing
Write-Host "Extrayendo Gradle..."
Expand-Archive -Path $archive -DestinationPath $distributionDir -Force
Remove-Item $archive -ErrorAction SilentlyContinue
if (-not (Test-Path $installed)) { throw "No se pudo instalar Gradle en $distributionDir" }
Write-Host "Gradle $version preparado correctamente."
