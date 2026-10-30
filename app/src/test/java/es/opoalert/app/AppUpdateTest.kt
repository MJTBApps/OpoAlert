package es.opoalert.app

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class AppUpdateTest {
    @Test fun comparesVersionsNumerically() {
        assertTrue(AppUpdate.isNewer("1.38.0", "1.37.0"))
        assertTrue(AppUpdate.isNewer("1.37.1", "1.37.0"))
        assertTrue(AppUpdate.isNewer("2.0.0", "1.99.9"))
        assertFalse(AppUpdate.isNewer("1.37.0", "1.37.0"))
        assertFalse(AppUpdate.isNewer("1.9.0", "1.37.0"))  // 9 < 37, no orden alfabético
        assertFalse(AppUpdate.isNewer("1.36.0", "1.37.0-privada"))
    }

    @Test fun onlyAcceptsWellFormedVersionFromTheWeb() {
        assertEquals("1.38.0", AppUpdate.parseLatest("""{"latestVersion":"1.38.0"}"""))
        assertEquals(null, AppUpdate.parseLatest("""{"latestVersion":"../malware"}"""))
        assertEquals(null, AppUpdate.parseLatest("no es json"))
        assertEquals("https://mjtbapps.github.io/OpoAlert/OpoAlert-1.38.0.apk", AppUpdate.apkUrl("1.38.0"))
    }
}
