import Foundation

/// Texto y enlace al compartir (como `ShareText.kt`).
public enum ShareText {
    public static let appLink = "https://mjtbapps.github.io/OpoAlert/app.html"
    public static let subject = "Convocatoria de empleo público · OpoAlert"

    public static func bulletin(_ id: String) -> String {
        let prefixes: [(String, String)] = [
            ("CIDO", "CIDO"), ("BOE-A-", "BOE"), ("MD-", "BOCM"), ("CM-", "DOCM"), ("CY-", "BOCYL"),
            ("EX-", "DOE"), ("MU-", "BORM"), ("DV-", "DOGV"), ("DC-", "DOGC"), ("BJ-", "BOJA"),
            ("AO-", "BOA"), ("DG-", "DOG"), ("PV-", "BOPV"),
        ]
        return prefixes.first { id.hasPrefix($0.0) }?.1 ?? "BOP"
    }
}

/// Seguimiento de una favorita, solo en el móvil (`FavoriteAgenda.kt`, misma clave y campos):
/// fecha orientativa de fin del plazo, si ya se ha presentado y una nota propia.
public struct AgendaEntry: Codable, Equatable, Sendable {
    public var until: String?
    public var checked: Bool
    public var submitted: Bool
    public var note: String?

    public static let noteMax = 300

    public init(until: String? = nil, checked: Bool = false, submitted: Bool = false, note: String? = nil) {
        self.until = until
        self.checked = checked
        self.submitted = submitted
        self.note = note
    }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        until = AgendaDates.valid(try? c.decodeIfPresent(String.self, forKey: .until))
        checked = (try? c.decodeIfPresent(Bool.self, forKey: .checked)) ?? false
        submitted = (try? c.decodeIfPresent(Bool.self, forKey: .submitted)) ?? false
        note = (try? c.decodeIfPresent(String.self, forKey: .note)).flatMap { $0 }.map { String($0.prefix(Self.noteMax)) }
    }

    public var noteText: String { note ?? "" }
}

/// Fechas «AAAA-MM-DD» de la agenda, en hora de España.
public enum AgendaDates {
    public static let calendar: Calendar = {
        var c = Calendar(identifier: .gregorian)
        c.timeZone = TimeZone(identifier: "Europe/Madrid")!
        c.locale = Locale(identifier: "es_ES")
        return c
    }()

    /// La fecha si tiene la forma y existe; si no, nil.
    public static func valid(_ raw: String?) -> String? {
        guard let raw, raw.range(of: #"^20\d\d-\d\d-\d\d$"#, options: .regularExpression) != nil,
              date(raw) != nil else { return nil }
        return raw
    }

    public static func date(_ raw: String) -> Date? {
        let p = raw.split(separator: "-").compactMap { Int($0) }
        guard p.count == 3 else { return nil }
        let comps = DateComponents(year: p[0], month: p[1], day: p[2])
        guard let d = calendar.date(from: comps),
              calendar.dateComponents([.year, .month, .day], from: d) == comps else { return nil }
        return d
    }

    public static func today(_ now: Date = Date()) -> Date { calendar.startOfDay(for: now) }

    /// Días de hoy a [raw] (negativo si ya pasó).
    public static func daysLeft(_ raw: String, now: Date = Date()) -> Int? {
        guard let end = date(raw) else { return nil }
        return calendar.dateComponents([.day], from: today(now), to: end).day
    }

    /// «20/11».
    public static func short(_ raw: String) -> String {
        let p = raw.split(separator: "-")
        return p.count == 3 ? "\(p[2])/\(p[1])" : raw
    }

    /// «jueves 20 de noviembre».
    public static func long(_ raw: String) -> String {
        guard let d = date(raw) else { return raw }
        let f = DateFormatter()
        f.calendar = calendar
        f.timeZone = calendar.timeZone
        f.locale = calendar.locale
        f.dateFormat = "EEEE d 'de' MMMM"
        return f.string(from: d)
    }

    /// Día del recordatorio: dos antes del fin, o hoy si ya queda menos; nil si ya pasó
    /// (`DeadlineReminder.remindDay`).
    public static func remindDay(_ raw: String, now: Date = Date()) -> Date? {
        guard let left = daysLeft(raw, now: now), left >= 0, let end = date(raw) else { return nil }
        return left > 2 ? calendar.date(byAdding: .day, value: -2, to: end) : today(now)
    }
}

public enum FavoriteAgenda {
    /// Primero las que acaban antes, luego sin fecha, luego pasadas y al final las presentadas.
    public static func sort(_ favorites: [Notice], agenda: [String: AgendaEntry], now: Date = Date()) -> [Notice] {
        func rank(_ n: Notice) -> (Int, Int) {
            guard let e = agenda[n.id] else { return (1, 0) }
            if e.submitted { return (3, 0) }
            guard let until = e.until, let left = AgendaDates.daysLeft(until, now: now) else { return (1, 0) }
            return left < 0 ? (2, 0) : (0, left)
        }
        return favorites.enumerated().sorted { a, b in
            let (ra, rb) = (rank(a.element), rank(b.element))
            if ra.0 != rb.0 { return ra.0 < rb.0 }
            if ra.0 == 0 && ra.1 != rb.1 { return ra.1 < rb.1 }
            return a.offset < b.offset
        }.map(\.element)
    }
}

extension Store {
    private static let agendaKey = "favorite_agenda_v1"

    public var agenda: [String: AgendaEntry] {
        guard let data = defaults.string(forKey: Self.agendaKey)?.data(using: .utf8)
                ?? defaults.data(forKey: Self.agendaKey),
              let raw = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else { return [:] }
        var out: [String: AgendaEntry] = [:]
        for (id, value) in raw {
            guard let json = try? JSONSerialization.data(withJSONObject: value),
                  let entry = try? JSONDecoder().decode(AgendaEntry.self, from: json) else { continue }
            out[id] = entry
        }
        return out
    }

    public func updateAgenda(_ id: String, _ change: (inout AgendaEntry) -> Void) {
        var all = agenda
        var entry = all[id] ?? AgendaEntry()
        change(&entry)
        if let note = entry.note { entry.note = note.isEmpty ? nil : String(note.prefix(AgendaEntry.noteMax)) }
        all[id] = entry
        saveAgenda(all)
    }

    public func removeAgenda(_ id: String) {
        var all = agenda
        if all.removeValue(forKey: id) != nil { saveAgenda(all) }
    }

    private func saveAgenda(_ all: [String: AgendaEntry]) {
        guard let data = try? JSONEncoder().encode(all), let text = String(data: data, encoding: .utf8) else { return }
        defaults.set(text, forKey: Self.agendaKey)
    }
}
