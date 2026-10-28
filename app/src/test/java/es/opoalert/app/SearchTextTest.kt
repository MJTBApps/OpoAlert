package es.opoalert.app

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class SearchTextTest {
    @Test fun accentInsensitive() {
        for (x in listOf("policia", "policía", "polícia", "POLICÍA")) {
            assertEquals("policia", SearchText.normalize(x))
        }
    }
    @Test fun matchingOfficialText() {
        for (x in listOf("policia", "policía", "polícia")) {
            assertTrue(SearchText.matchesNormalized(SearchText.normalize(x), "Policía Local"))
        }
    }
    @Test fun preservesEnye() {
        assertEquals("año", SearchText.normalize("AÑO"))
    }
}
