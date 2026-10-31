import OpoAlertCore
import SwiftUI

/// Ficha de una convocatoria. Solo muestra lo que dice el anuncio oficial:
/// nada de plazos calculados ni requisitos inventados.
struct NoticeDetailView: View {
    let notice: Notice
    @EnvironmentObject private var model: AppModel
    @Environment(\.openURL) private var openURL
    @State private var linkRejected = false
    @State private var pdfLink: PdfLink?

    private var source: Source { Source.of(notice) }

    var body: some View {
        let favorite = model.isFavorite(notice)
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                HStack(spacing: 6) {
                    NoticeTag(text: badge, color: notice.isPool ? Palette.poolText : Palette.blue,
                        fill: notice.isPool ? Palette.poolFill : Palette.positionFill)
                    // Solo lo que dice el título: si no da una cifra clara, no se muestra.
                    if let places = NoticeDetails.placesInTitle(notice.title) {
                        NoticeTag(text: places == 1 ? "1 plaza" : "\(places) plazas",
                                  color: Color(hex: 0xB4530A), fill: Color(hex: 0xFFF0E5))
                    }
                    if let group = NoticeDetails.groupInTitle(notice.title) {
                        NoticeTag(text: "Grupo \(group)", color: Color(hex: 0x28517E), fill: Color(hex: 0xE8EEF7))
                    }
                }
                Text(notice.headline)
                    .font(.title2.bold())
                    .foregroundStyle(Color(hex: 0x0E1C36))
                Text(notice.entity)
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(Color(hex: 0x5C6B80))
                Label("\(notice.province)  •  \(notice.date)", systemImage: "mappin.and.ellipse")
                    .font(.caption)
                    .foregroundStyle(Color(hex: 0x697C95))

                Button {
                    openOfficial()
                } label: {
                    Label(officialLabel, systemImage: "doc.richtext")
                        .font(.headline)
                        .frame(maxWidth: .infinity, minHeight: 48)
                }
                .buttonStyle(.borderedProminent)
                .tint(Color(hex: 0xFE4559))

                Text("Resumen del anuncio")
                    .font(.headline)
                    .padding(.top, 6)
                Text(notice.title.trimmingCharacters(in: .whitespacesAndNewlines))
                    .font(.subheadline)
                    .foregroundStyle(Color(hex: 0x35435C))
                    .textSelection(.enabled)
                    .padding(14)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(Color.white, in: RoundedRectangle(cornerRadius: 14))

                Text("Datos de la publicación")
                    .font(.headline)
                    .padding(.top, 6)
                VStack(alignment: .leading, spacing: 6) {
                    Label(source.fullName, systemImage: "building.columns")
                        .font(.subheadline.weight(.semibold))
                        .foregroundStyle(Color(hex: 0x203856))
                    Text(reference)
                        .font(.caption)
                        .foregroundStyle(Color(hex: 0x60748C))
                        .textSelection(.enabled)
                }
                .padding(14)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(Color.white, in: RoundedRectangle(cornerRadius: 14))

                ShareLink(item: notice.shareText, subject: Text("Convocatoria de empleo público · OpoAlert")) {
                    Label("Compartir convocatoria", systemImage: "square.and.arrow.up")
                        .frame(maxWidth: .infinity, minHeight: 44)
                }
                .buttonStyle(.bordered)
                Button {
                    model.toggleFavorite(notice)
                } label: {
                    Label(favorite ? "Quitar de favoritas" : "Guardar en favoritas",
                          systemImage: favorite ? "star.fill" : "star")
                        .frame(maxWidth: .infinity, minHeight: 44)
                }
                .buttonStyle(.bordered)
                .tint(Color(hex: 0xC96812))

                Text("OpoAlert no es una aplicación oficial. Las bases, requisitos y plazos válidos son los publicados por la Administración competente.")
                    .font(.caption2)
                    .foregroundStyle(Color(hex: 0x8190A5))
            }
            .padding(16)
        }
        .background(Palette.background)
        .navigationTitle("Convocatoria")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .navigationBarTrailing) {
                Button {
                    model.toggleFavorite(notice)
                } label: {
                    Image(systemName: favorite ? "star.fill" : "star")
                }
                .accessibilityLabel(favorite ? "Quitar de favoritas" : "Guardar en favoritas")
            }
        }
        .sheet(item: $pdfLink) { link in
            PdfViewerView(url: link.url, title: source.shortName)
        }
        .alert("El enlace oficial no se ha podido verificar.", isPresented: $linkRejected) {
            Button("Aceptar", role: .cancel) {}
        }
    }

    private var badge: String {
        if notice.isProcedureUpdate { return "TRÁMITE DEL PROCESO" }
        return notice.isPool ? "BOLSA DE TRABAJO" : "PLAZA / OPOSICIÓN"
    }

    private var officialLabel: String {
        if OfficialDocument.isPdf(notice) { return "Ver PDF oficial" }
        return notice.id.hasPrefix("CIDO") ? "Ver convocatoria en CIDO" : "Ver anuncio oficial"
    }

    private var reference: String {
        if notice.id.hasPrefix("CIDO") { return "Actualización \(notice.date)  ·  Ref. \(notice.id)" }
        if notice.id.hasPrefix("BA-") { return "BOP Barcelona · \(notice.date)  ·  Registro \(notice.id)" }
        return "\(source.shortName) n.º \(notice.bulletin)  ·  Registro \(notice.id)"
    }

    /// Solo se abre si el enlace es HTTPS al dominio y la ruta oficiales de la fuente.
    private func openOfficial() {
        guard source.isOfficialLink(notice.url), let url = URL(string: notice.url) else {
            linkRejected = true
            return
        }
        // El PDF se ve dentro de la app; si no fuera un PDF, el visor lo abre fuera.
        if OfficialDocument.isPdf(notice) { pdfLink = PdfLink(url: url) } else { openURL(url) }
    }
}

private struct PdfLink: Identifiable {
    let url: URL
    var id: String { url.absoluteString }
}
