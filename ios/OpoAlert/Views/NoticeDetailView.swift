import OpoAlertCore
import SwiftUI

/// Ficha de una convocatoria. Solo muestra lo que dice el anuncio oficial (la única fecha
/// calculada es la orientativa de `plazo_fin.py`, marcada como tal) y nada de requisitos inventados.
struct NoticeDetailView: View {
    let notice: Notice
    @EnvironmentObject private var model: AppModel
    @Environment(\.openURL) private var openURL
    @State private var linkRejected = false
    @State private var pdfLink: PdfLink?
    @State private var deadline: Deadline?
    @State private var sede: URL?
    @ObservedObject private var ads = Ads.shared
    @ObservedObject private var premium = PremiumStore.shared

    private var source: Source { Source.of(notice) }

    var body: some View {
        let favorite = model.isFavorite(notice)
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                // Banner de arriba, encima del título (el título lo separa del botón del PDF).
                if ads.ready && !premium.isActive {
                    AdSlot(slot: Ads.detailTopSlot)
                        .padding(.bottom, 4)
                }
                HStack(spacing: 6) {
                    NoticeTag(text: badge, color: notice.isPool ? Palette.poolText : Palette.blue,
                        fill: notice.isPool ? Palette.poolFill : Palette.positionFill)
                    // Solo lo que dice el título: si no da una cifra clara, no se muestra.
                    if let places = NoticeDetails.placesInTitle(notice.title) {
                        NoticeTag(text: places == 1 ? "1 plaza" : "\(places) plazas",
                                  color: Color(hex: 0xB4530A), fill: Color(hex: 0xFFF0E5))
                    }
                    if let group = NoticeDetails.groupInTitle(notice.title) {
                        NoticeTag(text: "Grupo \(group)", color: Color(hex: 0x28517E), fill: Color(hex: 0xE8EEF7))
                    }
                }
                Text(notice.headline)
                    .font(.title2.bold())
                    .foregroundStyle(Color(hex: 0x0E1C36))
                Text(notice.entity)
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(Color(hex: 0x5C6B80))
                Label("\(notice.province)  •  \(notice.date)", systemImage: "mappin.and.ellipse")
                    .font(.caption)
                    .foregroundStyle(Color(hex: 0x697C95))

                Button {
                    openOfficial()
                } label: {
                    Label(officialLabel, systemImage: "doc.richtext")
                        .font(.headline)
                        .frame(maxWidth: .infinity, minHeight: 48)
                }
                .buttonStyle(.borderedProminent)
                .tint(Color(hex: 0xFE4559))

                if let deadline {
                    DeadlineCard(deadline: deadline) { openOfficial(page: deadline.page) }
                }

                if favorite {
                    TrackingCard(notice: notice, hasEstimate: deadline?.until != nil)
                }

                if favorite && premium.isActive {
                    FollowUpCard(notice: notice) { openOther($0) }
                }

                if let sede {
                    // Sede de quien convoca, copiada del anuncio: se abre en Safari.
                    VStack(spacing: 6) {
                        Button {
                            openURL(sede)
                        } label: {
                            Label("Ir a la sede electrónica", systemImage: "building.columns")
                                .font(.headline)
                                .frame(maxWidth: .infinity, minHeight: 46)
                        }
                        .buttonStyle(.bordered)
                        .tint(Color(hex: 0x13795B))
                        Text("\(sede.host ?? "")\(sede.path.count > 1 ? sede.path : "") · dirección copiada del anuncio")
                            .font(.caption2)
                            .foregroundStyle(Color(hex: 0x5E7A6C))
                            .multilineTextAlignment(.center)
                    }
                }

                Text("Resumen del anuncio")
                    .font(.headline)
                    .padding(.top, 6)
                Text(notice.title.trimmingCharacters(in: .whitespacesAndNewlines))
                    .font(.subheadline)
                    .foregroundStyle(Color(hex: 0x35435C))
                    .textSelection(.enabled)
                    .padding(14)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(Color.white, in: RoundedRectangle(cornerRadius: 14))

                // Banner a mitad de la ficha, entre el resumen y los datos (lejos de los botones).
                if ads.ready && !premium.isActive {
                    AdSlot(slot: Ads.detailMidSlot)
                        .padding(.vertical, 8)
                }

                Text("Datos de la publicación")
                    .font(.headline)
                    .padding(.top, 6)
                VStack(alignment: .leading, spacing: 6) {
                    Label(source.fullName, systemImage: "building.columns")
                        .font(.subheadline.weight(.semibold))
                        .foregroundStyle(Color(hex: 0x203856))
                    Text(reference)
                        .font(.caption)
                        .foregroundStyle(Color(hex: 0x60748C))
                        .textSelection(.enabled)
                }
                .padding(14)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(Color.white, in: RoundedRectangle(cornerRadius: 14))

                ShareLink(item: notice.shareText(deadline: deadline), subject: Text(ShareText.subject)) {
                    Label("Compartir convocatoria", systemImage: "square.and.arrow.up")
                        .frame(maxWidth: .infinity, minHeight: 44)
                }
                .buttonStyle(.bordered)
                Button {
                    model.toggleFavorite(notice)
                } label: {
                    Label(favorite ? "Quitar de favoritas" : "Guardar en favoritas",
                          systemImage: favorite ? "star.fill" : "star")
                        .frame(maxWidth: .infinity, minHeight: 44)
                }
                .buttonStyle(.bordered)
                .tint(Color(hex: 0xC96812))

                Text("OpoAlert no es una aplicación oficial. Las bases, requisitos y plazos válidos son los publicados por la Administración competente.")
                    .font(.caption2)
                    .foregroundStyle(Color(hex: 0x8190A5))

                // Un banner al final de la ficha, lejos de los botones (sin anuncios con Premium).
                // Solo aparece cuando ha cargado: nunca un hueco vacío.
                if ads.ready && !premium.isActive {
                    AdSlot(slot: Ads.detailSlot)
                        .padding(.top, 18)
                }
            }
            .padding(16)
        }
        .background(Palette.background)
        .navigationTitle("Convocatoria")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .navigationBarTrailing) {
                Button {
                    model.toggleFavorite(notice)
                } label: {
                    Image(systemName: favorite ? "star.fill" : "star")
                }
                .accessibilityLabel(favorite ? "Quitar de favoritas" : "Guardar en favoritas")
            }
        }
        .task {
            (deadline, sede) = await Deadlines.fetchBoth(for: notice)
            model.remember(deadline, for: notice)
        }
        .onChange(of: favorite) { saved in if saved { model.remember(deadline, for: notice) } }
        .onAppear {
            ReviewPrompt.noticeOpened()
            if !premium.isActive { ads.refreshDetailBanner() }
        }
        // Al volver a la lista puede tocar el intersticial (cada 3 fichas); si no, quizá la valoración.
        .onDisappear {
            if !Ads.shared.noticeClosed(premium: PremiumStore.isActiveStored) { ReviewPrompt.maybeAsk() }
        }
        .sheet(item: $pdfLink) { link in
            PdfViewerView(url: link.url, title: link.title ?? source.shortName)
        }
        .alert("El enlace oficial no se ha podido verificar.", isPresented: $linkRejected) {
            Button("Aceptar", role: .cancel) {}
        }
    }

    private var badge: String {
        if notice.isProcedureUpdate { return "TRÁMITE DEL PROCESO" }
        return notice.isPool ? "BOLSA DE TRABAJO" : "PLAZA / OPOSICIÓN"
    }

    private var officialLabel: String {
        if OfficialDocument.isPdf(notice) { return "Ver PDF oficial" }
        return notice.id.hasPrefix("CIDO") ? "Ver convocatoria en CIDO" : "Ver anuncio oficial"
    }

    private var reference: String {
        if notice.id.hasPrefix("CIDO") { return "Actualización \(notice.date)  ·  Ref. \(notice.id)" }
        if notice.id.hasPrefix("BA-") { return "BOP Barcelona · \(notice.date)  ·  Registro \(notice.id)" }
        return "\(source.shortName) n.º \(notice.bulletin)  ·  Registro \(notice.id)"
    }

    /// Anuncio de un paso del seguimiento: mismas comprobaciones que el de la ficha.
    private func openOther(_ other: Notice) {
        let otherSource = Source.of(other)
        guard otherSource.isOfficialLink(other.url), let url = URL(string: other.url) else {
            linkRejected = true
            return
        }
        if OfficialDocument.isPdf(other) { pdfLink = PdfLink(url: url, title: otherSource.shortName) } else { openURL(url) }
    }

    /// Solo se abre si el enlace es HTTPS al dominio y la ruta oficiales de la fuente.
    private func openOfficial(page: Int? = nil) {
        guard source.isOfficialLink(notice.url), let url = URL(string: notice.url) else {
            linkRejected = true
            return
        }
        // El PDF se ve dentro de la app; si no fuera un PDF, el visor lo abre fuera.
        if OfficialDocument.isPdf(notice) {
            let address = page.map { notice.url.contains("#") ? notice.url : notice.url + "#page=\($0)" } ?? notice.url
            pdfLink = PdfLink(url: URL(string: address) ?? url)
        } else {
            openURL(url)
        }
    }
}

