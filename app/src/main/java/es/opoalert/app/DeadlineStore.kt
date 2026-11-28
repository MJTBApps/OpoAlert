package es.opoalert.app

import android.content.Context
import org.json.JSONObject
import java.io.File
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL

/**
 * Plazo de presentación tal como lo escribe el anuncio. [until] es la fecha orientativa del
 * último día, «como pronto», que `backend/plazo_fin.py` solo calcula cuando el plazo cuenta
 * desde este mismo boletín (sin festivos autonómicos ni locales, que solo pueden alargarlo).
 */
data class Deadline(val days: Int, val kind: String, val text: String, val page: Int,
                    val until: java.time.LocalDate? = null) {
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

    private val sedeHost = Regex("^([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\\.)+(es|cat|gal|eus|org|com|net|eu|online|info)$")

    /**
     * Sede electrónica de quien convoca, copiada del anuncio por `backend/plazos.py`
     * (campo `sedes`). Solo HTTPS y un dominio con forma normal; si no, nada.
     */
    fun findSede(context: Context, province: Province, noticeUrl: String): String? {
        val text = try {
            read(context, province)
        } catch (_: Exception) {
            return null
        } ?: return null
        return try {
            parseSede(text, noticeUrl)
        } catch (_: Exception) {
            null
        }
    }

    /**
     * Plazas de los extractos del BOE de ayuntamientos (campo `proveer` de `plazos/boe.json`,
     * copiado del PDF por `backend/plazos.py`). Para el seguimiento de favoritas.
     */
    fun boeExtracts(context: Context): Map<String, BoeExtract> = try {
        read(context, Province.BOE)?.let { parseBoeExtracts(it) }.orEmpty()
    } catch (_: Exception) {
        emptyMap()
    }

    private val feedDay = Regex("\\d\\d/\\d\\d/20\\d\\d")

    fun parseBoeExtracts(text: String): Map<String, BoeExtract> {
        val root = JSONObject(text)
        if (root.optInt("schemaVersion") != 1) return emptyMap()
        val all = root.optJSONObject("proveer") ?: return emptyMap()
        val out = HashMap<String, BoeExtract>()
        for (url in all.keys()) {
            if (!url.startsWith("https://www.boe.es/")) continue
            val o = all.optJSONObject(url) ?: continue
            val array = o.optJSONArray("items") ?: continue
            val items = (0 until array.length()).map { array.optString(it).trim() }.filter { it.length in 10..300 }
            if (items.isEmpty() || items.size > 15) continue
            val date = o.optJSONObject("bases")?.optString("fecha")?.takeIf { feedDay.matches(it) }
            out[url] = BoeExtract(items, date)
        }
        return out
    }

    fun parseSede(text: String, noticeUrl: String): String? {
        val root = JSONObject(text)
        if (root.optInt("schemaVersion") != 1) return null
        val link = root.optJSONObject("sedes")?.optString(noticeUrl).orEmpty()
        if (!link.startsWith("https://") || link.length > 120) return null
        val host = link.removePrefix("https://").substringBefore('/').removePrefix("www.")
        return if (sedeHost.matches(host)) link else null
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
        return Deadline(days, kind, quote, page, parseUntil(item.optString("hasta")))
    }

    private val isoDay = Regex("20\\d\\d-\\d\\d-\\d\\d")

    fun parseUntil(raw: String): java.time.LocalDate? =
        if (!isoDay.matches(raw)) null else try { java.time.LocalDate.parse(raw) } catch (_: Exception) { null }

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
