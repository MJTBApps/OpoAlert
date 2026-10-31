// swift-tools-version:5.8
import PackageDescription

// Núcleo de la app iOS: modelos, lectura y validación de los feeds, búsqueda,
// alertas y almacenamiento local. Sin interfaz, para poder comprobarlo también
// en macOS sin Xcode (`swift run OpoAlertChecks`).
let package = Package(
    name: "OpoAlertCore",
    platforms: [.iOS(.v16), .macOS(.v13)],
    products: [
        .library(name: "OpoAlertCore", targets: ["OpoAlertCore"]),
    ],
    targets: [
        .target(name: "OpoAlertCore"),
        .executableTarget(name: "OpoAlertChecks", dependencies: ["OpoAlertCore"]),
    ]
)
