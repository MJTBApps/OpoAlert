import Foundation

/// Alerta privada, guardada solo en el móvil (`AlertRule.kt`).
/// Las fuentes de cada alerta se cruzan con las fuentes que se siguen.
public struct AlertRule: Codable, Hashable, Identifiable, Sendable {
    public let id: String
    public var phrase: String
    /// Códigos de fuente (VA, AL, ES…).
    public var sources: Set<String>
    public var enabled: Bool

    public init(id: String, phrase: String, sources: Set<String>, enabled: Bool = true) {
        self.id = id
        self.phrase = phrase
        self.sources = sources
        self.enabled = enabled
    }

    // Mismo formato que Android: «provinces» con los códigos.
    enum CodingKeys: String, CodingKey { case id, phrase, sources = "provinces", enabled }
}

public enum SmartAlertMatcher {
    /// Todos los términos, sin importar tildes, mayúsculas ni el orden de las palabras.
    public static func matches(_ rule: AlertRule, _ notice: Notice, followed: Set<String>) -> Bool {
        guard rule.enabled, !rule.sources.isEmpty else { return false }
        let actual = Source.of(notice).code
        guard rule.sources.contains(actual), followed.contains(actual) else { return false }
        let terms = SearchText.normalize(rule.phrase).split(whereSeparator: \.isWhitespace)
        if terms.isEmpty { return false }
        let haystack = SearchText.normalize(notice.title + " " + notice.entity)
        return terms.allSatisfy { haystack.contains($0) }
    }

    /// Una misma convocatoria genera como máximo un aviso aunque coincida con varias alertas.
    public static func matching(_ newNotices: [Notice], rules: [AlertRule], followed: Set<String>) -> [Notice] {
        guard rules.contains(where: \.enabled), !followed.isEmpty else { return [] }
        var seen = Set<String>()
        return newNotices.filter { notice in
            rules.contains { matches($0, notice, followed: followed) } && seen.insert(notice.id).inserted
        }
    }
}

/// Identificadores de anuncios ya vistos, los más recientes primero (`SeenIds`).
public enum SeenIds {
    /// Cubre de sobra los feeds de 30 días de todas las fuentes.
    public static let max = 15000

    public static func merge(_ fresh: [String], _ previous: [String]) -> [String] {
        var seen = Set<String>()
        return Array((fresh + previous).filter { seen.insert($0).inserted }.prefix(max))
    }
}
