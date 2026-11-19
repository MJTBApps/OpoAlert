#!/bin/bash
# Archiva la app de iOS y la sube a App Store Connect (TestFlight).
# Lo usan GitHub Actions (ios-testflight.yml) y Codemagic (codemagic.yaml).
# Variables: TEAM_ID, BUILD_NUM, ASC_KEY_ID, ASC_ISSUER_ID, ASC_KEY_P8 y, opcionales,
# ADMOB_IOS_* y FIREBASE_*. La clave solo se escribe en una carpeta temporal y se borra.
set -euo pipefail
cd "$(dirname "$0")/../ios"
: "${TEAM_ID:=6QLP74LVPC}"
# Número de compilación por fecha y hora (UTC), p. ej. 261119.1030: siempre crece,
# compile GitHub o Codemagic, y es mayor que los antiguos (1, 2… 27).
: "${BUILD_NUM:=$(date -u +%y%m%d.%H%M)}"
for name in ASC_KEY_ID ASC_ISSUER_ID ASC_KEY_P8; do
  if [ -z "${!name:-}" ]; then echo "ERROR: falta $name"; exit 1; fi
done
case "$ASC_KEY_P8" in
  *"BEGIN PRIVATE KEY"*"END PRIVATE KEY"*) ;;
  *) echo "ERROR: ASC_KEY_P8 no parece un archivo .p8 completo"; exit 1;;
esac
for v in ADMOB_IOS_APP_ID ADMOB_IOS_BANNER ADMOB_IOS_OPEN_AD ADMOB_IOS_INTERSTITIAL \
         FIREBASE_IOS_APP_ID FIREBASE_IOS_API_KEY FIREBASE_IOS_SENDER_ID FIREBASE_PROJECT_ID; do
  export "$v=${!v:-}"
done
KEY_DIR="$(mktemp -d)"
trap 'rm -rf "$KEY_DIR"' EXIT
printf '%s\n' "$ASC_KEY_P8" > "$KEY_DIR/AuthKey_$ASC_KEY_ID.p8"
chmod 600 "$KEY_DIR/AuthKey_$ASC_KEY_ID.p8"

command -v xcodegen >/dev/null || brew install xcodegen
xcodegen generate

set -o pipefail
# Un identificador de AdMob mal pegado cierra la app al abrirla (19/11/2026,
# primera compilación de Codemagic): se comprueba la forma y no se compila si falla.
check_admob() {  # nombre, patrón
  local v="${!1}"
  [ -z "$v" ] && return 0
  echo "$v" | grep -Eqx "$2" || { echo "ERROR: $1 no tiene la forma correcta (pega solo el valor ca-app-pub-…, sin «nombre=» ni espacios)"; exit 1; }
}
check_admob ADMOB_IOS_APP_ID 'ca-app-pub-[0-9]{16}~[0-9]{10}'
check_admob ADMOB_IOS_BANNER 'ca-app-pub-[0-9]{16}/[0-9]{10}'
check_admob ADMOB_IOS_OPEN_AD 'ca-app-pub-[0-9]{16}/[0-9]{10}'
check_admob ADMOB_IOS_INTERSTITIAL 'ca-app-pub-[0-9]{16}/[0-9]{10}'
ADMOB=()
if [ -n "$ADMOB_IOS_APP_ID" ] && [ -n "$ADMOB_IOS_BANNER" ] && [ -n "$ADMOB_IOS_OPEN_AD" ]; then
  ADMOB=(ADMOB_APP_ID="$ADMOB_IOS_APP_ID" ADMOB_BANNER="$ADMOB_IOS_BANNER" ADMOB_OPEN_AD="$ADMOB_IOS_OPEN_AD" ADMOB_INTERSTITIAL="$ADMOB_IOS_INTERSTITIAL")
  # Sin el secreto ADMOB_IOS_INTERSTITIAL queda vacío: la app no muestra intersticial.
else
  echo "AVISO: Sin los secretos ADMOB_IOS_*: esta compilación lleva los anuncios de PRUEBA de Google (vale para TestFlight, no para el App Store)"