private struct PdfLink: Identifiable {
    let url: URL
    var title: String? = nil
    var id: String { url.absoluteString }
}

/// Plazo copiado del anuncio. Solo los días y la frase literal: no se calcula ninguna fecha.
private struct DeadlineCard: View {
    let deadline: Deadline
    let openPage: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Label("PLAZO DE PRESENTACIÓN", systemImage: "timer")
                .font(.caption.bold())
                .foregroundStyle(Color(hex: 0xB45309))
            Text(deadline.label)
                .font(.title2.bold())
                .foregroundStyle(Color(hex: 0x13223C))
            Text("Según el anuncio:")
                .font(.caption.bold())
                .foregroundStyle(Color(hex: 0x7A5A2B))
            Text("«\(deadline.text)»")
                .font(.subheadline.italic())
                .foregroundStyle(Color(hex: 0x4A3B22))
                .textSelection(.enabled)
            Button(action: openPage) {
                Label("Ver en el PDF (pág. \(deadline.page))", systemImage: "doc.text.magnifyingglass")
                    .font(.subheadline.bold())
            }
            .tint(Color(hex: 0xC2410C))
            if let until = deadline.until {
                let left = AgendaDates.daysLeft(until) ?? 0
                Text("Acaba como pronto el \(AgendaDates.long(until))" + (left < 0 ? " (ya ha pasado)" : ""))
                    .font(.subheadline.bold())
                    .foregroundStyle(Color(hex: 0x13223C))
                Text("Fecha orientativa: cuenta desde la publicación en este boletín, sin sábados, domingos ni fiestas nacionales. Los festivos de tu comunidad o municipio pueden alargarlo unos días. Compruébalo siempre en el anuncio oficial.")
                    .font(.caption2)
                    .foregroundStyle(Color(hex: 0x8A6D3B))
            } else {
                Text("OpoAlert no calcula la fecha: el plazo puede empezar con otra publicación (por ejemplo, el extracto en el BOE). Compruébalo siempre en el anuncio oficial.")
                    .font(.caption2)
                    .foregroundStyle(Color(hex: 0x8A6D3B))
            }
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color(hex: 0xFFF7E8), in: RoundedRectangle(cornerRadius: 16))
        .overlay(RoundedRectangle(cornerRadius: 16).stroke(Color(hex: 0xF5D9A8)))
    }
}

