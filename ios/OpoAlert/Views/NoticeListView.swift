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
            Section {
                Picker("Tipo", selection: $filter) {
                    ForEach(NoticeFilter.allCases) { Text($0.rawValue).tag($0) }
                }
                .pickerStyle(.segmented)
                .listRowBackground(Color.clear)
                .listRowInsets(EdgeInsets(top: 4, leading: 16, bottom: 4, trailing: 16))
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
                    ForEach(shown.prefix(limit)) { notice in
                        NoticeRow(notice: notice)
                            .listRowSeparator(.hidden)
                            .listRowBackground(Color.clear)
                            .listRowInsets(EdgeInsets(top: 4, leading: 16, bottom: 4, trailing: 16))
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
        .searchable(text: $query, prompt: "Buscar puesto, organismo o referencia")
        .refreshable { await model.refresh() }
        .onChange(of: query) { _ in limit = AppModel.pageSize }
        .onChange(of: filter) { _ in limit = AppModel.pageSize }
        .navigationDestination(for: Notice.self) { NoticeDetailView(notice: $0) }
        .toolbar {
            ToolbarItem(placement: .navigationBarTrailing) {
                Menu {
                    Button { Task { await model.refresh() } } label: { Label("Actualizar", systemImage: "arrow.clockwise") }
                    Button { model.showSourcePicker = true } label: { Label("Elegir boletines", systemImage: "list.bullet") }
                    Button { showAbout = true } label: { Label("Acerca de OpoAlert", systemImage: "info.circle") }
                } label: {
                    if model.isRefreshing { ProgressView() } else { Image(systemName: "ellipsis.circle") }
                }
                .accessibilityLabel("Opciones")
            }
        }
        .sheet(isPresented: $showAbout) { AboutView() }
    }

    private var emptyMessage: String {
        if mode == .favorites && model.favorites.isEmpty {
            return "Aún no tienes favoritas. Toca la estrella de una convocatoria para guardarla aquí."
        }
        if model.notices.isEmpty {
            return model.isRefreshing ? "Consultando los boletines…"
                : "Todavía no hay convocatorias. Desliza hacia abajo para consultar los boletines."
        }
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
