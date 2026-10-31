import Foundation

public struct FeedError: LocalizedError, Equatable {
    public let message: String
    public init(_ message: String) { self.message = message }
    public var errorDescription: String? { message }
}

/// El backend audita cada boletín antes de publicarlo; la app vuelve a comprobarlo.
public struct RemoteFeed: Sendable {
    public let notices: [Notice]
    public let status: String
    public let historyStatus: String
}

/// Lectura y validación de los feeds publicados (`RemoteFeedReader.kt`).
public enum FeedReader {
    public static let maxBytes = 5_000_000

    /// Las direcciones nunca vienen del usuario: solo los JSON auditados de GitHub Pages.
    public static func checkedURL(_ address: String, for source: Source) throws -> URL {
        guard address == source.feedURL else { throw FeedError("Fuente provincial no autorizada") }
        guard let parts = URLComponents(string: address), let url = parts.url,
              parts.scheme?.lowercased() == "https", parts.host == "mjtbapps.github.io",
              parts.user == nil, parts.password == nil, parts.port == nil, parts.fragment == nil else {
            throw FeedError("La fuente debe ser una URL HTTPS de OpoAlert")
        }
        return url
    }

    public static func fetch(_ source: Source, session: URLSession = .shared) async throws -> RemoteFeed {
        let url = try checkedURL(source.feedURL, for: source)
        var request = URLRequest(url: url, cachePolicy: .reloadIgnoringLocalCacheData, timeoutInterval: 20)
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        request.setValue("OpoAlert-iOS/1.0", forHTTPHeaderField: "User-Agent")
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, (200...299).contains(http.statusCode) else {
            let code = (response as? HTTPURLResponse)?.statusCode ?? 0
            throw FeedError("Fuente \(source.label): HTTP \(code)")
        }
        guard data.count <= maxBytes else { throw FeedError("JSON provincial demasiado grande") }
        return try parse(data, source: source)
    }

    public static func parse(_ data: Data, source: Source) throws -> RemoteFeed {
        let label = source.label
        guard let root = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any] else {
            throw FeedError("Fuente \(label): JSON invalido")
        }
        guard let coverage = root["coverage"] as? [String: Any] else {
            throw FeedError("\(label): falta auditoria oficial")
        }
        guard coverage["complete"] as? Bool == true else { throw FeedError("\(label): lectura no confirmada") }
        guard root["source"] as? String == source.expectedSource else {
            throw FeedError("\(label): fuente oficial inesperada")
        }
        if source.code != "VA" && root["province"] as? String != label {
            throw FeedError("\(label): identificacion provincial incorrecta")
        }
        guard let checked = root["lastCheckedUTC"] as? String, !blank(checked) else {
            throw FeedError("\(label): falta fecha de comprobacion")
        }
        guard let history = root["historyCoverage"] as? [String: Any],
              history["complete"] as? Bool == true else {
            throw FeedError("\(label): falta auditoria de 30 dias")
        }
        let rangeStart = history["rangeStart"] as? String ?? ""
        let rangeEnd = history["rangeEnd"] as? String ?? ""
        guard !blank(rangeStart), !blank(rangeEnd) else { throw FeedError("\(label): periodo de fechas ausente") }
        guard let array = root["notices"] as? [Any] else { throw FeedError("\(label): falta lista de anuncios") }
        guard array.count <= 5000 else { throw FeedError("Demasiados anuncios de \(label)") }
        var notices: [Notice] = []
        var ids = Set<String>()
        for item in array {
            guard let object = item as? [String: Any],
                  let raw = try? JSONSerialization.data(withJSONObject: object),
                  let notice = try? JSONDecoder().decode(Notice.self, from: raw),
                  !blank(notice.title), source.matchesId(notice.id),
                  notice.province == label, source.isOfficialLink(notice.url) else {
                throw FeedError("\(label): anuncio o enlace no validado")
            }
            guard ids.insert(notice.id).inserted else { throw FeedError("\(label): anuncios duplicados") }
            notices.append(notice)
        }
        let bulletins = history["bulletins"] as? [Any] ?? []
        let current = bulletins.last.map { "\($0)" } ?? (coverage["bulletin"].map { "\($0)" } ?? "?")
        let read = (coverage["announcementsRead"] as? NSNumber)?.intValue ?? 0
        let status = source.isCido ? "\(label): CIDO · \(read) procesos"
            : "\(label): \(source.shortName) \(current) · \(read) anuncios"
        let historyStatus = source.isCido
            ? "CIDO (actualizaciones de procesos): \(rangeStart) a \(rangeEnd)"
            : "Histórico verificado: \(rangeStart) a \(rangeEnd)"
        return RemoteFeed(notices: notices, status: status, historyStatus: historyStatus)
    }

    private static func blank(_ text: String) -> Bool {
        text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }
}
