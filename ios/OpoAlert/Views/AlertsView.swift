import OpoAlertCore
import SwiftUI

/// «Mis alertas»: avisos solo cuando aparecen anuncios nuevos que coinciden.
struct AlertsView: View {
    @EnvironmentObject private var model: AppModel
    @State private var editing: AlertDraft?

    var body: some View {
        List {
            Section {
                Text("Recibe avisos únicamente cuando aparezcan anuncios nuevos que coincidan con tus puestos o palabras clave. Las tildes y mayúsculas no importan.")
                    .font(.subheadline)
                    .foregroundStyle(Color(hex: 0x45546C))
                Button {
                    editing = AlertDraft(rule: nil, followed: model.selected)
                } label: {
                    Label("Crear nueva alerta", systemImage: "plus")
                        .font(.headline)
                        .frame(maxWidth: .infinity, minHeight: 44)
                }
                .buttonStyle(.borderedProminent)
                .disabled(model.rules.count >= Store.maxRules)
                if model.rules.count >= Store.maxRules {
                    Text("Puedes guardar hasta 20 alertas.").font(.caption).foregroundStyle(Palette.slate)
                }
            }
            Section(activeText) {
                if model.rules.isEmpty {
                    Text("Aún no tienes alertas.")
                        .font(.footnote)
                        .foregroundStyle(Palette.slate)
                }
                ForEach(model.rules) { rule in
                    HStack {
                        Button {
                            editing = AlertDraft(rule: rule, followed: model.selected)
                        } label: {
                            VStack(alignment: .leading, spacing: 3) {
                                Text(rule.phrase).font(.body.weight(.semibold)).foregroundStyle(Palette.navy)
                                Text(sourcesText(rule)).font(.caption).foregroundStyle(Palette.slate).lineLimit(2)
                            }
                        }
                        .buttonStyle(.plain)
                        Spacer()
                        Toggle("Activa", isOn: Binding(get: { rule.enabled },
                                                       set: { model.enableRule(rule, $0) }))
                            .labelsHidden()
                    }
                }
                .onDelete { offsets in
                    offsets.map { model.rules[$0] }.forEach(model.removeRule)
                }
            }
            Section {
                Text("Los avisos llegan cuando iOS permite a OpoAlert revisar en segundo plano (normalmente varias veces al día). No hay garantía de inmediatez: abre la app para revisar al momento.")
                    .font(.caption)
                    .foregroundStyle(Palette.slate)
            }
        }
        .navigationTitle("Mis alertas")
        .sheet(item: $editing) { AlertEditView(draft: $0) }
    }

    private var activeText: String {
        let active = model.rules.filter(\.enabled).count
        return active == 1 ? "1 activa" : "\(active) activas"
    }

    private func sourcesText(_ rule: AlertRule) -> String {
        Source.all.filter { rule.sources.contains($0.code) }.map(\.label).joined(separator: ", ")
    }
}

struct AlertDraft: Identifiable {
    let id = UUID()
    let rule: AlertRule?
    let followed: Set<String>
}

struct AlertEditView: View {
    let draft: AlertDraft
    @EnvironmentObject private var model: AppModel
    @Environment(\.dismiss) private var dismiss
    @State private var phrase = ""
    @State private var sources: Set<String> = []
    @State private var expanded: Set<String> = []
    @State private var error: String?

    var body: some View {
        let groups = SourceCatalog.groups(model.available)
        NavigationStack {
            Form {
                Section {
                    TextField("Ej.: policía local, auxiliar administrativo", text: $phrase)
                        .textInputAutocapitalization(.never)
                } header: {
                    Text("Puesto o palabras clave")
                } footer: {
                    Text("Avisa cuando el anuncio contiene todas las palabras, en cualquier orden.")
                }
                // Misma lista por comunidades que «Elegir boletines».
                SourceSections(chosen: $sources, expanded: $expanded, groups: groups)
                if let error {
                    Text(error).foregroundStyle(.red)
                }
            }
            .navigationTitle(draft.rule == nil ? "Nueva alerta" : "Editar alerta")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) { Button("Cancelar") { dismiss() } }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Guardar") {
                        do {
                            try model.saveRule(id: draft.rule?.id, phrase: phrase, sources: sources)
                            dismiss()
                        } catch {
                            self.error = error.localizedDescription
                        }
                    }
                }
            }
        }
        .onAppear {
            phrase = draft.rule?.phrase ?? ""
            sources = draft.rule?.sources ?? draft.followed
            expanded = SourceSections.initiallyExpanded(groups, chosen: sources)
        }
    }
}
