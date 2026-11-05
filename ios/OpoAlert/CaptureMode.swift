import Foundation
import OpoAlertCore

/// Capturas para la ficha del App Store (`ios-capturas.yml`). Solo existe en el
/// simulador: en un iPhone `screen` es siempre nil y la app no cambia en nada.
/// Se activa al lanzar con `-opoCapture <pantalla>` (explorar, ficha, filtro, alertas,
/// boletines, premium).
enum CaptureMode {
    #if targetEnvironment(simulator)
    static var screen: String? { UserDefaults.standard.string(forKey: "opoCapture") }
    #else
    static let screen: String? = nil
    #endif

    static var isOn: Bool { screen != nil }
    /// Captura de la pantalla de compra de Premium, que pide la revisión de la suscripción.
    static var showsPurchase: Bool { screen == "premium" }
    /// Precio de `opoalert_premium` en App Store Connect (España); solo para esa captura.
    static let price = "3,99 € al año"

    /// Alertas de ejemplo para la captura de «Alertas» y del filtro.
    static let demoRules: [(String, Set<String>)] = [
        ("enfermería", ["VA", "AL", "CS", "ES"]),
        ("auxiliar administrativo", ["VA", "AL", "CS"]),
        ("policía local", ["VA", "AL", "CS"]),
    ]

    /// Coloca la pantalla pedida cuando ya hay convocatorias cargadas.
    @MainActor static func apply(_ model: AppModel) async {
        guard let screen else { return }
        // Las hojas (ficha, boletines) no se abren si se piden antes de que la
        // lista termine de dibujarse.
        try? await Task.sleep(nanoseconds: 5_000_000_000)
        if model.rules.isEmpty {
            for (phrase, sources) in demoRules {
                try? model.saveRule(id: nil, phrase: phrase, sources: sources)
            }
        }
        switch screen {
        case "alertas": model.tab = .alerts
        case "filtro":
            model.tab = .explore
            model.requestedFilter = .alerts
        case "ficha":
            model.tab = .explore
            model.openedNotice = model.explore(query: "", filter: .positions).first
        case "boletines": model.showSourcePicker = true
        case "premium": model.showPremium = true
        default: model.tab = .explore
        }
    }
}
