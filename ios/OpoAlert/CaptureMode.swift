import Foundation
import OpoAlertCore

/// Capturas para la ficha del App Store (`ios-capturas.yml`). Solo existe en el
/// simulador: en un iPhone `screen` es siempre nil y la app no cambia en nada.
/// Se activa al lanzar con `-opoCapture <pantalla>` (explorar, alertas, ficha, boletines).
enum CaptureMode {
    #if targetEnvironment(simulator)
    static var screen: String? { UserDefaults.standard.string(forKey: "opoCapture") }
    #else
    static let screen: String? = nil
    #endif

    static var isOn: Bool { screen != nil }

    /// Alertas de ejemplo para la captura de «Alertas» y del filtro.
    static let demoRules: [(String, Set<String>)] = [
        ("enfermería", ["VA", "AL", "CS", "ES"]),
        ("auxiliar administrativo", ["VA", "AL", "CS"]),
        ("policía local", ["VA", "AL", "CS"]),
    ]

    /// Coloca la pantalla pedida cuando ya hay convocatorias cargadas.
    @MainActor static func apply(_ model: AppModel) {
        guard let screen else { return }
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
        default: model.tab = .explore
        }
    }
}
