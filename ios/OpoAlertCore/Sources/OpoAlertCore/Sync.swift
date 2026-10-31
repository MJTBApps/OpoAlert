import Foundation

public struct SyncResult: Sendable {
    public let all: [Notice]
    public let newOnes: [Notice]
    public let scanned: Int
    public let sourceMessage: String
    public let historyMessage: String
    public let alertMatches: [Notice]
}

/// Revisión de las fuentes seguidas (`Repository.sync` de Android).
public struct Synchronizer: Sendable {
    public static let cacheSize = 2000

    public typealias FeedFetcher = @Sendable (Source) async throws -> RemoteFeed
    public typealias ActiveFetcher = @Sendable () async -> Data?

    let store: Store
    let fetchFeed: FeedFetcher
    let fetchActive: ActiveFetcher

    public init(store: Store,
                fetchFeed: @escaping FeedFetcher = { try await FeedReader.fetch($0) },
                fetchActive: @escaping ActiveFetcher = Synchronizer.downloadActive) {
        self.store = store
        self.fetchFeed = fetchFeed
        self.fetchActive = fetchActive
    }

    /// Lista de fuentes activas de la web; sin conexión se conserva la anterior.
    @Sendable public static func downloadActive() async -> Data? {
        var request = URLRequest(url: SourceCatalog.activeURL, cachePolicy: .reloadIgnoringLocalCacheData,
                                 timeoutInterval: 15)
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        guard let (data, response) = try? await URLSession.shared.data(for: request),
              let http = response as? HTTPURLResponse, (200...299).contains(http.statusCode),
              data.count < 100_000 else { return nil }
        return data
    }

    public func sync(now: Date = Date()) async throws -> SyncResult {
        if let active = await fetchActive() { store.saveActive(active) }
        let chosen = store.selected
        // Las alertas creadas durante la descarga no reciben avisos de este mismo ciclo.
        let rulesAtStart = store.rules
        let old = store.cached
        // Los ya vistos no dependen de la caché de 2000, que solo sirve para la lista.
        let storedSeen = store.seen
        let seen = Set((storedSeen ?? []) + old.map(\.id))
        let sources = store.availableSources.filter { chosen.contains($0.code) }

        var results: [String: Result<RemoteFeed, Error>] = [:]
        await withTaskGroup(of: (String, Result<RemoteFeed, Error>).self) { group in
            for source in sources {
                group.addTask {
                    do { return (source.code, .success(try await fetchFeed(source))) }
                    catch { return (source.code, .failure(error)) }
                }
            }
            for await (code, result) in group { results[code] = result }
        }
        var downloaded: [(Source, RemoteFeed)] = []
        var failures: [String] = []
        for source in sources {
            switch results[source.code] {
            case .success(let feed)?: downloaded.append((source, feed))
            default: failures.append(source.label)
            }
        }
        guard !downloaded.isEmpty else {
            throw FeedError("No se ha podido consultar ninguna de las provincias seleccionadas")
        }

        let fresh = downloaded.flatMap(\.1.notices)
        let newOnes = downloaded.flatMap { source, feed -> [Notice] in
            // Primera revisión de una fuente: solo se rellena, sin avisos.
            guard store.isInitialized(source.code), storedSeen != nil else { return [] }
            return feed.notices.filter { !seen.contains($0.id) }
        }
        var ids = Set<String>()
        let merged = (fresh + old).filter { ids.insert($0.id).inserted }
            .sorted { a, b in
                let ka = NoticeDates.sortKey(a.date), kb = NoticeDates.sortKey(b.date)
                return ka != kb ? ka > kb : a.id > b.id
            }
            .prefix(Synchronizer.cacheSize).map { $0 }

        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "es_ES")
        formatter.dateFormat = "dd/MM/yyyy HH:mm"
        let counts = downloaded.map { "\($0.0.code): \($0.1.notices.count)" }.joined(separator: " · ")
        let status = failures.isEmpty ? counts : "\(counts) · Sin datos verificados: \(failures.joined(separator: ", "))"
        let history = failures.isEmpty ? downloaded[0].1.historyStatus
            : "Cobertura parcial: pendientes \(failures.joined(separator: ", "))"
        store.saveSync(entries: merged, lastSync: formatter.string(from: now), source: status, history: history,
                       seen: SeenIds.merge(fresh.map(\.id), storedSeen ?? []),
                       initialized: downloaded.map(\.0.code))
        let matches = SmartAlertMatcher.matching(newOnes, rules: rulesAtStart, followed: chosen)
        return SyncResult(all: merged, newOnes: newOnes, scanned: fresh.count, sourceMessage: status,
                          historyMessage: history, alertMatches: matches)
    }
}
