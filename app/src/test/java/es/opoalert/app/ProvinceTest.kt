package es.opoalert.app

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ProvinceTest {
    @Test fun threeProvincesAndNationalBOEAvailable() {
        assertEquals(listOf("Valencia", "Alicante", "Castellón", "España (BOE)",
            "Barcelona", "Girona", "Lleida", "Tarragona", "Tarragona (BOP)", "Barcelona (BOP)", "Girona (BOP)", "Huesca", "Teruel", "Zaragoza", "Almería", "Córdoba", "Granada", "Sevilla", "Huelva", "Madrid", "Albacete", "Ciudad Real", "Cuenca", "Guadalajara", "Toledo", "Castilla-La Mancha (DOCM)", "Ávila", "León", "Palencia", "Zamora", "Soria", "Castilla y León (BOCYL)", "Badajoz", "Cáceres", "Extremadura (DOE)", "Cádiz"), Province.entries.map { it.label })
    }
    @Test fun keepOldValenciaIdsAndUseProvincialPrefixes() {
        assertTrue(Province.VALENCIA.idPattern.matches("2026/12855"))
        assertTrue(Province.ALICANTE.idPattern.matches("AL-2026-8223"))
        assertTrue(Province.CASTELLON.idPattern.matches("CS-168667"))
        assertFalse(Province.VALENCIA.idPattern.matches("AL-2026-8223"))
        assertEquals(Province.VALENCIA, Province.fromNoticeId("2026/12855"))
        assertEquals(Province.ALICANTE, Province.fromNoticeId("AL-2026-8223"))
        assertEquals(Province.CASTELLON, Province.fromNoticeId("CS-168667"))
        assertEquals(Province.BOE, Province.fromNoticeId("BOE-A-2026-22556"))
        assertTrue(Province.BOE.idPattern.matches("BOE-A-2026-22556"))
        assertEquals(Province.BARCELONA, Province.fromNoticeId("CIDO5-12345"))
        assertEquals(Province.GIRONA, Province.fromNoticeId("CIDO6-12345"))
        assertEquals(Province.LLEIDA, Province.fromNoticeId("CIDO7-12345"))
        assertEquals(Province.TARRAGONA, Province.fromNoticeId("CIDO8-12345"))
        assertEquals(Province.TARRAGONA_BOP, Province.fromNoticeId("TA-2026-09890"))
        assertEquals(Province.BARCELONA_BOP, Province.fromNoticeId("BA-202610159954"))
        assertEquals(Province.GIRONA_BOP, Province.fromNoticeId("GI-2026-208-09310"))
        assertEquals(Province.HUESCA, Province.fromNoticeId("HU-2026-207001"))
        assertTrue(Province.HUESCA.idPattern.matches("HU-2026-207001"))
        assertEquals(Province.TERUEL, Province.fromNoticeId("TE-2026-3129-78AF45C9E931954CC1258E9D0035774E"))
        assertTrue(Province.TERUEL.idPattern.matches("TE-2026-3129-78AF45C9E931954CC1258E9D0035774E"))
        assertEquals(Province.ZARAGOZA, Province.fromNoticeId("ZA-000344663"))
        assertTrue(Province.ZARAGOZA.idPattern.matches("ZA-000344663"))
        assertEquals(Province.CADIZ, Province.fromNoticeId("CA-2026-354710"))
        assertTrue(Province.CADIZ.idPattern.matches("CA-2026-354710"))
        assertEquals(Province.ALMERIA, Province.fromNoticeId("AM-2026-02765"))
        assertTrue(Province.ALMERIA.idPattern.matches("AM-2026-02765"))
        assertEquals(Province.GRANADA, Province.fromNoticeId("GR-2026-210001"))
        assertTrue(Province.GRANADA.idPattern.matches("GR-2026-210001"))
        assertEquals(Province.CORDOBA, Province.fromNoticeId("CO-2026-3644"))
        assertTrue(Province.CORDOBA.idPattern.matches("CO-2026-3644"))
        assertEquals(Province.SEVILLA, Province.fromNoticeId("SV-2026-210001"))
        assertTrue(Province.SEVILLA.idPattern.matches("SV-2026-210001"))
        assertEquals(Province.HUELVA_BOP, Province.fromNoticeId("HB-2026-381433"))
        assertEquals(Province.AVILA, Province.fromNoticeId("AV-2026-2162"))
        assertEquals(Province.LEON_BOP, Province.fromNoticeId("LN-2026-205001"))
        assertEquals(Province.ZAMORA_BOP, Province.fromNoticeId("ZM-202602392"))
        assertEquals(Province.PALENCIA_BOP, Province.fromNoticeId("PL-20261009-004"))
        assertEquals(Province.SORIA_BOP, Province.fromNoticeId("SR-2026-2024"))
        assertEquals(Province.CYL_BOCYL, Province.fromNoticeId("CY-20261029-5"))
        assertEquals(Province.BADAJOZ_BOP, Province.fromNoticeId("BD-2026-165015"))
        assertEquals(Province.CACERES_BOP, Province.fromNoticeId("CC-2026-4651"))
        assertEquals(Province.EXTREMADURA_DOE, Province.fromNoticeId("EX-2026-26AC0067"))
        assertTrue(Province.BADAJOZ_BOP.allowsOfficialPath("/ficheros/bop/bopedictos/2026-10-29000000_4283.pdf"))
        assertTrue(Province.CACERES_BOP.allowsOfficialPath("/bop/services/anuncios/contenidoPdfIdAnuncio"))
        assertTrue(Province.EXTREMADURA_DOE.allowsOfficialPath("/pdfs/doe/2026/2090o/26050120.pdf"))
        assertEquals(Province.ALBACETE, Province.fromNoticeId("AB-2026-1001"))
        assertEquals(Province.CIUDAD_REAL, Province.fromNoticeId("CR-2026-3482"))
        assertEquals(Province.CUENCA, Province.fromNoticeId("CU-2026-3320"))
        assertEquals(Province.GUADALAJARA, Province.fromNoticeId("GJ-2026-2801"))
        assertEquals(Province.TOLEDO, Province.fromNoticeId("TO-2026-1932"))
        assertEquals(Province.CLM_DOCM, Province.fromNoticeId("CM-2026-7856"))
        assertEquals(Province.MADRID, Province.fromNoticeId("MD-20261028-37"))
        assertTrue(Province.MADRID.idPattern.matches("MD-20261028-37"))
        assertTrue(Province.MADRID.allowsOfficialPath("/boletin/CM_Orden_BOCM/2026/10/28/BOCM-20261028-37.PDF"))
        assertTrue(Province.ALMERIA.allowsOfficialPath("/bop/services/manager/edicto/2026/2765/anuncio.pdf"))
        assertTrue(Province.ALMERIA.allowsOfficialPath("/pandora/high.raw"))
        assertFalse(Province.ALMERIA.allowsOfficialPath("/untrusted/notice.pdf"))
    }
    @Test fun everyFeedIsFromOurPublicSiteButOfficialSourcesDiffer() {
        assertEquals(36, Province.entries.map { it.feedUrl }.toSet().size)
        assertTrue(Province.entries.all { it.feedUrl.startsWith("https://mjtbapps.github.io/OpoAlert/") })
        assertEquals(33, Province.entries.map { it.expectedSource }.toSet().size)
    }
}
