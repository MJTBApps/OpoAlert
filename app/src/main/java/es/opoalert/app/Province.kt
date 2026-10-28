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
    );

    companion object {
        fun fromLabel(label: String): Province? = entries.find { it.label == label }
        fun fromNoticeId(id: String): Province = when {
            id.startsWith("AL-") -> ALICANTE
            id.startsWith("CS-") -> CASTELLON
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

    fun display(context: Context): String =
        Province.entries.filter { it in selected(context) }
            .joinToString(" · ") { it.label }
}
