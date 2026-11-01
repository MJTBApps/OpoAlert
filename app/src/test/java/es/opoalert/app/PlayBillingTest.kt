package es.opoalert.app

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class PlayBillingTest {
    @Test fun billingPeriodsInSpanish() {
        assertEquals(" al año", PlayBilling.periodLabel("P1Y"))
        assertEquals(" al mes", PlayBilling.periodLabel("P1M"))
        assertEquals("", PlayBilling.periodLabel("P2Y"))
    }

    @Test fun freeTrialLength() {
        assertEquals(7, PlayBilling.trialDays("P7D"))
        assertEquals(14, PlayBilling.trialDays("P2W"))
        assertEquals(30, PlayBilling.trialDays("P1M"))
        assertNull(PlayBilling.trialDays("P1Y"))
    }

    @Test fun alertsArePaidOnlyWithBilling() {
        assertEquals(true, Premium.unlocked(premium = false, billingReady = false))
        assertEquals(false, Premium.unlocked(premium = false, billingReady = true))
        assertEquals(true, Premium.unlocked(premium = true, billingReady = true))
    }
}
