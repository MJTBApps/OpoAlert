import Foundation
import OpoAlertCore

// Comprobaciones del núcleo iOS. Funcionan sin Xcode (no hay XCTest en las
// herramientas de línea de comandos):
//   swift run OpoAlertChecks [carpeta docs]
// Con la carpeta docs/ del repositorio, valida además todos los feeds publicados
// con las mismas reglas que la app.

var failures = 0
var checks = 0

func check(_ condition: @autoclosure () -> Bool, _ message: String, line: Int = #line) {
    checks += 1
    if !condition() {
        failures += 1
        print("FALLO (línea \(line)): \(message)")
    }
}

func equal<T: Equatable>(_ actual: T, _ expected: T, _ message: String, line: Int = #line) {
    check(actual == expected, "\(message): se esperaba \(expected), salió \(actual)", line: line)
}

// MARK: Búsqueda

for text in ["policia", "policía", "polícia", "POLICÍA"] {
    equal(SearchText.normalize(text), "policia", "sin tildes ni mayúsculas")
    check(SearchText.matchesNormalized(SearchText.normalize(text), "Policía Local"), "busca \(text)")
}
equal(SearchText.normalize("AÑO"), "año", "conserva la ñ")

// MARK: Plazas y grupo

equal(NoticeDetails.placesInTitle("Convocatoria de 5 plazas de Policía Local"), 5, "cifra")
equal(NoticeDetails.placesInTitle("Se convocan 4 places de administratiu"), 4, "catalán")
equal(NoticeDetails.placesInTitle("Bolsa de auxiliar administrativo plazas"), nil, "sin número")
equal(NoticeDetails.placesInTitle("Convocatoria de cinco plazas de bombero"), 5, "con letra")
equal(NoticeDetails.placesInTitle(
    "Cuatro plazas de profesorado de orquesta, instrumento viola, una reservada para el turno de discapacidad"), 4,
      "con letra y mayúscula")
equal(NoticeDetails.placesInTitle("Bases para proveer una plaza de auxiliar administrativo"), 1, "una plaza")
equal(NoticeDetails.placesInTitle("Convocatòria de tres places d'agent de la policia local"), 3, "tres places")
equal(NoticeDetails.placesInTitle("Procés selectiu de dues places de tècnic"), 2, "dues places")
equal(NoticeDetails.placesInTitle("Bases d'una plaça d'administratiu"), 1, "una plaça")
equal(NoticeDetails.placesInTitle("Convocatoria de las plazas vacantes de bombero"), nil, "«las» no es número")
equal(NoticeDetails.placesInTitle("Creación de bolsa para diversas plazas"), nil, "«diversas»")
equal(NoticeDetails.placesInTitle("Convocatoria de dos plazas y tres plazas de conserje"), nil, "dos cifras")
equal(NoticeDetails.placesInTitle("Convocatoria de 4 plazas y 2 plazas"), nil, "ambiguo")
equal(NoticeDetails.placesInTitle("Modificación de las bases de 5 plazas de Policía Local"), nil, "trámite")
equal(NoticeDetails.groupInTitle("Convocatoria de Grupo C1 de administrativos"), "C1", "grupo")
equal(NoticeDetails.groupInTitle("Subgrupo A2, turno libre"), "A2", "subgrupo")
equal(NoticeDetails.groupInTitle("Oferta de empleo 2026"), nil, "sin grupo")
equal(NoticeDetails.placesInTitle("Selección de dos (2) plazas de Técnico/a de Administración General"), 2, "paréntesis")
equal(NoticeDetails.placesInTitle("Provisión dunha (1) praza de axudante de obras e servizos"), 1, "gallego")
equal(NoticeDetails.placesInTitle("Bases para tres prazas de auxiliar administrativo"), 3, "prazas")
equal(NoticeDetails.placesInTitle("Convocatoria de dos (3) plazas de conserje"), nil, "paréntesis contradictorio")
equal(OfficialDocument.startPage("https://www.bopcadiz.es/x/BOP210_30-10-26.pdf#page=29"), 29, "página del anuncio")
equal(OfficialDocument.startPage("https://www.boe.es/boe/dias/2026/10/31/pdfs/BOE-A-2026-22836.pdf"), 1, "sin página")
equal(OfficialDocument.looksLikePdf(Data("%PDF-1.7".utf8)), true, "PDF")
equal(OfficialDocument.looksLikePdf(Data("<!DOCTYPE html>".utf8)), false, "HTML no es PDF")

