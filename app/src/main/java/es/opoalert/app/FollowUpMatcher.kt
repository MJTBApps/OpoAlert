package es.opoalert.app

import java.text.Normalizer

/**
 * Plazas que cita un extracto del BOE de un ayuntamiento y fecha del boletín donde se
 * publicaron sus bases, copiadas del PDF por `backend/plazos.py` (campo `proveer`).
 * El título del BOE no dice el puesto («referente a la convocatoria para proveer una plaza»).
 */
data class BoeExtract(val items: List<String>, val basesDate: String?)

/**
 * Seguimiento de favoritas (1.59.0): ¿puede este anuncio ser otro paso de la misma
 * convocatoria? Mismo organismo LOCAL (ayuntamiento, diputación, comarca, mancomunidad,
 * cabildo o consell insular) y mismo puesto, sin masculino ni femenino, con la misma
 * modalidad y el mismo número de plazas cuando los dos lo dicen.
 *
 * Medido el 28/11/2026 con los feeds reales: 94 % de aciertos en la última muestra
 * revisada a mano. Por eso la app dice siempre «posible» y pide confirmarlo. Las
 * consejerías, ministerios y universidades quedan fuera: sus títulos son tan genéricos
 * que casi todas las parejas eran falsas.
 *
 * La misma lógica está en `ios/OpoAlertCore/.../FollowUp.swift` y en `backend/seguimiento.py`;
 * los casos de `backend/tests/seguimiento_casos.json` los comprueban las tres.
 */
object FollowUpMatcher {
    data class Org(val kind: String, val name: String)

    fun fold(text: String): String =
        Normalizer.normalize(text.lowercase(), Normalizer.Form.NFKD)
            .replace(Regex("\\p{Mn}+"), "")
            .replace('’', '\'').replace("·", "")

    // ---------- organismo ----------
    private val kinds = listOf(
        "ayto" to "(?:excmo\\.?|excelentisimo|ilustre|iltre\\.?|m\\.?\\s*i\\.?)?\\s*(?:ayuntamientos?|ajuntament|concello|udala|ayto\\.?)",
        "dipu" to "(?:excma\\.?)?\\s*(?:diputacion|diputacio|deputacion)(?: provincial| foral)?",
        "comarca" to "(?:comarca|consell comarcal)",
        "manc" to "(?:mancomunidad|mancomunitat)",
        "cabildo" to "cabildo(?: insular)?",
        "consell" to "consell insular",
        "univ" to "(?:universidad|universitat|universidade)",
    ).map { (kind, rx) -> kind to Regex("^\\s*(?:$rx)\\b") }
    private val orgStop = setOf("de", "del", "d", "la", "el", "los", "las", "l", "les", "els", "a", "o", "os", "as",
        "y", "i", "e", "do", "da", "dos", "das")
    private val orgInTitle = Regex(
        "\\b(ayuntamiento|ajuntament|concello|diputacion provincial|diputacion|universidad|comarca|mancomunidad|cabildo insular)" +
            "\\s+(de |del |d')?([^,.;()]+?)(?=\\s*(?:\\(|,|\\.|;| sobre | por | referente| relativ| de fecha| para | que | en |$))"
    )
    private val words = Regex("[a-z0-9]+")

    private fun orgFrom(text: String): Org? {
        var t = fold(text).trim(' ', '–', '-')
        t = t.replace(Regex("\\([^)]*\\)"), " ").split(" - ").first()
        var kind: String? = null
        for ((k, rx) in kinds) {
            val m = rx.find(t) ?: continue
            kind = k
            t = t.substring(m.range.last + 1)
            break
        }
        val tokens = words.findAll(t).map { it.value }.filter { it !in orgStop }.toList()
        if (tokens.isEmpty()) return null
        return Org(kind ?: "?", tokens.joinToString(" "))
    }

    private fun orgKey(entity: String, title: String): Org? {
        val m = orgInTitle.find(fold(title))
        val fromTitle = m?.let { orgFrom(it.groupValues[1] + " " + it.groupValues[3]) }
        // BOJA trae en «entity» un texto de la web que no es el organismo.
        val bad = entity.isBlank() || "recomendador" in fold(entity)
        val fromEntity = if (bad) null else orgFrom(entity)
        if (fromEntity != null && fromEntity.kind == "?" && fromTitle != null && fromTitle.kind != "?") return fromTitle
        return fromEntity ?: fromTitle
    }

