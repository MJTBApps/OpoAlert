import OpoAlertCore
import SwiftUI

/// Lista de convocatorias (Explorar) o de favoritas, con búsqueda y filtro.
struct NoticeListView: View {
    enum Mode { case explore, favorites }

    let mode: Mode
    @EnvironmentObject private var model: AppModel
    @State private var query = ""
    @State private var filter = NoticeFilter.all
    @State private var limit = AppModel.pageSize
    @State private var showAbout = false
    @State private var showPremium = false
    @ObservedObject private var ads = Ads.shared
    @ObservedObject private var premium = PremiumStore.shared

    private var shown: [Notice] {
        mode == .explore ? model.explore(query: query, filter: filter)
            : model.favoriteList(query: query, filter: filter)
    }

    var body: some View {
        let shown = self.shown
        List {
            if mode == .explore {
                Section { SummaryCard(showPicker: { model.showSourcePicker = true }) }
                    .listRowInsets(EdgeInsets(top: 8, leading: 16, bottom: 8, trailing: 16))
            }
            // Favoritas: solo las que has marcado, sin filtros.
            if mode == .explore {
            Section {
                Picker("Tipo", selection: $filter) {
                    ForEach(NoticeFilter.allCases) { option in
                        Text(label(option)).tag(option)
                    }
                }
                .pickerStyle(.segmented)
                .listRowBackground(Color.clear)
                .listRowInsets(EdgeInsets(top: 4, leading: 16, bottom: 4, trailing: 16))
            }
            }
            Section {
                if shown.isEmpty {
                    Text(emptyMessage)
                        .font(.footnote)
                        .foregroundStyle(Palette.slate)
                        .multilineTextAlignment(.center)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 30)
                        .listRowBackground(Color.clear)
                } else {
                    ForEach(Array(shown.prefix(limit).enumerated()), id: \.element.id) { index, notice in
                        NoticeRow(notice: notice)
                            .listRowSeparator(.hidden)
                            .listRowBackground(Color.clear)
                            .listRowInsets(EdgeInsets(top: 4, leading: 16, bottom: 4, trailing: 16))
                        // Un anuncio cada 8 convocatorias, como mucho 5 (sin anuncios con Premium).
                        if mode == .explore && ads.ready && !premium.isActive && index % Ads.listAdEvery == 3
                            && index / Ads.listAdEvery < Ads.maxListAds {
                            BannerAdView(adUnitID: ads.bannerID)
                                .frame(width: 320, height: 50)
                                .frame(maxWidth: .infinity)
                                .listRowSeparator(.hidden)
                                .listRowBackground(Color.clear)
                        }
                    }
                    if shown.count > limit {
                        Button {
                            limit += AppModel.pageSize
                        } label: {
                            Text("Ver \(min(AppModel.pageSize, shown.count - limit)) más · \(shown.count) resultados")
                                .font(.subheadline.bold())
                                .frame(maxWidth: .infinity, minHeight: 44)
                        }
                        .buttonStyle(.bordered)
                        .listRowBackground(Color.clear)
                        .listRowSeparator(.hidden)
                    }
                    Text("Consulta siempre las bases oficiales y los plazos de inscripción.")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                        .frame(maxWidth: .infinity)
                        .listRowBackground(Color.clear)
                        .listRowSeparator(.hidden)
                }
            } header: {
                Text(mode == .favorites ? "Mis favoritas · \(shown.count)" : "Convocatorias · \(shown.count)")
            }
        }
        .listStyle(.plain)
        .background(Palette.background)
        .scrollContentBackground(.hidden)
        .navigationTitle(mode == .favorites ? "Favoritas" : "OpoAlert")
        // La barra de búsqueda se queda fija arriba al bajar por la lista.
        .searchable(text: $query, placement: .navigationBarDrawer(displayMode: .always), prompt: "Buscar puesto, organismo o referencia")
        .refreshable { await model.refresh() }
        .onChange(of: query) { _ in limit = AppModel.pageSize }
        .onChange(of: filter) { option in
            // Las convocatorias de las alertas van con las alertas: son de Premium.
            if option == .alerts && !premium.isActive {
                filter = .all
                showPremium = true
            }
        }
        .onAppear(perform: applyRequestedFilter)
        .onChange(of: model.requestedFilter) { _ in applyRequestedFilter() }
        .onChange(of: filter) { _ in limit = AppModel.pageSize }
        .navigationDestination(for: Notice.self) { NoticeDetailView(notice: $0) }
        .toolbar {
            ToolbarItem(placement: .navigationBarTrailing) {
                Menu {
                    Button { Task { await model.refresh() } } label: { Label("Actualizar", systemImage: "arrow.clockwise") }
                    Button { model.showSourcePicker = true } label: { Label("Elegir boletines", systemImage: "list.bullet") }
                    Button { showPremium = true } label: {
                        Label(premium.isActive ? "OpoAlert Premium ✓" : "OpoAlert Premium", systemImage: "star.circle")
                    }
                    if ads.privacyOptionsRequired {
                        Button { ads.showPrivacyOptions() } label: { Label("Privacidad y publicidad", systemImage: "hand.raised") }
                    }
                    Button { showAbout = true } label: { Label("Acerca de OpoAlert", systemImage: "info.circle") }
                } label: {
                    if model.isRefreshing { ProgressView() } else { Image(systemName: "ellipsis.circle") }
                }
                .accessibilityLabel("Opciones")
            }
        }
        .sheet(isPresented: $showAbout) { AboutView() }
        .sheet(isPresented: $showPremium) { PremiumView() }
    }

    private func label(_ option: NoticeFilter) -> String {
        // Sin número: en la barra no cabe.
        option.rawValue
    }

    /// Un aviso con varias convocatorias abre la lista con el filtro «Avisos».
    private func applyRequestedFilter() {
        guard mode == .explore, let requested = model.requestedFilter else { return }
        model.requestedFilter = nil
        query = ""
        filter = requested
    }

    private var emptyMessage: String {
        if mode == .favorites && model.favorites.isEmpty {
            return "Aún no tienes favoritas. Toca la estrella de una convocatoria para guardarla aquí."
        }
        if model.notices.isEmpty {
            return model.isRefreshing ? "Consultando los boletines…"
                : "Todavía no hay convocatorias. Desliza hacia abajo para consultar los boletines."
        }
        if filter == .fresh { return "No hay convocatorias nuevas desde tu última visita." }
        if filter == .alerts && !model.rules.contains(where: \.enabled) {
            return "Aún no tienes alertas activas. Créalas en «Alertas» y aquí verás las convocatorias que encuentren."
        }
        if filter == .alerts { return "Ninguna convocatoria de los últimos 30 días coincide con tus alertas." }
        return "No hay convocatorias que coincidan con tu búsqueda."
    }
}

