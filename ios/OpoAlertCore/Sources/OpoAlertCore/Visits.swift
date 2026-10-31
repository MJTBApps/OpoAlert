import Foundation

/// «Nuevas desde tu última visita» (`VisitStore.kt`). Una visita termina cuando la app
/// pasa más de 15 minutos sin usarse. Es nueva la convocatoria que no se había cargado en
/// visitas anteriores, salvo las de un boletín recién añadido. Solo en el móvil.
public struct VisitTracker {
    public static let visitGap: TimeInterval = 15 * 60
    private static let maxIds = 20000
    private enum Key {
        static let seen = "seen_ids_v1", seenSources = "seen_sources_v1"
        static let current = "visit_ids_v1", currentSources = "visit_sources_v1"
        static let lastActive = "last_active_ms_v1"
    }
    private let defaults: UserDefaults

    public init(defaults: UserDefaults = .standard) { self.defaults = defaults }

    private func set(_ key: String) -> Set<String> { Set(defaults.stringArray(forKey: key) ?? []) }
    private func save(_ value: Set<String>, _ key: String) { defaults.set(Array(value), forKey: key) }

    public func startVisit(now: Date = Date()) {
        let last = defaults.double(forKey: Key.lastActive) / 1000
        guard now.timeIntervalSince1970 - last >= Self.visitGap else { return }
        let current = set(Key.current)
        let seen = set(Key.seen).union(current)
        save(seen.count > Self.maxIds ? current : seen, Key.seen)
        save(set(Key.seenSources).union(set(Key.currentSources)), Key.seenSources)
        save([], Key.current)
        save([], Key.currentSources)
        defaults.set(now.timeIntervalSince1970 * 1000, forKey: Key.lastActive)
    }

    public func remember(_ notices: [Notice], now: Date = Date()) {
        save(set(Key.current).union(notices.map(\.id)), Key.current)
        save(set(Key.currentSources).union(notices.map(\.province)), Key.currentSources)
        defaults.set(now.timeIntervalSince1970 * 1000, forKey: Key.lastActive)
    }

    public func newIds(_ notices: [Notice]) -> Set<String> {
        let seen = set(Key.seen), sources = set(Key.seenSources)
        return Set(notices.filter { sources.contains($0.province) && !seen.contains($0.id) }.map(\.id))
    }
}
