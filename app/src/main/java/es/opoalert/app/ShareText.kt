package es.opoalert.app

/**
 * Texto que se manda al compartir una convocatoria (WhatsApp, Telegram, correo…).
 * Lleva el enlace oficial, el plazo literal si se conoce y, al final, el enlace para
 * descargar OpoAlert (la página elige Google Play o el App Store según el móvil).
 */
object ShareText {
    const val APP_LINK = "https://mjtbapps.github.io/OpoAlert/app.html"
    const val SUBJECT = "Convocatoria de empleo público · OpoAlert"

    fun bulletin(id: String): String = when {
        id.startsWith("CIDO") -> "CIDO"
        id.startsWith("BOE-A-") -> "BOE"
        id.startsWith("MD-") -> "BOCM"
        id.startsWith("CM-") -> "DOCM"
        id.startsWith("CY-") -> "BOCYL"
        id.startsWith("EX-") -> "DOE"
        id.startsWith("MU-") -> "BORM"
        id.startsWith("DV-") -> "DOGV"
        id.startsWith("DC-") -> "DOGC"
        id.startsWith("BJ-") -> "BOJA"
        id.startsWith("AO-") -> "BOA"
        id.startsWith("DG-") -> "DOG"
        id.startsWith("PV-") -> "BOPV"
        else -> "BOP"
    }

    fun message(notice: Notice, deadline: Deadline? = null): String = buildString {
        append("📢 ").append(NoticeText.headline(notice.title)).append('\n')
        if (notice.entity.isNotBlank()) append(notice.entity).append('\n')
        append(bulletin(notice.id)).append(' ').append(notice.province).append(" · ").append(notice.date).append('\n')
        if (deadline != null) {
            append("⏱ Plazo: ").append(deadline.label).append(" (según el anuncio)\n")
        }
        append("\nAnuncio oficial: ").append(notice.url).append('\n')
        append("Comprueba siempre las bases y los plazos en el anuncio oficial.\n\n")
        append("Visto en OpoAlert, la app gratis de oposiciones y empleo público: ").append(APP_LINK)
    }
}
