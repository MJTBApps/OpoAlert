package es.opoalert.app

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class PremiumTest {
    @Test fun alertsStayFreeUntilBillingWorks() {
        assertTrue(Premium.unlocked(premium = false, billingReady = false))
        assertTrue(Premium.unlocked(premium = true, billingReady = false))
    }

    @Test fun withBillingAlertsNeedPremium() {
        assertFalse(Premium.unlocked(premium = false, billingReady = true))
        assertTrue(Premium.unlocked(premium = true, billingReady = true))
    }

    // SHA-256 de «ABCDE-FGHJK-LMNPQ-RSTUV», un código de ejemplo (el real no está en el repositorio).
    private val sample = "76a8a3cce1f8d0e6fa9b4fdd1df3f3dbe3fd0f6b8b6bbbdeb4c7e6d43b0e2b0c"

    @Test fun reviewCodeNeedsTheExactCode() {
        val hash = java.security.MessageDigest.getInstance("SHA-256")
            .digest("ABCDE-FGHJK-LMNPQ-RSTUV".toByteArray()).joinToString("") { "%02x".format(it) }
        assertTrue(Premium.reviewCodeMatches("ABCDE-FGHJK-LMNPQ-RSTUV", hash))
        assertTrue(Premium.reviewCodeMatches("  abcde-fghjk-lmnpq-rstuv ", hash))
        assertFalse(Premium.reviewCodeMatches("ABCDE-FGHJK-LMNPQ-RSTUW", hash))
        assertFalse(Premium.reviewCodeMatches("", hash))
    }

    @Test fun withoutReviewCodeNothingUnlocks() {
        assertFalse(Premium.reviewCodeMatches("ABCDE-FGHJK-LMNPQ-RSTUV", ""))
        assertFalse(Premium.reviewCodeMatches("ABCDE-FGHJK-LMNPQ-RSTUV", sample.reversed()))
    }
}
