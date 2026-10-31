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
}
