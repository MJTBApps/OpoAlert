import OpoAlertCore
import SwiftUI
import UserNotifications

@main
struct OpoAlertApp: App {
    @UIApplicationDelegateAdaptor(AppDelegate.self) private var delegate
    @StateObject private var model = AppModel()
    @Environment(\.scenePhase) private var scenePhase

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(model)
                .tint(Palette.blue)
                .onAppear { delegate.attach(model) }
                .task { await model.refresh() }
        }
        .onChange(of: scenePhase) { phase in
            if phase == .background { BackgroundRefresh.schedule() }
            if phase == .active, !model.isRefreshing { Task { await model.refresh() } }
        }
    }
}

final class AppDelegate: NSObject, UIApplicationDelegate, UNUserNotificationCenterDelegate {
    private weak var model: AppModel?
    /// Aviso tocado con la app cerrada: llega antes que la pantalla y se aplica al aparecer.
    private var pending: (() -> Void)?

    @MainActor func attach(_ model: AppModel) {
        self.model = model
        pending?()
        pending = nil
    }

    func application(_ application: UIApplication,
                     didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil) -> Bool {
        UNUserNotificationCenter.current().delegate = self
        BackgroundRefresh.register()
        return true
    }

    /// Con la app abierta, el aviso también se muestra.
    func userNotificationCenter(_ center: UNUserNotificationCenter, willPresent notification: UNNotification,
                                withCompletionHandler completionHandler: @escaping (UNNotificationPresentationOptions) -> Void) {
        completionHandler([.banner, .list, .sound])
    }

    /// Al tocar el aviso: la ficha si era una sola convocatoria; si no, las alertas.
    func userNotificationCenter(_ center: UNUserNotificationCenter, didReceive response: UNNotificationResponse,
                                withCompletionHandler completionHandler: @escaping () -> Void) {
        let notice = AlertNotifications.notice(from: response)
        Task { @MainActor in
            let open = { [weak self] in
                guard let model = self?.model else { return }
                if let notice {
                    model.tab = .explore
                    model.openedNotice = notice
                } else {
                    model.tab = .alerts
                }
            }
            if self.model == nil { self.pending = open } else { open() }
            completionHandler()
        }
    }
}
