import Foundation

public struct StoreError: LocalizedError, Equatable {
    public let message: String
    public init(_ message: String) { self.message = message }
    public var errorDescription: String? { message }
}

/// Todo se guarda solo en el móvil: ni cuentas ni envíos a terceros.
/// Las claves son las de la app Android (`opoalert_store`).
public final class Store: @unchecked Sendable {
    public static let maxRules = 20

    private let defaults: UserDefaults
    private let lock = NSLock()

    public init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
    }

    private enum Key {
        static let entries = "entries"
        static let lastSync = "last_sync"
        static let lastSource = "last_source_v04"
        static let lastHistory = "last_history_v04"
        static let seen = "seen_notice_ids_v1"
        static let initializedPrefix = "province_initialized_v1_"
        static let selected = "selected_provinces_v1"
        static let pickerShown = "province_picker_seen_v1"
        static let favorites = "favorites_v2"
        static let rules = "keyword_alert_rules_v1"
        static let active = "active_sources_v1"
    }

    private func decode<T: Decodable>(_ type: T.Type, _ key: String) -> T? {
        guard let data = defaults.data(forKey: key) else { return nil }
        return try? JSONDecoder().decode(type, from: data)
    }

    private func encode<T: Encodable>(_ value: T, _ key: String) {
        defaults.set(try? JSONEncoder().encode(value), forKey: key)
    }

    /// Lista que se salta los elementos dañados en lugar de perderlo todo.
    private func lenientList<T: Decodable>(_ type: T.Type, _ key: String) -> [T] {
        guard let data = defaults.data(forKey: key),
              let items = try? JSONDecoder().decode([Lenient<T>].self, from: data) else { return [] }
        return items.compactMap(\.value)
    }

    // MARK: Fuentes activas y fuentes seguidas

    public var activeSources: Set<String>? {
        defaults.data(forKey: Key.active).flatMap(SourceCatalog.parseActive)
    }

    public func saveActive(_ data: Data) {
        guard SourceCatalog.parseActive(data) != nil else { return }
        defaults.set(data, forKey: Key.active)
    }

    public var availableSources: [Source] { SourceCatalog.available(active: activeSources) }

    public var selected: Set<String> {
        let stored = Set((defaults.string(forKey: Key.selected) ?? "VA").split(separator: ",").map {
            $0.trimmingCharacters(in: .whitespaces)
        })
        let chosen = Set(availableSources.map(\.code).filter { stored.contains($0) })
        return chosen.isEmpty ? ["VA"] : chosen
    }

    @discardableResult
    public func saveSelected(_ chosen: Set<String>) -> Bool {
        guard !chosen.isEmpty else { return false }
        defaults.set(availableSources.map(\.code).filter { chosen.contains($0) }.joined(separator: ","),
                     forKey: Key.selected)
        return true
    }

    public var pickerShown: Bool {
        get { defaults.bool(forKey: Key.pickerShown) }
        set { defaults.set(newValue, forKey: Key.pickerShown) }
    }

    // MARK: Favoritas (la ficha completa, para que no desaparezca con el feed)

    public var favorites: [Notice] {
        var seen = Set<String>()
        return lenientList(Notice.self, Key.favorites).filter { seen.insert($0.id).inserted }
    }

    public func isFavorite(_ id: String) -> Bool { favorites.contains { $0.id == id } }

    /// true si queda guardada; false si se ha quitado.
    @discardableResult
    public func toggleFavorite(_ notice: Notice) -> Bool {
        lock.lock()
        defer { lock.unlock() }
        let current = favorites
        let wasSaved = current.contains { $0.id == notice.id }
        encode(wasSaved ? current.filter { $0.id != notice.id } : [notice] + current, Key.favorites)
        return !wasSaved
    }

    // MARK: Alertas

    public var rules: [AlertRule] {
        var seen = Set<String>()
        let known = Set(Source.all.map(\.code))
        return lenientList(AlertRule.self, Key.rules).compactMap { rule -> AlertRule? in
            var rule = rule
            rule.sources = rule.sources.intersection(known)
            let phrase = rule.phrase.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !rule.id.isEmpty, !phrase.isEmpty, !rule.sources.isEmpty, seen.insert(rule.id).inserted else { return nil }
            rule.phrase = phrase
            return rule
        }.prefix(Store.maxRules).map { $0 }
    }

    @discardableResult
    public func upsertRule(id: String?, input: String, sources: Set<String>) throws -> AlertRule {
        lock.lock()
        defer { lock.unlock() }
        let phrase = input.trimmingCharacters(in: .whitespacesAndNewlines)
            .replacingOccurrences(of: #"\s+"#, with: " ", options: .regularExpression)
        guard (3...70).contains(phrase.count) else { throw StoreError("Escribe entre 3 y 70 caracteres.") }
        guard !sources.isEmpty else { throw StoreError("Selecciona al menos una provincia.") }
        let current = rules
        if let id, !current.contains(where: { $0.id == id }) { throw StoreError("La alerta ya no existe.") }
        if id == nil && current.count >= Store.maxRules { throw StoreError("Máximo de 20 alertas.") }
        let key = SearchText.normalize(phrase)
        if current.contains(where: { $0.id != id && SearchText.normalize($0.phrase) == key && $0.sources == sources }) {
            throw StoreError("Ya tienes esa alerta para las mismas provincias.")
        }
        let old = current.first { $0.id == id }
        let rule = AlertRule(id: id ?? UUID().uuidString.lowercased(), phrase: phrase, sources: sources,
                             enabled: old?.enabled ?? true)
        encode(old == nil ? [rule] + current : current.map { $0.id == id ? rule : $0 }, Key.rules)
        return rule
    }

    public func enableRule(_ id: String, _ enabled: Bool) {
        lock.lock()
        defer { lock.unlock() }
        encode(rules.map { rule -> AlertRule in
            var rule = rule
            if rule.id == id { rule.enabled = enabled }
            return rule
        }, Key.rules)
    }

    public func removeRule(_ id: String) {
        lock.lock()
        defer { lock.unlock() }
        encode(rules.filter { $0.id != id }, Key.rules)
    }

    // MARK: Caché de la última revisión

    public var cached: [Notice] { lenientList(Notice.self, Key.entries) }
    public var lastSync: String { defaults.string(forKey: Key.lastSync) ?? "" }
    public var lastSource: String { defaults.string(forKey: Key.lastSource) ?? "" }
    public var lastHistory: String { defaults.string(forKey: Key.lastHistory) ?? "" }
    var seen: [String]? { decode([String].self, Key.seen) }

    func isInitialized(_ code: String) -> Bool { defaults.bool(forKey: Key.initializedPrefix + code) }

    func saveSync(entries: [Notice], lastSync: String, source: String, history: String,
                  seen: [String], initialized: [String]) {
        encode(entries, Key.entries)
        defaults.set(lastSync, forKey: Key.lastSync)
        defaults.set(source, forKey: Key.lastSource)
        defaults.set(history, forKey: Key.lastHistory)
        encode(seen, Key.seen)
        for code in initialized { defaults.set(true, forKey: Key.initializedPrefix + code) }
    }
}

private struct Lenient<T: Decodable>: Decodable {
    let value: T?
    init(from decoder: Decoder) throws { value = try? T(from: decoder) }
}
