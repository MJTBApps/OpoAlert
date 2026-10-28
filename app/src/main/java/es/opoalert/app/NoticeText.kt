package es.opoalert.app

import java.util.Locale

/** Short, faithful previews of the public notice headings. The PDF remains authoritative. */
object NoticeText {
    private val rolePattern = Regex(
        """(?iu)(?:\b(?:\d+|un|una|dues|dos|tres|quatre|cuatro|cinc|cinco|sis|seis|set|siete|vuit|ocho|nou|nueve|deu|diez)\s+places?\s+(?:de\b|d')|\bborsa\b|\bbolsa de trabajo\b|\bplaça\s+(?:de\b|d')|\bplaza\s+(?:de\b|d')|\bplaces\s+(?:de\b|d')|\bplazas\s+(?:de\b|d'))"""
    )
    private val procedures = listOf(
        "designació de membres", "designación de miembros", "nomenament de membres",
        "modificació de les bases", "modificación de las bases", "rectificació de les bases",
        "correcció d'errades", "corrección de errores", "estimació del recurs",
        "addició d'una plaça"
    )
    private val cutMarkers = listOf(
        " corresponent a ", " incloses en ", " inclosa en ",
        " mitjançant el sistema ", " mediante el sistema ", " expedient "
    )

    /** A procedural notice must never look like a fresh vacancy just because it mentions a role. */
    fun isProcedureUpdate(officialTitle: String): Boolean =
        procedures.any { officialTitle.lowercase(Locale.ROOT).contains(it) }

    /**
     * Removes the formula "Anunci de [organisme] sobre..." and, where safe,
     * starts at the position or pool mentioned in the original text. Does not
     * translate, invent qualifications, or infer application deadlines.
     */
    fun headline(officialTitle: String): String {
        val whole = officialTitle.trim()
        val start = whole.indexOf(" sobre ", ignoreCase = true)
        val content = if (start >= 0) whole.substring(start + 7) else whole
        if (isProcedureUpdate(officialTitle)) {
            return content.trim().trimEnd('.').replaceFirstChar { it.uppercaseChar() }
        }
        val found = rolePattern.find(content)
        val subject = if (found != null) content.substring(found.range.first) else content
        val normalized = subject.replace(Regex("""\s+"""), " ").trim().trimEnd('.')
        val cutAt = cutMarkers.map { normalized.indexOf(it, ignoreCase = true) }
            .filter { it > 44 }.minOrNull()
        val title = if (cutAt != null) normalized.substring(0, cutAt) else normalized
        return title.replaceFirstChar { it.uppercaseChar() }
    }
}
