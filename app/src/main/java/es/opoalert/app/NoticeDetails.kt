package es.opoalert.app

/**
 * Solo presenta el número de plazas escrito en el encabezado oficial (con cifra o con letra).
 * OpoAlert NO calcula plazos de solicitud ni presume fechas de cierre.
 */
object NoticeDetails {
    // Cifra o número escrito con letra (castellano y catalán) justo antes de «plaza(s)»/«plaça/places».
    private val places = Regex("""(?iu)(?<![\p{L}\d])(\d{1,3}|[\p{L}]+)\s+(?:plazas?|pla[çc]a|places)\b""")
    private val words = mapOf(
        "una" to 1, "un" to 1, "uno" to 1, "dos" to 2, "dues" to 2, "tres" to 3, "cuatro" to 4, "quatre" to 4,
        "cinco" to 5, "cinc" to 5, "seis" to 6, "sis" to 6, "siete" to 7, "set" to 7, "ocho" to 8, "vuit" to 8,
        "nueve" to 9, "nou" to 9, "diez" to 10, "deu" to 10, "once" to 11, "onze" to 11, "doce" to 12,
        "dotze" to 12, "trece" to 13, "tretze" to 13, "catorce" to 14, "catorze" to 14, "quince" to 15,
        "quinze" to 15, "dieciséis" to 16, "dieciseis" to 16, "setze" to 16, "diecisiete" to 17,
        "disset" to 17, "dieciocho" to 18, "divuit" to 18, "diecinueve" to 19, "dinou" to 19,
        "veinte" to 20, "vint" to 20,
    )
    private val group = Regex("""(?iu)\b(?:subgrupo|grupo|subgrup|grup)\s*:?\s*(A1|A2|C1|C2|B|E)\b""")

    fun placesInTitle(title: String): Int? {
        if (NoticeText.isProcedureUpdate(title)) return null
        val explicit = places.findAll(title).mapNotNull { match ->
            val value = match.groupValues[1]
            value.toIntOrNull() ?: words[value.lowercase(java.util.Locale.ROOT)]
        }.distinct().toList()
        return explicit.singleOrNull()?.takeIf { it > 0 }
    }

    fun groupInTitle(title: String): String? =
        group.find(title)?.groupValues?.get(1)?.uppercase(java.util.Locale.ROOT)

    // Los datos oficiales actuales no incluyen un plazo de solicitudes verificado.
    // El cómputo puede depender de una publicación posterior en BOE/DOGV.
    fun deadlineLabel(): String = "Consultar bases"
}