    private val regional = Regex(
        "\\b(?:consejeria|conselleria|departament|departamento|ministerio|servicio|servei|servizo|comunidad|comunitat|administracion|" +
            "direccion|direccio|instituto|institut|agencia|osakidetza|organismo|organisme|junta|gobierno|govern|generalitat|xunta|consorci|" +
            "consorcio|fundacion|fundacio|escuela|escola|sociedad|empresa|entidad|ente|parlamento|tribunal|corporacion|universidad|" +
            "hospital|area|seccion|presidencia|vicepresidencia|educacion|sanidad|salud|justicia|hacienda|economia|empleo|trabajo|cultura|turismo|" +
            "interior|igualdad|derechos|bienestar|medio ambiente|agricultura|industria|vivienda|transportes|deporte|juventud|familia|politica)\\b"
    )
    private val localKinds = setOf("ayto", "dipu", "comarca", "manc", "cabildo", "consell")

    /** Organismo local del anuncio, o null si no es local o no se reconoce. */
    fun localOrg(entity: String, title: String): Org? {
        val o = orgKey(entity, title) ?: return null
        if (o.kind in localKinds) return o
        if (o.kind == "?" && !regional.containsMatchIn(o.name)) return Org("ayto", o.name)
        return null
    }

    fun sameOrg(a: Org?, b: Org?): Boolean {
        if (a == null || b == null || a.name != b.name) return false
        return a.kind == b.kind || (("?" == a.kind || "?" == b.kind) && setOf(a.kind, b.kind).all { it == "?" || it == "ayto" })
    }

    // ---------- puesto ----------
    private val posStart = Regex(
        "\\b(?:plazas?|places?|placa|prazas?|puestos?(?: de trabajo)?|llocs?(?: de treball)?|postos?(?: de traballo)?|" +
            "bolsas?(?: de (?:trabajo|empleo|empleo temporal|trabajo temporal|traballo|emprego))?|borsas?(?: de treball| d'ocupacio)?|" +
            "categorias?(?: profesional)?|cuerpos?|escala|especialidad)\\s+(?:vacantes?\\s+|vacants?\\s+)?" +
            "(?:de |del |d'|en la categoria de |para (?:la contratacion de |cubrir )?)?"
    )
    private val posStop = Regex(
        "[,.;:\\[\"«]| mediante| por (?!cuenta)| per | pel | como | com | en regimen| vacantes?\\b| del grupo| grupo | subgrupo| incluid| correspondiente|" +
            " de la plantilla| de este| de esta| del ayuntamiento| de l'ajuntament| del concello| para (?!la contratacion)| en el | en la | con caracter| turno|" +
            " sistema| personal | funcionari| laboral| escala| a traves| de la oferta| oep| en propiedad| interin| temporal| fij[oa]| de caracter| reservad| y la constitucion|" +
            " y constitucion| y creacion| y formacion| y bolsa| mas bolsa| \\d{4}\\b| expediente| exp\\b| de administracion (?:general|especial)| del organismo|" +
            " de la (?:diputacion|universidad)| d'aquest| de l'| pertenec| pertany| dins"
    )
    private val generic = setOf(
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
    )
    private val genericStems = generic.map { stem(it) }.toSet()

    /** «técnico medio», «técnico superior», «oficial»…: sin especialidad. */
    private val level = setOf("tecnic", "mitj", "medi", "superior", "auxiliar", "administraci", "administracion", "general", "especial",
        "gestio", "gestion", "grau", "grad", "titulad", "diplomad", "licenciad", "oficial", "operari")
    /** Si un puesto tiene una de estas palabras y el otro no, son plazas distintas. */
    private val discrim = setOf("auxiliar", "superior", "mitj", "medi", "jef", "cap", "oficial", "ayudant", "ajudant", "primer",
        "segund", "inspector", "subinspector", "coordinador", "director", "responsabl", "encargad", "peon", "peo", "conserj",
        "administrativ", "administratiu", "subaltern", "ordenanz", "agent", "sargent", "cabo", "intendent", "comisari")

