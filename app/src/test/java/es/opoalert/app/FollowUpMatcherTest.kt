package es.opoalert.app

import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/** Parejas reales revisadas a mano: las mismas que comprueban `backend/tests/test_seguimiento.py` e iOS. */
class FollowUpMatcherTest {
    private fun casesFile(): File =
        listOf("../backend/tests/seguimiento_casos.json", "backend/tests/seguimiento_casos.json")
            .map { File(it) }.first { it.exists() }

    private fun item(o: JSONObject): FollowUpMatcher.Item {
        val ex = o.optJSONObject("extract")
        val extract = ex?.let {
            val items = it.getJSONArray("items")
            BoeExtract((0 until items.length()).map { i -> items.getString(i) }, it.optString("basesDate").ifEmpty { null })
        }
        val url = o.getString("url")
        return FollowUpMatcher.Item(url, o.getString("title"), o.getString("entity"), o.getString("date"),
            o.getString("source"), o.optBoolean("cido"), url.startsWith("https://www.boe.es/"), extract)
    }

    @Test fun sharedCases() {
        val cases = JSONObject(casesFile().readText()).getJSONArray("cases")
        assertTrue(cases.length() >= 20)
        for (i in 0 until cases.length()) {
            val case = cases.getJSONObject(i)
            val fav = item(case.getJSONObject("favorite"))
            val cand = item(case.getJSONObject("candidate"))
            assertEquals(case.getString("name"), case.getBoolean("followUp"), FollowUpMatcher.isFollowUp(fav, cand))
            if (case.has("step")) assertEquals(case.getString("name"), case.getString("step"), cand.step)
        }
    }

    @Test fun noMasculineOrFeminine() {
        assertEquals(FollowUpMatcher.jobKey("una plaza de trabajador/a social"),
            FollowUpMatcher.jobKey("una plaza de trabajadora social"))
        assertEquals(FollowUpMatcher.jobKey("tres plazas de Auxiliares Administrativos"),
            FollowUpMatcher.jobKey("una plaza de auxiliar administrativo/a"))
    }

    @Test fun numberOfPlaces() {
        assertEquals(2, FollowUpMatcher.plazasCount("de dues places de tècnic/a"))
        assertEquals(1, FollowUpMatcher.plazasCount("Una (1) plaza de Traductor/a"))
        assertNull(FollowUpMatcher.plazasCount("bolsa de trabajo de conserje"))
    }

    @Test fun onlyLocalBodies() {
        assertEquals(FollowUpMatcher.Org("ayto", "colmenar viejo"),
            FollowUpMatcher.localOrg("Ayuntamiento de Colmenar Viejo (Madrid)", ""))
        assertEquals(FollowUpMatcher.Org("ayto", "pobla segur"),
            FollowUpMatcher.localOrg("AJUNTAMENT DE LA POBLA DE SEGUR (POBLA DE SEGUR, LA)", ""))
        assertNull(FollowUpMatcher.localOrg("MINISTERIO DE HACIENDA", ""))
        assertNull(FollowUpMatcher.localOrg("Universidad de Málaga", ""))
    }
}
