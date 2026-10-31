# OpoAlert para iOS

App nativa en **SwiftUI** (iOS 16 o posterior) que lee los mismos feeds JSON
auditados de GitHub Pages que la app Android. El backend no cambia.

## Qué hace (igual que Android)

- **Explorar**: convocatorias de los últimos 30 días de los boletines que sigues,
  con búsqueda sin tildes, filtro Todas / Bolsas / Plazas y paginación.
- **Ficha**: «Ver PDF oficial» arriba (el PDF se ve dentro de la app con PDFKit
  y se abre en la página del anuncio si el enlace trae `#page=N`), etiqueta con
  el número de plazas solo si el título lo dice, grupo y datos de la publicación.
  No se muestra ningún plazo (nunca se inventa). El enlace solo se abre si es
  HTTPS al dominio y la ruta oficiales.
- **Favoritas**: se guarda la ficha completa en el móvil.
- **Alertas**: hasta 20, por palabras (sin importar tildes ni orden) y por
  boletín. Avisos locales cuando iOS deja revisar en segundo plano
  (`BGAppRefreshTask`, se pide cada hora; iOS decide cuándo).
- **Elegir boletines**: BOE y comunidades con sus provincias, como en Android.
  La lista de fuentes activas se lee de `fuentes_activas.json`.

Sin publicidad ni Premium de momento (ver `PLAN_MONETIZACION_IOS.md`).

## Estructura

- `OpoAlertCore/`: paquete Swift sin interfaz (modelos, lectura y validación de
  feeds, búsqueda, alertas, almacenamiento y revisión). Es el equivalente de
  `Province.kt`, `RemoteFeedReader.kt`, `Repository.kt`, etc.
  - `Fuentes.generated.swift` **se genera desde Android**:
    `python scripts/generar_fuentes_ios.py` (y `--check` para comprobarlo; lo
    hace también `backend/tests/test_fuentes_ios.py`). No editarlo a mano.
  - `OpoAlertChecks`: comprobaciones (las pruebas de Android portadas, una
    revisión simulada completa y la validación de **todos** los feeds de `docs/`).
- `OpoAlert/`: la app SwiftUI (pantallas, avisos y revisión en segundo plano).
- `project.yml`: proyecto de Xcode para XcodeGen (el `.xcodeproj` no se sube).

## Compilar

**En GitHub Actions** (`.github/workflows/ios-app.yml`, macOS con el Xcode más
reciente): comprueba las fuentes, pasa las comprobaciones del núcleo, compila
para el simulador y guarda dos capturas como artefacto (`capturas-ios`).

**En un Mac con Xcode 26** (el iMac de casa, con macOS 13, no lo admite):

```
brew install xcodegen
cd ios && xcodegen generate && open OpoAlert.xcodeproj
```

**Solo el núcleo, en el iMac sin Xcode** (SwiftPM no funciona sin Xcode, pero
`swiftc` sí):

```
cd ios/OpoAlertCore
mkdir -p /tmp/opoalert-ios
swiftc -module-name OpoAlertCore -emit-module -emit-library -static -parse-as-library \
  -o /tmp/opoalert-ios/libOpoAlertCore.a -emit-module-path /tmp/opoalert-ios/OpoAlertCore.swiftmodule \
  Sources/OpoAlertCore/*.swift
swiftc -I /tmp/opoalert-ios -L /tmp/opoalert-ios -lOpoAlertCore -o /tmp/opoalert-ios/checks \
  Sources/OpoAlertChecks/main.swift
/tmp/opoalert-ios/checks ../../docs
```

## Para publicarla (lo hace el propietario)

1. **Apple Developer Program** (99 USD al año) y el equipo en `DEVELOPMENT_TEAM`.
2. Firmar y subir a **TestFlight** (se puede automatizar en Actions con un
   certificado y una clave de App Store Connect guardados como *secrets*; nunca
   en el repositorio, que es público).
3. Ficha del App Store: privacidad («no se recogen datos»), capturas y descripción.
