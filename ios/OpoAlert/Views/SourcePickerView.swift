import OpoAlertCore
import SwiftUI

/// «Elegir boletines»: el BOE y cada comunidad con sus provincias y boletines.
/// Es un menú de navegación: nunca se usa la ubicación del móvil.
struct SourcePickerView: View {
    let firstLaunch: Bool
    @EnvironmentObject private var model: AppModel
    @Environment(\.dismiss) private var dismiss
    @State private var chosen: Set<String> = []
    @State private var expanded: Set<String> = []

    var body: some View {
        let groups = SourceCatalog.groups(model.available)
        NavigationStack {
            List {
                Section {
                    Text("Elige qué boletines quieres consultar. Puedes seguir varias provincias.")
                        .font(.subheadline)
                        .foregroundStyle(Palette.slate)
                    Toggle(isOn: binding(Source.boe.code)) {
                        VStack(alignment: .leading) {
                            Text("BOE").font(.body.weight(.semibold))
                            Text("Toda España").font(.caption).foregroundStyle(Palette.slate)
                        }
                    }
                }
                ForEach(groups) { community in
                    Section {
                        DisclosureGroup(isExpanded: expandedBinding(community.name)) {
                            let all = Set(community.sources.map(\.code))
                            Toggle("Todas", isOn: Binding(
                                get: { all.isSubset(of: chosen) },
                                set: { on in if on { chosen.formUnion(all) } else { chosen.subtract(all) } }
                            ))
                            .font(.subheadline.weight(.semibold))
                            ForEach(community.territories) { territory in
                                ForEach(territory.sources) { source in
                                    Toggle(isOn: binding(source.code)) {
                                        VStack(alignment: .leading) {
                                            Text(territory.name)
                                            Text(source.name).font(.caption).foregroundStyle(Palette.slate)
                                        }
                                    }
                                }
                            }
                        } label: {
                            let count = community.sources.filter { chosen.contains($0.code) }.count
                            HStack {
                                Text(community.name).font(.body.weight(.semibold))
                                Spacer()
                                Text("\(count)/\(community.sources.count)")
                                    .font(.caption)
                                    .foregroundStyle(count > 0 ? Palette.blue : Palette.slate)
                            }
                        }
                    }
                }
                Section {
                    Text("CIDO es un catálogo de procesos selectivos y no sustituye al BOP. Solo se muestran boletines con lectura auditada de los últimos 30 días.")
                        .font(.caption)
                        .foregroundStyle(Palette.slate)
                }
            }
            .navigationTitle("Elegir boletines")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                if !firstLaunch {
                    ToolbarItem(placement: .cancellationAction) {
                        Button("Cancelar") { dismiss() }
                    }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Guardar") {
                        if model.saveSources(chosen) { dismiss() }
                    }
                    .disabled(chosen.isEmpty)
                }
            }
        }
        .interactiveDismissDisabled(firstLaunch)
        .onAppear {
            chosen = model.selected
            expanded = Set(groups.filter { $0.sources.contains { chosen.contains($0.code) } }.map(\.name))
        }
        .onDisappear { model.closePicker() }
    }

    private func binding(_ code: String) -> Binding<Bool> {
        Binding(get: { chosen.contains(code) },
                set: { on in if on { chosen.insert(code) } else { chosen.remove(code) } })
    }

    private func expandedBinding(_ name: String) -> Binding<Bool> {
        Binding(get: { expanded.contains(name) },
                set: { on in if on { expanded.insert(name) } else { expanded.remove(name) } })
    }
}
