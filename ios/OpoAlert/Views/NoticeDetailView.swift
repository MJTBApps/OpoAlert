import OpoAlertCore
import SwiftUI

/// Ficha de una convocatoria. Solo muestra lo que dice el anuncio oficial:
/// nada de plazos calculados ni requisitos inventados.
struct NoticeDetailView: View {
    let notice: Notice
    @EnvironmentObject private var model: AppModel
    @Environment(\.openURL) private var openURL
    @State private var linkRejected = false

    private var source: Source { Source.of(notice) }

    var body: some View {
        let favorite = model.isFavorite(notice)
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                HStack(spacing: 6) {
                    NoticeTag(text: badge, color: notice.isPool ? Palette.poolText : Palette.blue,
                        fill: notice.isPool ? Palette.poolFill : Palette.positionFill)
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

                HStack(spacing: 10) {
                    Metric(label: "PLAZAS", value: NoticeDetails.placesInTitle(notice.title).map { String($0) } ?? "Ver bases",
                           systemImage: "person.2")
                    Metric(label: "PLAZO", value: NoticeDetails.deadlineLabel(), systemImage: "calendar")
                }
                Text("Plazas y plazos: consulta siempre las bases y, en su caso, la publicación de apertura del plazo.")
                    .font(.caption)
                    .foregroundStyle(Palette.slate)

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
        .alert("El enlace oficial no se ha podido verificar.", isPresented: $linkRejected) {
            Button("Aceptar", role: .cancel) {}
        }
    }

    private var badge: String {
        if notice.isProcedureUpdate { return "TRÁMITE DEL PROCESO" }
        return notice.isPool ? "BOLSA DE TRABAJO" : "PLAZA / OPOSICIÓN"
    }

    private var officialLabel: String {
        if notice.id.hasPrefix("CIDO") { return "Ver convocatoria en CIDO" }
        if notice.province == "Teruel" || notice.url.contains("ExportarBoletinServlet") { return "Ver anuncio oficial" }
        return "Ver PDF oficial"
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
        openURL(url)
    }
}

private struct Metric: View {
    let label: String
    let value: String
    let systemImage: String

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Label(label, systemImage: systemImage)
                .font(.caption2.bold())
                .foregroundStyle(Palette.slate)
            Text(value)
                .font(value.count > 10 ? .headline : .title2.bold())
                .foregroundStyle(Palette.navy)
        }
        .padding(12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color.white, in: RoundedRectangle(cornerRadius: 14))
    }
}
