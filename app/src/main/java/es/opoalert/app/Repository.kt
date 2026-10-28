package es.opoalert.app

import android.content.Context
import org.json.JSONArray
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

data class SyncResult(
    val all: List<Notice>,
    val newOnes: List<Notice>,
    val scanned: Int,
    val sourceMessage: String,
    val historyMessage: String
)

object Repository {
    private const val PREFS = "opoalert_store"
    private const val ENTRIES = "entries"
    private const val INITIALIZED = "initialized"
    private const val REMOTE_INITIALIZED = "remote_feed_initialized_v04"
    private const val FEED_URL = "remote_feed_url_v04"
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

    // The feed belongs to OpoAlert; end users do not need to configure a URL.
    fun feedUrl(ctx: Context): String = DEFAULT_FEED_URL

    fun setFeedUrl(ctx: Context, address: String) {
        val normalized = address.trim()
        if (normalized.isNotEmpty() && !normalized.startsWith("https://", ignoreCase = true)) {
            throw IllegalArgumentException("La direccion debe empezar por https://")
        }
        val prefs = ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        if (prefs.getString(FEED_URL, "") != normalized) {
            prefs.edit().putString(FEED_URL, normalized)
                .putBoolean(REMOTE_INITIALIZED, false).apply()
        }
    }

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
        // Nunca se borra una cache correcta si la descarga o auditoria fallan.
        val remote = feedUrl(ctx).isNotBlank()
        val feed = if (remote) RemoteFeedReader.fetch(feedUrl(ctx)) else null
        val freshRead = feed?.notices ?: BopReader().fetch()
        val prefs = ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val old = cached(ctx)
        val oldIds = old.map { it.id }.toHashSet()
        // Al activar un feed historico no se envian alertas de 30 dias anteriores.
        val wasInitialized = prefs.getBoolean(if (remote) REMOTE_INITIALIZED else INITIALIZED, false)
        val newOnes = if (wasInitialized) freshRead.filter { it.id !in oldIds } else emptyList()
        val merged = (freshRead + old).distinctBy { it.id }
            .sortedWith(compareByDescending<Notice> { dateKey(it.date) }.thenByDescending { it.id })
            .take(2000)
        val saved = JSONArray().also { array -> merged.forEach { array.put(it.toJson()) } }
        val whenSync = SimpleDateFormat("dd/MM/yyyy HH:mm", Locale("es", "ES")).format(Date())
        val sourceMessage = feed?.status ?: "Solo portada del BOP · lectura NO exhaustiva"
        val historyMessage = feed?.historyStatus ?: "Configura un feed central para leer el sumario completo"
        val preferenceKey = if (remote) REMOTE_INITIALIZED else INITIALIZED
        if (!prefs.edit()
                .putString(ENTRIES, saved.toString())
                .putString(LAST_SYNC, whenSync)
                .putString(LAST_SOURCE, sourceMessage)
                .putString(LAST_HISTORY, historyMessage)
                .putBoolean(preferenceKey, true).commit()) {
            throw IllegalStateException("No se han podido guardar los datos")
        }
        return SyncResult(merged, newOnes, freshRead.size, sourceMessage, historyMessage)
    }

    private fun dateKey(date: String): String {
        val parts = date.split('/')
        return if (parts.size == 3) "${parts[2]}${parts[1]}${parts[0]}" else date
    }
}
