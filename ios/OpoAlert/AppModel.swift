import Foundation
import OpoAlertCore
import SwiftUI

enum NoticeFilter: String, CaseIterable, Identifiable {
    case all = "Todas", pools = "Bolsas", positions = "Plazas"
    var id: String { rawValue }

    func accepts(_ notice: Notice) -> Bool {
        switch self {
        case .all: return true
        case .pools: return notice.isPool
        case .positions: return notice.isPosition
        }
    }
}

/// Estado de la app: lo que se ve en pantalla sale siempre del `Store` local.
@MainActor
final class AppModel: ObservableObject {
    static let pageSize = 40

    let store: Store
    @Published private(set) var notices: [Notice] = []
    @Published private(set) var favorites: [Notice] = []
    @Published private(set) var rules: [AlertRule] = []
    @Published private(set) var selected: Set<String> = []
    @Published private(set) var available: [Source] = []
    @Published private(set) var lastSync = ""
    @Published private(set) var lastSource = ""
    @Published private(set) var lastHistory = ""
    @Published private(set) var isRefreshing = false
    @Published var message: String?
    @Published var showSourcePicker = false
    /// Ficha abierta desde un aviso.
    @Published var openedNotice: Notice?
    @Published var tab: AppTab = .explore

    init(store: Store = Store()) {
        self.store = store
        reload()
        showSourcePicker = !store.pickerShown
    }

    func reload() {
        notices = store.cached
        favorites = store.favorites
        rules = store.rules
        selected = store.selected
        available = store.availableSources
        lastSync = store.lastSync
        lastSource = store.lastSource
        lastHistory = store.lastHistory
    }

    // MARK: Revisión

    func refresh() async {
        guard !isRefreshing else { return }
        isRefreshing = true
        defer { isRefreshing = false }
        do {
            let result = try await Synchronizer(store: store).sync()
            await AlertNotifications.show(result.alertMatches)
            message = nil
        } catch {
            message = "Sin conexión: se muestran los últimos datos guardados."
        }
        reload()
    }

    // MARK: Lista

    var selectedLabels: Set<String> {
        Set(available.filter { selected.contains($0.code) }.map(\.label))
    }

    /// Anuncios de los últimos 30 días de las fuentes seguidas (como el contador de Android).
    var recentCount: Int {
        let labels = selectedLabels
        return notices.filter { labels.contains($0.province) && NoticeDates.isRecent($0.date) }.count
    }

    func explore(query: String, filter: NoticeFilter) -> [Notice] {
        let labels = selectedLabels
        return filtered(notices.filter { labels.contains($0.province) && NoticeDates.isRecent($0.date) },
                        query: query, filter: filter)
    }

    /// Las favoritas se ven aunque se deje de seguir su fuente, con la ficha más reciente si la hay.
    func favoriteList(query: String, filter: NoticeFilter) -> [Notice] {
        let latest = Dictionary(notices.map { ($0.id, $0) }, uniquingKeysWith: { first, _ in first })
        return filtered(favorites.map { latest[$0.id] ?? $0 }, query: query, filter: filter)
    }

    private func filtered(_ list: [Notice], query: String, filter: NoticeFilter) -> [Notice] {
        let normalized = SearchText.normalize(query.trimmingCharacters(in: .whitespacesAndNewlines))
        return list.filter { notice in
            filter.accepts(notice) &&
                SearchText.matchesNormalized(normalized, notice.title, notice.headline, notice.entity, notice.id)
        }
    }

    // MARK: Favoritas

    func isFavorite(_ notice: Notice) -> Bool { favorites.contains { $0.id == notice.id } }

    func toggleFavorite(_ notice: Notice) {
        store.toggleFavorite(notice)
        favorites = store.favorites
    }

    // MARK: Fuentes

    var followingText: String { SourceCatalog.display(selected, available: available) }

    func saveSources(_ chosen: Set<String>) -> Bool {
        guard store.saveSelected(chosen) else { return false }
        store.pickerShown = true
        reload()
        Task { await refresh() }
        return true
    }

    func closePicker() {
        store.pickerShown = true
        showSourcePicker = false
    }

    // MARK: Alertas

    func saveRule(id: String?, phrase: String, sources: Set<String>) throws {
        try store.upsertRule(id: id, input: phrase, sources: sources)
        rules = store.rules
        Task { await AlertNotifications.requestPermission() }
    }

    func enableRule(_ rule: AlertRule, _ enabled: Bool) {
        store.enableRule(rule.id, enabled)
        rules = store.rules
    }

    func removeRule(_ rule: AlertRule) {
        store.removeRule(rule.id)
        rules = store.rules
    }
}

enum AppTab: Hashable { case explore, favorites, alerts }
