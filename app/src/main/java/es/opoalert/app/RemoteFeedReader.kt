package es.opoalert.app

import org.json.JSONObject
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL

/** Lee el resultado auditado del rastreador central. No interpreta el HTML del BOP. */
data class RemoteFeed(
    val notices: List<Notice>,
    val status: String,
    val historyStatus: String
)

object RemoteFeedReader {
    fun fetch(address: String): RemoteFeed {
        val url = URL(address)
        if (url.protocol.lowercase() != "https" || url.host.isBlank() ||
            url.userInfo != null || url.port != -1 || url.ref != null) {
            throw IOException("La fuente debe ser una URL HTTPS publica y valida")
        }
        val connection = url.openConnection() as HttpURLConnection
        connection.connectTimeout = 16000
        connection.readTimeout = 20000
        connection.instanceFollowRedirects = true
        connection.setRequestProperty("Accept", "application/json")
        connection.setRequestProperty("User-Agent", "OpoAlert-Android/0.4")
        return try {
            if (connection.responseCode !in 200..299) {
                throw IOException("La fuente devolvio HTTP ${connection.responseCode}")
            }
            // Evita cargar archivos arbitrariamente grandes en la memoria del movil.
            val bytes = connection.inputStream.use { stream ->
                val out = java.io.ByteArrayOutputStream()
                val buffer = ByteArray(8192)
                while (true) {
                    val n = stream.read(buffer)
                    if (n == -1) break
                    if (out.size() + n > 5_000_000) throw IOException("Archivo JSON demasiado grande")
                    out.write(buffer, 0, n)
                }
                out.toByteArray()
            }
            parse(String(bytes, Charsets.UTF_8))
        } catch (error: org.json.JSONException) {
            throw IOException("La fuente no contiene un JSON valido", error)
        } finally {
            connection.disconnect()
        }
    }

    fun parse(text: String): RemoteFeed {
        val root = JSONObject(text)
        val coverage = root.optJSONObject("coverage")
            ?: throw IOException("El feed no incluye auditoria de cobertura")
        if (!coverage.optBoolean("complete", false)) {
            throw IOException("El lector central no ha confirmado el final del boletin")
        }
        val source = root.optString("source", "")
        if (source != "https://bop.dival.es/bop/xhtml/portal.xhtml") {
            throw IOException("La fuente de los anuncios no coincide con el BOP Valencia")
        }
        val checked = root.optString("lastCheckedUTC", "")
        if (checked.isBlank()) throw IOException("No consta fecha de la ultima lectura")
        val array = root.optJSONArray("notices")
            ?: throw IOException("El feed no contiene una lista de anuncios")
        if (array.length() > 5000) throw IOException("Demasiados anuncios para esta version")
        val records = (0 until array.length()).map { index ->
            val notice = Notice.fromJson(array.getJSONObject(index))
            if (!notice.id.matches(Regex("\\d{4}/\\d{3,7}")) ||
                !notice.url.startsWith("https://bop.dival.es/bop/downloads?")) {
                throw IOException("El feed contiene un registro no valido")
            }
            notice
        }.distinctBy { it.id }
        val bulletin = coverage.optString("bulletin", "?")
        val pages = coverage.optInt("pagesVisited", 0)
        val announcements = coverage.optInt("announcementsRead", 0)
        val status = "BOP $bulletin: $announcements anuncios en $pages paginas · Feed actualizado $checked"
        val history = root.optJSONObject("historyCoverage")
        val historyStatus = if (history?.optBoolean("complete", false) == true) {
            "Historico verificado: ${history.optString("rangeStart")} a ${history.optString("rangeEnd")}"
        } else {
            "Historico acumulado: aun sin confirmar los ultimos 30 dias completos"
        }
        return RemoteFeed(records, status, historyStatus)
    }
}
