package es.opoalert.app

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class SmartAlertMatcherTest {
    private val onlyValencia = setOf(Province.VALENCIA)
    private val valenciaAndAlicante = setOf(Province.VALENCIA, Province.ALICANTE)
    private val role = AlertRule("a", "policia local", valenciaAndAlicante)
    private val policeAl = Notice(
        id = "AL-2026-1234",
        title = "Convocatoria de agente de Policía Local",
        entity = "Ayuntamiento de Alicante",
        date = "28/10/2026", bulletin = "205",
        type = "Plaza / oposición", url = "https://example.com",
        province = "Alicante"
    )
    private val adminVal = Notice(
        id = "2026/1234",
        title = "Bases de Auxiliar Administrativo",
        entity = "Ayuntamiento de Náquera",
        date = "28/10/2026", bulletin = "207",
        type = "Plaza / oposición", url = "https://example.com",
        province = "Valencia"
    )

    @Test fun ignoresAccentsAndWordOrder() {
        assertTrue(SmartAlertMatcher.matches(role.copy(phrase = "polícia LOCAL"), policeAl, valenciaAndAlicante))
        assertTrue(SmartAlertMatcher.matches(role.copy(phrase = "local policía"), policeAl, valenciaAndAlicante))
        assertTrue(SmartAlertMatcher.matches(
            role.copy(phrase = "alicante policia"), policeAl, valenciaAndAlicante
        ))
    }

    @Test fun requiresBothFollowedAndAlertProvince() {
        assertFalse(SmartAlertMatcher.matches(role, policeAl, onlyValencia))
        assertFalse(SmartAlertMatcher.matches(
            role.copy(provinces = onlyValencia), policeAl, valenciaAndAlicante
        ))
    }

    @Test fun ignoredWhenPausedAndDoesNotMatchDifferentPosition() {
        assertFalse(SmartAlertMatcher.matches(role.copy(enabled = false), policeAl, valenciaAndAlicante))
        assertFalse(SmartAlertMatcher.matches(role, adminVal, valenciaAndAlicante))
        assertTrue(SmartAlertMatcher.matches(
            role.copy(phrase = "naquera administrativo"), adminVal, valenciaAndAlicante
        ))
    }

    @Test fun oneNoticeMatchesAtMostOnceEvenWithOverlappingAlerts() {
        val candidates = listOf(policeAl, policeAl, adminVal)
        val rules = listOf(role, role.copy(id = "b", phrase = "policía"))
        val matching = SmartAlertMatcher.matching(candidates, rules, valenciaAndAlicante)
        assertEquals(1, matching.size)
        assertEquals(policeAl.id, matching[0].id)
    }

    @Test fun noRulesMeansNoNotifications() {
        assertTrue(SmartAlertMatcher.matching(listOf(policeAl), emptyList(), valenciaAndAlicante).isEmpty())
        assertTrue(SmartAlertMatcher.matching(
            listOf(policeAl), listOf(role.copy(enabled = false)), valenciaAndAlicante
        ).isEmpty())
        assertFalse(SmartAlertMatcher.matches(role.copy(phrase = "ano"), adminVal, valenciaAndAlicante))
    }

    @Test fun castellonIsMatchedOnlyWhenSelected() {
        val notice = policeAl.copy(id="CS-1234", province="Castellón", entity="Ayuntamiento de Vinaròs")
        val ruleCs = role.copy(provinces=setOf(Province.CASTELLON))
        assertTrue(SmartAlertMatcher.matches(ruleCs, notice, setOf(Province.CASTELLON)))
        assertFalse(SmartAlertMatcher.matches(ruleCs, notice, onlyValencia))
    }
}
