import AppTrackingTransparency
import GoogleMobileAds
import SwiftUI
import UIKit
import UserMessagingPlatform

/// Publicidad de AdMob con las mismas reglas que Android (`DemoAds.kt`):
/// - Primero el consentimiento del RGPD (mensaje de AdMob) y el aviso de Apple de seguimiento.
/// - Un anuncio al abrir la app (también la primera vez), como mucho uno cada 15 minutos y se
///   descarta si tarda más de 5 segundos.
/// - Un intersticial cada 3 fichas cerradas, nunca a menos de 1 minuto de otro a pantalla completa.
/// - Un banner cada 2 convocatorias de la lista, también al pulsar «Ver más», y dos en la ficha
///   (arriba, a mitad y al final, lejos de los botones). El hueco solo aparece cuando el anuncio ha cargado.
/// - Con Premium no hay anuncios.
@MainActor
final class Ads: ObservableObject {
    static let shared = Ads()
    static let listAdEvery = 2
    /// Banner de la ficha (uno para todas: se vuelve a pedir en cada ficha).
    static let detailSlot = -1
    /// Banner de la mitad de la ficha (entre el resumen y los datos de la publicación).
    static let detailMidSlot = -2
    /// Banner de arriba de la ficha (encima del título, separado del botón del PDF).
    static let detailTopSlot = -3
    static let noticesPerInterstitial = 3
    static let fullscreenGap: TimeInterval = 60
    /// Un intersticial cargado caduca a la hora: se pide otro antes.
    static let interstitialLifetime: TimeInterval = 50 * 60
    /// Cada cuánto puede salir el anuncio de apertura (segundos).
    static let openAdInterval: TimeInterval = 15 * 60

    @Published private(set) var ready = false
    /// Banners de la lista que tienen anuncio: solo esos se muestran.
    @Published private(set) var loadedSlots: Set<Int> = []
    private let lastFullscreenKey = "last_fullscreen_ad"
    private let noticesKey = "notices_since_interstitial"
    private var interstitial: InterstitialAd?
    private var loadingInterstitial = false
    private var interstitialLoadedAt = Date.distantPast
    private let fullscreenDelegate = FullscreenDelegate()
    private var starting = false
    private let defaults = UserDefaults.standard
    private let lastOpenAdKey = "last_app_open_ad"
    private let launchesKey = "app_launches_v1"

    var bannerID: String { Bundle.main.object(forInfoDictionaryKey: "OpoAdmobBanner") as? String ?? "" }
    private var openAdID: String { Bundle.main.object(forInfoDictionaryKey: "OpoAdmobOpenAd") as? String ?? "" }
    /// Vacío = sin intersticial (compilación del App Store sin el bloque creado en AdMob).
    private var interstitialID: String { Bundle.main.object(forInfoDictionaryKey: "OpoAdmobInterstitial") as? String ?? "" }
    var usesTestAds: Bool { bannerID.hasPrefix("ca-app-pub-3940256099942544") }

    /// Al arrancar: consentimiento, seguimiento y, si procede, el anuncio de apertura.
    func start(premium: Bool) {
        // Con Premium no hay anuncios: tampoco se pregunta por el consentimiento ni por el
        // seguimiento (como en Android). Si deja de ser Premium, empieza al abrir de nuevo.
        guard !premium, !starting else { return }
        starting = true
        defaults.set(defaults.integer(forKey: launchesKey) + 1, forKey: launchesKey)
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
                        self.showOpenAd()
                        self.preload(slot: 0)
                        self.preload(slot: 1)
                        self.loadInterstitial()
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
        // Tras un rato fuera, los banners guardados ya no muestran nada (el anuncio caduca y
        // iOS para su refresco en segundo plano): se vuelven a pedir todos. Antes había que
        // cerrar la app del todo para que volvieran.
        reloadBanners()
        showOpenAd()
    }