/// «Mi seguimiento» de una favorita (Premium, como las alertas): recordatorio del plazo,
/// «ya la he presentado» y una nota. Sin Premium se explica y abre la pantalla de Premium.
private struct TrackingCard: View {
    let notice: Notice
    let hasEstimate: Bool
    @EnvironmentObject private var model: AppModel
    @ObservedObject private var premium = PremiumStore.shared
    @State private var showPremium = false
    @State private var editingNote = false
    @State private var draft = ""

    var body: some View {
        let entry = model.agenda[notice.id]
        VStack(alignment: .leading, spacing: 10) {
            Label("MI SEGUIMIENTO", systemImage: "star.fill")
                .font(.caption.bold())
                .foregroundStyle(Color(hex: 0x6D28D9))
            if !premium.isActive {
                Text("Con OpoAlert Premium te avisamos antes de que acabe el plazo y si sale otro anuncio de esta convocatoria, marcas las solicitudes que ya has presentado y guardas tus notas.")
                    .font(.subheadline)
                    .foregroundStyle(Color(hex: 0x3B2A63))
                Button { showPremium = true } label: {
                    Text(premium.trialDays.map { "Probar Premium \($0) días gratis" } ?? "Ver Premium")
                        .font(.headline).frame(maxWidth: .infinity, minHeight: 44)
                }
                .buttonStyle(.borderedProminent)
                .tint(Color(hex: 0x6D28D9))
            } else {
                Text(reminderText(entry))
                    .font(.subheadline)
                    .foregroundStyle(Color(hex: 0x3B2A63))
                Toggle("Ya he presentado la solicitud", isOn: Binding(
                    get: { entry?.submitted ?? false },
                    set: { model.setSubmitted($0, for: notice) }))
                    .font(.subheadline.weight(.semibold))
                    .tint(Color(hex: 0x6D28D9))
                Button {
                    draft = entry?.noteText ?? ""
                    editingNote = true
                } label: {
                    Label((entry?.noteText.isEmpty ?? true) ? "Añadir una nota" : (entry?.noteText ?? ""),
                          systemImage: "square.and.pencil")
                        .font(.subheadline)
                        .multilineTextAlignment(.leading)
                }
                .tint(Color(hex: 0x6D28D9))
            }
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color(hex: 0xF3F0FF), in: RoundedRectangle(cornerRadius: 16))
        .overlay(RoundedRectangle(cornerRadius: 16).stroke(Color(hex: 0xDDD3FB)))
        .sheet(isPresented: $showPremium) { PremiumView() }
        .alert("Nota de esta convocatoria", isPresented: $editingNote) {
            TextField("Por ejemplo: pagar la tasa antes del viernes", text: $draft)
            Button("Guardar") { model.setNote(String(draft.prefix(AgendaEntry.noteMax)), for: notice) }
            Button("Cancelar", role: .cancel) {}
        }
    }

