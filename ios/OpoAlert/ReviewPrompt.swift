import Foundation
import StoreKit
import UIKit

/// Valoración en el App Store sin salir de la app (`ReviewPrompt.kt`, mismas reglas): al volver
/// a la lista tras una ficha, si se han abierto 5 fichas, se ha usado la app 3 días distintos
/// y se instaló hace 3 días o más. Como mucho 3 veces y con 4 meses entre una y otra; Apple
/// además limita a 3 ventanas al año y no dice si se ha valorado.
@MainActor
enum ReviewPrompt {
    private static let openedKey = "review_opened_v1"
    private static let daysKey = "review_days_v1"
    private static let lastKey = "review_last_v1"
    private static let countKey = "review_count_v1"
    private static let firstKey = "review_first_use_v1"

    nonisolated static func shouldAsk(opened: Int, days: Int, installedDays: Int, times: Int, daysSinceLast: Int) -> Bool {
        opened >= 5 && days >= 3 && installedDays >= 3 && times < 3 && (times == 0 || daysSinceLast >= 120)
    }

    private static func dayNumber(_ date: Date = Date()) -> Int {
        Int(date.timeIntervalSince1970 / 86_400)
    }

    static func noticeOpened() {
        let d = UserDefaults.standard
        if d.object(forKey: firstKey) == nil { d.set(dayNumber(), forKey: firstKey) }
        var days = Set(d.stringArray(forKey: daysKey) ?? [])
        days.insert(String(dayNumber()))
        d.set(Array(days.sorted().suffix(10)), forKey: daysKey)
        d.set(d.integer(forKey: openedKey) + 1, forKey: openedKey)
    }

    static func maybeAsk() {
        guard !CaptureMode.isOn else { return }
        let d = UserDefaults.standard
        let today = dayNumber()
        let times = d.integer(forKey: countKey)
        let first = d.object(forKey: firstKey) as? Int ?? today
        guard shouldAsk(opened: d.integer(forKey: openedKey), days: (d.stringArray(forKey: daysKey) ?? []).count,
                        installedDays: today - first, times: times,
                        daysSinceLast: today - d.integer(forKey: lastKey)) else { return }
        d.set(times + 1, forKey: countKey)
        d.set(today, forKey: lastKey)
        Task { @MainActor in
            // Después de la animación de volver a la lista.
            try? await Task.sleep(nanoseconds: 1_200_000_000)
            guard let scene = UIApplication.shared.connectedScenes
                .first(where: { $0.activationState == .foregroundActive }) as? UIWindowScene else { return }
            SKStoreReviewController.requestReview(in: scene)
        }
    }
}
