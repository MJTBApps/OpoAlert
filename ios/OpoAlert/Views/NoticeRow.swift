import OpoAlertCore
import SwiftUI

/// Tarjeta de una convocatoria, con el mismo contenido que en Android.
struct NoticeRow: View {
    let notice: Notice
    @EnvironmentObject private var model: AppModel

    var body: some View {
        let favorite = model.isFavorite(notice)
        VStack(alignment: .leading, spacing: 6) {
            HStack(spacing: 5) {
                NoticeTag(text: notice.isPool ? "BOLSA" : "PLAZA",
                    color: notice.isPool ? Palette.poolText : Palette.blue,
                    fill: notice.isPool ? Palette.poolFill : Palette.positionFill)
                if notice.isProcedureUpdate {
                    NoticeTag(text: "TRÁMITE", color: Palette.procedureText, fill: Palette.procedureFill)
                }
                Spacer()
                Text(notice.date)
                    .font(.caption)
                    .foregroundStyle(Palette.slate)
                Button {
                    model.toggleFavorite(notice)
                } label: {
                    Image(systemName: favorite ? "star.fill" : "star")
                        .font(.title3)
                        .foregroundStyle(favorite ? Palette.star : Palette.slate)
                        .frame(width: 40, height: 36)
                }
                .buttonStyle(.borderless)
                .accessibilityLabel(favorite ? "Quitar de favoritas" : "Añadir a favoritas")
            }
            NavigationLink(value: notice) {
                VStack(alignment: .leading, spacing: 6) {
                    Text(notice.headline)
                        .font(.body.weight(.semibold))
                        .foregroundStyle(Palette.navy)
                        .lineLimit(3)
                        .multilineTextAlignment(.leading)
                    Text(notice.entity)
                        .font(.footnote)
                        .foregroundStyle(Palette.slate)
                        .lineLimit(2)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
            }
            .buttonStyle(.plain)
            HStack {
                Text("\(notice.origin) · Ref. \(notice.id)")
                    .font(.caption2)
                    .foregroundStyle(Palette.slate)
                    .lineLimit(1)
                Spacer()
                ShareLink(item: notice.shareText, subject: Text("Convocatoria de empleo público · OpoAlert")) {
                    Label("Compartir", systemImage: "square.and.arrow.up")
                        .font(.caption.bold())
                }
                .buttonStyle(.borderless)
            }
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 11)
        .background(Color.white, in: RoundedRectangle(cornerRadius: 16))
        .overlay(RoundedRectangle(cornerRadius: 16).stroke(favorite ? Palette.favoriteBorder : Palette.border))
    }
}

struct NoticeTag: View {
    let text: String
    let color: Color
    let fill: Color

    var body: some View {
        Text(text)
            .font(.caption2.bold())
            .foregroundStyle(color)
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .background(fill, in: RoundedRectangle(cornerRadius: 8))
    }
}
