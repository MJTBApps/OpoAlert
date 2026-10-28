package es.opoalert.app

import android.content.Context

/** Each official BOP is scanned separately and validated before publication. */
enum class Province(
    val code: String,
    val label: String,
    val feedUrl: String,
    val expectedSource: String,
    val pdfHost: String,
    val pdfPathPrefix: String,
    val idPattern: Regex,
) {
    VALENCIA(
        "VA", "Valencia",
        "https://mjtbapps.github.io/OpoAlert/convocatorias.json",
        "https://bop.dival.es/bop/xhtml/portal.xhtml",
        "bop.dival.es", "/bop/downloads", Regex("\\d{4}/\\d{3,7}"),
    ),
    ALICANTE(
        "AL", "Alicante",
        "https://mjtbapps.github.io/OpoAlert/alicante.json",
        "https://sede.diputacionalicante.es/consultas.bop/",
        "www.dip-alicante.es", "/bop2/pdftotal/", Regex("AL-\\d{4}-\\d+"),
    ),
    CASTELLON(
        "CS", "Castellón",
        "https://mjtbapps.github.io/OpoAlert/castellon.json",
        "https://bop.dipcas.es/PortalBOP/",
        "bop.dipcas.es", "/PortalBOP/api/descargarAnuncio", Regex("CS-\\d+"),
    ),
    // BOE es una fuente de ámbito nacional, no un boletín provincial.
    BOE(
        "ES", "España (BOE)",
        "https://mjtbapps.github.io/OpoAlert/boe.json",
        "https://www.boe.es/datosabiertos/api/boe/sumario/",
        "www.boe.es", "/boe/dias/", Regex("BOE-A-\\d{4}-\\d{1,7}"),
    ),

    // CIDO es el catalogo publico de procesos selectivos de la Diputacion de
    // Barcelona. No equivale a la lectura exhaustiva de cada BOP provincial.
    BARCELONA(
        "CB", "Barcelona",
        "https://mjtbapps.github.io/OpoAlert/barcelona.json",
        "https://api.diba.cat/dadesobertes/cido/v1/oposicions",
        "cido.diba.cat", "/oposicions/", Regex("CIDO5-\\d+"),
    ),
    GIRONA(
        "CG", "Girona",
        "https://mjtbapps.github.io/OpoAlert/girona.json",
        "https://api.diba.cat/dadesobertes/cido/v1/oposicions",
        "cido.diba.cat", "/oposicions/", Regex("CIDO6-\\d+"),
    ),
    LLEIDA(
        "CL", "Lleida",
        "https://mjtbapps.github.io/OpoAlert/lleida.json",
        "https://api.diba.cat/dadesobertes/cido/v1/oposicions",
        "cido.diba.cat", "/oposicions/", Regex("CIDO7-\\d+"),
    ),
    TARRAGONA(
        "CT", "Tarragona",
        "https://mjtbapps.github.io/OpoAlert/tarragona_cido.json",
        "https://api.diba.cat/dadesobertes/cido/v1/oposicions",
        "cido.diba.cat", "/oposicions/", Regex("CIDO8-\\d+"),
    ),
    TARRAGONA_BOP(
        "TB", "Tarragona (BOP)",
        "https://mjtbapps.github.io/OpoAlert/tarragona_bop.json",
        "https://aplicacions.dipta.cat/bopt/web/anteriores/",
        "aplicacions.dipta.cat", "/bopt/web/anuncio/descargar-pdf/",
        Regex("TA-\\d{4}-\\d{5}"),
    ),
    BARCELONA_BOP(
        "BB", "Barcelona (BOP)",
        "https://mjtbapps.github.io/OpoAlert/barcelona_bop.json",
        "https://bop.diba.cat/anteriors/",
        "bop.diba.cat", "/anunci/descarrega-pdf/", Regex("BA-\\d{12}"),
    ),
    GIRONA_BOP(
        "BG", "Girona (BOP)",
        "https://mjtbapps.github.io/OpoAlert/girona_bop.json",
        "https://www.ddgi.cat/bop/",
        "ssl4.ddgi.cat", "/bopV1/pdf/", Regex("GI-\\d{4}-\\d{3}-\\d{5}"),
    ),
    HUESCA(
        "HU", "Huesca",
        "https://mjtbapps.github.io/OpoAlert/huesca_bop.json",
        "https://bop.dphuesca.es/publica/consulta-de-bops/",
        "bop.dphuesca.es", "/export/sites/bop/.galleries/Documentos-Anuncios-en-PDF/",
        Regex("HU-\\d{4}-\\d{6}"),
    ),
    TERUEL(
        "TE", "Teruel",
        "https://mjtbapps.github.io/OpoAlert/teruel_bop.json",
        "https://bender.dpteruel.es/dpt/bopt.nsf/inicio.xsp",
        "bender.dpteruel.es", "/dpt/bopt.nsf/0/", Regex("TE-\\d{4}-\\d{4}-[A-F0-9]{32}"),
    ),
    ZARAGOZA(
        "ZA", "Zaragoza",
        "https://mjtbapps.github.io/OpoAlert/zaragoza_bop.json",
        "https://www.boa.aragon.es/cgi-bin/EBOA/BRSCGI",
        "www.boa.aragon.es", "/cgi-bin/EBOA/BRSCGI",
        Regex("ZA-\\d{9}"),
    ),
    CADIZ(
        "CA", "Cádiz",
        "https://mjtbapps.github.io/OpoAlert/cadiz_bop.json",
        "https://www.bopcadiz.es/",
        "www.bopcadiz.es", "/export/sites/default/.boletines_pdf/",
        Regex("CA-\\d{4}-\\d{4,7}"),
    );

    companion object {
        fun fromLabel(label: String): Province? = entries.find { it.label == label }
        fun fromNoticeId(id: String): Province = when {
            id.startsWith("AL-") -> ALICANTE
            id.startsWith("CS-") -> CASTELLON
            id.startsWith("BOE-A-") -> BOE
            id.startsWith("CIDO5-") -> BARCELONA
            id.startsWith("CIDO6-") -> GIRONA
            id.startsWith("CIDO7-") -> LLEIDA
            id.startsWith("CIDO8-") -> TARRAGONA
            id.startsWith("TA-") -> TARRAGONA_BOP
            id.startsWith("BA-") -> BARCELONA_BOP
            id.startsWith("GI-") -> GIRONA_BOP
            id.startsWith("HU-") -> HUESCA
            id.startsWith("TE-") -> TERUEL
            id.startsWith("ZA-") -> ZARAGOZA
            id.startsWith("CA-") -> CADIZ
            else -> VALENCIA
        }
    }
}

