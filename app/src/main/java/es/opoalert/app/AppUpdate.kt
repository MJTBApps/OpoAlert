package es.opoalert.app

import android.content.Context
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

/**
 * Aviso de versión nueva. La app no está en una tienda: se actualiza con la APK
 * de la web (misma firma, así que se instala encima sin perder datos).
 * La web publica version.json con la última APK disponible.
 */
object AppUpdate {
    private const val PREFS = "opoalert_store"
    private const val LATEST = "latest_app_version_v1"
    private const val DISMISSED = "dismissed_app_version_v1"
    private const val BASE = "https://mjtbapps.github.io/OpoAlert/"
    private val VERSION = Regex("\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}")

    /** Consulta la web; sin conexión se conserva lo que ya se sabía. */
    fun refresh(context: Context) {
        val connection = URL(BASE + "version.json").openConnection() as HttpURLConnection
        try {
            connection.connectTimeout = 12000
            connection.readTimeout = 15000
            if (connection.responseCode !in 200..299) return
            val text = connection.inputStream.use { it.readBytes().takeIf { b -> b.size < 10_000 } }
                ?.toString(Charsets.UTF_8) ?: return
            val latest = parseLatest(text) ?: return
            context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().putString(LATEST, latest).apply()
        } catch (_: Exception) {
        } finally {
            connection.disconnect()
        }
    }

    fun parseLatest(text: String): String? = try {
        JSONObject(text).optString("latestVersion").takeIf { VERSION.matches(it) }
    } catch (_: Exception) { null }

    /** Versión nueva por instalar que el usuario aún no ha descartado, o null. */
    fun pending(context: Context): String? {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val latest = prefs.getString(LATEST, null) ?: return null
        val current = context.packageManager.getPackageInfo(context.packageName, 0).versionName ?: return null
        if (!isNewer(latest, current) || prefs.getString(DISMISSED, null) == latest) return null
        return latest
    }

    fun dismiss(context: Context, version: String) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().putString(DISMISSED, version).apply()
    }

    /** La APK sale siempre de la web de OpoAlert; nunca de una URL recibida. */
    fun apkUrl(version: String): String = "${BASE}OpoAlert-$version.apk"

    fun isNewer(candidate: String, current: String): Boolean {
        val a = candidate.split('.').map { it.toIntOrNull() ?: 0 }
        val b = current.substringBefore('-').split('.').map { it.toIntOrNull() ?: 0 }
        for (i in 0 until maxOf(a.size, b.size)) {
            val x = a.getOrElse(i) { 0 }
            val y = b.getOrElse(i) { 0 }
            if (x != y) return x > y
        }
        return false
    }
}
