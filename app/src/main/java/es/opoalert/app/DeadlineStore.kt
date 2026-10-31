package es.opoalert.app

import android.content.Context
import org.json.JSONObject
import java.io.File
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL

/** Plazo de presentación tal como lo escribe el anuncio. OpoAlert no calcula fechas. */
data class Deadline(val days: Int, val kind: String, val text: String, val page: Int) {
    val label: String get() = "$days días $kind"
}

/**
 * Lee `docs/plazos/<feed>.json` (lo genera `backend/plazos.py` en Actions): un archivo
 * por fuente, así solo se descarga el del boletín de la ficha. Se guarda unas horas en
 * la caché. Si no hay plazo o algo no cuadra, no se muestra nada.
 */
object DeadlineStore {
    private const val MAX_AGE_MS = 3 * 60 * 60 * 1000L
    private val kinds = setOf("hábiles", "naturales")

    fun urlFor(province: Province): String =
        province.feedUrl.substringBeforeLast('/') + "/plazos/" + province.feedUrl.substringAfterLast('/')

    /** Se llama fuera del hilo principal. */
    fun find(context: Context, province: Province, noticeUrl: String): Deadline? {
        val text = try {
            read(context, province)
        } catch (_: Exception) {
            return null
        } ?: return null
        return try {
            parse(text, noticeUrl)
        } catch (_: Exception) {
            null
        }
    }

    fun parse(text: String, noticeUrl: String): Deadline? {
        val root = JSONObject(text)
        if (root.optInt("schemaVersion") != 1) return null
        val item = root.optJSONObject("items")?.optJSONObject(noticeUrl) ?: return null
        val days = item.optInt("days", -1)
        val kind = item.optString("kind")
        val quote = item.optString("text").trim()
        val page = item.optInt("page", -1)
        // Las mismas comprobaciones que el servidor: si algo no encaja, mejor no mostrarlo.
        if (days !in 1..90 || kind !in kinds || page < 1 || quote.length !in 20..400) return null
        return Deadline(days, kind, quote, page)
    }

    private fun read(context: Context, province: Province): String? {
        val address = urlFor(province)
        val cache = File(File(context.cacheDir, "plazos").apply { mkdirs() }, address.substringAfterLast('/'))
        if (cache.exists() && System.currentTimeMillis() - cache.lastModified() < MAX_AGE_MS) return cache.readText()
        val url = URL(address)
        if (url.protocol != "https" || url.host != "mjtbapps.github.io") throw IOException("Origen no autorizado")
        val connection = url.openConnection() as HttpURLConnection
        connection.connectTimeout = 12000
        connection.readTimeout = 15000
        connection.setRequestProperty("Accept", "application/json")
        connection.setRequestProperty("User-Agent", "OpoAlert-Android/1.0")
        return try {
            when (connection.responseCode) {
                404 -> null  // fuente todavía sin plazos
                in 200..299 -> {
                    val bytes = connection.inputStream.use { stream ->
                        val out = java.io.ByteArrayOutputStream()
                        val buffer = ByteArray(8192)
                        while (true) {
                            val n = stream.read(buffer)
                            if (n == -1) break
                            if (out.size() + n > 3_000_000) throw IOException("Plazos demasiado grandes")
                            out.write(buffer, 0, n)
                        }
                        out.toByteArray()
                    }
                    String(bytes, Charsets.UTF_8).also { cache.writeText(it) }
                }
                else -> if (cache.exists()) cache.readText() else null
            }
        } catch (error: IOException) {
            if (cache.exists()) cache.readText() else throw error
        } finally {
            connection.disconnect()
        }
    }
}
