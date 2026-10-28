package es.opoalert.app

/**
 * Solo presenta cifras presentes literalmente en el encabezado oficial.
 * OpoAlert NO calcula plazos de solicitud ni presume fechas de cierre.
 */
object NoticeDetails {
    private val places = Regex("""(?iu)\b(\d{1,3})\s+(?:plazas?|places?)\b""")
    private val group = Regex("""(?iu)\b(?:subgrupo|grupo|subgrup|grup)\s*:?\s*(A1|A2|C1|C2|B|E)\b""")

    fun placesInTitle(title: String): Int? {
        if (NoticeText.isProcedureUpdate(title)) return null
        val explicit = places.findAll(title).map { it.groupValues[1].toInt() }.distinct().toList()
        return explicit.singleOrNull()?.takeIf { it > 0 }
    }

    fun groupInTitle(title: String): String? =
        group.find(title)?.groupValues?.get(1)?.uppercase(java.util.Locale.ROOT)

    // Los datos oficiales actuales no incluyen un plazo de solicitudes verificado.
    // El cómputo puede depender de una publicación posterior en BOE/DOGV.
    fun deadlineLabel(): String = "Consultar bases"
}
