import Foundation

public struct BulletinTerritory: Identifiable, Hashable, Sendable {
    public let name: String
    public let sources: [Source]
    public var id: String { name }
}

public struct BulletinCommunity: Identifiable, Hashable, Sendable {
    public let name: String
    public let territories: [BulletinTerritory]
    public var id: String { name }
    public var sources: [Source] { territories.flatMap(\.sources) }
}

/// Agrupación del selector «Elegir boletines» (`SourceCatalog.kt`).
/// La comunidad es un grupo de navegación, NUNCA la ubicación del móvil.
public enum SourceCatalog {
    public static let activeURL = URL(string: "https://mjtbapps.github.io/OpoAlert/fuentes_activas.json")!

    /// Fuentes que se pueden elegir: las activas en la web o, sin esa lista, todas menos las pendientes.
    public static func available(active: Set<String>?) -> [Source] {
        if let active { return Source.all.filter { active.contains($0.code) } }
        return Source.all.filter { !Fuentes.pendingDailyFeed.contains($0.code) }
    }

    /// Solo códigos que conoce esta versión; una lista casi vacía se considera dañada.
    public static func parseActive(_ data: Data) -> Set<String>? {
        guard let root = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any] else { return nil }
        let known = Set(Source.all.map(\.code))
        let codes = Set((root["active"] as? [Any] ?? []).compactMap { $0 as? String }.filter { known.contains($0) })
        return codes.count >= 5 ? codes : nil
    }

    public static func groups(_ sources: [Source]) -> [BulletinCommunity] {
        let placed = Dictionary(grouping: sources.filter { !$0.isBOE && $0.community != nil }) { $0.community! }
        return placed.map { community, values in
            let ranking = Fuentes.territoryOrder[community] ?? []
            let places = Dictionary(grouping: values) { $0.territory ?? community }
            let territories = places.map { name, provincial in
                // Orden estable: el de la lista oficial, con los catálogos CIDO al final.
                let ordered = Source.all.filter { provincial.contains($0) }
                return BulletinTerritory(name: name, sources: ordered.filter { !$0.isCido } + ordered.filter(\.isCido))
            }.sorted { a, b in
                let ia = ranking.firstIndex(of: a.name) ?? Int.max, ib = ranking.firstIndex(of: b.name) ?? Int.max
                return ia != ib ? ia < ib : a.name < b.name
            }
            return BulletinCommunity(name: community, territories: territories)
        }.sorted { a, b in
            let ia = Fuentes.communityOrder.firstIndex(of: a.name) ?? Int.max
            let ib = Fuentes.communityOrder.firstIndex(of: b.name) ?? Int.max
            return ia != ib ? ia < ib : a.name < b.name
        }
    }

    /// «Valencia», «3 provincias + BOE»…
    public static func display(_ chosen: Set<String>, available: [Source]) -> String {
        let locals = available.filter { chosen.contains($0.code) && !$0.isBOE }
        let local: String? = locals.isEmpty ? nil : (locals.count == 1 ? locals[0].label : "\(locals.count) provincias")
        let boe: String? = chosen.contains(Source.boe.code) ? "BOE" : nil
        return [local, boe].compactMap { $0 }.joined(separator: " + ")
    }
}