/** Selection is private to the device and never requires location permission. */
object ProvinceSettings {
    private const val PREFS = "opoalert_store"
    private const val SELECTED = "selected_provinces_v1"
    private const val INITIAL_PICKER_SHOWN = "province_picker_seen_v1"

    fun selected(context: Context): Set<Province> {
        val stored = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .getString(SELECTED, Province.VALENCIA.code).orEmpty()
        val codes = stored.split(',').map { it.trim() }.toSet()
        val selected = Province.entries.filter { it.code in codes }.toSet()
        return selected.ifEmpty { setOf(Province.VALENCIA) }
    }

    fun save(context: Context, chosen: Set<Province>): Boolean {
        if (chosen.isEmpty()) return false
        val value = Province.entries.filter { it in chosen }.joinToString(",") { it.code }
        return context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit().putString(SELECTED, value).commit()
    }

    fun wasPickerShown(context: Context): Boolean =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .getBoolean(INITIAL_PICKER_SHOWN, false)

    fun markPickerShown(context: Context) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit().putBoolean(INITIAL_PICKER_SHOWN, true).apply()
    }

    fun display(context: Context): String {
        val chosen = selected(context)
        val locals = Province.entries.filter { it in chosen && it != Province.BOE }
        val localText = when (locals.size) {
            0 -> ""
            1 -> locals.first().label
            else -> "${locals.size} provincias"
        }
        return listOfNotNull(
            localText.takeIf { it.isNotEmpty() },
            "BOE".takeIf { Province.BOE in chosen }
        ).joinToString(" + ")
    }
}