    fun stem(word: String): String {
        if (word.length <= 4) return word
        var w = word
        if (w.endsWith("es") && w.length > 6 && w[w.length - 3] in "rlnd") w = w.dropLast(2)
        else if (w.endsWith("s")) w = w.dropLast(1)
        if (w.length > 4 && w.last() in "oae") w = w.dropLast(1)
        return w
    }

    private const val NUM = "(?:\\d+|una?|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce|quince|veinte|treinta|cuarenta|" +
        "cincuenta|dues|quatre|sis|set|vuit|nou|deu|duas|catro|sete|oito)"
    private val count = Regex("\\b($NUM)(?:\\s*\\(\\d+\\))?\\s+(?:plazas?|places?|placa|prazas?|puestos?|llocs?)\\b")
    private val numberAtEnd = Regex("$NUM(?:\\s*\\(\\d+\\))?\\s*$")
    private val numberWords = mapOf("un" to 1, "una" to 1, "dos" to 2, "dues" to 2, "duas" to 2, "tres" to 3, "cuatro" to 4,
        "quatre" to 4, "catro" to 4, "cinco" to 5, "cinc" to 5, "seis" to 6, "sis" to 6, "siete" to 7, "set" to 7, "sete" to 7,
        "ocho" to 8, "vuit" to 8, "oito" to 8, "nueve" to 9, "nou" to 9, "diez" to 10, "deu" to 10, "once" to 11, "doce" to 12,
        "quince" to 15, "veinte" to 20, "treinta" to 30, "cuarenta" to 40, "cincuenta" to 50)
    private val filler = Regex(
        "^(?:(?:unica|permanente|ordinaria|extraordinaria|urgente|urgent|d'urgencia|posibles|eventuales|futuras|vacantes?|de|del|d'|y|i|e|personal|persoal|laboral|temporal|" +
            "funcionari[oa]?|interin[oa]?|fij[oa]|fix|treball|trabajo|traballo|empleo|emprego|ocupacio|las?|los|el|les|els|categoria|cuerpo|escala)" +
            "(?:\\s+|(?<=')))+"
    )
    private val codeParen = Regex("\\((?:\\s*\\d|codi|cod|exp|sel|rh|ref|conv|oep|grup|subgrup|[abc][12]\\b|pp\\.)[^)]*\\)")
    private val genderSlash = Regex("(\\w)/[a-z]{1,4}\\b")
    private val genderParen = Regex("\\((?:a|as|os|o)\\)")
    private val leadingCount = Regex("^(?:\\d+\\s+|una?\\s+|dos\\s+|tres\\s+|\\(\\d+\\)\\s*)+")
    private val leadingPlace = Regex("^(?:plazas?|places?|placa|prazas?|puestos?)\\s+(?:de |d'|del )?")
    private val placeTrigger = Regex("^(?:plazas?|places?|placa|prazas?)\\b")
    private val groupCode = Regex("[abc][12]?")

    private fun cleanTitle(title: String): String =
        fold(title).replace(genderSlash, "$1").replace(genderParen, "")

    fun plazasCount(title: String): Int? {
        val w = count.find(cleanTitle(title))?.groupValues?.get(1) ?: return null
        return w.toIntOrNull() ?: numberWords[w]
    }

    private val anyParen = Regex("\\([^)]*\\)")

    /**
     * El puesto con lo que va entre paréntesis («técnico medio (inspector de actividades)») y sin
     * ello («operario de servicios múltiples (oficial 1.ª)»).
     */
    fun jobKeys(title: String): List<Set<String>> =
        listOfNotNull(jobKey(title, true), jobKey(title, false)).distinct()

