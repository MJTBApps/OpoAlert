package es.opoalert.app

import android.content.Context
import org.json.JSONArray
import java.io.IOException
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

data class SyncResult(
    val all: List<Notice>,
    val newOnes: List<Notice>,
    val scanned: Int,
    val sourceMessage: String,
    val historyMessage: String,
)

object Repository {
    private const val PREFS = "opoalert_store"
    private const val ENTRIES = "entries"
    private const val REMOTE_INITIALIZED = "remote_feed_initialized_v04"
    private const val INITIALIZED_PREFIX = "province_initialized_v1_"
    private const val DEFAULT_FEED_URL = "https://mjtbapps.github.io/OpoAlert/convocatorias.json"
    private const val LAST_SYNC = "last_sync"
    private const val LAST_SOURCE = "last_source_v04"
    private const val LAST_HISTORY = "last_history_v04"
    private const val ALERTS = "alerts"

    fun alertsEnabled(ctx: Context): Boolean =
        ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getBoolean(ALERTS, false)

    fun setAlertsEnabled(ctx: Context, enabled: Boolean) {
        ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().putBoolean(ALERTS, enabled).apply()
    }

    fun feedUrl(ctx: Context): String = DEFAULT_FEED_URL
    fun lastSync(ctx: Context): String =
        ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(LAST_SYNC, "") ?: ""
    fun lastSource(ctx: Context): String =
        ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(LAST_SOURCE, "") ?: ""
    fun lastHistory(ctx: Context): String =
        ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(LAST_HISTORY, "") ?: ""

    fun cached(ctx: Context): List<Notice> {
        val source = ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .getString(ENTRIES, "[]") ?: "[]"
        return try {
            val array = JSONArray(source)
            (0 until array.length()).mapNotNull { index ->
                try { Notice.fromJson(array.getJSONObject(index)) }
                catch (_: Exception) { null }
            }
        } catch (_: Exception) { emptyList() }
    }

    @Synchronized
    fun sync(ctx: Context): SyncResult {
        val chosen = ProvinceSettings.selected(ctx)
        val prefs = ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val old = cached(ctx)
        val oldIds = old.map { it.id }.toHashSet()
        val downloaded = mutableListOf<Pair<Province, RemoteFeed>>()
        val failures = mutableListOf<String>()
        // The Android app reads validated JSON; it never scrapes BOP HTML.
        for (province in Province.entries.filter { it in chosen }) {
            try {
                downloaded.add(province to RemoteFeedReader.fetch(province.feedUrl, province))
            } catch (_: Exception) {
                failures.add(province.label)
            }
        }
        if (downloaded.isEmpty()) {
            throw IOException("No se ha podido consultar ninguna de las provincias seleccionadas")
        }
        val fresh = downloaded.flatMap { it.second.notices }
        val newOnes = downloaded.flatMap { (province, feed) ->
            val initialized = prefs.getBoolean(INITIALIZED_PREFIX + province.code,
                province == Province.VALENCIA && prefs.getBoolean(REMOTE_INITIALIZED, false))
            if (initialized) feed.notices.filter { it.id !in oldIds } else emptyList()
        }
        val merged = (fresh + old).distinctBy { it.id }
            .sortedWith(compareByDescending<Notice> { dateKey(it.date) }.thenByDescending { it.id })
            .take(2000)
        val saved = JSONArray().also { array -> merged.forEach { array.put(it.toJson()) } }
        val whenSync = SimpleDateFormat("dd/MM/yyyy HH:mm", Locale("es", "ES")).format(Date())
        val sources = downloaded.joinToString(" · ") { it.second.status }
        val status = if (failures.isEmpty()) sources
            else "$sources · Sin datos verificados: ${failures.joinToString(", ")}" 
        val historyMessage = if (failures.isEmpty()) downloaded.first().second.historyStatus
            else "Cobertura parcial: pendientes ${failures.joinToString(", ")}" 
        val editor = prefs.edit()
            .putString(ENTRIES, saved.toString())
            .putString(LAST_SYNC, whenSync)
            .putString(LAST_SOURCE, status)
            .putString(LAST_HISTORY, historyMessage)
            .putBoolean(REMOTE_INITIALIZED, true)
        for ((province, _) in downloaded) {
            editor.putBoolean(INITIALIZED_PREFIX + province.code, true)
        }
        if (!editor.commit()) throw IOException("No se han podido guardar los datos")
        return SyncResult(merged, newOnes, fresh.size, status, historyMessage)
    }

    private fun dateKey(date: String): String {
        val parts = date.split('/')
        return if (parts.size == 3) "${parts[2]}${parts[1]}${parts[0]}" else date
    }
}
