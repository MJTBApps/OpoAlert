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
    ALMERIA(
        "AM", "Almería",
        "https://mjtbapps.github.io/OpoAlert/almeria_bop.json",
        "https://app.dipalme.org/pandora/results.vm?q=parent:0000010919&view=boletines",
        "app.dipalme.org", "/bop/services/manager/edicto/",
        Regex("AM-\\d{4}-\\d{5}"),
    ),
    CORDOBA(
        "CO", "Córdoba",
        "https://mjtbapps.github.io/OpoAlert/cordoba_bop.json",
        "https://bop.dipucordoba.es/",
        "bop.dipucordoba.es", "/visor-pdf/",
        Regex("CO-\\d{4}-\\d{1,7}"),
    ),
    GRANADA(
        "GR", "Granada",
        "https://mjtbapps.github.io/OpoAlert/granada_bop.json",
        "https://bop.dipgra.es/publica/consulta-de-bops/",
        "bop.dipgra.es", "/export/sites/bop/.galleries/Documentos-Anuncios-en-PDF/",
        Regex("GR-\\d{4}-\\d{6}"),
    ),
    SEVILLA(
        "SV", "Sevilla",
        "https://mjtbapps.github.io/OpoAlert/sevilla_bop.json",
        "https://bopsevilla.dipusevilla.es/publica/consulta-de-bops/",
        "bopsevilla.dipusevilla.es", "/export/sites/bop/.galleries/Documentos-Anuncios-en-PDF/",
        Regex("SV-\\d{4}-\\d{6}"),
    ),
    HUELVA_BOP(
        "HB", "Huelva",
        "https://mjtbapps.github.io/OpoAlert/huelva_bop.json",
        "https://s2.diphuelva.es/servicios/bope_web/busquedaCalendario",
        "s2.diphuelva.es", "/portalweb/bope/anuncios/",
        Regex("HB-\\d{4}-\\d{1,8}"),
    ),
    MADRID(
        "MD", "Madrid",
        "https://mjtbapps.github.io/OpoAlert/madrid_bocm.json",
        "https://www.bocm.es/listado-de-boletines",
        "www.bocm.es", "/boletin/CM_Orden_BOCM/",
        Regex("MD-\\d{8}-\\d{1,5}"),
    ),
    ALBACETE(
        "AB", "Albacete",
        "https://mjtbapps.github.io/OpoAlert/albacete_bop.json",
        "https://bop.dipualba.es/",
        "bop.dipualba.es", "/servicesajax/",
        Regex("AB-\\d{4}-\\d{1,8}"),
    ),
    CIUDAD_REAL(
        "CR", "Ciudad Real",
        "https://mjtbapps.github.io/OpoAlert/ciudad_real_bop.json",
        "https://bop.dipucr.es/",
        "se1.dipucr.es", "/SIGEM_BuscadorDocsWeb/getDocument.do",
        Regex("CR-\\d{4}-\\d{1,8}"),
    ),
    CUENCA(
        "CU", "Cuenca",
        "https://mjtbapps.github.io/OpoAlert/cuenca_bop.json",
        "https://www.dipucuenca.es/boletin-oficial-de-la-provincia",
        "www.dipucuenca.es", "/documents/",
        Regex("CU-\\d{4}-\\d{1,8}"),
    ),
    GUADALAJARA(
        "GJ", "Guadalajara",
        "https://mjtbapps.github.io/OpoAlert/guadalajara_bop.json",
        "https://boletin.dguadalajara.es/boletin/",
        "boletin.dguadalajara.es", "/boletin/",
        Regex("GJ-\\d{4}-\\d{1,8}"),
    ),
    TOLEDO(
        "TO", "Toledo",
        "https://mjtbapps.github.io/OpoAlert/toledo_bop.json",
        "https://bop.diputoledo.es/webEbop/",
        "bop.diputoledo.es", "/webEbop/",
        Regex("TO-\\d{4}-\\d{1,8}"),
    ),
    CLM_DOCM(
        "CM", "Castilla-La Mancha (DOCM)",
        "https://mjtbapps.github.io/OpoAlert/castilla_mancha_docm.json",
        "https://docm.jccm.es/docm/",
        "docm.jccm.es", "/docm/descargarArchivo.do",
        Regex("CM-\\d{4}-\\d{1,8}"),
    ),
    AVILA(
        "AV", "Ávila",
        "https://mjtbapps.github.io/OpoAlert/avila_bop.json",
        "https://www.diputacionavila.es/boletin-oficial/2026/",
        "www.diputacionavila.es", "/bops/2026/",
        Regex("AV-\\d{4}-\\d{1,7}"),
    ),
    LEON_BOP(
        "LN", "León",
        "https://mjtbapps.github.io/OpoAlert/leon_bop.json",
        "https://bop.dipuleon.es/publica/consulta-de-bops/",
        "bop.dipuleon.es", "/export/sites/bop/.galleries/Documentos-Anuncios-en-PDF/",
        Regex("LN-\\d{4}-\\d{6}"),
    ),
    PALENCIA_BOP(
        "PL", "Palencia",
        "https://mjtbapps.github.io/OpoAlert/palencia_bop.json",
        "https://www.diputaciondepalencia.es/servicios/boletin-oficial-provincia",
        "www.diputaciondepalencia.es", "/system/files/bop/2026/",
        Regex("PL-\\d{8}-\\d{3}"),
    ),
    ZAMORA_BOP(
        "ZM", "Zamora",
        "https://mjtbapps.github.io/OpoAlert/zamora_bop.json",
        "https://www.diputaciondezamora.es/opencms/servicios/BOP/busqueda-en-el-bop/",
        "www.diputaciondezamora.es", "/opencms/export/sites/dipu-zamora/servicios/BOP/.Archivos/documentos/BOP/anuncios/",
        Regex("ZM-\\d{9}"),
    ),
    SORIA_BOP(
        "SR", "Soria",
        "https://mjtbapps.github.io/OpoAlert/soria_bop.json",
        "https://bop.dipsoria.es/index.php/mod.boloficial/relmenu.149",
        "bop.dipsoria.es", "/index.php/mod.documentos/mem.descargar/fichero.documentos_",
        Regex("SR-\\d{4}-\\d{1,6}"),
    ),
    CYL_BOCYL(
        "CY", "Castilla y León (BOCYL)",
        "https://mjtbapps.github.io/OpoAlert/castilla_leon_bocyl.json",
        "https://bocyl.jcyl.es/",
        "bocyl.jcyl.es", "/boletines/",
        Regex("CY-\\d{8}-\\d{1,4}"),
    ),
    BADAJOZ_BOP(
        "BD", "Badajoz",
        "https://mjtbapps.github.io/OpoAlert/badajoz_bop.json",
        "https://www.dip-badajoz.es/bop/",
        "www.dip-badajoz.es", "/ficheros/bop/bopedictos/",
        Regex("BD-\\d{4}-\\d{5,9}"),
    ),
    CACERES_BOP(
        "CC", "Cáceres",
        "https://mjtbapps.github.io/OpoAlert/caceres_bop.json",
        "https://bop.dip-caceres.es/bop/index.html",
        "bop.dip-caceres.es", "/bop/services/anuncios/contenidoPdfIdAnuncio",
        Regex("CC-\\d{4}-\\d{1,7}"),
    ),
    EXTREMADURA_DOE(
        "EX", "Extremadura (DOE)",
        "https://mjtbapps.github.io/OpoAlert/extremadura_doe.json",
        "https://doe.juntaex.es/",
        "doe.juntaex.es", "/pdfs/doe/",
        Regex("EX-\\d{4}-[A-Z0-9]{8}"),
    ),
    MURCIA_BORM(
        "MU", "Región de Murcia (BORM)",
        "https://mjtbapps.github.io/OpoAlert/murcia_borm.json",
        "https://transparencia.carm.es/rest-services/services/restFile/BORMIndice.json",
        "www.borm.es", "/services/anuncio/",
        Regex("MU-\\d{4}-\\d{1,8}"),
    ),
    CADIZ(
        "CA", "Cádiz",
        "https://mjtbapps.github.io/OpoAlert/cadiz_bop.json",
        "https://www.bopcadiz.es/",
        "www.bopcadiz.es", "/export/sites/default/.boletines_pdf/",
        Regex("CA-\\d{4}-\\d{4,7}"),
    );

    fun allowsOfficialPath(path: String): Boolean =
        path.startsWith(pdfPathPrefix) ||
        (this == ALMERIA && path == "/pandora/high.raw")

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
            id.startsWith("HB-") -> HUELVA_BOP
            id.startsWith("AV-") -> AVILA
            id.startsWith("LN-") -> LEON_BOP
            id.startsWith("ZM-") -> ZAMORA_BOP
            id.startsWith("PL-") -> PALENCIA_BOP
            id.startsWith("SR-") -> SORIA_BOP
            id.startsWith("CY-") -> CYL_BOCYL
            id.startsWith("BD-") -> BADAJOZ_BOP
            id.startsWith("CC-") -> CACERES_BOP
            id.startsWith("EX-") -> EXTREMADURA_DOE
            id.startsWith("MU-") -> MURCIA_BORM
            id.startsWith("MD-") -> MADRID
            id.startsWith("AB-") -> ALBACETE
            id.startsWith("CR-") -> CIUDAD_REAL
            id.startsWith("CU-") -> CUENCA
            id.startsWith("GJ-") -> GUADALAJARA
            id.startsWith("TO-") -> TOLEDO
            id.startsWith("CM-") -> CLM_DOCM
            id.startsWith("CO-") -> CORDOBA
            id.startsWith("GR-") -> GRANADA
            id.startsWith("SV-") -> SEVILLA
            id.startsWith("AM-") -> ALMERIA
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
        val selected = SourceCatalog.availableSources.filter { it.code in codes }.toSet()
        return selected.ifEmpty { setOf(Province.VALENCIA) }
    }

    fun save(context: Context, chosen: Set<Province>): Boolean {
        if (chosen.isEmpty()) return false
        val value = SourceCatalog.availableSources.filter { it in chosen }.joinToString(",") { it.code }
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
        val locals = SourceCatalog.availableSources.filter { it in chosen && it != Province.BOE }
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