    /** Palabras del puesto, sin género ni plural; null si el texto no lo dice. */
    fun jobKey(title: String, insideParens: Boolean = true): Set<String>? {
        val coded = cleanTitle(title).replace(codeParen, " ; ")
        val t = if (insideParens) coded.replace("(", " ").replace(")", " ") else coded.replace(anyParen, " ")
        var best: Pair<Int, Set<String>>? = null
        for (m in posStart.findAll(t)) {
            val before = t.substring(maxOf(0, m.range.first - 16), m.range.first)
            val prio = when {
                numberAtEnd.containsMatchIn(before) -> 0
                placeTrigger.containsMatchIn(m.value) -> 1
                else -> 2
            }
            var rest = t.substring(m.range.last + 1)
            rest = leadingCount.replace(rest, "")
            rest = leadingPlace.replace(rest, "")
            rest = filler.replace(rest, "")
            val cut = posStop.find(rest)
            val segment = if (cut != null) rest.substring(0, cut.range.first) else rest.take(60)
            val tokens = words.findAll(segment).map { it.value }
                .filter { it !in generic && it.any { c -> !c.isDigit() } && !groupCode.matches(it) }
                .map { stem(it) }.filter { it !in genericStems }.toList()
            if (tokens.isNotEmpty() && tokens.joinToString(" ").length >= 4 && (best == null || prio < best.first)) {
                best = prio to tokens.take(6).toSet()
            }
        }
        return best?.second
    }

    fun sameJob(a: Set<String>?, b: Set<String>?, sameBasesDate: Boolean = false): Boolean {
        if (a == null || b == null) return false
        if (a == b) return true
        val (small, big) = if (a.size <= b.size) a to b else b to a
        if (level.containsAll(small) && !sameBasesDate) return false
        return small.size >= 2 && big.containsAll(small) && (big - small).none { it in discrim }
    }

    // ---------- modalidad ----------
    private val modeRules = listOf(
        "interna" to Regex("promocion interna|promocio interna|promocion intern"),
        "movilidad" to Regex("movilidad|mobilitat|concurso de traslados|comision de servicios|comissio de serveis"),
        "libre_designacion" to Regex("libre designacion|lliure designacio"),
        "estabilizacion" to Regex("estabilizacion|estabilitzacio|excepcional"),
        "bolsa" to Regex("bolsa|borsa|lista de (?:espera|reserva)|interin|temporal|substitu|sustitu"),
        "fija" to Regex("en propiedad|personal laboral fijo|laboral fix|funcionari[oa]s? de carrera|funcionari de carrera|" +
            "plazas? vacantes?|oferta de empleo publico|turno libre|torn lliure"),
    )

    fun modes(title: String): Set<String> {
        val t = fold(title)
        return modeRules.filter { it.second.containsMatchIn(t) }.map { it.first }.toSet()
    }

    /** Si los dos dicen la modalidad y no comparten ninguna, son procesos distintos. */
    fun compatible(aTitle: String, bTitle: String): Boolean {
        var a = modes(aTitle)
        var b = modes(bTitle)
        // «una plaza … y constitución de bolsa»: la bolsa acompaña a la plaza.
        if ("bolsa" in a && plazasCount(aTitle) != null) a = a + "fija"
        if ("bolsa" in b && plazasCount(bTitle) != null) b = b + "fija"
        if (a.isEmpty() || b.isEmpty()) return true
        return a.intersect(b).isNotEmpty()
    }

    // ---------- trámite ----------
    const val STEP_BASES = "Bases y convocatoria"
    const val STEP_BOE = "Extracto en el BOE"
    const val STEP_OTHER = "Anuncio relacionado"
    private val steps = listOf(
        "Corrección de errores" to "correcci(?:on|o) d(?:e|')\\s*(?:error|errad|erro)|rectificaci|se corrigen errores|subsanaci",
        "Modificación de bases" to "modificaci(?:on|o) (?:de |d'|das? )?(?:las |les |as )?bases",
        "Lista definitiva de admitidos" to "(?:admitid|admes|admisi).{0,60}definitiv|definitiv.{0,60}(?:admitid|admes|admisi)",
        "Lista provisional de admitidos" to "(?:admitid|admes|admisi).{0,60}provisional|provisional.{0,60}(?:admitid|admes|admisi)|" +
            "admitidos y excluidos|admesos i exclosos|lista de admitidos",
        "Tribunal" to "tribunal|organo de seleccion|organ de seleccio|comision de valoracion|composicion del organo",
        "Fecha de examen" to "(?:fecha|data|dia|lugar|convocatoria).{0,40}(?:ejercicio|examen|prueba|exercici|proba)|primer ejercicio|celebracion d",
        "Aprobados o resultado" to "aprobad|aprovad|superad|resultado|resultat|calificacion|puntuacion|qualificacio|" +
            "propuesta de (?:nombramiento|contratacion)|relacion definitiva|seleccionad",
        "Nombramiento" to "nombramiento|nomenament|nombra |toma de posesion|presa de possessio|se nombra",
        "Bolsa resultante" to "(?:constitucion|composicion|creacion|funcionamiento|activacion).{0,30}bolsa|lista de reserva|" +
            "bolsa resultante|borsa resultant",
        "Extracto" to "^extracto|referente a la convocatoria|anuncio de convocatoria|extracte",
        STEP_BASES to "bases|convocatoria|convoca|proceso selectivo|proces selectiu",
    ).map { (name, rx) -> name to Regex(rx) }

