import OpoAlertCore
import SwiftUI
import UserNotifications

/// «Mis alertas»: avisos solo cuando aparecen anuncios nuevos que coinciden.
struct AlertsView: View {
    @EnvironmentObject private var model: AppModel
    @State private var editing: AlertDraft?
    @State private var showPremium = false
    @ObservedObject private var premium = PremiumStore.shared
    /// iOS tiene denegadas las notificaciones de OpoAlert: las alertas no pueden avisar.
    @State private var notificationsDenied = false
    @Environment(\.openURL) private var openURL
    @Environment(\.scenePhase) private var scenePhase

    var body: some View {
        List {
            if notificationsDenied && premium.isActive {
                Section {
                    Button {
                        if let url = URL(string: UIApplication.openSettingsURLString) { openURL(url) }
                    } label: {
                        VStack(alignment: .leading, spacing: 6) {
                            Label("Los avisos están desactivados", systemImage: "bell.slash.fill")
                                .font(.headline).foregroundStyle(Color(hex: 0x7A4A00))
                            Text("iOS tiene bloqueadas las notificaciones de OpoAlert y tus alertas no pueden avisarte. Toca aquí para permitirlas en Ajustes.")
                                .font(.subheadline).foregroundStyle(Color(hex: 0x7A5A2B))
                        }
                    }
                    .buttonStyle(.plain)
                    .listRowBackground(Color(hex: 0xFFF4E5))
                }
            }
            if !premium.isActive {
                Section {
                    Button { showPremium = true } label: {
                        VStack(alignment: .leading, spacing: 6) {
                            Label("Las alertas son de OpoAlert Premium", systemImage: "star.fill")
                                .font(.headline).foregroundStyle(Color(hex: 0x7A4A00))
                            Text("Te avisamos en cuanto sale una convocatoria de tu puesto y provincia, y sin publicidad. Toca aquí para ver el precio y la prueba gratuita.")
                                .font(.subheadline).foregroundStyle(Color(hex: 0x7A5A2B))
                        }
                    }
                    .buttonStyle(.plain)
                    .listRowBackground(Color(hex: 0xFFF7E8))
                }
            }
            Section {
                Text("Recibe avisos únicamente cuando aparezcan anuncios nuevos que coincidan con tus puestos o palabras clave. Las tildes y mayúsculas no importan.")
                    .font(.subheadline)
                    .foregroundStyle(Color(hex: 0x45546C))
                Button {
                    if premium.isActive { editing = AlertDraft(rule: nil, followed: model.selected) } else { showPremium = true }
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
                Text("Los avisos llegan cuando iOS permite a OpoAlert revisar en segundo plano (normalmente varias veces al día). No hay garantía de inmediatez: abre la app para revisar al momento. Si cierras la app deslizándola hacia arriba, iOS deja de avisar hasta que la vuelvas a abrir.")
                    .font(.caption)
                    .foregroundStyle(Palette.slate)
            }
        }
        .navigationTitle("Mis alertas")
        .sheet(item: $editing) { AlertEditView(draft: $0) }
        .sheet(isPresented: $showPremium) { PremiumView() }
        .task { await checkNotifications() }
        // Al volver de Ajustes (o tras responder al permiso) se comprueba de nuevo.
        .onChange(of: scenePhase) { phase in
            if phase == .active { Task { await checkNotifications() } }
        }
        .onChange(of: model.rules.count) { _ in Task { await checkNotifications() } }
    }

    private func checkNotifications() async {
        let settings = await UNUserNotificationCenter.current().notificationSettings()
        notificationsDenied = settings.authorizationStatus == .denied
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
