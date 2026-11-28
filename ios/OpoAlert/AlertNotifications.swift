import BackgroundTasks
import Foundation
import OpoAlertCore
import UserNotifications

/// Avisos locales: se generan en el propio móvil, sin servidor ni cuenta.
enum AlertNotifications {
    static let noticeKey = "notice"
    static let filterKey = "filter"

    static func requestPermission() async {
        let center = UNUserNotificationCenter.current()
        let settings = await center.notificationSettings()
        guard settings.authorizationStatus == .notDetermined else { return }
        _ = try? await center.requestAuthorization(options: [.alert, .sound, .badge])
    }

    /// Un aviso por revisión: con una sola convocatoria abre su ficha; con varias, la lista
    /// con el filtro «Avisos».
    static func show(_ matching: [Notice]) async {
        // Las alertas son de OpoAlert Premium.
        guard !matching.isEmpty, PremiumStore.isActiveStored else { return }
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
        } else {
            content.userInfo = [filterKey: NoticeFilter.alerts.rawValue]
        }
        let request = UNNotificationRequest(identifier: UUID().uuidString, content: content, trigger: nil)
        try? await center.add(request)
    }

    /// «Posible novedad en tu favorita» (seguimiento, 1.59.0, Premium): un aviso por favorita,
    /// con su propio identificador; tocarlo abre la ficha de la favorita.
    static func showFollowUps(_ news: [FollowUpNews]) async {
        guard !news.isEmpty, PremiumStore.isActiveStored else { return }
        let center = UNUserNotificationCenter.current()
        let settings = await center.notificationSettings()
        guard settings.authorizationStatus == .authorized || settings.authorizationStatus == .provisional else { return }
        // Se vuelve a mirar: si se quitó la favorita o se contestó «No» mientras se buscaba, no se avisa.
        let store = Store()
        let favorites = Dictionary(store.favorites.map { ($0.id, $0) }, uniquingKeysWith: { a, _ in a })
        for (favoriteId, items) in Dictionary(grouping: news, by: \.favorite.id) {
            guard let favorite = favorites[favoriteId] else { continue }
            let state = store.followUpState(favoriteId)
            let live = items.filter { n in state.items.contains { $0.notice.id == n.item.notice.id && $0.state != FollowUpItem.no } }
            guard let first = live.first else { continue }
            let content = UNMutableNotificationContent()
            content.title = "Posible novedad en tu favorita"
            let step = first.item.step + " · " + first.item.notice.date
            content.body = (live.count == 1 ? step : "\(live.count) posibles novedades · \(step)") + "\n" +
                String(favorite.headline.prefix(140)) + "\nComprueba siempre el anuncio oficial."
            content.sound = .default
            if let data = try? JSONEncoder().encode(favorite) { content.userInfo = [noticeKey: data] }
            let request = UNNotificationRequest(identifier: "seguimiento-" + favoriteId, content: content, trigger: nil)
            try? await center.add(request)
        }
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
                    let result = try await Synchronizer(store: Store(), followUps: PremiumStore.isActiveStored).sync()
                    await AlertNotifications.show(result.alertMatches)
                    await AlertNotifications.showFollowUps(result.followUps)
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
