import Foundation

/// Plazas que cita un extracto del BOE de un ayuntamiento y fecha del boletín de sus bases,
/// copiadas del PDF por `backend/plazos.py` (campo `proveer`). `BoeExtract` en Android.
public struct BoeExtract: Equatable, Sendable {
    public let items: [String]
    public let basesDate: String?
    public init(items: [String], basesDate: String?) {
        self.items = items
        self.basesDate = basesDate
    }
}

/// Expresión regular sobre texto ya normalizado (minúsculas, sin tildes).
struct Rx: @unchecked Sendable {
    let re: NSRegularExpression
    init(_ pattern: String) { re = try! NSRegularExpression(pattern: pattern) }
    private func all(_ s: String) -> NSRange { NSRange(s.startIndex..., in: s) }
    func first(_ s: String) -> NSTextCheckingResult? { re.firstMatch(in: s, range: all(s)) }
    func matches(_ s: String) -> [NSTextCheckingResult] { re.matches(in: s, range: all(s)) }
    func contains(_ s: String) -> Bool { first(s) != nil }
    func whole(_ s: String) -> Bool { first(s).map { $0.range == all(s) } ?? false }
    func replace(_ s: String, _ template: String) -> String {
        re.stringByReplacingMatches(in: s, range: all(s), withTemplate: template)
    }
}

private extension String {
    func sub(_ range: NSRange) -> String { (self as NSString).substring(with: range) }
    func from(_ location: Int) -> String { (self as NSString).substring(from: location) }
    func to(_ location: Int) -> String { (self as NSString).substring(to: location) }
    var nsLength: Int { (self as NSString).length }
}

/// Seguimiento de favoritas (1.59.0): ¿puede este anuncio ser otro paso de la misma
/// convocatoria? Misma lógica que `FollowUpMatcher.kt` y `backend/seguimiento.py`; los casos
/// de `backend/tests/seguimiento_casos.json` los comprueban las tres. Solo organismos locales,
/// y siempre «posible»: medido con los feeds reales, 94 % de aciertos.
public enum FollowUpMatcher {
    public struct Org: Equatable, Sendable {
        public let kind: String
        public let name: String
    }

    public static func fold(_ text: String) -> String {
        let decomposed = text.lowercased().decomposedStringWithCompatibilityMapping
        let scalars = decomposed.unicodeScalars.filter { $0.properties.generalCategory != .nonspacingMark }
        return String(String.UnicodeScalarView(scalars)).replacingOccurrences(of: "’", with: "'")
            .replacingOccurrences(of: "·", with: "")
    }

    // MARK: Organismo

