import StoreKit
import SwiftUI

/// OpoAlert Premium con la compra de Apple (StoreKit 2), igual que `PlayBilling.kt`:
/// suscripción anual `opoalert_premium` con prueba gratuita, sin anuncios y con alertas.
/// Apple cobra, renueva y gestiona las cancelaciones; aquí solo se mira si está activa.
@MainActor
final class PremiumStore: ObservableObject {
    static let shared = PremiumStore()
    nonisolated static let productID = "opoalert_premium"
    /// Misma clave que Android; la leen también los avisos en segundo plano.
    nonisolated static let activeKey = "premium_active_v1"

    nonisolated static var isActiveStored: Bool { UserDefaults.standard.bool(forKey: activeKey) }

    @Published private(set) var isActive = PremiumStore.isActiveStored
    @Published private(set) var product: Product?
    @Published private(set) var trialDays: Int?
    @Published var message: String?
    private var updates: Task<Void, Never>?

    func start() {
        guard updates == nil else { return }
        // Renovaciones, cancelaciones y compras hechas en otro dispositivo.
        updates = Task { [weak self] in
            for await result in Transaction.updates {
                if case .verified(let transaction) = result { await transaction.finish() }
                await self?.refresh()
            }
        }
        Task { await refresh(); await loadProduct() }
    }

    func refresh() async {
        // Capturas del App Store en el simulador: como Premium, sin anuncios, salvo la
        // de la pantalla de compra (para el equipo de revisión de la suscripción).
        if CaptureMode.isOn {
            isActive = !CaptureMode.showsPurchase
            if CaptureMode.showsPurchase { trialDays = 7 }
            return
        }
        var active = false
        for await result in Transaction.currentEntitlements {
            if case .verified(let transaction) = result, transaction.productID == Self.productID,
               transaction.revocationDate == nil {
                active = true
            }
        }
        isActive = active
        UserDefaults.standard.set(active, forKey: Self.activeKey)
    }

    func loadProduct() async {
        // El simulador no tiene la tienda: la captura usa el precio configurado.
        if CaptureMode.isOn { return }
        guard let found = try? await Product.products(for: [Self.productID]).first else { return }
        product = found
        if let offer = found.subscription?.introductoryOffer, offer.paymentMode == .freeTrial,
           await found.subscription?.isEligibleForIntroOffer == true {
            trialDays = Self.days(offer.period)
        } else {
            trialDays = nil
        }
    }

    /// «3,99 € al año», con el precio y la moneda de cada país que da Apple.
    var priceText: String? {
        if CaptureMode.showsPurchase { return CaptureMode.price }
        guard let product, let period = product.subscription?.subscriptionPeriod else { return nil }
        let unit: String
        switch period.unit {
        case .year: unit = period.value == 1 ? " al año" : ""
        case .month: unit = period.value == 1 ? " al mes" : ""
        case .week: unit = " a la semana"
        default: unit = ""
        }
        return product.displayPrice + unit
    }

    func buy() async {
        if product == nil { await loadProduct() }
        guard let product else {
            message = "Ahora no se puede consultar el App Store. Comprueba la conexión e inténtalo de nuevo."
            return
        }
        do {
            switch try await product.purchase() {
            case .success(let result):
                if case .verified(let transaction) = result { await transaction.finish() }
                await refresh()
            case .pending:
                message = "La compra está pendiente de aprobación."
            default:
                break
            }
        } catch {
            message = "No se pudo completar la compra."
        }
    }

    func restore() async {
        try? await AppStore.sync()
        await refresh()
        message = isActive ? "Suscripción recuperada." : "No hay ninguna suscripción activa con este Apple ID."
    }

    private static func days(_ period: Product.SubscriptionPeriod) -> Int {
        switch period.unit {
        case .day: return period.value
        case .week: return period.value * 7
        case .month: return period.value * 30
        default: return period.value * 365
        }
    }
}

/// Pantalla de OpoAlert Premium (menú y pestaña de alertas).
struct PremiumView: View {
    @ObservedObject var premium = PremiumStore.shared
    @Environment(\.dismiss) private var dismiss
    @State private var buying = false

    var body: some View {
        NavigationStack {
            List {
                Section {
                    Label("Sin publicidad: ni al abrir la app ni entre las convocatorias.", systemImage: "nosign")
                    Label("Alertas personalizadas: te avisamos cuando sale una convocatoria de tu puesto y provincia.",
                          systemImage: "bell.badge")
                    Label("Con tu suscripción ayudas a mantener OpoAlert, un proyecto independiente, y a seguir añadiendo boletines.",
                          systemImage: "heart")
                }
                if premium.isActive {
                    Section {
                        Text("Tienes OpoAlert Premium activo. Puedes cancelarlo o cambiarlo cuando quieras en Ajustes → tu nombre → Suscripciones.")
                    }
                } else {
                    Section {
                        if let price = premium.priceText {
                            Text((premium.trialDays.map { "Pruébalo \($0) días gratis. Después, " } ?? "") + price +
                                 ". Se renueva automáticamente; puedes cancelarlo cuando quieras desde Ajustes.")
                            Button {
                                buying = true
                                Task { await premium.buy(); buying = false }
                            } label: {
                                Text(premium.trialDays != nil ? "Probar gratis" : "Suscribirme")
                                    .font(.headline).frame(maxWidth: .infinity, minHeight: 44)
                            }
                            .buttonStyle(.borderedProminent)
                            .disabled(buying)
                        } else {
                            Text("Consultando el App Store…").foregroundStyle(Palette.slate)
                        }
                        Button("Ya soy Premium (restaurar compra)") { Task { await premium.restore() } }
                    }
                    Section {
                        Link("Política de privacidad",
                             destination: URL(string: "https://mjtbapps.github.io/OpoAlert/privacidad.html")!)
                        Link("Condiciones de uso (Apple)",
                             destination: URL(string: "https://www.apple.com/legal/internet-services/itunes/dev/stdeula/")!)
                    }
                }
                if let message = premium.message {
                    Section { Text(message).foregroundStyle(Palette.slate) }
                }
            }
            .navigationTitle("OpoAlert Premium")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar { ToolbarItem(placement: .confirmationAction) { Button("Cerrar") { dismiss() } } }
            .task { if premium.product == nil { await premium.loadProduct() } }
        }
    }
}
