package es.opoalert.app

import android.content.Context
import org.json.JSONObject
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import java.util.Locale

/**
 * Seguimiento de cada favorita, solo en el móvil (1.57.0): fecha orientativa de fin del plazo
 * (copiada de `DeadlineStore`, para ordenar sin conexión), si ya se ha presentado la solicitud
 * y una nota propia. Las notas y el estado son de Premium; el orden por plazo, para todos.
 */
data class AgendaEntry(val until: LocalDate? = null, val checked: Boolean = false,
                       val submitted: Boolean = false, val note: String = "")

object FavoriteAgenda {
    private const val PREFS = "opoalert_store"
    private const val KEY = "favorite_agenda_v1"
    const val NOTE_MAX = 300

    @Synchronized
    fun all(context: Context): Map<String, AgendaEntry> {
        val raw = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(KEY, "{}") ?: "{}"
        return try {
            val json = JSONObject(raw)
            json.keys().asSequence().associateWith { id ->
                val o = json.getJSONObject(id)
                AgendaEntry(
                    DeadlineStore.parseUntil(o.optString("until")),
                    o.optBoolean("checked"), o.optBoolean("submitted"), o.optString("note").take(NOTE_MAX)
                )
            }
        } catch (_: Exception) {
            emptyMap()
        }
    }

    fun get(context: Context, id: String): AgendaEntry = all(context)[id] ?: AgendaEntry()

    @Synchronized
    fun update(context: Context, id: String, change: (AgendaEntry) -> AgendaEntry) {
        val next = all(context).toMutableMap()
        next[id] = change(next[id] ?: AgendaEntry())
        save(context, next)
    }

    /** Se borra al quitar la favorita. */
    @Synchronized
    fun remove(context: Context, id: String) {
        val next = all(context).toMutableMap()
        if (next.remove(id) != null) save(context, next)
    }

    private fun save(context: Context, entries: Map<String, AgendaEntry>) {
        val json = JSONObject()
        for ((id, e) in entries) {
            json.put(id, JSONObject().apply {
                e.until?.let { put("until", it.toString()) }
                put("checked", e.checked)
                put("submitted", e.submitted)
                if (e.note.isNotBlank()) put("note", e.note.take(NOTE_MAX))
            })
        }
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().putString(KEY, json.toString()).apply()
    }

    /**
     * Orden de Favoritas: primero las que tienen plazo por delante (la que acaba antes, arriba),
     * luego las que no tienen fecha y al final las de plazo pasado o ya presentadas.
     * Dentro de cada grupo se respeta el orden en que se guardaron.
     */
    fun sort(favorites: List<Notice>, agenda: Map<String, AgendaEntry>, today: LocalDate): List<Notice> =
        favorites.withIndex().sortedWith(compareBy({ (_, n) ->
            val e = agenda[n.id]
            when {
                e?.submitted == true -> 3
                e?.until == null -> 1
                e.until.isBefore(today) -> 2
                else -> 0
            }
        }, { (i, n) ->
            val e = agenda[n.id]
            if (e?.until != null && e.submitted.not() && !e.until.isBefore(today)) e.until.toEpochDay() else i.toLong()
        })).map { it.value }

    /**
     * Completa la fecha orientativa de las favoritas que aún no la tienen (el plazo se lee
     * horas después de publicarse el anuncio). Bloquea: se llama fuera del hilo principal.
     * Devuelve true si ha cambiado algo.
     */
    fun refresh(context: Context, favorites: List<Notice>): Boolean {
        var changed = false
        val agenda = all(context)
        for (notice in favorites) {
            val entry = agenda[notice.id]
            if (entry?.until != null) continue
            val province = Province.fromLabel(notice.province) ?: Province.fromNoticeId(notice.id)
            val until = DeadlineStore.find(context, province, notice.url)?.until
            if (until != null || entry?.checked != true) {
                update(context, notice.id) { it.copy(until = until, checked = true) }
                if (until != null) {
                    changed = true
                    DeadlineReminder.sync(context, notice)
                }
            }
        }
        return changed
    }

    private val dayFormat = DateTimeFormatter.ofPattern("EEEE d 'de' MMMM", Locale.forLanguageTag("es-ES"))

    /** «jueves 20 de noviembre». */
    fun longDay(date: LocalDate): String = dayFormat.format(date)

    fun shortDay(date: LocalDate): String = "%02d/%02d".format(date.dayOfMonth, date.monthValue)
}
