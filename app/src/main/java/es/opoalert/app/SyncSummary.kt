package es.opoalert.app

/**
 * Convierte el resumen interno de la última revisión ("VA: 61 · AL: 20 ·
 * Sin datos verificados: Cuenca") en un texto para personas.
 */
object SyncSummary {
    private val count = Regex("""\b[A-Z]{2}:\s*(\d+)""")

    fun describe(raw: String): String {
        val parts = raw.split(" · Sin datos verificados: ", limit = 2)
        val counts = count.findAll(parts[0]).map { it.groupValues[1].toInt() }.toList()
        if (counts.isEmpty()) return raw
        val notices = counts.sum()
        val text = "${notices} anuncio${if (notices == 1) "" else "s"} · " +
            if (counts.size == 1) "1 boletín" else "${counts.size} boletines"
        return if (parts.size == 2) "$text · sin datos: ${parts[1]}" else text
    }
}
