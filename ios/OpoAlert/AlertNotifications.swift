import BackgroundTasks
import Foundation
import OpoAlertCore
import UserNotifications

/// Avisos locales: se generan en el propio móvil, sin servidor ni cuenta.
enum AlertNotifications {
    static let noticeKey = "notice"

    static func requestPermission() async {
        let center = UNUserNotificationCenter.current()
        let settings = await center.notificationSettings()
        guard settings.authorizationStatus == .notDetermined else { return }
        _ = try? await center.requestAuthorization(options: [.alert, .sound, .badge])
    }

    /// Un aviso por revisión: con una sola convocatoria abre su ficha; con varias, la lista.
    static func show(_ matching: [Notice]) async {
        guard !matching.isEmpty else { return }
        let center = UNUserNotificationCenter.current()
        let settings = await center.notificationSettings()
        guard settings.authorizationStatus == .authorized || settings.authorizationStatus == .provisional else { return }
        let content = UNMutableNotificationContent()
        content.title = matching.count == 1 ? "Nueva convocatoria para tus alertas"
            : "\(matching.count) convocatorias para tus alertas"
        let lines = matching.prefix(5).map { String($0.headline.prefix(76)) + " · " + $0.province }
        content.body = lines.joined(separator: "\n") +
            (matching.count > lines.count ? "\n+ \(matching.count - lines.count) anuncios más" : "")
        content.sound = .default
        if matching.count == 1, let data = try? JSONEncoder().encode(matching[0]) {
            content.userInfo = [noticeKey: data]
        }
        let request = UNNotificationRequest(identifier: UUID().uuidString, content: content, trigger: nil)
        try? await center.add(request)
    }

    static func notice(from response: UNNotificationResponse) -> Notice? {
        guard let data = response.notification.request.content.userInfo[noticeKey] as? Data else { return nil }
        return try? JSONDecoder().decode(Notice.self, from: data)
    }
}

/// Revisión en segundo plano. iOS decide cuándo ejecutarla (normalmente
/// varias veces al día si se usa la app); no hay garantía de inmediatez.
enum BackgroundRefresh {
    static let identifier = "es.opoalert.app.refresh"

    static func register() {
        BGTaskScheduler.shared.register(forTaskWithIdentifier: identifier, using: nil) { task in
            guard let task = task as? BGAppRefreshTask else { return }
            schedule()
            let work = Task {
                do {
                    let result = try await Synchronizer(store: Store()).sync()
                    await AlertNotifications.show(result.alertMatches)
                    task.setTaskCompleted(success: true)
                } catch {
                    task.setTaskCompleted(success: false)
                }
            }
            task.expirationHandler = { work.cancel() }
        }
    }

    /// Como en Android: se pide una revisión cada hora (iOS puede espaciarla más).
    static func schedule() {
        let request = BGAppRefreshTaskRequest(identifier: identifier)
        request.earliestBeginDate = Date(timeIntervalSinceNow: 60 * 60)
        try? BGTaskScheduler.shared.submit(request)
    }
}