    /** Tipo de trámite según el título (orientativo: se muestra como «posible»). */
    fun stepOf(title: String, isBoe: Boolean = false): String {
        val t = fold(title)
        val found = steps.firstOrNull { it.second.containsMatchIn(t) }?.first
        if (isBoe && (found == null || found == "Extracto" || found == STEP_BASES)) return STEP_BOE
        return found ?: STEP_OTHER
    }

    // ---------- pareja ----------
    /**
     * Datos de un anuncio para emparejar. [source] identifica el boletín (dos anuncios del
     * mismo boletín que son los dos «bases» son procesos distintos); [cido] marca el catálogo
     * CIDO, que repite el anuncio del BOP y no cuenta como novedad.
     */
    data class Item(
        val url: String, val title: String, val entity: String, val date: String, val source: String,
        val cido: Boolean = false, val isBoe: Boolean = false, val extract: BoeExtract? = null,
    ) {
        val org: Org? by lazy { localOrg(entity, title) }
        /** Textos con el puesto: el título o, en el BOE, cada plaza del extracto. */
        val texts: List<String> get() = extract?.items?.takeIf { it.isNotEmpty() } ?: listOf(title)
        val step: String by lazy { stepOf(title, isBoe) }
    }

    /** ¿Puede [candidate] ser otro paso de la convocatoria guardada en [favorite]? */
    fun isFollowUp(favorite: Item, candidate: Item): Boolean {
        if (candidate.cido || candidate.url == favorite.url) return false
        if (!sameOrg(favorite.org, candidate.org)) return false
        if (favorite.source == candidate.source && favorite.step == STEP_BASES && candidate.step == STEP_BASES) return false
        // El extracto del BOE cita la fecha del boletín de las bases: si coincide, es casi seguro.
        val sameBasesDate = candidate.extract?.basesDate == favorite.date || favorite.extract?.basesDate == candidate.date
        return favorite.texts.any { f -> candidate.texts.any { c -> textsMatch(f, c, sameBasesDate) } }
    }

    private fun textsMatch(fav: String, cand: String, sameBasesDate: Boolean): Boolean {
        // Sin paréntesis solo por un lado: si los dos los llevan y dicen cosas distintas, son plazas distintas.
        val candKeys = jobKeys(cand)
        val fj = jobKeys(fav).withIndex().firstOrNull { (i, f) ->
            candKeys.withIndex().any { (j, c) ->
                (i == 0 || j == 0) && !(i + j > 0 && level.containsAll(f)) && sameJob(f, c, sameBasesDate)
            }
        }?.value ?: return false
        if (!compatible(fav, cand)) return false
        val a = plazasCount(fav)
        val b = plazasCount(cand)
        if (a != null && b != null && a != b) return false
        val ma = modes(fav)
        val mb = modes(cand)
        if ((a != null && "bolsa" !in ma && "bolsa" in mb && b == null) ||
            (b != null && "bolsa" !in mb && "bolsa" in ma && a == null)) return false
        // Puesto sin especialidad: solo con el mismo número de plazas o la fecha de las bases.
        if (level.containsAll(fj) && !(a != null && b != null) && !sameBasesDate) return false
        return true
    }
}
