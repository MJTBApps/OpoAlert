import Foundation

/// Plazo de presentación tal como lo escribe el anuncio (`DeadlineStore.kt`).
/// OpoAlert no calcula fechas.
public struct Deadline: Equatable, Sendable {
    public let days: Int
    public let kind: String
    public let text: String
    public let page: Int
    public var label: String { "\(days) días \(kind)" }
}

/// `docs/plazos/<feed>.json`, un archivo por fuente (lo genera `backend/plazos.py`).
public enum Deadlines {
    private static let kinds: Set<String> = ["hábiles", "naturales"]

    public static func url(for source: Source) -> URL? {
        guard let slash = source.feedURL.lastIndex(of: "/") else { return nil }
        let base = source.feedURL[..<slash]
        let file = source.feedURL[source.feedURL.index(after: slash)...]
        return URL(string: "\(base)/plazos/\(file)")
    }

    /// Las mismas comprobaciones que el servidor: si algo no encaja, no se muestra.
    public static func parse(_ data: Data, noticeURL: String) -> Deadline? {
        guard let root = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              root["schemaVersion"] as? Int == 1,
              let items = root["items"] as? [String: Any],
              let item = items[noticeURL] as? [String: Any],
              let days = item["days"] as? Int, (1...90).contains(days),
              let kind = item["kind"] as? String, kinds.contains(kind),
              let page = item["page"] as? Int, page >= 1,
              let text = (item["text"] as? String)?.trimmingCharacters(in: .whitespacesAndNewlines),
              (20...400).contains(text.count) else { return nil }
        return Deadline(days: days, kind: kind, text: text, page: page)
    }

    /// Sede electrónica de quien convoca, copiada del anuncio (campo `sedes`;
    /// `DeadlineStore.parseSede` en Android). Solo HTTPS y un dominio con forma normal.
    public static func parseSede(_ data: Data, noticeURL: String) -> URL? {
        guard let root = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              root["schemaVersion"] as? Int == 1,
              let sedes = root["sedes"] as? [String: Any],
              let link = sedes[noticeURL] as? String,
              link.hasPrefix("https://"), link.count <= 120 else { return nil }
        var host = String(link.dropFirst("https://".count).prefix { $0 != "/" })
        if host.hasPrefix("www.") { host.removeFirst(4) }
        guard host.range(of: #"^([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+(es|cat|gal|eus|org|com|net|eu|online|info)$"#,
                         options: .regularExpression) != nil else { return nil }
        return URL(string: link)
    }

    public static func fetch(for notice: Notice, session: URLSession = .shared) async -> Deadline? {
        guard !notice.isProcedureUpdate, let data = await file(for: notice, session: session) else { return nil }
        return parse(data, noticeURL: notice.url)
    }

    /// Plazo y sede con una sola descarga.
    public static func fetchBoth(for notice: Notice, session: URLSession = .shared) async -> (Deadline?, URL?) {
        guard let data = await file(for: notice, session: session) else { return (nil, nil) }
        return (notice.isProcedureUpdate ? nil : parse(data, noticeURL: notice.url), parseSede(data, noticeURL: notice.url))
    }

    private static func file(for notice: Notice, session: URLSession) async -> Data? {
        guard OfficialDocument.isPdf(notice),
              let url = url(for: Source.of(notice)), url.scheme == "https", url.host == "mjtbapps.github.io" else { return nil }
        var request = URLRequest(url: url, cachePolicy: .returnCacheDataElseLoad, timeoutInterval: 15)
        request.setValue("OpoAlert-iOS/1.0", forHTTPHeaderField: "User-Agent")
        guard let (data, response) = try? await session.data(for: request),
              (response as? HTTPURLResponse)?.statusCode == 200, data.count < 3_000_000 else { return nil }
        return data
    }
}
