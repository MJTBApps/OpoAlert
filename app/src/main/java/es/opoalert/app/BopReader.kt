package es.opoalert.app

import org.jsoup.Jsoup
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL
import java.text.Normalizer
import java.util.Locale

/** Lectura experimental del SUMARIO VISIBLE del último boletín, NO de todo el histórico. */
class BopReader {
    private val sourceUrl = "https://bop.dival.es/bop/xhtml/portal.xhtml"
    private val metadata = Regex(
        """N[uú]m\.?\s*(?:de\s*)?regist(?:re|ro)\s*:\s*(\d{4}/\d{3,7}).{0,110}?(?:Data|Fecha)\s+publicaci[oó]n?\s*:\s*(\d{2}/\d{2}/\d{4}).{0,90}?(?:Butllet[ií]|Bolet[ií]n)\s*:\s*(\d+)""",
        setOf(RegexOption.IGNORE_CASE, RegexOption.DOT_MATCHES_ALL)
    )
    private val announce = Regex("""\bAnunci(?:o)?\s+(?:de\s|del\s|d['’])""", RegexOption.IGNORE_CASE)

    fun fetch(): List<Notice> {
        val connection = URL(sourceUrl).openConnection() as HttpURLConnection
        connection.connectTimeout = 20000
        connection.readTimeout = 20000
        connection.instanceFollowRedirects = true
        connection.setRequestProperty("User-Agent", "Mozilla/5.0 (compatible; OpoAlert/0.1; Android)")
        connection.setRequestProperty("Accept", "text/html,application/xhtml+xml")
        connection.setRequestProperty("Accept-Language", "ca-ES,es-ES;q=0.9")
        return try {
            if (connection.responseCode !in 200..299) {
                throw IOException("El BOP respondió con HTTP ${connection.responseCode}")
            }
            val html = connection.inputStream.bufferedReader(Charsets.UTF_8).use { it.readText() }
            parse(html)
        } finally {
            connection.disconnect()
        }
    }

    fun parse(html: String): List<Notice> {
        val doc = Jsoup.parse(html)
        doc.select("script, style, noscript, footer").remove()
        val plain = doc.body().text().replace(Regex("""\s+"""), " ")
        val matches = metadata.findAll(plain).toList()
        if (matches.isEmpty()) {
            throw IOException("No se han podido leer los anuncios del BOP. Puede haber cambiado su web.")
        }
        var previousEnd = 0
        val notices = mutableListOf<Notice>()
        for (match in matches) {
            val before = plain.substring(previousEnd, match.range.first)
            previousEnd = match.range.last + 1
            val titleStart = announce.findAll(before).lastOrNull()?.range?.first ?: continue
            val title = before.substring(titleStart).trim().take(1000)
            val kind = classify(title) ?: continue
            val id = match.groupValues[1]
            notices.add(
                Notice(
                    id = id,
                    title = title,
                    entity = entityFrom(title),
                    date = match.groupValues[2],
                    bulletin = match.groupValues[3],
                    type = kind,
                    url = "https://bop.dival.es/bop/downloads?anuncioNumReg=${id.replace("/", "%2F")}&lang=es"
                )
            )
        }
        return notices.distinctBy { it.id }
    }

    private fun entityFrom(title: String): String {
        val chunk = title.substringBefore(" sobre ", title)
            .substringBefore(" sobre la ", title)
        val match = Regex(
            """(?:Ajuntament|Ayuntamiento)\s+(?:de|del|d['’])\s+(.+)$""",
            RegexOption.IGNORE_CASE
        ).find(chunk)
        if (match != null) {
            return "Ayuntamiento de ${match.groupValues[1].trim().take(65)}"
        }
        return when {
            fold(title).contains("diputacio provincial") -> "Diputación de Valencia"
            fold(title).contains("consorci provincial de bombers") -> "Consorcio Provincial de Bomberos"
            else -> "Administración pública"
        }
    }

    private fun fold(input: String): String = Normalizer.normalize(
        input.lowercase(Locale.ROOT), Normalizer.Form.NFD
    ).replace(Regex("""\p{Mn}+"""), "")

    private fun classify(title: String): String? {
        val t = fold(title)
        val forbidden = listOf(
            "subvencio", "nomenament", "nombramiento", "admes", "admitid", "excluid",
            "exclos", "relacio definitiva", "relacion definitiva", "relacio provisional",
            "relacion provisional", "resultat", "resultado", "llista definitiva",
            "lista definitiva", "cessio de la borsa", "cesion de la bolsa",
            "jutge de pau", "juez de paz", "licitacio", "licitacion", "eleccions"
        )
        if (forbidden.any(t::contains)) return null
        val newProcess = listOf(
            "convocatoria", "bases", "constitucio", "constitucion", "creacio", "creacion"
        ).any(t::contains)
        val pool = t.contains("borsa de treball") || t.contains("bolsa de trabajo") ||
            t.contains("borsa per a") || t.contains("bolsa para") ||
            t.contains("borsa d'") || t.contains("bolsa de empleo")
        if (pool && newProcess) return "Bolsa de trabajo"
        val position = listOf(
            "placa de", "places de", "plaza de", "plazas de", "proces selectiu",
            "proceso selectivo", "seleccio de personal", "seleccion de personal"
        ).any(t::contains)
        if (newProcess && position) return "Plaza / oposición"
        return null
    }
}
