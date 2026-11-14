import AppTrackingTransparency
import GoogleMobileAds
import SwiftUI
import UIKit
import UserMessagingPlatform

/// Publicidad de AdMob con las mismas reglas que Android (`DemoAds.kt`):
/// - Primero el consentimiento del RGPD (mensaje de AdMob) y el aviso de Apple de seguimiento.
/// - Un anuncio al abrir la app: nunca la primera vez, como mucho uno cada 15 minutos y se
///   descarta si tarda más de 5 segundos.
/// - Un banner cada 6 convocatorias de la lista, también al pulsar «Ver más».
/// - Con Premium no hay anuncios.
@MainActor
final class Ads: ObservableObject {
    static let shared = Ads()
    static let listAdEvery = 6
    /// Cada cuánto puede salir el anuncio de apertura (segundos).
    static let openAdInterval: TimeInterval = 15 * 60

    @Published private(set) var ready = false
    private var starting = false
    private let defaults = UserDefaults.standard
    private let lastOpenAdKey = "last_app_open_ad"
    private let launchesKey = "app_launches_v1"

    var bannerID: String { Bundle.main.object(forInfoDictionaryKey: "OpoAdmobBanner") as? String ?? "" }
    private var openAdID: String { Bundle.main.object(forInfoDictionaryKey: "OpoAdmobOpenAd") as? String ?? "" }
    var usesTestAds: Bool { bannerID.hasPrefix("ca-app-pub-3940256099942544") }

    /// Al arrancar: consentimiento, seguimiento y, si procede, el anuncio de apertura.
    func start(premium: Bool) {
        // Con Premium no hay anuncios: tampoco se pregunta por el consentimiento ni por el
        // seguimiento (como en Android). Si deja de ser Premium, empieza al abrir de nuevo.
        guard !premium, !starting else { return }
        starting = true
        let launches = defaults.integer(forKey: launchesKey) + 1
        defaults.set(launches, forKey: launchesKey)
        let parameters = RequestParameters()
        ConsentInformation.shared.requestConsentInfoUpdate(with: parameters) { [weak self] _ in
            Task { @MainActor in
                guard let self else { return }
                ConsentForm.loadAndPresentIfRequired(from: Self.topController()) { _ in
                    Task { @MainActor in
                        guard ConsentInformation.shared.canRequestAds else { return }
                        await self.askTracking()
                        MobileAds.shared.start(completionHandler: nil)
                        self.ready = true
                        if !premium && launches > 1 { self.showOpenAd() }
                    }
                }
            }
        }
    }

    private var backgroundSince: Date?

    /// La app pasa a segundo plano (para el anuncio al volver).
    func didEnterBackground() { backgroundSince = Date() }

    /// Al volver a la app tras 5 minutos o más fuera (iOS suele mantenerla abierta horas),
    /// también sale el anuncio de apertura. Volver de Safari tras pulsar un anuncio no cuenta.
    func didBecomeActive(premium: Bool) {
        defer { backgroundSince = nil }
        guard ready, !premium, let since = backgroundSince, Date().timeIntervalSince(since) >= 5 * 60 else { return }
        showOpenAd()
    }

    /// El aviso de Apple solo se muestra una vez; si se rechaza, los anuncios no son personalizados.
    private func askTracking() async {
        guard ATTrackingManager.trackingAuthorizationStatus == .notDetermined else { return }
        await withCheckedContinuation { (done: CheckedContinuation<Void, Never>) in
            ATTrackingManager.requestTrackingAuthorization { _ in done.resume() }
        }
    }

    private func showOpenAd() {
        let last = defaults.double(forKey: lastOpenAdKey)
        guard Date().timeIntervalSince1970 - last >= Self.openAdInterval else { return }
        let requested = Date()
        AppOpenAd.load(with: openAdID, request: Request()) { [weak self] ad, _ in
            Task { @MainActor in
                // Si tarda más de 5 segundos, ya no se muestra: el usuario ya está usando la app.
                guard let self, let ad, Date().timeIntervalSince(requested) <= 5 else { return }
                self.defaults.set(Date().timeIntervalSince1970, forKey: self.lastOpenAdKey)
                ad.present(from: Self.topController())
            }
        }
    }

    /// Los banners se guardan por posición: si SwiftUI vuelve a dibujar la lista (por ejemplo
    /// al volver de Safari tras pulsar un anuncio), se reutiliza el mismo y no queda un hueco vacío.
    private var banners: [Int: BannerView] = [:]

    func banner(slot: Int) -> BannerView {
        if let view = banners[slot] { return view }
        let view = BannerView(adSize: AdSizeBanner)
        view.adUnitID = bannerID
        view.rootViewController = Self.topController()
        view.load(Request())
        banners[slot] = view
        return view
    }

    var privacyOptionsRequired: Bool {
        ConsentInformation.shared.privacyOptionsRequirementStatus == .required
    }

    func showPrivacyOptions() {
        ConsentForm.presentPrivacyOptionsForm(from: Self.topController()) { _ in }
    }

    static func topController() -> UIViewController? {
        let scene = UIApplication.shared.connectedScenes.compactMap { $0 as? UIWindowScene }
            .first { $0.activationState == .foregroundActive } ??
            UIApplication.shared.connectedScenes.compactMap { $0 as? UIWindowScene }.first
        var top = scene?.windows.first { $0.isKeyWindow }?.rootViewController ?? scene?.windows.first?.rootViewController
        while let presented = top?.presentedViewController { top = presented }
        return top
    }
}

/// Banner estándar (320×50) entre las convocatorias.
struct BannerAdView: UIViewRepresentable {
    let slot: Int

    func makeUIView(context: Context) -> UIView {
        let box = UIView()
        attach(to: box)
        return box
    }

    func updateUIView(_ box: UIView, context: Context) {
        if box.subviews.isEmpty { attach(to: box) }
    }

    private func attach(to box: UIView) {
        let banner = Ads.shared.banner(slot: slot)
        banner.removeFromSuperview()
        banner.frame = CGRect(x: 0, y: 0, width: 320, height: 50)
        box.addSubview(banner)
        if banner.rootViewController == nil { banner.rootViewController = Ads.topController() }
    }
}