/// Resumen de la última revisión: número de anuncios, fuentes y periodo verificado.
struct SummaryCard: View {
    let showPicker: () -> Void
    @EnvironmentObject private var model: AppModel

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(alignment: .firstTextBaseline) {
                Text("\(model.recentCount)")
                    .font(.system(size: 24, weight: .bold))
                    .foregroundStyle(Palette.navy)
                Text("convocatorias · 30 días")
                    .font(.footnote)
                    .foregroundStyle(Palette.slate)
                Spacer()
                Text("★ \(model.favorites.count)")
                    .font(.footnote.bold())
                    .foregroundStyle(Palette.star)
            }
            Button(action: showPicker) {
                HStack {
                    Image(systemName: "mappin.and.ellipse")
                    Text("Siguiendo: \(model.followingText)")
                        .lineLimit(1)
                    Spacer()
                    Image(systemName: "chevron.right").font(.caption)
                }
                .font(.subheadline.weight(.semibold))
            }
            .buttonStyle(.borderless)
            Text(statusLine)
                .font(.caption)
                .foregroundStyle(Palette.slate)
                .lineLimit(1)
            Text(SyncSummary.compactHistory(model.lastHistory))
                .font(.caption)
                .foregroundStyle(Palette.slate)
                .lineLimit(1)
            if let message = model.message {
                Text(message)
                    .font(.caption)
                    .foregroundStyle(.orange)
            }
        }
        .padding(12)
        .background(Color.white, in: RoundedRectangle(cornerRadius: 16))
        .overlay(RoundedRectangle(cornerRadius: 16).stroke(Palette.border))
    }

    private var statusLine: String {
        let updated = model.isRefreshing ? "Actualizando…"
            : (model.lastSync.isEmpty ? "Sin consultar" : SyncSummary.compactUpdated(model.lastSync))
        let source = model.lastSource.isEmpty ? "Fuentes: \(model.followingText)" : SyncSummary.describe(model.lastSource)
        return "\(updated) · \(source)"
    }
}
