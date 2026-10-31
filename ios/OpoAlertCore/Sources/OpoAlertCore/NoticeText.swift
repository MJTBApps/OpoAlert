import Foundation

/// Resúmenes fieles de los títulos oficiales (`NoticeText.kt`). El PDF manda.
public enum NoticeText {
    private static let rolePattern =
        #"(?i)(?:\b(?:\d+|un|una|dues|dos|tres|quatre|cuatro|cinc|cinco|sis|seis|set|siete|vuit|ocho|nou|nueve|deu|diez)\s+(?:places?|plazas?)\s+(?:de\b|d')|\bborsa\b|\bbolsa de trabajo\b|\bplaça\s+(?:de\b|d')|\bplaza\s+(?:de\b|d')|\bplaces\s+(?:de\b|d')|\bplazas\s+(?:de\b|d'))"#
    private static let procedures = [
        "designació de membres", "designación de miembros", "nomenament de membres",
        "modificació de les bases", "modificación de las bases", "rectificació de les bases",
        "correcció d'errades", "corrección de errores", "estimació del recurs",
        "estimación del recurso", "adición de una plaza", "ampliación de plazas",
        "addició d'una plaça",
    ]
    private static let cutMarkers = [
        " corresponent a ", " correspondiente a ", " correspondientes a ",
        " incloses en ", " inclosa en ", " incluidas en ", " incluida en ",
        " incluidos en ", " incluido en ", " mitjançant el sistema ",
        " mediante el sistema ", " expedient ", " expediente ",
    ]

    /// Un trámite (corrección, tribunal…) nunca debe parecer una plaza nueva.
    public static func isProcedureUpdate(_ officialTitle: String) -> Bool {
        let lower = officialTitle.lowercased()
        return procedures.contains { lower.contains($0) }
    }

    /// Quita la fórmula «Anunci de [organisme] sobre…» y, si es seguro, empieza
    /// en la plaza o bolsa que cita el texto. No traduce ni inventa nada.
    public static func headline(_ officialTitle: String) -> String {
        let whole = officialTitle.trimmingCharacters(in: .whitespacesAndNewlines)
        let content: String
        if let range = whole.range(of: " sobre ", options: .caseInsensitive) {
            content = String(whole[range.upperBound...])
        } else {
            content = whole
        }
        if isProcedureUpdate(officialTitle) {
            return capitalizedFirst(trimDots(content.trimmingCharacters(in: .whitespacesAndNewlines)))
        }
        let subject = Patterns.firstRange(rolePattern, content).map { String(content[$0.lowerBound...]) } ?? content
        let normalized = trimDots(subject.replacingOccurrences(of: #"\s+"#, with: " ", options: .regularExpression)
            .trimmingCharacters(in: .whitespacesAndNewlines))
        let cut = cutMarkers.compactMap { marker -> Int? in
            guard let range = normalized.range(of: marker, options: .caseInsensitive) else { return nil }
            let offset = normalized.distance(from: normalized.startIndex, to: range.lowerBound)
            return offset > 44 ? offset : nil
        }.min()
        let title = cut.map { String(normalized.prefix($0)) } ?? normalized
        return capitalizedFirst(title)
    }

    private static func trimDots(_ text: String) -> String {
        var result = Substring(text)
        while result.hasSuffix(".") { result = result.dropLast() }
        return String(result)
    }

    private static func capitalizedFirst(_ text: String) -> String {
        guard let first = text.first else { return text }
        return first.uppercased() + text.dropFirst()
    }
}

/// Solo datos escritos en el encabezado oficial (`NoticeDetails.kt`).
/// OpoAlert NO calcula plazos de solicitud ni presume fechas de cierre.
public enum NoticeDetails {
    private static let places = #"(?i)(?<![\p{L}\d])(\d{1,3}|[\p{L}]+)\s+(?:plazas?|pla[çc]a|places)\b"#
    private static let words: [String: Int] = [
        "una": 1, "un": 1, "uno": 1, "dos": 2, "dues": 2, "tres": 3, "cuatro": 4, "quatre": 4,
        "cinco": 5, "cinc": 5, "seis": 6, "sis": 6, "siete": 7, "set": 7, "ocho": 8, "vuit": 8,
        "nueve": 9, "nou": 9, "diez": 10, "deu": 10, "once": 11, "onze": 11, "doce": 12,
        "dotze": 12, "trece": 13, "tretze": 13, "catorce": 14, "catorze": 14, "quince": 15,
        "quinze": 15, "dieciséis": 16, "dieciseis": 16, "setze": 16, "diecisiete": 17,
        "disset": 17, "dieciocho": 18, "divuit": 18, "diecinueve": 19, "dinou": 19,
        "veinte": 20, "vint": 20,
    ]
    private static let group = #"(?i)\b(?:subgrupo|grupo|subgrup|grup)\s*:?\s*(A1|A2|C1|C2|B|E)\b"#