fi
FCM=()
# Firebase cierra la app al abrirla si el identificador está mal (1.54.0):
# se comprueba la forma de cada secreto y, si no vale, no se compila.
if [ -n "$FIREBASE_IOS_APP_ID$FIREBASE_IOS_API_KEY$FIREBASE_IOS_SENDER_ID$FIREBASE_PROJECT_ID" ]; then
  echo "$FIREBASE_IOS_APP_ID" | grep -Eqx '1:[0-9]+:ios:[0-9a-f]+' || { echo "ERROR: FIREBASE_IOS_APP_ID no tiene la forma 1:NÚMERO:ios:HEX (pega solo el valor, sin «NOMBRE=»)"; exit 1; }
  echo "$FIREBASE_IOS_SENDER_ID" | grep -Eqx '[0-9]+' || { echo "ERROR: FIREBASE_IOS_SENDER_ID debe ser solo el número"; exit 1; }
  echo "$FIREBASE_IOS_APP_ID" | grep -q "^1:$FIREBASE_IOS_SENDER_ID:" || { echo "ERROR: FIREBASE_IOS_SENDER_ID no coincide con FIREBASE_IOS_APP_ID"; exit 1; }
  echo "$FIREBASE_IOS_API_KEY" | grep -Eqx 'AIza[0-9A-Za-z_-]{35}' || { echo "ERROR: FIREBASE_IOS_API_KEY no tiene la forma AIza… (pega solo el valor)"; exit 1; }
  echo "$FIREBASE_PROJECT_ID" | grep -Eqx '[a-z0-9-]+' || { echo "ERROR: FIREBASE_PROJECT_ID debe ser solo el identificador (opoalert-14a87)"; exit 1; }
fi
if [ -n "$FIREBASE_IOS_APP_ID" ] && [ -n "$FIREBASE_IOS_API_KEY" ] && [ -n "$FIREBASE_IOS_SENDER_ID" ] && [ -n "$FIREBASE_PROJECT_ID" ]; then
  FCM=(FCM_IOS_APP_ID="$FIREBASE_IOS_APP_ID" FCM_IOS_API_KEY="$FIREBASE_IOS_API_KEY" FCM_IOS_SENDER_ID="$FIREBASE_IOS_SENDER_ID" FCM_IOS_PROJECT_ID="$FIREBASE_PROJECT_ID")
else
  echo "AVISO: Sin los secretos FIREBASE_*: esta compilación no recibe avisos desde GitHub"
fi
# Se archiva sin firmar: firmar aquí pide un perfil de desarrollo, y ese perfil
# exige un iPhone registrado (fallo del 05/11/2026). La firma de distribución
# la hace el paso siguiente.
xcodebuild -project OpoAlert.xcodeproj -scheme OpoAlert -configuration Release \
  -destination 'generic/platform=iOS' -archivePath build/OpoAlert.xcarchive \
  DEVELOPMENT_TEAM="$TEAM_ID" CODE_SIGN_STYLE=Automatic CODE_SIGNING_ALLOWED=NO \
  CURRENT_PROJECT_VERSION="$BUILD_NUM" ${ADMOB[@]+"${ADMOB[@]}"} ${FCM[@]+"${FCM[@]}"} \
  archive | tail -n 80

# Las librerías de Google (anuncios y consentimiento) llegan al archivo sin
# firmar con una firma de Google que ya no es válida, y App Store Connect las
# rechazaba (05/11/2026). Sin firma, la exportación las firma con la app.
for fw in build/OpoAlert.xcarchive/Products/Applications/OpoAlert.app/Frameworks/*.framework; do
  [ -d "$fw" ] || continue
  echo "Quitar la firma de $(basename "$fw")"
  codesign --remove-signature "$fw" || true
  rm -rf "$fw/_CodeSignature"
done
# Se archiva sin firmar y la exportación no vería el permiso de avisos
# (aps-environment): se marca la app con sus entitlements antes de exportar.
codesign --force --sign - --entitlements OpoAlert/OpoAlert.entitlements \
  build/OpoAlert.xcarchive/Products/Applications/OpoAlert.app
cat > build/ExportOptions.plist <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>method</key><string>app-store-connect</string>
  <key>destination</key><string>upload</string>
  <key>teamID</key><string>$TEAM_ID</string>
  <key>signingStyle</key><string>automatic</string>
  <key>manageAppVersionAndBuildNumber</key><false/>
</dict></plist>
EOF
xcodebuild -exportArchive -archivePath build/OpoAlert.xcarchive \
  -exportOptionsPlist build/ExportOptions.plist -exportPath build/export \
  -allowProvisioningUpdates \
  -authenticationKeyPath "$KEY_DIR/AuthKey_$ASC_KEY_ID.p8" \
  -authenticationKeyID "$ASC_KEY_ID" -authenticationKeyIssuerID "$ASC_ISSUER_ID" \
  | tail -n 60
echo "Subida la compilación $BUILD_NUM. App Store Connect tarda unos minutos en procesarla."
