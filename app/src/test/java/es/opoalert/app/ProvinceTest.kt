package es.opoalert.app

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ProvinceTest {
    @Test fun threeProvincesAreAvailable() {
        assertEquals(listOf("Valencia", "Alicante", "Castellón"), Province.entries.map { it.label })
    }
    @Test fun keepOldValenciaIdsAndUseProvincialPrefixes() {
        assertTrue(Province.VALENCIA.idPattern.matches("2026/12855"))
        assertTrue(Province.ALICANTE.idPattern.matches("AL-2026-8223"))
        assertTrue(Province.CASTELLON.idPattern.matches("CS-168667"))
        assertFalse(Province.VALENCIA.idPattern.matches("AL-2026-8223"))
        assertEquals(Province.VALENCIA, Province.fromNoticeId("2026/12855"))
        assertEquals(Province.ALICANTE, Province.fromNoticeId("AL-2026-8223"))
        assertEquals(Province.CASTELLON, Province.fromNoticeId("CS-168667"))
    }
    @Test fun everyFeedIsFromOurPublicSiteButOfficialSourcesDiffer() {
        assertEquals(3, Province.entries.map { it.feedUrl }.toSet().size)
        assertTrue(Province.entries.all { it.feedUrl.startsWith("https://mjtbapps.github.io/OpoAlert/") })
        assertEquals(3, Province.entries.map { it.expectedSource }.toSet().size)
    }
}
