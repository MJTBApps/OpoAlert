import Foundation
import UIKit

/// Avisa cuando el App Store tiene una versión más nueva que la instalada.
/// Consulta la ficha pública de Apple (sin datos del usuario) como mucho cada 6 horas.
///
/// 1.57.0: antes era una alerta que se marcaba como vista al pedirla; si en ese momento había
/// otra ventana (anuncio de apertura, «Elegir boletines»…) iOS no la enseñaba y ya no salía más.
/// Ahora es una tarjeta fija arriba de la lista (`UpdateCard`) que sigue ahí hasta actualizar
/// o cerrarla con la ✕ (entonces no vuelve hasta la versión siguiente).
@MainActor
final class UpdateCheck: ObservableObject {
    static let shared = UpdateCheck()
    static let appStoreURL = URL(string: "https://apps.apple.com/es/app/opoalert-oposiciones-y-empleo/id6831053083")!
    private static let lookupURL = URL(string: "https://itunes.apple.com/lookup?id=6831053083&country=es")!
    private static let lastCheckKey = "update_check_last_v1"
    private static let storeVersionKey = "update_store_version_v2"
    private static let dismissedKey = "update_dismissed_v2"

    @Published private(set) var latest = UserDefaults.standard.string(forKey: UpdateCheck.storeVersionKey) ?? ""
    @Published private(set) var dismissed = UserDefaults.standard.string(forKey: UpdateCheck.dismissedKey) ?? ""

    private var running = false

    static var installed: String {
        Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? ""
    }

    /// Hay una versión más nueva y no se ha cerrado su aviso.
    var available: Bool {
        !CaptureMode.isOn && !latest.isEmpty && Self.isNewer(latest, than: Self.installed) && dismissed != latest
    }

    func check() async {
        guard !running, !CaptureMode.isOn else { return }
        let defaults = UserDefaults.standard
        let now = Date().timeIntervalSince1970
        if now - defaults.double(forKey: Self.lastCheckKey) < 6 * 3600 { return }
        running = true
        defer { running = false }
        // La ficha de Apple pasa por una caché: «t» la salta para no ver una versión vieja.
        var components = URLComponents(url: Self.lookupURL, resolvingAgainstBaseURL: false)!
        components.queryItems?.append(URLQueryItem(name: "t", value: String(Int(now))))
        var request = URLRequest(url: components.url!, cachePolicy: .reloadIgnoringLocalCacheData, timeoutInterval: 15)
        request.httpMethod = "GET"
        guard let (data, _) = try? await URLSession.shared.data(for: request),
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let results = json["results"] as? [[String: Any]],
              let store = results.first?["version"] as? String,
              store.range(of: #"^\d{1,3}(\.\d{1,3}){1,2}$"#, options: .regularExpression) != nil else { return }
        defaults.set(now, forKey: Self.lastCheckKey)
        defaults.set(store, forKey: Self.storeVersionKey)
        latest = store
    }

    func openStore() { UIApplication.shared.open(Self.appStoreURL) }

    func dismiss() {
        UserDefaults.standard.set(latest, forKey: Self.dismissedKey)
        dismissed = latest
    }

    /// «1.54.10» > «1.54.9»: compara número a número.
    nonisolated static func isNewer(_ a: String, than b: String) -> Bool {
        let x = a.split(separator: ".").map { Int($0) ?? 0 }
        let y = b.split(separator: ".").map { Int($0) ?? 0 }
        for i in 0..<max(x.count, y.count) {
            let l = i < x.count ? x[i] : 0, r = i < y.count ? y[i] : 0
            if l != r { return l > r }
        }
        return false
    }
}
