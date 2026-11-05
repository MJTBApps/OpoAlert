package es.opoalert.app

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class PremiumNudgeTest {
    private val day = 24L * 60 * 60 * 1000
    private val now = 100 * day

    @Test fun firstTimeAtThirdFavorite() {
        assertFalse(PremiumNudge.shouldShow(2, 0, 0, now, locked = true))
        assertTrue(PremiumNudge.shouldShow(3, 0, 0, now, locked = true))
    }

    @Test fun neverWithPremiumOrFreeAlerts() {
        assertFalse(PremiumNudge.shouldShow(3, 0, 0, now, locked = false))
        assertFalse(PremiumNudge.shouldShow(20, 1, 0, now, locked = false))
    }

    @Test fun secondTimeOnlyAtTenAndTwoWeeksLater() {
        assertFalse(PremiumNudge.shouldShow(4, 1, now - 30 * day, now, locked = true))
        assertFalse(PremiumNudge.shouldShow(10, 1, now - 13 * day, now, locked = true))
        assertTrue(PremiumNudge.shouldShow(10, 1, now - 14 * day, now, locked = true))
    }

    @Test fun atMostTwice() {
        assertFalse(PremiumNudge.shouldShow(50, 2, 0, now, locked = true))
    }

    @Test fun messageMentionsSupportingTheProject() {
        assertTrue(PremiumNudge.MESSAGE.contains("ayudas a mantener OpoAlert"))
    }
}
