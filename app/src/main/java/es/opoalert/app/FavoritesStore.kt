package es.opoalert.app

import android.content.Context
import org.json.JSONArray

/**
 * Favoritos personales guardados de forma local.
 *
 * Se almacena la ficha COMPLETA, no solo el identificador, para que una plaza
 * siga disponible en Favoritas aunque desaparezca del sumario o de la cache.
 * Se conserva la misma instalacion de OpoAlert v0.1; no requiere cuenta.
 */
object FavoritesStore {
    private const val PREFS = "opoalert_store"
    private const val KEY = "favorites_v2"

    @Synchronized
    fun list(context: Context): List<Notice> {
        val raw = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .getString(KEY, "[]") ?: "[]"
        return try {
            val array = JSONArray(raw)
            (0 until array.length()).mapNotNull { index ->
                try { Notice.fromJson(array.getJSONObject(index)) }
                catch (_: Exception) { null }
            }.distinctBy { it.id }
        } catch (_: Exception) {
            emptyList()
        }
    }

    @Synchronized
    fun contains(context: Context, id: String): Boolean =
        list(context).any { it.id == id }

    /** Devuelve true si queda guardado, false si se ha eliminado de favoritos. */
    @Synchronized
    fun toggle(context: Context, notice: Notice): Boolean {
        val current = list(context)
        val wasSaved = current.any { it.id == notice.id }
        val next = if (wasSaved) {
            current.filterNot { it.id == notice.id }
        } else {
            listOf(notice) + current
        }
        val serialized = JSONArray().also { json ->
            next.forEach { json.put(it.toJson()) }
        }.toString()
        val saved = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit().putString(KEY, serialized).commit()
        if (!saved) throw IllegalStateException("No se han podido guardar los favoritos")
        return !wasSaved
    }
}
