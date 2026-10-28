package es.opoalert.app

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class SearchTextTest {
    @Test fun accentVariantsHaveSameKey() {
        assertEquals("policia", SearchText.normalize("policia"))
        assertEquals("policia", SearchText.normalize("policía"))
        assertEquals("policia", SearchText.normalize("polícia"))
        assertEquals("policia", SearchText.normalize("POLICÍA"))
        assertEquals("policia", SearchText.normalize("POLI\u0301CIA"))
    }

    @Test fun accentDoesNotAffectMatchingOfficialTitle() {
        val title = "Convocatoria de plazas de agente de Policía Local"
        for (term in listOf("policia", "policía", "polícia", "POLICIA")) {
            assertTrue(SearchText.matchesNormalized(SearchText.normalize(term), title))
        }
    }

    @Test fun entityMatchesWithAndWithoutAccents() {
        assertTrue(SearchText.matchesNormalized(SearchText.normalize("naquera"),
            "Ayuntamiento de Náquera"))
        assertTrue(SearchText.matchesNormalized(SearchText.normalize("NÁQUERA"),
            "Ayuntamiento de Náquera"))
        assertTrue(SearchText.matchesNormalized(SearchText.normalize("gestio"),
            "Técnico de gestió"))
    }

    @Test fun preservingEnyeAvoidsFalseMatches() {
        assertEquals("niño", SearchText.normalize("NIÑO"))
        assertNotEquals(SearchText.normalize("año"), SearchText.normalize("ano"))
        assertFalse(SearchText.matchesNormalized(SearchText.normalize("ano"), "Año 2026"))
    }

    @Test fun doesNotLoseExistingCaseInsensitiveAndIdSearch() {
        assertTrue(SearchText.matchesNormalized(SearchText.normalize("2026/12798"), "2026/12798"))
        assertTrue(SearchText.matchesNormalized(SearchText.normalize("VALENCIA"), "Valencia"))
        assertTrue(SearchText.matchesNormalized("", "Cualquier título"))
        assertFalse(SearchText.matchesNormalized(SearchText.normalize("policia"),
            "Bolsa de trabajo de biblioteca", "Ayuntamiento de Xàtiva"))
    }
}
