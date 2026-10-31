package es.opoalert.app

import android.content.Context

/**
 * «Nuevas desde tu última visita». Una visita termina cuando la app pasa más de
 * 15 minutos sin usarse; así abrir una ficha y volver no borra las marcas. Es nueva
 * la convocatoria que no se había cargado en visitas anteriores, salvo las de un
 * boletín que se acaba de añadir (si no, todo su mes saldría como nuevo).
 * Todo se guarda solo en el móvil.
 */
object VisitStore {
    private const val PREFS = "opoalert_visits"
    private const val SEEN = "seen_ids_v1"
    private const val SEEN_SOURCES = "seen_sources_v1"
    private const val CURRENT = "visit_ids_v1"
    private const val CURRENT_SOURCES = "visit_sources_v1"
    private const val LAST_ACTIVE = "last_active_ms_v1"
    const val VISIT_GAP_MS = 15 * 60 * 1000L
    private const val MAX_IDS = 20000

    /** Al abrir la app: si la última vez fue hace más de 15 minutos, empieza otra visita. */
    fun startVisit(context: Context, now: Long = System.currentTimeMillis()) {
        val prefs = prefs(context)
        if (now - prefs.getLong(LAST_ACTIVE, 0L) < VISIT_GAP_MS) return
        val seen = prefs.getStringSet(SEEN, emptySet()).orEmpty() + prefs.getStringSet(CURRENT, emptySet()).orEmpty()
        prefs.edit()
            .putStringSet(SEEN, if (seen.size > MAX_IDS) prefs.getStringSet(CURRENT, emptySet()).orEmpty() else seen)
            .putStringSet(SEEN_SOURCES, prefs.getStringSet(SEEN_SOURCES, emptySet()).orEmpty() +
                prefs.getStringSet(CURRENT_SOURCES, emptySet()).orEmpty())
            .putStringSet(CURRENT, emptySet())
            .putStringSet(CURRENT_SOURCES, emptySet())
            .putLong(LAST_ACTIVE, now)
            .apply()
    }

    /** Las convocatorias cargadas en esta visita dejan de ser nuevas en la siguiente. */
    fun remember(context: Context, notices: List<Notice>, now: Long = System.currentTimeMillis()) {
        val prefs = prefs(context)
        prefs.edit()
            .putStringSet(CURRENT, prefs.getStringSet(CURRENT, emptySet()).orEmpty() + notices.map { it.id })
            .putStringSet(CURRENT_SOURCES, prefs.getStringSet(CURRENT_SOURCES, emptySet()).orEmpty() +
                notices.map { it.province })
            .putLong(LAST_ACTIVE, now)
            .apply()
    }

    fun newIds(context: Context, notices: List<Notice>): Set<String> {
        val prefs = prefs(context)
        val seen = prefs.getStringSet(SEEN, emptySet()).orEmpty()
        val sources = prefs.getStringSet(SEEN_SOURCES, emptySet()).orEmpty()
        return notices.filter { it.province in sources && it.id !in seen }.map { it.id }.toSet()
    }

    private fun prefs(context: Context) = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
}
