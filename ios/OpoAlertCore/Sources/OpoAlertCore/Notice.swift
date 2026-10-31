import Foundation

/// Un anuncio publicado, tal como llega en los feeds de GitHub Pages (`Notice.kt`).
public struct Notice: Codable, Hashable, Identifiable, Sendable {
    public let id: String
    public let title: String
    public let entity: String
    /// dd/MM/yyyy
    public let date: String
    public let bulletin: String
    /// «Plaza / oposición», «Bolsa de trabajo»…
    public let type: String
    public let url: String
    public let province: String

    public init(id: String, title: String, entity: String, date: String, bulletin: String,
                type: String, url: String, province: String? = nil) {
        self.id = id
        self.title = title
        self.entity = entity
        self.date = date
        self.bulletin = bulletin
        self.type = type
        self.url = url
        self.province = province ?? Source.fromNoticeId(id).label
    }

    enum CodingKeys: String, CodingKey { case id, title, entity, date, bulletin, type, url, province }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        let id = try c.decode(String.self, forKey: .id)
        self.init(
            id: id,
            title: try c.decode(String.self, forKey: .title),
            entity: (try? c.decodeIfPresent(String.self, forKey: .entity)) ?? "Administración pública",
            date: try c.decode(String.self, forKey: .date),
            bulletin: Notice.text(c, .bulletin) ?? "",
            type: (try? c.decodeIfPresent(String.self, forKey: .type)) ?? "Plaza",
            url: try c.decode(String.self, forKey: .url),
            province: try? c.decodeIfPresent(String.self, forKey: .province)
        )
    }

    private static func text(_ c: KeyedDecodingContainer<CodingKeys>, _ key: CodingKeys) -> String? {
        if let value = try? c.decodeIfPresent(String.self, forKey: key) { return value }
        if let value = try? c.decodeIfPresent(Int.self, forKey: key) { return String(value) }
        return nil
    }

    public var isPool: Bool { type.hasPrefix("Bolsa") }
    public var isPosition: Bool { type.hasPrefix("Plaza") }
    public var isProcedureUpdate: Bool { NoticeText.isProcedureUpdate(title) }
    public var headline: String { NoticeText.headline(title) }

    /// «BOP Valencia 207», «BOE · España»… (pie de cada tarjeta, como en Android).
    public var origin: String {
        if id.hasPrefix("CIDO") { return "CIDO · \(province)" }
        if id.hasPrefix("BOE-A-") { return "BOE · España" }
        if id.hasPrefix("MD-") { return "BOCM · Madrid n.º \(bulletin)" }
        if id.hasPrefix("CM-") { return "DOCM · Castilla-La Mancha n.º \(bulletin)" }
        if id.hasPrefix("TA-") { return "BOP · Tarragona \(bulletin)" }
        if id.hasPrefix("BA-") { return "BOP · Barcelona \(bulletin)" }
        if id.hasPrefix("GI-") { return "BOP · Girona n.º \(bulletin)" }
        return "BOP \(province) \(bulletin)"
    }

    /// Texto para compartir: siempre con el enlace oficial y el aviso de comprobarlo.
    public var shareText: String {
        let kind: String
        if id.hasPrefix("CIDO") { kind = "CIDO" }
        else if id.hasPrefix("BOE-A-") { kind = "BOE" }
        else if id.hasPrefix("MD-") { kind = "BOCM" }
        else if id.hasPrefix("CM-") { kind = "DOCM" }
        else { kind = "BOP" }
        return "\(headline)\n\(entity)\n\(kind) \(province) · \(date) · Referencia \(id)\n\(url)\n\n" +
            "Comprueba siempre el anuncio oficial y los plazos."
    }
}

public enum NoticeDates {
    private static let calendar: Calendar = {
        var c = Calendar(identifier: .gregorian)
        c.timeZone = TimeZone(identifier: "Europe/Madrid")!
        return c
    }()

    /// dd/MM/yyyy estricto; nil si la fecha no existe.
    public static func parse(_ text: String) -> DateComponents? {
        let parts = text.split(separator: "/")
        guard parts.count == 3, parts[0].count == 2, parts[1].count == 2, parts[2].count == 4,
              let d = Int(parts[0]), let m = Int(parts[1]), let y = Int(parts[2]) else { return nil }
        let components = DateComponents(year: y, month: m, day: d)
        guard let date = calendar.date(from: components),
              calendar.dateComponents([.year, .month, .day], from: date) == components else { return nil }
        return components
    }

    /// Publicado en los últimos 30 días (hoy incluido), como `MainActivity.isRecent`.
    public static func isRecent(_ text: String, today: Date = Date()) -> Bool {
        guard let parsed = parse(text), let day = calendar.date(from: parsed) else { return false }
        let end = calendar.startOfDay(for: today)
        guard let start = calendar.date(byAdding: .day, value: -29, to: end) else { return false }
        return day >= start && day <= end
    }

    /// Clave ordenable yyyyMMdd.
    public static func sortKey(_ text: String) -> String {
        let parts = text.split(separator: "/")
        return parts.count == 3 ? "\(parts[2])\(parts[1])\(parts[0])" : text
    }
}
