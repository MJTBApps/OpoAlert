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

    public static func fetch(for notice: Notice, session: URLSession = .shared) async -> Deadline? {
        guard OfficialDocument.isPdf(notice), !notice.isProcedureUpdate,
              let url = url(for: Source.of(notice)), url.scheme == "https", url.host == "mjtbapps.github.io" else { return nil }
        var request = URLRequest(url: url, cachePolicy: .returnCacheDataElseLoad, timeoutInterval: 15)
        request.setValue("OpoAlert-iOS/1.0", forHTTPHeaderField: "User-Agent")
        guard let (data, response) = try? await session.data(for: request),
              (response as? HTTPURLResponse)?.statusCode == 200, data.count < 3_000_000 else { return nil }
        return parse(data, noticeURL: notice.url)
    }
}
