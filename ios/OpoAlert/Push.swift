import FirebaseCore
import FirebaseMessaging
import OpoAlertCore
import UIKit

/// Aviso silencioso desde GitHub (1.54.0), igual que `Push.kt` en Android.
/// `backend/aviso_fcm.py` manda un mensaje al tema «convocatorias» cuando hay
/// convocatorias nuevas; el iPhone descarga los feeds y compara con sus alertas,
/// que nunca salen del teléfono. Sin los datos de Firebase (secretos FIREBASE_IOS_*
/// al compilar) no hace nada y queda la revisión en segundo plano de iOS.
enum Push {
    static let topic = "convocatorias"

    private static func value(_ key: String) -> String {
        (Bundle.main.object(forInfoDictionaryKey: key) as? String ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
    }

    /// Firebase cierra la app (NSException) si el identificador no tiene la forma
    /// «1:NÚMERO:ios:HEX» (fallo de la 1.54.0 al abrirla): sin datos válidos, no se inicia.
    static var configured: Bool {
        let appId = value("OpoFcmAppId"), sender = value("OpoFcmSenderId")
        let parts = appId.split(separator: ":", omittingEmptySubsequences: false)
        guard parts.count == 4, parts[0] == "1", parts[1] == Substring(sender), parts[2] == "ios",
              !sender.isEmpty, sender.allSatisfy(\.isNumber),
              parts[3].allSatisfy(\.isHexDigit), !parts[3].isEmpty else { return false }
        return ["OpoFcmApiKey", "OpoFcmProjectId"].allSatisfy { key in
            let v = value(key)
            return !v.isEmpty && !v.contains("=") && !v.contains(" ") && !v.contains("\"")
        }
    }

    static func start(_ application: UIApplication) {
        guard configured else { return }
        if FirebaseApp.app() == nil {
            let options = FirebaseOptions(googleAppID: value("OpoFcmAppId"), gcmSenderID: value("OpoFcmSenderId"))
            options.apiKey = value("OpoFcmApiKey")
            options.projectID = value("OpoFcmProjectId")
            options.bundleID = Bundle.main.bundleIdentifier ?? "es.opoalert.app"
            FirebaseApp.configure(options: options)
        }
        // El aviso es silencioso: no pide permiso de notificaciones.
        application.registerForRemoteNotifications()
    }

    static func didRegister(deviceToken: Data) {
        guard configured, FirebaseApp.app() != nil else { return }
        Messaging.messaging().apnsToken = deviceToken
        Messaging.messaging().subscribe(toTopic: topic)
    }

    /// Revisión al llegar el aviso (iOS da unos 30 segundos).
    static func handle(_ userInfo: [AnyHashable: Any]) async -> UIBackgroundFetchResult {
        guard userInfo["tipo"] as? String == "feeds" else { return .noData }
        do {
            let result = try await Synchronizer(store: Store()).sync()
            await AlertNotifications.show(result.alertMatches)
            return result.alertMatches.isEmpty ? .noData : .newData
        } catch {
            return .failed
        }
    }
}