// MARK: Títulos

equal(NoticeText.headline("Anuncio del Ayuntamiento de Gandia sobre bases de 2 plazas de agente de policía local."),
      "2 plazas de agente de policía local", "quita la fórmula y empieza en la plaza")
equal(NoticeText.headline("Anuncio sobre corrección de errores de las bases."), "Corrección de errores de las bases",
      "trámite sin recortar")
check(NoticeText.isProcedureUpdate("Modificación de las bases de la convocatoria"), "trámite")
check(!NoticeText.isProcedureUpdate("Bases de la convocatoria de 1 plaza de conserje"), "no es trámite")

// MARK: Resumen de la revisión

equal(SyncSummary.describe("VA: 61 · AL: 20"), "81 anuncios · 2 boletines", "resumen")
equal(SyncSummary.describe("VA: 1"), "1 anuncio · 1 boletín", "singular")
equal(SyncSummary.describe("VA: 61 · AL: 20 · Sin datos verificados: Cuenca"),
      "81 anuncios · 2 boletines · sin datos: Cuenca", "fuentes sin datos")
equal(SyncSummary.compactUpdated("31/10/2026 07:40"), "Act. 31/10 07:40", "hora de la revisión")
equal(SyncSummary.compactHistory("Histórico verificado: 2026-10-02 a 2026-10-31"),
      "Histórico verificado · 02/10 – 31/10", "periodo")

// MARK: Fuentes (las mismas reglas que Province.kt)

equal(Source.all.count, Set(Source.all.map(\.code)).count, "códigos únicos")
check(Source.valencia.matchesId("2026/12855"), "id de Valencia")
check(!Source.valencia.matchesId("AL-2026-8223"), "id de otra fuente")
check(!Source.valencia.matchesId("x2026/12855"), "coincidencia completa")
equal(Source.fromNoticeId("2026/12855").code, "VA", "Valencia por defecto")
equal(Source.fromNoticeId("AL-2026-8223").code, "AL", "Alicante")
equal(Source.fromNoticeId("BOE-A-2026-22556").code, "ES", "BOE")
equal(Source.fromNoticeId("CIDO5-12345").code, "CB", "CIDO Barcelona")
equal(Source.fromNoticeId("LE-202610290001").code, "LE", "BOP Lleida")
equal(Source.fromNoticeId("CN-2026-12345").code, "CN", "Cantabria")
check(Source.code("ES")!.matchesId("BOE-A-2026-22556"), "id del BOE")
check(Source.code("SA")!.allowsOfficialPath("/documentacion/bop/2026/20261028/BOP-SA-20261028-005.pdf"), "ruta Salamanca")
check(Source.code("AM")!.allowsOfficialPath("/pandora/high.raw"), "ruta especial de Almería")
check(Source.code("RI")!.allowsOfficialPath("/boletin/ExportarBoletinServlet"), "ruta especial de La Rioja")
check(Source.valencia.isOfficialLink("https://bop.dival.es/bop/downloads/x.pdf"), "enlace oficial")
check(!Source.valencia.isOfficialLink("http://bop.dival.es/bop/downloads/x.pdf"), "sin HTTPS")
check(!Source.valencia.isOfficialLink("https://evil.example/bop/downloads/x.pdf"), "otro dominio")
check(!Source.valencia.isOfficialLink("https://user@bop.dival.es/bop/downloads/x.pdf"), "con usuario")
check(Source.all.allSatisfy { $0.isBOE || $0.community != nil }, "todas tienen comunidad")

let groups = SourceCatalog.groups(SourceCatalog.available(active: nil))
equal(groups.first?.name, "Comunidad Valenciana", "primera comunidad")
equal(groups.first?.territories.map(\.name), ["Valencia", "Alicante", "Castellón", "Diario autonómico"],
      "orden de provincias")
