import Foundation
import OpoAlertCore
import UserNotifications

/// Recordatorio de fin de plazo de una favorita (Premium; `DeadlineReminder.kt`): a las 9:00
/// dos días antes de la fecha orientativa, o ese mismo día si ya queda menos. La fecha es
/// «como pronto»: el aviso nunca llega tarde.
enum Reminders {
    private static func identifier(_ id: String) -> String { "plazo-" + id }

    static func eligible(_ entry: AgendaEntry?) -> Bool {
        guard let entry, entry.until != nil, !entry.submitted else { return false }
        return PremiumStore.isActiveStored
    }

    /// Día y hora del aviso, o nil si no hay.
    static func planned(_ entry: AgendaEntry?, favorite: Bool) -> Date? {
        guard favorite, eligible(entry), let until = entry?.until, let day = AgendaDates.remindDay(until) else { return nil }
        let at = AgendaDates.calendar.date(bySettingHour: 9, minute: 0, second: 0, of: day)
        // Si hoy ya han pasado las 9, avisa en unos minutos.
        return at.map { max($0, Date().addingTimeInterval(60)) }
    }

    static func sync(_ notice: Notice, entry: AgendaEntry?, favorite: Bool) async {
        let center = UNUserNotificationCenter.current()
        center.removePendingNotificationRequests(withIdentifiers: [identifier(notice.id)])
        guard let at = planned(entry, favorite: favorite), let until = entry?.until else { return }
        await AlertNotifications.requestPermission()
        let content = UNMutableNotificationContent()
        content.title = "⏱ Se acaba el plazo: " + String(notice.headline.prefix(60))
        content.body = "Según el anuncio, el plazo acaba como pronto el \(AgendaDates.long(until)). Compruébalo en el anuncio oficial."
        content.sound = .default
        if let data = try? JSONEncoder().encode(notice) {
            content.userInfo = [AlertNotifications.noticeKey: data]
        }
        let parts = AgendaDates.calendar.dateComponents([.year, .month, .day, .hour, .minute], from: at)
        let trigger = UNCalendarNotificationTrigger(dateMatching: parts, repeats: false)
        try? await center.add(UNNotificationRequest(identifier: identifier(notice.id), content: content, trigger: trigger))
    }

    static func cancel(_ id: String) {
        UNUserNotificationCenter.current().removePendingNotificationRequests(withIdentifiers: [identifier(id)])
    }
}
