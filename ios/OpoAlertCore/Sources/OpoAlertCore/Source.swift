import Foundation

/// Una fuente oficial (boletín o catálogo) con las mismas reglas que `Province.kt`.
/// La lista completa está en `Fuentes.generated.swift`, generada desde Android.
public struct Source: Hashable, Identifiable, Sendable {
    public let code: String
    public let label: String
    public let feedURL: String
    public let expectedSource: String
    public let pdfHost: String
    public let pdfPathPrefix: String
    public let idPattern: String
    public let extraPaths: [String]
    /// Comunidad y provincia del selector «Elegir boletines» (nil solo para el BOE).
    public let community: String?
    public let territory: String?
    /// «BOP · boletín provincial», «CIDO · procesos selectivos»…
    public let name: String
    /// Siglas para el estado de la revisión (BOP, BOE, DOGV…).
    public let shortName: String
    /// Nombre completo del boletín para la ficha.
    public let fullName: String
    public let isCido: Bool

    public var id: String { code }
    public var isBOE: Bool { code == "ES" }

    public func allowsOfficialPath(_ path: String) -> Bool {
        path.hasPrefix(pdfPathPrefix) || extraPaths.contains(path)
    }

    /// Coincidencia completa del identificador, como `Regex.matches` en Kotlin.
    public func matchesId(_ id: String) -> Bool {
        Patterns.fullMatch(idPattern, id)
    }

    /// Solo enlaces HTTPS al dominio y la ruta oficiales de la fuente.
    public func isOfficialLink(_ address: String) -> Bool {
        guard let parts = URLComponents(string: address),
              parts.scheme?.lowercased() == "https",
              parts.host == pdfHost,
              parts.user == nil, parts.password == nil else { return false }
        return allowsOfficialPath(parts.percentEncodedPath)
    }
}

extension Source {
    public static let all = Fuentes.all
    public static let boe = all.first { $0.code == "ES" }!
    public static let valencia = all.first { $0.code == "VA" }!

    public static func code(_ code: String) -> Source? { all.first { $0.code == code } }
    public static func fromLabel(_ label: String) -> Source? { all.first { $0.label == label } }

    /// Fuente de un anuncio según su identificador (`Province.fromNoticeId`).
    public static func fromNoticeId(_ id: String) -> Source {
        let code = Fuentes.idPrefixes.first { id.hasPrefix($0.0) }?.1 ?? Fuentes.fallbackCode
        return Source.code(code)!
    }

    /// La fuente real de un anuncio: por su provincia y, si no, por su identificador.
    public static func of(_ notice: Notice) -> Source {
        fromLabel(notice.province) ?? fromNoticeId(notice.id)
    }
}

enum Patterns {
    private static var cache: [String: NSRegularExpression] = [:]
    private static let lock = NSLock()

    static func regex(_ pattern: String) -> NSRegularExpression {
        lock.lock()
        defer { lock.unlock() }
        if let found = cache[pattern] { return found }
        let compiled = try! NSRegularExpression(pattern: pattern)
        cache[pattern] = compiled
        return compiled
    }

    static func fullMatch(_ pattern: String, _ text: String) -> Bool {
        regex(#"\A(?:"# + pattern + #")\z"#)
            .firstMatch(in: text, range: NSRange(text.startIndex..., in: text)) != nil
    }

    static func matches(_ pattern: String, _ text: String) -> [[String]] {
        regex(pattern).matches(in: text, range: NSRange(text.startIndex..., in: text)).map { match in
            (0..<match.numberOfRanges).map { index in
                Range(match.range(at: index), in: text).map { String(text[$0]) } ?? ""
            }
        }
    }

    static func firstRange(_ pattern: String, _ text: String) -> Range<String.Index>? {
        regex(pattern).firstMatch(in: text, range: NSRange(text.startIndex..., in: text))
            .flatMap { Range($0.range, in: text) }
    }
}