let barcelona = groups.first { $0.name == "Cataluña" }?.territories.first { $0.name == "Barcelona" }
equal(barcelona?.sources.map(\.code), ["BB", "CB"], "el BOP antes que el CIDO")
check(!groups.flatMap(\.sources).contains(Source.boe), "el BOE va aparte")
equal(SourceCatalog.parseActive(Data(#"{"active":["VA","AL","CS","ES","CB","XX"]}"#.utf8)),
      Set(["VA", "AL", "CS", "ES", "CB"]), "solo códigos conocidos")
equal(SourceCatalog.parseActive(Data(#"{"active":["VA"]}"#.utf8)), nil, "lista casi vacía: dañada")
equal(SourceCatalog.display(["VA", "AL", "ES"], available: Source.all), "2 provincias + BOE", "resumen de fuentes")
equal(SourceCatalog.display(["VA"], available: Source.all), "Valencia", "una fuente")

// MARK: Alertas

let policeAL = Notice(id: "AL-2026-1234", title: "Convocatoria de agente de Policía Local",
                      entity: "Ayuntamiento de Alicante", date: "28/10/2026", bulletin: "205",
                      type: "Plaza / oposición", url: "https://example.com", province: "Alicante")
let adminVA = Notice(id: "2026/1234", title: "Bases de Auxiliar Administrativo", entity: "Ayuntamiento de Náquera",
                     date: "28/10/2026", bulletin: "207", type: "Plaza / oposición", url: "https://example.com",
                     province: "Valencia")
let both: Set<String> = ["VA", "AL"]
let role = AlertRule(id: "a", phrase: "policia local", sources: both)
func with(_ rule: AlertRule, phrase: String? = nil, sources: Set<String>? = nil, enabled: Bool? = nil) -> AlertRule {
    AlertRule(id: rule.id, phrase: phrase ?? rule.phrase, sources: sources ?? rule.sources, enabled: enabled ?? rule.enabled)
}
check(SmartAlertMatcher.matches(with(role, phrase: "polícia LOCAL"), policeAL, followed: both), "tildes y mayúsculas")
check(SmartAlertMatcher.matches(with(role, phrase: "local policía"), policeAL, followed: both), "orden de palabras")
check(SmartAlertMatcher.matches(with(role, phrase: "alicante policia"), policeAL, followed: both), "busca en el organismo")
check(!SmartAlertMatcher.matches(role, policeAL, followed: ["VA"]), "fuente no seguida")
check(!SmartAlertMatcher.matches(with(role, sources: ["VA"]), policeAL, followed: both), "fuente fuera de la alerta")
check(!SmartAlertMatcher.matches(with(role, enabled: false), policeAL, followed: both), "alerta en pausa")
check(!SmartAlertMatcher.matches(role, adminVA, followed: both), "otro puesto")
check(!SmartAlertMatcher.matches(with(role, phrase: "ano"), adminVA, followed: both), "ñ distinta de n")
let once = SmartAlertMatcher.matching([policeAL, policeAL, adminVA],
                                      rules: [role, AlertRule(id: "b", phrase: "policía", sources: both)], followed: both)
equal(once.map(\.id), [policeAL.id], "un aviso por convocatoria")
check(SmartAlertMatcher.matching([policeAL], rules: [], followed: both).isEmpty, "sin alertas no hay avisos")
equal(SeenIds.merge(["c", "a"], ["a", "b"]), ["c", "a", "b"], "vistos: recientes primero y sin repetir")

// MARK: Feed de ejemplo

func feed(_ notices: [[String: Any]], complete: Bool = true, source: String = Source.valencia.expectedSource) -> Data {
    let root: [String: Any] = [
        "schemaVersion": 1, "province": "Valencia", "source": source, "lastCheckedUTC": "2026-10-31T06:40:09Z",
        "coverage": ["complete": complete, "bulletin": "209", "announcementsRead": 61] as [String: Any],
        "historyCoverage": ["complete": true, "rangeStart": "2026-10-02", "rangeEnd": "2026-10-31",
                            "bulletins": ["188", "209"]] as [String: Any],
        "notices": notices,
    ]
    return try! JSONSerialization.data(withJSONObject: root)
}
func valencia(_ id: String, date: String = "30/10/2026", title: String = "Bases de 1 plaza de conserje") -> [String: Any] {
    ["id": id, "title": title, "entity": "Ayuntamiento de Xàtiva", "date": date, "bulletin": "209",
     "type": "Plaza / oposición", "url": "https://bop.dival.es/bop/downloads/\(id.replacingOccurrences(of: "/", with: "-")).pdf",
     "province": "Valencia"]
}
do {
    let parsed = try FeedReader.parse(feed([valencia("2026/10001")]), source: Source.valencia)
    equal(parsed.notices.count, 1, "anuncio leído")
    equal(parsed.status, "Valencia: BOP 209 · 61 anuncios", "estado")
    equal(parsed.historyStatus, "Histórico verificado: 2026-10-02 a 2026-10-31", "histórico")
} catch {
    check(false, "feed válido rechazado: \(error)")
}
func rejected(_ data: Data, _ message: String, line: Int = #line) {
    check((try? FeedReader.parse(data, source: Source.valencia)) == nil, message, line: line)
}
rejected(feed([valencia("2026/10001")], complete: false), "lectura no confirmada")
rejected(feed([valencia("2026/10001")], source: "https://otra.fuente/"), "fuente inesperada")
rejected(feed([valencia("2026/10001"), valencia("2026/10001")]), "duplicados")
rejected(feed([valencia("AL-2026-1")]), "id de otra fuente")
var outside = valencia("2026/10002")
outside["url"] = "https://example.com/x.pdf"
rejected(feed([outside]), "enlace no oficial")
check((try? FeedReader.checkedURL("https://example.com/feed.json", for: Source.valencia)) == nil, "feed no autorizado")

// MARK: Revisión completa con datos simulados

let suite = "opoalert-checks-\(UUID().uuidString)"
let defaults = UserDefaults(suiteName: suite)!
let store = Store(defaults: defaults)
/// Lo que «publica» la web simulada en cada revisión.
final class FakeWeb: @unchecked Sendable { var notices: [[String: Any]] = [] }
let web = FakeWeb()
web.notices = [valencia("2026/10001")]
let synchronizer = Synchronizer(store: store,
                                fetchFeed: { [web] source in
                                    guard source.code == "VA" else { throw FeedError("sin datos") }
                                    return try FeedReader.parse(feed(web.notices), source: source)
                                },
                                fetchActive: { nil })

func runSync() async throws -> SyncResult { try await synchronizer.sync() }

do {
    try store.upsertRule(id: nil, input: "  policia   local ", sources: ["VA"])
    let first = try await runSync()
    equal(first.newOnes.count, 0, "la primera revisión solo rellena")
    web.notices.append(valencia("2026/10002", title: "Bases de 2 plazas de policía local"))
    web.notices.append(valencia("2026/10003", title: "Bases de 1 plaza de conserje"))
    let second = try await runSync()
    equal(second.newOnes.map(\.id), ["2026/10002", "2026/10003"], "anuncios nuevos")
    equal(second.alertMatches.map(\.id), ["2026/10002"], "aviso de la alerta")
    let third = try await runSync()
    equal(third.newOnes.count, 0, "no se repiten avisos")
    equal(store.cached.count, 3, "caché")
    equal(store.rules.first?.phrase, "policia local", "frase limpia")
    check((try? store.upsertRule(id: nil, input: "Policía Local", sources: ["VA"])) == nil, "alerta repetida")
    check((try? store.upsertRule(id: nil, input: "ab", sources: ["VA"])) == nil, "frase corta")
    check(store.toggleFavorite(policeAL), "guarda favorita")
    check(store.isFavorite(policeAL.id), "favorita guardada")
    check(!store.toggleFavorite(policeAL), "quita favorita")
    check(store.saveSelected(["VA", "ES", "XX"]), "guarda fuentes")
    equal(store.selected, ["VA", "ES"], "solo fuentes conocidas")
} catch {
    check(false, "revisión simulada: \(error)")
}
defaults.removePersistentDomain(forName: suite)

// MARK: Feeds publicados (docs/)

if CommandLine.arguments.count > 1 {
    let docs = URL(fileURLWithPath: CommandLine.arguments[1])
    var read = 0, total = 0, skipped: [String] = []
    for source in Source.all {
        let file = docs.appendingPathComponent(URL(string: source.feedURL)!.lastPathComponent)
        guard let data = try? Data(contentsOf: file) else { skipped.append(source.code); continue }
        do {
            total += try FeedReader.parse(data, source: source).notices.count
            read += 1
        } catch {
            check(false, "feed publicado de \(source.label) rechazado: \(error.localizedDescription)")
        }
    }
    print("Feeds publicados: \(read) válidos con \(total) anuncios" +
          (skipped.isEmpty ? "" : "; sin archivo: \(skipped.joined(separator: ", "))"))
}

if failures > 0 {
    print("\(failures) de \(checks) comprobaciones fallidas")
    exit(1)
}
print("OK: \(checks) comprobaciones del núcleo iOS")
