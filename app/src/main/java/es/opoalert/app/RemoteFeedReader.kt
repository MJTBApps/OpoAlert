package es.opoalert.app

import org.json.JSONObject
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL

/** The backend audits each provincial bulletin before Android accepts its feed. */
data class RemoteFeed(
    val notices: List<Notice>,
    val status: String,
    val historyStatus: String,
)

object RemoteFeedReader {
    fun fetch(address: String, province: Province = Province.VALENCIA): RemoteFeed {
        // URLs are never taken from user input: only our audited Github Pages files.
        if (address != province.feedUrl) throw IOException("Fuente provincial no autorizada")
        val url = URL(address)
        if (url.protocol.lowercase() != "https" || url.host != "mjtbapps.github.io" ||
            url.userInfo != null || url.port != -1 || url.ref != null) {
            throw IOException("La fuente debe ser una URL HTTPS de OpoAlert")
        }
        val connection = url.openConnection() as HttpURLConnection
        connection.connectTimeout = 16000
        connection.readTimeout = 20000
        connection.instanceFollowRedirects = true
        connection.setRequestProperty("Accept", "application/json")
        connection.setRequestProperty("User-Agent", "OpoAlert-Android/1.0")
        return try {
            if (connection.responseCode !in 200..299) {
                throw IOException("Fuente ${province.label}: HTTP ${connection.responseCode}")
            }
            val bytes = connection.inputStream.use { stream ->
                val out = java.io.ByteArrayOutputStream()
                val buffer = ByteArray(8192)
                while (true) {
                    val n = stream.read(buffer)
                    if (n == -1) break
                    if (out.size() + n > 5_000_000) throw IOException("JSON provincial demasiado grande")
                    out.write(buffer, 0, n)
                }
                out.toByteArray()
            }
            parse(String(bytes, Charsets.UTF_8), province)
        } catch (error: org.json.JSONException) {
            throw IOException("Fuente ${province.label}: JSON invalido", error)
        } finally {
            connection.disconnect()
        }
    }

    fun parse(text: String, province: Province = Province.VALENCIA): RemoteFeed {
        val root = JSONObject(text)
        val coverage = root.optJSONObject("coverage")
            ?: throw IOException("${province.label}: falta auditoria oficial")
        if (!coverage.optBoolean("complete", false)) {
            throw IOException("${province.label}: lectura no confirmada")
        }
        val source = root.optString("source", "")
        if (source != province.expectedSource) {
            throw IOException("${province.label}: fuente oficial inesperada")
        }
        if (province != Province.VALENCIA && root.optString("province") != province.label) {
            throw IOException("${province.label}: identificacion provincial incorrecta")
        }
        if (root.optString("lastCheckedUTC").isBlank()) {
            throw IOException("${province.label}: falta fecha de comprobacion")
        }
        val history = root.optJSONObject("historyCoverage")
            ?: throw IOException("${province.label}: falta auditoria de 30 dias")
        if (!history.optBoolean("complete", false)) {
            throw IOException("${province.label}: falta auditoria de 30 dias")
        }
        if (history.optString("rangeStart").isBlank() || history.optString("rangeEnd").isBlank()) {
            throw IOException("${province.label}: periodo de fechas ausente")
        }
        val array = root.optJSONArray("notices")
            ?: throw IOException("${province.label}: falta lista de anuncios")
        if (array.length() > 5000) throw IOException("Demasiados anuncios de ${province.label}")
        val records = (0 until array.length()).map { index ->
            val notice = Notice.fromJson(array.getJSONObject(index))
            val docUrl = URL(notice.url)
            if (notice.title.isBlank() || !notice.id.matches(province.idPattern) ||
                notice.province != province.label ||
                docUrl.protocol.lowercase() != "https" ||
                docUrl.host != province.pdfHost ||
                !province.allowsOfficialPath(docUrl.path) ||
                docUrl.userInfo != null) {
                throw IOException("${province.label}: anuncio o enlace no validado")
            }
            notice
        }
        if (records.distinctBy { it.id }.size != records.size) {
            throw IOException("${province.label}: anuncios duplicados")
        }
        val bulletins = history.optJSONArray("bulletins")
        val currentBulletin = if (bulletins != null && bulletins.length() > 0)
            bulletins.optString(bulletins.length() - 1) else coverage.optString("bulletin", "?")
        val read = coverage.optInt("announcementsRead", 0)
        val cido = province in setOf(Province.BARCELONA, Province.GIRONA, Province.LLEIDA, Province.TARRAGONA)
        val status = if (cido) "${province.label}: CIDO · $read procesos" else
            "${province.label}: ${if (province == Province.BOE) "BOE" else "BOP"} $currentBulletin · $read anuncios"
        val historyStatus = if (cido)
            "CIDO (actualizaciones de procesos): ${history.optString("rangeStart")} a ${history.optString("rangeEnd")}" else
            "Histórico verificado: ${history.optString("rangeStart")} a ${history.optString("rangeEnd")}"
        return RemoteFeed(records, status, historyStatus)
    }
}
