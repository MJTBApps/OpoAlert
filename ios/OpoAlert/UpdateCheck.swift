import Foundation
import UIKit

/// Avisa cuando el App Store tiene una versión más nueva que la instalada.
/// Consulta la ficha pública de Apple (sin datos del usuario) como mucho cada 6 horas
/// y muestra el aviso una vez por versión nueva.
@MainActor
final class UpdateCheck: ObservableObject {
    static let shared = UpdateCheck()
    static let appStoreURL = URL(string: "https://apps.apple.com/es/app/opoalert-oposiciones-y-empleo/id6831053083")!
    private static let lookupURL = URL(string: "https://itunes.apple.com/lookup?id=6831053083&country=es")!
    private static let lastCheckKey = "update_check_last_v1"
    private static let shownKey = "update_check_shown_v1"

    @Published var showAlert = false
    @Published private(set) var latest = ""

    private var running = false

    func check() async {
        guard !running, !CaptureMode.isOn else { return }
        let defaults = UserDefaults.standard
        let now = Date().timeIntervalSince1970
        if now - defaults.double(forKey: Self.lastCheckKey) < 6 * 3600 { return }
        running = true
        defer { running = false }
        var request = URLRequest(url: Self.lookupURL, cachePolicy: .reloadIgnoringLocalCacheData, timeoutInterval: 15)
        request.httpMethod = "GET"
        guard let (data, _) = try? await URLSession.shared.data(for: request),
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let results = json["results"] as? [[String: Any]],
              let store = results.first?["version"] as? String else { return }
        defaults.set(now, forKey: Self.lastCheckKey)
        let installed = Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? ""
        guard Self.isNewer(store, than: installed), defaults.string(forKey: Self.shownKey) != store else { return }
        defaults.set(store, forKey: Self.shownKey)
        latest = store
        showAlert = true
    }

    func openStore() { UIApplication.shared.open(Self.appStoreURL) }

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