    private static let kinds: [(String, Rx)] = [
        ("ayto", #"(?:excmo\.?|excelentisimo|ilustre|iltre\.?|m\.?\s*i\.?)?\s*(?:ayuntamientos?|ajuntament|concello|udala|ayto\.?)"#),
        ("dipu", #"(?:excma\.?)?\s*(?:diputacion|diputacio|deputacion)(?: provincial| foral)?"#),
        ("comarca", "(?:comarca|consell comarcal)"),
        ("manc", "(?:mancomunidad|mancomunitat)"),
        ("cabildo", "cabildo(?: insular)?"),
        ("consell", "consell insular"),
        ("univ", "(?:universidad|universitat|universidade)"),
    ].map { ($0.0, Rx(#"^\s*(?:"# + $0.1 + #")\b"#)) }
    private static let orgStop: Set<String> = ["de", "del", "d", "la", "el", "los", "las", "l", "les", "els", "a", "o",
                                               "os", "as", "y", "i", "e", "do", "da", "dos", "das"]
    private static let orgInTitle = Rx(
        #"\b(ayuntamiento|ajuntament|concello|diputacion provincial|diputacion|universidad|comarca|mancomunidad|cabildo insular)"# +
        #"\s+(de |del |d')?([^,.;()]+?)(?=\s*(?:\(|,|\.|;| sobre | por | referente| relativ| de fecha| para | que | en |$))"#)
    private static let words = Rx("[a-z0-9]+")
    private static let parens = Rx(#"\([^)]*\)"#)

    private static func tokens(_ s: String) -> [String] { words.matches(s).map { s.sub($0.range) } }

    private static func orgFrom(_ text: String) -> Org? {
        var t = fold(text).trimmingCharacters(in: CharacterSet(charactersIn: " –-"))
        t = parens.replace(t, " ").components(separatedBy: " - ").first ?? ""
        var kind: String?
        for (k, rx) in kinds {
            guard let m = rx.first(t) else { continue }
            kind = k
            t = t.from(m.range.location + m.range.length)
            break
        }
        let names = tokens(t).filter { !orgStop.contains($0) }
        guard !names.isEmpty else { return nil }
        return Org(kind: kind ?? "?", name: names.joined(separator: " "))
    }

    private static func orgKey(entity: String, title: String) -> Org? {
        let ft = fold(title)
        let fromTitle = orgInTitle.first(ft).flatMap { m in orgFrom(ft.sub(m.range(at: 1)) + " " + ft.sub(m.range(at: 3))) }
        // BOJA trae en «entity» un texto de la web que no es el organismo.
        let bad = entity.trimmingCharacters(in: .whitespaces).isEmpty || fold(entity).contains("recomendador")
        let fromEntity = bad ? nil : orgFrom(entity)
        if let e = fromEntity, e.kind == "?", let t = fromTitle, t.kind != "?" { return t }
        return fromEntity ?? fromTitle
    }

    private static let regional = Rx(
        #"\b(?:consejeria|conselleria|departament|departamento|ministerio|servicio|servei|servizo|comunidad|comunitat|administracion|"# +
        #"direccion|direccio|instituto|institut|agencia|osakidetza|organismo|organisme|junta|gobierno|govern|generalitat|xunta|consorci|"# +
        #"consorcio|fundacion|fundacio|escuela|escola|sociedad|empresa|entidad|ente|parlamento|tribunal|corporacion|universidad|"# +
        #"hospital|area|seccion|presidencia|vicepresidencia|educacion|sanidad|salud|justicia|hacienda|economia|empleo|trabajo|cultura|turismo|"# +
        #"interior|igualdad|derechos|bienestar|medio ambiente|agricultura|industria|vivienda|transportes|deporte|juventud|familia|politica)\b"#)
    private static let localKinds: Set<String> = ["ayto", "dipu", "comarca", "manc", "cabildo", "consell"]

    /// Organismo local del anuncio, o nil si no es local o no se reconoce.
    public static func localOrg(entity: String, title: String) -> Org? {
        guard let o = orgKey(entity: entity, title: title) else { return nil }
        if localKinds.contains(o.kind) { return o }
        if o.kind == "?" && !regional.contains(o.name) { return Org(kind: "ayto", name: o.name) }
        return nil
    }

    public static func sameOrg(_ a: Org?, _ b: Org?) -> Bool {
        guard let a, let b, a.name == b.name else { return false }
        return a.kind == b.kind || ((a.kind == "?" || b.kind == "?") && Set([a.kind, b.kind]).isSubset(of: ["?", "ayto"]))
    }

    // MARK: Puesto

    private static let posStart = Rx(
        #"\b(?:plazas?|places?|placa|prazas?|puestos?(?: de trabajo)?|llocs?(?: de treball)?|postos?(?: de traballo)?|"# +
        #"bolsas?(?: de (?:trabajo|empleo|empleo temporal|trabajo temporal|traballo|emprego))?|borsas?(?: de treball| d'ocupacio)?|"# +
        #"categorias?(?: profesional)?|cuerpos?|escala|especialidad)\s+(?:vacantes?\s+|vacants?\s+)?"# +
        #"(?:de |del |d'|en la categoria de |para (?:la contratacion de |cubrir )?)?"#)
    private static let posStop = Rx(
        #"[,.;:\["«]| mediante| por (?!cuenta)| per | pel | como | com | en regimen| vacantes?\b| del grupo| grupo | subgrupo| incluid| correspondiente|"# +
        #" de la plantilla| de este| de esta| del ayuntamiento| de l'ajuntament| del concello| para (?!la contratacion)| en el | en la | con caracter| turno|"# +
        #" sistema| personal | funcionari| laboral| escala| a traves| de la oferta| oep| en propiedad| interin| temporal| fij[oa]| de caracter| reservad| y la constitucion|"# +
        #" y constitucion| y creacion| y formacion| y bolsa| mas bolsa| \d{4}\b| expediente| exp\b| de administracion (?:general|especial)| del organismo|"# +
        #" de la (?:diputacion|universidad)| d'aquest| de l'| pertenec| pertany| dins"#)
    private static let generic: Set<String> = [
        "plaza", "plazas", "puesto", "personal", "funcionario", "funcionaria", "laboral", "fijo", "temporal", "interino", "carrera",
        "bolsa", "trabajo", "empleo", "vacante", "una", "un", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve", "diez",
        "oep", "turno", "libre", "promocion", "interna", "de", "del", "la", "el", "los", "las", "y", "e", "i", "o", "en", "para", "con",
        "d", "l", "les", "els", "dels", "per", "a", "da", "do", "das", "na", "no",
        "naturaleza", "cita", "citan", "que", "se", "al", "designacion", "designacio", "orden", "ordre", "caracter", "correspondiente",
        "correspondientes", "unico", "unica", "varias", "diversas", "distintas", "siguiente", "siguientes", "relacionan", "ofertan", "establece",
        "treball", "traballo", "profesional", "categoria", "cuerpo", "cuerpos", "procedimiento", "proceso", "procesos", "selectivo",
        "seleccion", "convocatoria", "convocadas", "resolucion", "esta", "este", "por", "su", "sus", "aspirantes", "aprobados", "personas",
        "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
        "gener", "febrer", "marc", "maig", "juny", "juliol", "setembre", "novembre", "desembre", "excepcional", "reservada",
        "reservadas", "vacantes", "contratacion", "cubrir", "cobrir", "provision", "provisio", "ambito", "ambit", "adscrita", "adscrito",
        "grupo", "grup", "marco", "concurso", "concurs", "primer", "primera", "segunda", "ingreso", "acceso", "nuevo", "nueva", "plantilla",
        "carrec", "cargo",
    ]
    private static let genericStems = Set(generic.map(stem))
    /// «técnico medio», «técnico superior», «oficial»…: sin especialidad.
    static let level: Set<String> = ["tecnic", "mitj", "medi", "superior", "auxiliar", "administraci", "administracion", "general",
                                     "especial", "gestio", "gestion", "grau", "grad", "titulad", "diplomad", "licenciad", "oficial", "operari"]
    /// Si un puesto tiene una de estas palabras y el otro no, son plazas distintas.
    private static let discrim: Set<String> = ["auxiliar", "superior", "mitj", "medi", "jef", "cap", "oficial", "ayudant", "ajudant",
        "primer", "segund", "inspector", "subinspector", "coordinador", "director", "responsabl", "encargad", "peon", "peo", "conserj",
        "administrativ", "administratiu", "subaltern", "ordenanz", "agent", "sargent", "cabo", "intendent", "comisari"]

    public static func stem(_ word: String) -> String {
        guard word.count > 4 else { return word }
        var w = Array(word)
        if word.hasSuffix("es") && w.count > 6 && "rlnd".contains(w[w.count - 3]) { w.removeLast(2) }
        else if w.last == "s" { w.removeLast() }
        if w.count > 4, let last = w.last, "oae".contains(last) { w.removeLast() }
        return String(w)
    }

    private static let num = "(?:\\d+|una?|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce|quince|veinte|treinta|cuarenta|" +
        "cincuenta|dues|quatre|sis|set|vuit|nou|deu|duas|catro|sete|oito)"
    private static let count = Rx("\\b(" + num + ")(?:\\s*\\(\\d+\\))?\\s+(?:plazas?|places?|placa|prazas?|puestos?|llocs?)\\b")
    private static let numberAtEnd = Rx(num + "(?:\\s*\\(\\d+\\))?\\s*$")
    private static let numberWords: [String: Int] = ["un": 1, "una": 1, "dos": 2, "dues": 2, "duas": 2, "tres": 3, "cuatro": 4,
        "quatre": 4, "catro": 4, "cinco": 5, "cinc": 5, "seis": 6, "sis": 6, "siete": 7, "set": 7, "sete": 7, "ocho": 8,
        "vuit": 8, "oito": 8, "nueve": 9, "nou": 9, "diez": 10, "deu": 10, "once": 11, "doce": 12, "quince": 15,
        "veinte": 20, "treinta": 30, "cuarenta": 40, "cincuenta": 50]
    private static let filler = Rx(
        #"^(?:(?:unica|permanente|ordinaria|extraordinaria|urgente|urgent|d'urgencia|posibles|eventuales|futuras|vacantes?|de|del|d'|y|i|e|personal|persoal|laboral|temporal|"# +
        #"funcionari[oa]?|interin[oa]?|fij[oa]|fix|treball|trabajo|traballo|empleo|emprego|ocupacio|las?|los|el|les|els|categoria|cuerpo|escala)"# +
        #"(?:\s+|(?<=')))+"#)
    private static let codeParen = Rx(#"\((?:\s*\d|codi|cod|exp|sel|rh|ref|conv|oep|grup|subgrup|[abc][12]\b|pp\.)[^)]*\)"#)
    private static let genderSlash = Rx(#"(\w)/[a-z]{1,4}\b"#)
    private static let genderParen = Rx(#"\((?:a|as|os|o)\)"#)
    private static let leadingCount = Rx(#"^(?:\d+\s+|una?\s+|dos\s+|tres\s+|\(\d+\)\s*)+"#)
    private static let leadingPlace = Rx(#"^(?:plazas?|places?|placa|prazas?|puestos?)\s+(?:de |d'|del )?"#)
    private static let placeTrigger = Rx(#"^(?:plazas?|places?|placa|prazas?)\b"#)
    private static let groupCode = Rx("[abc][12]?")

    private static func cleanTitle(_ title: String) -> String {
        genderParen.replace(genderSlash.replace(fold(title), "$1"), "")
    }

    public static func plazasCount(_ title: String) -> Int? {
        let t = cleanTitle(title)
        guard let m = count.first(t) else { return nil }
        let w = t.sub(m.range(at: 1))
        return Int(w) ?? numberWords[w]
    }

    /// El puesto con lo que va entre paréntesis y sin ello.
    public static func jobKeys(_ title: String) -> [Set<String>] {
        var keys: [Set<String>] = []
        for inside in [true, false] {
            if let key = jobKey(title, insideParens: inside), !keys.contains(key) { keys.append(key) }
        }
        return keys
    }

    /// Palabras del puesto, sin género ni plural; nil si el texto no lo dice.
    public static func jobKey(_ title: String, insideParens: Bool = true) -> Set<String>? {
        let coded = codeParen.replace(cleanTitle(title), " ; ")
        let t = insideParens ? coded.replacingOccurrences(of: "(", with: " ").replacingOccurrences(of: ")", with: " ")
            : parens.replace(coded, " ")
        var best: (Int, Set<String>)?
        for m in posStart.matches(t) {
            let start = m.range.location
            let before = t.sub(NSRange(location: max(0, start - 16), length: start - max(0, start - 16)))
            let trigger = t.sub(m.range)
            let prio = numberAtEnd.contains(before) ? 0 : (placeTrigger.contains(trigger) ? 1 : 2)
            var rest = t.from(start + m.range.length)
            rest = filler.replace(leadingPlace.replace(leadingCount.replace(rest, ""), ""), "")
            let segment: String
            if let cut = posStop.first(rest) { segment = rest.to(cut.range.location) }
            else { segment = String(rest.prefix(60)) }
            let found = tokens(segment)
                .filter { !generic.contains($0) && $0.contains(where: { !$0.isNumber }) && !groupCode.whole($0) }
                .map(stem).filter { !genericStems.contains($0) }
            if !found.isEmpty, found.joined(separator: " ").count >= 4, best == nil || prio < best!.0 {
                best = (prio, Set(found.prefix(6)))
            }
        }
        return best?.1
    }

    public static func sameJob(_ a: Set<String>?, _ b: Set<String>?, sameBasesDate: Bool = false) -> Bool {
        guard let a, let b else { return false }
        if a == b { return true }
        let (small, big) = a.count <= b.count ? (a, b) : (b, a)
        if small.isSubset(of: level) && !sameBasesDate { return false }
        return small.count >= 2 && small.isSubset(of: big) && big.subtracting(small).isDisjoint(with: discrim)
    }

    // MARK: Modalidad

    private static let modeRules: [(String, Rx)] = [
        ("interna", Rx("promocion interna|promocio interna|promocion intern")),
        ("movilidad", Rx("movilidad|mobilitat|concurso de traslados|comision de servicios|comissio de serveis")),
        ("libre_designacion", Rx("libre designacion|lliure designacio")),
        ("estabilizacion", Rx("estabilizacion|estabilitzacio|excepcional")),
        ("bolsa", Rx("bolsa|borsa|lista de (?:espera|reserva)|interin|temporal|substitu|sustitu")),
        ("fija", Rx("en propiedad|personal laboral fijo|laboral fix|funcionari[oa]s? de carrera|funcionari de carrera|" +
                    "plazas? vacantes?|oferta de empleo publico|turno libre|torn lliure")),
    ]

    public static func modes(_ title: String) -> Set<String> {
        let t = fold(title)
        return Set(modeRules.filter { $0.1.contains(t) }.map(\.0))
    }

    /// Si los dos dicen la modalidad y no comparten ninguna, son procesos distintos.
    public static func compatible(_ aTitle: String, _ bTitle: String) -> Bool {
        var a = modes(aTitle), b = modes(bTitle)
        if a.contains("bolsa") && plazasCount(aTitle) != nil { a.insert("fija") }
        if b.contains("bolsa") && plazasCount(bTitle) != nil { b.insert("fija") }
        if a.isEmpty || b.isEmpty { return true }
        return !a.isDisjoint(with: b)
    }

    // MARK: Trámite

    public static let stepBases = "Bases y convocatoria"
    public static let stepBOE = "Extracto en el BOE"
    public static let stepOther = "Anuncio relacionado"
    private static let steps: [(String, Rx)] = [
        ("Corrección de errores", #"correcci(?:on|o) d(?:e|')\s*(?:error|errad|erro)|rectificaci|se corrigen errores|subsanaci"#),
        ("Modificación de bases", "modificaci(?:on|o) (?:de |d'|das? )?(?:las |les |as )?bases"),
        ("Lista definitiva de admitidos", "(?:admitid|admes|admisi).{0,60}definitiv|definitiv.{0,60}(?:admitid|admes|admisi)"),
        ("Lista provisional de admitidos", "(?:admitid|admes|admisi).{0,60}provisional|provisional.{0,60}(?:admitid|admes|admisi)|" +
            "admitidos y excluidos|admesos i exclosos|lista de admitidos"),
        ("Tribunal", "tribunal|organo de seleccion|organ de seleccio|comision de valoracion|composicion del organo"),
        ("Fecha de examen", "(?:fecha|data|dia|lugar|convocatoria).{0,40}(?:ejercicio|examen|prueba|exercici|proba)|primer ejercicio|celebracion d"),
        ("Aprobados o resultado", "aprobad|aprovad|superad|resultado|resultat|calificacion|puntuacion|qualificacio|" +
            "propuesta de (?:nombramiento|contratacion)|relacion definitiva|seleccionad"),
        ("Nombramiento", "nombramiento|nomenament|nombra |toma de posesion|presa de possessio|se nombra"),
        ("Bolsa resultante", "(?:constitucion|composicion|creacion|funcionamiento|activacion).{0,30}bolsa|lista de reserva|" +
            "bolsa resultante|borsa resultant"),
        ("Extracto", "^extracto|referente a la convocatoria|anuncio de convocatoria|extracte"),
        (stepBases, "bases|convocatoria|convoca|proceso selectivo|proces selectiu"),
    ].map { ($0.0, Rx($0.1)) }

    /// Tipo de trámite según el título (orientativo: se muestra como «posible»).
    public static func stepOf(_ title: String, isBoe: Bool = false) -> String {
        let t = fold(title)
        let found = steps.first { $0.1.contains(t) }?.0
        if isBoe && (found == nil || found == "Extracto" || found == stepBases) { return stepBOE }
        return found ?? stepOther
    }

    // MARK: Pareja

    /// Datos de un anuncio para emparejar (`FollowUpMatcher.Item` en Android).
    public struct Item: Sendable {
        public let url: String, title: String, entity: String, date: String, source: String
        public let cido: Bool, isBoe: Bool
        public let extract: BoeExtract?
        public let org: Org?
        public let step: String

        public init(url: String, title: String, entity: String, date: String, source: String,
                    cido: Bool = false, isBoe: Bool = false, extract: BoeExtract? = nil) {
            self.url = url; self.title = title; self.entity = entity; self.date = date; self.source = source
            self.cido = cido; self.isBoe = isBoe; self.extract = extract
            org = FollowUpMatcher.localOrg(entity: entity, title: title)
            step = FollowUpMatcher.stepOf(title, isBoe: isBoe)
        }

        /// El título o, en el BOE, cada plaza del extracto.
        var texts: [String] {
            if let items = extract?.items, !items.isEmpty { return items }
            return [title]
        }
    }

    /// ¿Puede `candidate` ser otro paso de la convocatoria guardada en `favorite`?
    public static func isFollowUp(_ favorite: Item, _ candidate: Item) -> Bool {
        if candidate.cido || candidate.url == favorite.url { return false }
        if !sameOrg(favorite.org, candidate.org) { return false }
        if favorite.source == candidate.source && favorite.step == stepBases && candidate.step == stepBases { return false }
        let sameBasesDate = candidate.extract?.basesDate == favorite.date || favorite.extract?.basesDate == candidate.date
        return favorite.texts.contains { f in candidate.texts.contains { c in textsMatch(f, c, sameBasesDate) } }
    }

    private static func textsMatch(_ fav: String, _ cand: String, _ sameBasesDate: Bool) -> Bool {
        // Sin paréntesis solo por un lado: si los dos los llevan y dicen cosas distintas, son plazas distintas.
        let candKeys = jobKeys(cand)
        var matched: Set<String>?
        for (i, f) in jobKeys(fav).enumerated() where matched == nil {
            for (j, c) in candKeys.enumerated() where (i == 0 || j == 0) && !(i + j > 0 && f.isSubset(of: level)) {
                if sameJob(f, c, sameBasesDate: sameBasesDate) { matched = f; break }
            }
        }
        guard let fj = matched, compatible(fav, cand) else { return false }
        let a = plazasCount(fav), b = plazasCount(cand)
        if let a, let b, a != b { return false }
        let ma = modes(fav), mb = modes(cand)
        if (a != nil && !ma.contains("bolsa") && mb.contains("bolsa") && b == nil) ||
            (b != nil && !mb.contains("bolsa") && ma.contains("bolsa") && a == nil) { return false }
        if fj.isSubset(of: level) && !(a != nil && b != nil) && !sameBasesDate { return false }
        return true
    }
}

// MARK: - Guardado (`FollowUps.kt`, misma clave y el mismo JSON)

public struct FollowUpItem: Equatable, Sendable {
    public static let pending = "pending", yes = "yes", no = "no"
    public var notice: Notice
    public var step: String
    public var state: String
    public var unread: Bool

    public init(notice: Notice, step: String, state: String = FollowUpItem.pending, unread: Bool = false) {
        self.notice = notice
        self.step = step
        self.state = state
        self.unread = unread
    }
}

public struct FollowUpState: Equatable, Sendable {
    public var initialized: Bool
    public var items: [FollowUpItem]

    public init(initialized: Bool = false, items: [FollowUpItem] = []) {
        self.initialized = initialized
        self.items = items
    }

    /// Lo que se enseña: sin los descartados, del más reciente al más antiguo.
    public var visible: [FollowUpItem] {
        items.filter { $0.state != FollowUpItem.no }
            .sorted { NoticeDates.sortKey($0.notice.date) > NoticeDates.sortKey($1.notice.date) }
    }
    public var unreadCount: Int { items.filter { $0.unread && $0.state != FollowUpItem.no }.count }
}

public enum FollowUps {
    static let key = "favorite_followups_v1"
    /// Los boletines de más se descargan como mucho cada 3 horas (o al guardar una favorita).
    public static let every: TimeInterval = 3 * 60 * 60
    static let maxItems = 40

    public struct Stored: Equatable, Sendable {
        public var lastCheck: Double
        public var favorites: [String: FollowUpState]
        public init(lastCheck: Double = 0, favorites: [String: FollowUpState] = [:]) {
            self.lastCheck = lastCheck
            self.favorites = favorites
        }
    }

    public static func encode(_ stored: Stored) -> Data {
        var favorites: [String: Any] = [:]
        for (id, state) in stored.favorites {
            favorites[id] = ["init": state.initialized, "items": state.items.compactMap { item -> [String: Any]? in
                guard let data = try? JSONEncoder().encode(item.notice),
                      var json = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any] else { return nil }
                json["step"] = item.step
                json["state"] = item.state
                json["unread"] = item.unread
                return json
            }]
        }
        let root: [String: Any] = ["v": 1, "lastCheck": stored.lastCheck, "favorites": favorites]
        return (try? JSONSerialization.data(withJSONObject: root)) ?? Data()
    }

    public static func parse(_ data: Data?) -> Stored {
        guard let data, let root = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any] else { return Stored() }
        let favorites = root["favorites"] as? [String: Any] ?? [:]
        var out: [String: FollowUpState] = [:]
        for (id, value) in favorites {
            guard let o = value as? [String: Any] else { continue }
            let items = (o["items"] as? [Any] ?? []).compactMap { raw -> FollowUpItem? in
                guard let json = raw as? [String: Any], let d = try? JSONSerialization.data(withJSONObject: json),
                      let notice = try? JSONDecoder().decode(Notice.self, from: d) else { return nil }
                let state = json["state"] as? String ?? FollowUpItem.pending
                return FollowUpItem(notice: notice, step: json["step"] as? String ?? FollowUpMatcher.stepOther,
                                    state: [FollowUpItem.yes, FollowUpItem.no].contains(state) ? state : FollowUpItem.pending,
                                    unread: json["unread"] as? Bool ?? false)
            }
            out[id] = FollowUpState(initialized: o["init"] as? Bool ?? false, items: items)
        }
        let last = (root["lastCheck"] as? NSNumber)?.doubleValue ?? 0
        return Stored(lastCheck: last, favorites: out)
    }

    /// Origen de un anuncio para el emparejador.
    public static func item(_ notice: Notice, extracts: [String: BoeExtract]) -> FollowUpMatcher.Item {
        let source = Source.of(notice)
        return FollowUpMatcher.Item(url: notice.url, title: notice.title, entity: notice.entity, date: notice.date,
                                    source: source.code, cido: source.isCido, isBoe: source.isBOE,
                                    extract: extracts[notice.url])
    }

    /// Busca los posibles pasos de cada favorita (`FollowUps.update` en Android). Devuelve el estado
    /// nuevo y las novedades que merecen aviso: las que aparecen después de la primera búsqueda.
    public static func update(favorites: [Notice], candidates: [Notice], extracts: [String: BoeExtract],
                              previous: [String: FollowUpState]) -> ([String: FollowUpState], [(Notice, FollowUpItem)]) {
        var byOrg: [String: [(Notice, FollowUpMatcher.Item)]] = [:]
        var ids = Set<String>()
        for notice in candidates where ids.insert(notice.id).inserted {
            let it = item(notice, extracts: extracts)
            guard let org = it.org else { continue }
            byOrg[org.name, default: []].append((notice, it))
        }
        var result: [String: FollowUpState] = [:]
        var fresh: [(Notice, FollowUpItem)] = []
        for favorite in favorites {
            let before = previous[favorite.id] ?? FollowUpState()
            let fav = item(favorite, extracts: extracts)
            guard let org = fav.org else {
                result[favorite.id] = FollowUpState(initialized: true, items: before.items)
                continue
            }
            let known = Set(before.items.map(\.notice.id))
            let added = (byOrg[org.name] ?? []).filter { notice, it in
                notice.id != favorite.id && !known.contains(notice.id) && FollowUpMatcher.isFollowUp(fav, it)
            }.map { FollowUpItem(notice: $0.0, step: $0.1.step, unread: before.initialized) }
            fresh += added.filter(\.unread).map { (favorite, $0) }
            let items = (before.items + added)
                .sorted { NoticeDates.sortKey($0.notice.date) > NoticeDates.sortKey($1.notice.date) }
                .prefix(maxItems)
            result[favorite.id] = FollowUpState(initialized: true, items: Array(items))
        }
        return (result, fresh)
    }

    /// Copia en `next` el estado y la lectura guardados en `latest` para los mismos anuncios.
    public static func keepAnswers(_ next: [String: FollowUpState], _ latest: [String: FollowUpState]) -> [String: FollowUpState] {
        next.mapValues { _ in FollowUpState() }.reduce(into: [:]) { out, pair in
            var state = next[pair.key]!
            let saved = Dictionary((latest[pair.key]?.items ?? []).map { ($0.notice.id, $0) }, uniquingKeysWith: { a, _ in a })
            state.items = state.items.map { item in
                guard let s = saved[item.notice.id] else { return item }
                var copy = item
                copy.state = s.state
                copy.unread = s.unread
                return copy
            }
            out[pair.key] = state
        }
    }

    /// Plazas de los extractos del BOE (campo `proveer` de `plazos/boe.json`).
    public static func parseBoeExtracts(_ data: Data) -> [String: BoeExtract] {
        guard let root = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              root["schemaVersion"] as? Int == 1, let all = root["proveer"] as? [String: Any] else { return [:] }
        var out: [String: BoeExtract] = [:]
        for (url, value) in all where url.hasPrefix("https://www.boe.es/") {
            guard let o = value as? [String: Any], let raw = o["items"] as? [Any] else { continue }
            let items = raw.compactMap { ($0 as? String)?.trimmingCharacters(in: .whitespacesAndNewlines) }
                .filter { (10...300).contains($0.count) }
            guard !items.isEmpty, items.count <= 15 else { continue }
            let date = (o["bases"] as? [String: Any])?["fecha"] as? String
            let valid = date.flatMap { $0.range(of: #"^\d\d/\d\d/20\d\d$"#, options: .regularExpression) != nil ? $0 : nil }
            out[url] = BoeExtract(items: items, basesDate: valid)
        }
        return out
    }

    /// Boletines donde puede salir otro paso (`SourceCatalog.followUpSources` en Android): el propio,
    /// los de su comunidad y el BOE, sin CIDO.
    public static func sources(for source: Source, available: [Source]) -> [Source] {
        available.filter { s in
            !s.isCido && (s == source || s.isBOE || (source.community != nil && s.community == source.community))
        }
    }
}

extension Store {
    public var followUps: FollowUps.Stored { FollowUps.parse(defaults.data(forKey: FollowUps.key)) }

    public func saveFollowUps(_ stored: FollowUps.Stored) {
        defaults.set(FollowUps.encode(stored), forKey: FollowUps.key)
    }

    public func followUpState(_ favoriteId: String) -> FollowUpState { followUps.favorites[favoriteId] ?? FollowUpState() }

    private func changeFollowUp(_ favoriteId: String, _ change: (inout FollowUpState) -> Void) {
        var stored = followUps
        var state = stored.favorites[favoriteId] ?? FollowUpState()
        change(&state)
        stored.favorites[favoriteId] = state
        saveFollowUps(stored)
    }

    /// Al abrir la ficha de la favorita: las novedades dejan de serlo.
    public func markFollowUpsRead(_ favoriteId: String) {
        guard followUpState(favoriteId).unreadCount > 0 else { return }
        changeFollowUp(favoriteId) { state in
            state.items = state.items.map { var i = $0; i.unread = false; return i }
        }
    }

    /// «Sí» o «No» a «¿Es de esta convocatoria?». «No» la oculta para siempre.
    public func answerFollowUp(_ favoriteId: String, noticeId: String, yes: Bool) {
        changeFollowUp(favoriteId) { state in
            state.items = state.items.map {
                var i = $0
                if i.notice.id == noticeId { i.state = yes ? FollowUpItem.yes : FollowUpItem.no; i.unread = false }
                return i
            }
        }
    }

    public func removeFollowUps(_ favoriteId: String) {
        var stored = followUps
        if stored.favorites.removeValue(forKey: favoriteId) != nil { saveFollowUps(stored) }
    }
}