    private func reloadBanners() {
        let root = Self.topController()
        for (slot, view) in banners {
            loadedSlots.remove(slot)
            view.rootViewController = root
            view.load(Request())
        }
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
                self.defaults.set(Date().timeIntervalSince1970, forKey: self.lastFullscreenKey)
                ad.present(from: Self.topController())
            }
        }
    }

    private func loadInterstitial() {
        guard ready, !interstitialID.isEmpty, interstitial == nil, !loadingInterstitial else { return }
        loadingInterstitial = true
        InterstitialAd.load(with: interstitialID, request: Request()) { [weak self] ad, _ in
            Task { @MainActor in
                guard let self else { return }
                self.loadingInterstitial = false
                if let ad {
                    ad.fullScreenContentDelegate = self.fullscreenDelegate
                    self.interstitial = ad
                    self.interstitialLoadedAt = Date()
                    return
                }
                try? await Task.sleep(nanoseconds: 60_000_000_000)
                self.loadInterstitial()
            }
        }
    }

    /// Se ha cerrado una ficha. Cada 3 sale un intersticial; si aún no ha cargado o es
    /// pronto (menos de 1 minuto desde otro a pantalla completa), sale en la siguiente.
    /// true si va a intentar mostrar el intersticial (entonces no se pide la valoración).
    @discardableResult
    func noticeClosed(premium: Bool) -> Bool {
        guard ready, !premium, !interstitialID.isEmpty else { return false }
        let count = defaults.integer(forKey: noticesKey) + 1
        defaults.set(count, forKey: noticesKey)
        if interstitial != nil, Date().timeIntervalSince(interstitialLoadedAt) > Self.interstitialLifetime {
            interstitial = nil  // caducado: Google ya no lo mostraría
        }
        guard count >= Self.noticesPerInterstitial, interstitial != nil,
              Date().timeIntervalSince1970 - defaults.double(forKey: lastFullscreenKey) >= Self.fullscreenGap else {
            loadInterstitial()
            return false
        }
        // Antes se presentaba a los 0,5 s, a veces con la animación de volver a la lista aún
        // en marcha: iOS rechazaba la presentación sin avisar y nunca salía ninguno
        // (AdMob: 0 impresiones del intersticial). Ahora se espera a que acabe la transición.
        Task { @MainActor in
            for _ in 0..<20 {
                try? await Task.sleep(nanoseconds: 250_000_000)
                if let top = Self.topController(), top.transitionCoordinator == nil, !top.isBeingDismissed,
                   top.view.window != nil { break }
            }
            guard let ad = self.interstitial, let top = Self.topController(), top.view.window != nil else { return }
            self.interstitial = nil
            self.defaults.set(0, forKey: self.noticesKey)
            self.defaults.set(Date().timeIntervalSince1970, forKey: self.lastFullscreenKey)
            self.fullscreenDelegate.finished = { [weak self] shown in
                guard let self else { return }
                // Si no se pudo mostrar, toca en la próxima ficha.
                if !shown { self.defaults.set(Self.noticesPerInterstitial - 1, forKey: self.noticesKey) }
                self.loadInterstitial()
            }
            ad.present(from: top)
        }
        return true
    }

    /// Los banners se guardan por posición: si SwiftUI vuelve a dibujar la lista (por ejemplo
    /// al volver de Safari tras pulsar un anuncio), se reutiliza el mismo y no queda un hueco vacío.
    private var banners: [Int: BannerView] = [:]
    /// Si Google no devuelve anuncio (sin conexión o sin anuncio que servir), se vuelve a pedir
    /// al cabo de un rato; antes el hueco se quedaba vacío hasta cerrar y abrir la app.
    private let retry = BannerRetry()

    /// Pide el banner de esa posición; se mostrará cuando cargue.
    func preload(slot: Int) { _ = banner(slot: slot) }

    /// Banner del final de la ficha: el mismo para todas, con un anuncio nuevo en cada ficha.
    func refreshDetailBanner() {
        guard ready else { return }
        for slot in [Self.detailTopSlot, Self.detailMidSlot, Self.detailSlot] {
            guard let view = banners[slot] else { _ = banner(slot: slot); continue }
            loadedSlots.remove(slot)
            view.rootViewController = Self.topController()
            view.load(Request())
        }
    }

    fileprivate func bannerChanged(_ view: BannerView, loaded: Bool) {
        guard let slot = banners.first(where: { $0.value === view })?.key else { return }
        if loaded { loadedSlots.insert(slot) } else if loadedSlots.contains(slot) { loadedSlots.remove(slot) }
    }

    func banner(slot: Int) -> BannerView {
        if let view = banners[slot] { return view }
        let view = BannerView(adSize: AdSizeBanner)
        view.adUnitID = bannerID
        view.rootViewController = Self.topController()
        view.delegate = retry
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

/// Avisa cuando el intersticial se cierra o no se ha podido mostrar.
@MainActor
final class FullscreenDelegate: NSObject, FullScreenContentDelegate {
    var finished: ((Bool) -> Void)?

    nonisolated func adDidDismissFullScreenContent(_ ad: FullScreenPresentingAd) {
        MainActor.assumeIsolated { finished?(true); finished = nil }
    }

    nonisolated func ad(_ ad: FullScreenPresentingAd, didFailToPresentFullScreenContentWithError error: Error) {
        MainActor.assumeIsolated { finished?(false); finished = nil }
    }
}

/// Vuelve a pedir un banner que no ha cargado: a los 30 s, luego 60 s… hasta 5 minutos.
@MainActor
final class BannerRetry: NSObject, BannerViewDelegate {
    private var attempts: [ObjectIdentifier: Int] = [:]

    nonisolated func bannerViewDidReceiveAd(_ bannerView: BannerView) {
        MainActor.assumeIsolated { received(bannerView) }
    }

    nonisolated func bannerView(_ bannerView: BannerView, didFailToReceiveAdWithError error: Error) {
        MainActor.assumeIsolated { failed(bannerView) }
    }

    private func received(_ bannerView: BannerView) {
        attempts[ObjectIdentifier(bannerView)] = 0
        Ads.shared.bannerChanged(bannerView, loaded: true)
    }

    private func failed(_ bannerView: BannerView) {
        // Sin anuncio, el hueco se quita de la lista (nunca un recuadro vacío).
        Ads.shared.bannerChanged(bannerView, loaded: false)
        let key = ObjectIdentifier(bannerView)
        let tries = (attempts[key] ?? 0) + 1
        attempts[key] = tries
        let delay = min(30.0 * Double(tries), 300.0)
        Task { @MainActor [weak bannerView] in
            try? await Task.sleep(nanoseconds: UInt64(delay * 1_000_000_000))
            guard let bannerView else { return }
            if bannerView.rootViewController == nil { bannerView.rootViewController = Ads.topController() }
            bannerView.load(Request())
        }
    }
}

/// Hueco de anuncio que está siempre en pantalla: el banner se pide ya colocado en la ventana
/// (antes se pedía fuera de pantalla y luego se movía, y muchos anuncios recibidos no se veían).
/// Hasta que llega el anuncio no ocupa sitio ni muestra «PUBLICIDAD»: nunca un hueco vacío.
struct AdSlot: View {
    let slot: Int
    @ObservedObject private var ads = Ads.shared

    var body: some View {
        let loaded = ads.loadedSlots.contains(slot)
        VStack(spacing: 6) {
            if loaded {
                Text("PUBLICIDAD")
                    .font(.system(size: 10))
                    .foregroundStyle(Color(hex: 0x64748B))
            }
            BannerAdView(slot: slot)
                .frame(width: 320, height: loaded ? 50 : 0)
                .clipped()
        }
        .frame(maxWidth: .infinity)
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
