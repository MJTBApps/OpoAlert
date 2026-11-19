package es.opoalert.app

/**
 * Alertas privadas, guardadas solamente en el dispositivo.
 * Las provincias de cada alerta se cruzan con las provincias seguidas.
 */
data class AlertRule(
    val id: String,
    val phrase: String,
    val provinces: Set<Province>,
    val enabled: Boolean = true,
)

object SmartAlertMatcher {
    private val whitespace = Regex("\\s+")

    /** La búsqueda por términos ignora tildes, caja y el orden de las palabras. */
    fun matches(rule: AlertRule, notice: Notice, followed: Set<Province>): Boolean {
        if (!rule.enabled || rule.provinces.isEmpty()) return false
        val actualProvince = Province.fromLabel(notice.province)
            ?: Province.fromNoticeId(notice.id)
        if (actualProvince !in rule.provinces || actualProvince !in followed) return false
        val terms = SearchText.normalize(rule.phrase).trim()
            .split(whitespace).filter { it.isNotBlank() }
        if (terms.isEmpty()) return false
        val haystack = SearchText.normalize(notice.title + " " + notice.entity)
        return terms.all { termMatches(it, haystack) }
    }

    private val genderEnding = Regex("(os|as|o|a)$")

    /**
     * «administrativo» también encuentra «administrativa», «administrativo/a»
     * o «administrativas/os»: una palabra acabada en -o/-a/-os/-as vale con
     * cualquiera de esas terminaciones. Nunca encuentra menos que antes.
     */
    internal fun termMatches(term: String, haystack: String): Boolean {
        if (haystack.contains(term)) return true
        val ending = genderEnding.find(term) ?: return false
        val stem = term.substring(0, ending.range.first)
        if (stem.length < 4) return false
        return Regex(Regex.escape(stem) + "(os|as|o|a)(?![\\p{L}\\p{N}])").containsMatchIn(haystack)
    }

    /**
     * Para el filtro «Avisos» de la lista: cada convocatoria que coincide con
     * alguna alerta activa, con las frases de las alertas que la encuentran.
     */
    fun hits(
        notices: List<Notice>, rules: List<AlertRule>, followed: Set<Province>
    ): Map<String, List<String>> {
        val active = rules.filter { it.enabled }
        if (active.isEmpty() || followed.isEmpty()) return emptyMap()
        val result = LinkedHashMap<String, List<String>>()
        for (notice in notices) {
            if (notice.id in result) continue
            val phrases = active.filter { matches(it, notice, followed) }
                .map { it.phrase.trim() }.distinct()
            if (phrases.isNotEmpty()) result[notice.id] = phrases
        }
        return result
    }

    /** Una misma convocatoria genera, como máximo, un aviso aunque coincida con varias alertas. */
    fun matching(
        newNotices: List<Notice>, rules: List<AlertRule>, followed: Set<Province>
    ): List<Notice> {
        if (rules.none { it.enabled } || followed.isEmpty()) return emptyList()
        return newNotices.filter { notice -> rules.any { matches(it, notice, followed) } }
            .distinctBy { it.id }
    }
}
