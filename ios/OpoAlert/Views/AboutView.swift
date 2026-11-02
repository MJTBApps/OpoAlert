import SwiftUI

struct AboutView: View {
    @Environment(\.dismiss) private var dismiss

    private var version: String {
        Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "?"
    }

    var body: some View {
        NavigationStack {
            List {
                Section {
                    VStack(alignment: .leading, spacing: 6) {
                        Text("OpoAlert \(version)").font(.title3.bold())
                        Text("Empleo público a tu alcance").foregroundStyle(Palette.slate)
                    }
                    Text("Convocatorias de empleo público, bolsas y oposiciones de los boletines oficiales (BOE, boletines provinciales y autonómicos y el catálogo CIDO), revisadas cada día.")
                }
                Section("Importante") {
                    Text("OpoAlert es un proyecto gratuito e independiente de las Administraciones. No es una aplicación oficial.")
                    Text("«Candidata» no significa plaza confirmada: el filtrado es conservador. Las bases, requisitos y plazos válidos son los del anuncio oficial, que siempre se enlaza.")
                }
                Section("Privacidad") {
                    Text("Tus favoritas, alertas y boletines se guardan solo en este móvil. OpoAlert no tiene cuentas. La versión gratuita muestra anuncios de Google (AdMob), que pueden usar datos del dispositivo según el consentimiento que des.")
                    Link("Política de privacidad", destination: URL(string: "https://mjtbapps.github.io/OpoAlert/privacidad.html")!)
                }
                Section {
                    Link("Web y código abierto", destination: URL(string: "https://mjtbapps.github.io/OpoAlert/")!)
                }
            }
            .navigationTitle("Acerca de")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) { Button("Cerrar") { dismiss() } }
            }
        }
    }
}
