package es.opoalert.app

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ProvinceTest {
    @Test fun threeProvincesAndNationalBOEAvailable() {
        assertEquals(listOf("Valencia", "Alicante", "Castellón", "España (BOE)",
            "Barcelona", "Girona", "Lleida", "Tarragona", "Tarragona (BOP)", "Barcelona (BOP)", "Girona (BOP)", "Huesca", "Teruel", "Zaragoza", "Almería", "Jaén", "Cádiz"), Province.entries.map { it.label })
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
        assertTrue(Province.ALMERIA.allowsOfficialPath("/bop/services/manager/edicto/2026/2765/anuncio.pdf"))
        assertTrue(Province.ALMERIA.allowsOfficialPath("/pandora/high.raw"))
        assertFalse(Province.ALMERIA.allowsOfficialPath("/private/untrusted.pdf"))
        assertEquals(Province.JAEN, Province.fromNoticeId("JA-2026-04560"))
        assertTrue(Province.JAEN.idPattern.matches("JA-2026-04560"))
    }
    @Test fun everyFeedIsFromOurPublicSiteButOfficialSourcesDiffer() {
        assertEquals(17, Province.entries.map { it.feedUrl }.toSet().size)
        assertTrue(Province.entries.all { it.feedUrl.startsWith("https://mjtbapps.github.io/OpoAlert/") })
        assertEquals(14, Province.entries.map { it.expectedSource }.toSet().size)
    }
}
