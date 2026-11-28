import OpoAlertCore
import SwiftUI

/// Tarjeta de una convocatoria, con el mismo contenido que en Android.
struct NoticeRow: View {
    let notice: Notice
    /// En Favoritas: plazo orientativo, «presentada» y nota (1.57.0).
    var showAgenda = false
    @EnvironmentObject private var model: AppModel
    @ObservedObject private var premium = PremiumStore.shared

    var body: some View {
        let favorite = model.isFavorite(notice)
        VStack(alignment: .leading, spacing: 6) {
            HStack(spacing: 5) {
                NoticeTag(text: notice.isPool ? "BOLSA" : "PLAZA",
                    color: notice.isPool ? Palette.poolText : Palette.blue,
                    fill: notice.isPool ? Palette.poolFill : Palette.positionFill)
                if model.freshIds.contains(notice.id) {
                    NoticeTag(text: "NUEVA", color: .white, fill: Color(hex: 0xFE4559))
                        .accessibilityLabel("Nueva desde tu última visita")
                }
                if showAgenda, premium.isActive, let badge = unreadBadge {
                    NoticeTag(text: badge, color: .white, fill: Color(hex: 0x7C3AED))
                        .accessibilityLabel("Posible novedad de esta convocatoria")
                }
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
                    if premium.isActive, let phrases = model.alertHits[notice.id] {
                        Label("Alerta: " + phrases.joined(separator: " · "), systemImage: "bell.fill")
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(Color(hex: 0x7C3AED))
                            .lineLimit(1)
                            .padding(.horizontal, 8)
                            .padding(.vertical, 4)
                            .background(Color(hex: 0xF1EAFE), in: RoundedRectangle(cornerRadius: 8))
                            .accessibilityLabel("Encontrada por tus alertas: " + phrases.joined(separator: ", "))
                    }
                    if showAgenda, let entry = model.agenda[notice.id] {
                        AgendaLine(entry: entry)
                    }
                    if showAgenda, premium.isActive, let last = model.followUpState(notice).visible.first {
                        Text("Último paso: \(last.step) · \(last.notice.date)")
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(Color(hex: 0x7C3AED))
                            .lineLimit(1)
                            .padding(.horizontal, 8)
                            .padding(.vertical, 4)
                            .background(Color(hex: 0xF1EAFE), in: RoundedRectangle(cornerRadius: 8))
                            .accessibilityLabel("Último paso posible: \(last.step), \(last.notice.date)")
                    }
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
                ShareLink(item: notice.shareText, subject: Text(ShareText.subject)) {
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

    /// «1 NOVEDAD» del seguimiento de la favorita (1.59.0).
    private var unreadBadge: String? {
        let unread = model.followUpState(notice).unreadCount
        return unread == 0 ? nil : (unread == 1 ? "1 NOVEDAD" : "\(unread) NOVEDADES")
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

/// Plazo orientativo y seguimiento de una favorita, como en Android.
struct AgendaLine: View {
    let entry: AgendaEntry

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            if let label {
                Text(label.text)
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(label.color)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(label.fill, in: RoundedRectangle(cornerRadius: 8))
            }
            if !entry.noteText.isEmpty {
                Text("✎ " + entry.noteText)
                    .font(.caption)
                    .foregroundStyle(Color(hex: 0x5B4B8A))
                    .lineLimit(2)
            }
        }
    }

    private var label: (text: String, color: Color, fill: Color)? {
        if entry.submitted { return ("✓ Solicitud presentada", Color(hex: 0x13795B), Color(hex: 0xE8F5EE)) }
        guard let until = entry.until, let left = AgendaDates.daysLeft(until) else { return nil }
        if left < 0 { return ("⏱ Plazo orientativo pasado (\(AgendaDates.short(until)))", Color(hex: 0xB45309), Color(hex: 0xFFF7E8)) }
        let text = left == 0 ? "⏱ Acaba como pronto hoy"
            : "⏱ Acaba como pronto el \(AgendaDates.short(until)) · quedan \(left) días"
        return left <= 3 ? (text, Color(hex: 0xB91C1C), Color(hex: 0xFDECEC)) : (text, Color(hex: 0xB45309), Color(hex: 0xFFF7E8))
    }
}