    public static func placesInTitle(_ title: String) -> Int? {
        if NoticeText.isProcedureUpdate(title) { return nil }
        var found: [Int] = []
        for match in Patterns.matches(places, title) {
            let value = match[1]
            guard let number = Int(value) ?? words[value.lowercased()] else { continue }
            if !found.contains(number) { found.append(number) }
        }
        guard found.count == 1, let only = found.first, only > 0 else { return nil }
        return only
    }

    public static func groupInTitle(_ title: String) -> String? {
        Patterns.matches(group, title).first.map { $0[1].uppercased() }
    }

    /// Los datos oficiales no incluyen un plazo de solicitudes verificado.
    public static func deadlineLabel() -> String { "Consultar bases" }
}

/// Búsqueda sin tildes ni mayúsculas, conservando la ñ (`SearchText.kt`).
public enum SearchText {
    private static let enyeMarker = "\u{E000}"

    public static func normalize(_ text: String) -> String {
        let lower = text.precomposedStringWithCanonicalMapping.lowercased()
            .replacingOccurrences(of: "ñ", with: enyeMarker)
        let scalars = lower.decomposedStringWithCanonicalMapping.unicodeScalars.filter { scalar in
            switch scalar.properties.generalCategory {
            case .nonspacingMark, .spacingMark, .enclosingMark: return false
            default: return true
            }
        }
        return String(String.UnicodeScalarView(scalars)).replacingOccurrences(of: enyeMarker, with: "ñ")
    }

    public static func matchesNormalized(_ normalizedQuery: String, _ values: String...) -> Bool {
        normalizedQuery.isEmpty || values.contains { normalize($0).contains(normalizedQuery) }
    }
}

/// «VA: 61 · AL: 20 · Sin datos verificados: X» → «81 anuncios · 2 boletines · sin datos: X».
public enum SyncSummary {
    public static func describe(_ raw: String) -> String {
        let parts = raw.components(separatedBy: " · Sin datos verificados: ")
        let counts = Patterns.matches(#"\b[A-Z]{2}:\s*(\d+)"#, parts[0]).compactMap { Int($0[1]) }
        if counts.isEmpty { return raw }
        let notices = counts.reduce(0, +)
        let text = "\(notices) anuncio\(notices == 1 ? "" : "s") · " +
            (counts.count == 1 ? "1 boletín" : "\(counts.count) boletines")
        return parts.count >= 2 ? "\(text) · sin datos: \(parts.dropFirst().joined(separator: " · Sin datos verificados: "))" : text
    }

    /// «31/10/2026 07:40» → «Act. 31/10 07:40».
    public static func compactUpdated(_ raw: String) -> String {
        guard let m = Patterns.matches(#"(\d{2})/(\d{2})/\d{4}\s+(\d{2}:\d{2})"#, raw).first else { return "Act. \(raw)" }
        return "Act. \(m[1])/\(m[2]) \(m[3])"
    }

    /// «Histórico verificado: 2026-10-02 a 2026-10-31» → «Histórico verificado · 02/10 – 31/10».
    public static func compactHistory(_ raw: String) -> String {
        if raw.range(of: "verificado", options: .caseInsensitive) == nil { return "Histórico pendiente de comprobar" }
        let dates = Patterns.matches(#"(\d{4})-(\d{2})-(\d{2})"#, raw).prefix(2)
        guard dates.count == 2 else { return "Histórico verificado · Últimos 30 días" }
        let a = dates[dates.startIndex], b = dates[dates.startIndex + 1]
        if a[1] == b[1] { return "Histórico verificado · \(a[3])/\(a[2]) – \(b[3])/\(b[2])" }
        return "Histórico verificado · \(a[3])/\(a[2])/\(a[1].suffix(2)) – \(b[3])/\(b[2])/\(b[1].suffix(2))"
    }
}