    private func reminderText(_ entry: AgendaEntry?) -> String {
        if entry?.submitted == true { return "Solicitud presentada: no hace falta recordatorio." }
        if let at = Reminders.planned(entry, favorite: true) {
            let f = DateFormatter()
            f.locale = Locale(identifier: "es_ES")
            f.timeZone = AgendaDates.calendar.timeZone
            f.dateFormat = "EEEE d 'de' MMMM 'a las' H:mm"
            return "🔔 Te avisaremos el \(f.string(from: at))."
        }
        if hasEstimate || entry?.until != nil { return "El plazo orientativo ya ha pasado." }
        return "Sin recordatorio: este anuncio no permite estimar la fecha de fin."
    }
}

/// Seguimiento de la convocatoria (1.59.0, Premium): otros anuncios que pueden ser de la misma
/// convocatoria, en orden de fecha (`renderFollowUps` en Android). Nunca se afirma: se encuentran
/// por el organismo y el puesto, y cada uno pregunta «¿Es de esta convocatoria?».
private struct FollowUpCard: View {
    let notice: Notice
    let open: (Notice) -> Void
    @EnvironmentObject private var model: AppModel

    var body: some View {
        let state = model.followUpState(notice)
        let steps = state.visible.reversed()
        let local = FollowUpMatcher.localOrg(entity: notice.entity, title: notice.title) != nil
        VStack(alignment: .leading, spacing: 10) {
            Text("SEGUIMIENTO")
                .font(.caption.bold())
                .foregroundStyle(Color(hex: 0x7C3AED))
            row(step: FollowUpMatcher.stepOf(notice.title, isBoe: Source.of(notice).isBOE) + " · la que guardaste",
                item: notice, followUp: nil)
            ForEach(Array(steps), id: \.notice.id) { followUp in
                row(step: followUp.step, item: followUp.notice, followUp: followUp)
            }
            if let note = note(local: local, state: state, empty: steps.isEmpty) {
                Text(note)
                    .font(.subheadline)
                    .foregroundStyle(Color(hex: 0x3B2A63))
            }
            Text("Encontrado por el organismo y el puesto. Comprueba siempre el anuncio oficial.")
                .font(.caption)
                .foregroundStyle(Color(hex: 0x64748B))
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color.white, in: RoundedRectangle(cornerRadius: 16))
        .overlay(RoundedRectangle(cornerRadius: 16).stroke(Color(hex: 0xDDD3FB)))
        .onDisappear { model.markFollowUpsRead(notice) }
    }

    private func note(local: Bool, state: FollowUpState, empty: Bool) -> String? {
        if !local {
            return "El seguimiento solo funciona con convocatorias de ayuntamientos, diputaciones, comarcas, mancomunidades y cabildos: en las de otros organismos los títulos no permiten distinguir cada proceso."
        }
        if !state.initialized { return "Buscando otros anuncios de esta convocatoria…" }
        return empty ? "Aún no hay otros anuncios de esta convocatoria. Si aparece uno posible, te avisaremos." : nil
    }

    @ViewBuilder
    private func row(step: String, item: Notice, followUp: FollowUpItem?) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack(spacing: 8) {
                Circle()
                    .fill(followUp == nil ? Color(hex: 0x94A3B8) : Color(hex: 0x7C3AED))
                    .frame(width: 8, height: 8)
                Text(step)
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(Palette.navy)
                Spacer()
                if followUp?.unread == true {
                    NoticeTag(text: "NOVEDAD", color: .white, fill: Color(hex: 0x7C3AED))
                }
            }
            Group {
                Text("\(item.date) · \(item.province)")
                    .font(.caption)
                    .foregroundStyle(Palette.slate)
                Text(item.headline)
                    .font(.footnote)
                    .foregroundStyle(Color(hex: 0x3B4A63))
                    .lineLimit(3)
                if let followUp {
                    HStack(spacing: 6) {
                        if followUp.state == FollowUpItem.yes {
                            Text("✓ Es de esta convocatoria")
                                .font(.footnote.weight(.semibold))
                                .foregroundStyle(Color(hex: 0x13795B))
                        } else {
                            Text("¿Es de esta convocatoria?")
                                .font(.footnote)
                                .foregroundStyle(Color(hex: 0x3B2A63))
                            Spacer(minLength: 4)
                            Button("Sí") { model.answerFollowUp(followUp, of: notice, yes: true) }
                                .buttonStyle(.bordered).tint(Color(hex: 0x6D28D9))
                            Button("No") { model.answerFollowUp(followUp, of: notice, yes: false) }
                                .buttonStyle(.bordered).tint(Color(hex: 0x475569))
                        }
                        if followUp.state == FollowUpItem.yes { Spacer(minLength: 4) }
                        Button(OfficialDocument.isPdf(item) ? "Ver PDF" : "Ver anuncio") { open(item) }
                            .buttonStyle(.bordered).tint(Palette.blue)
                    }
                    .font(.footnote)
                    .padding(.top, 2)
                }
            }
            .padding(.leading, 16)
        }
    }
}
