package es.opoalert.app

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class DeadlineStoreTest {
    private val url = "https://www.boe.es/boe/dias/2026/10/31/pdfs/BOE-A-2026-22836.pdf"
    private fun file(item: String) = """{"schemaVersion":1,"items":{"$url":$item},"none":[],"tries":{}}"""

    @Test fun readsTheDeadlineWrittenInTheNotice() {
        val deadline = DeadlineStore.parse(file(
            """{"days":20,"kind":"hábiles","page":1,"text":"El plazo de presentación de solicitudes será de veinte días hábiles."}"""
        ), url)!!
        assertEquals("20 días hábiles", deadline.label)
        assertEquals(1, deadline.page)
    }

    @Test fun showsNothingIfSomethingDoesNotFit() {
        assertNull(DeadlineStore.parse(file("""{"days":20,"kind":"hábiles","page":1,"text":"corto"}"""), url))
        assertNull(DeadlineStore.parse(file("""{"days":0,"kind":"hábiles","page":1,"text":"El plazo será de cero días hábiles sin más."}"""), url))
        assertNull(DeadlineStore.parse(file("""{"days":20,"kind":"lectivos","page":1,"text":"El plazo será de veinte días lectivos sin más."}"""), url))
        assertNull(DeadlineStore.parse(file("""{"days":20,"kind":"hábiles","page":0,"text":"El plazo será de veinte días hábiles sin más."}"""), url))
        assertNull(DeadlineStore.parse(file("""{"days":20,"kind":"hábiles","page":1,"text":"El plazo será de veinte días hábiles sin más."}"""), url + "x"))
        assertNull(DeadlineStore.parse("""{"schemaVersion":2,"items":{}}""", url))
    }

    private fun sedes(link: String) = """{"schemaVersion":1,"items":{},"sedes":{"$url":"$link"}}"""

    @Test fun readsTheSedeWrittenInTheNotice() {
        assertEquals("https://lietor.sedipualba.es/", DeadlineStore.parseSede(sedes("https://lietor.sedipualba.es/"), url))
        assertEquals("https://www.seu-e.cat/ca/web/bascara", DeadlineStore.parseSede(sedes("https://www.seu-e.cat/ca/web/bascara"), url))
        assertNull(DeadlineStore.parseSede(sedes("http://lietor.sedipualba.es/"), url))
        assertNull(DeadlineStore.parseSede(sedes("https://lietor.sedi-/"), url))
        assertNull(DeadlineStore.parseSede(sedes("javascript:alert(1)"), url))
        assertNull(DeadlineStore.parseSede(file("{}"), url))
    }

    @Test fun readsBoeExtractsForFollowUps() {
        val text = """{"schemaVersion":1,"items":{},"proveer":{
            "$url":{"items":["Una plaza de Administrativo/a, por el sistema de oposición, en turno libre."],
                    "bases":{"diario":"Boletín Oficial de la Provincia de Lugo","numero":"236","fecha":"15/10/2026"}},
            "https://otro.es/a.pdf":{"items":["Una plaza de Administrativo/a, en turno libre."]},
            "https://www.boe.es/b.pdf":{"items":["corto"]}}}"""
        val extracts = DeadlineStore.parseBoeExtracts(text)
        assertEquals(setOf(url), extracts.keys)
        assertEquals("15/10/2026", extracts.getValue(url).basesDate)
        assertEquals(emptyMap<String, BoeExtract>(), DeadlineStore.parseBoeExtracts("""{"schemaVersion":1,"items":{}}"""))
    }

    @Test fun oneFilePerSource() {
        assertEquals("https://mjtbapps.github.io/OpoAlert/plazos/boe.json", DeadlineStore.urlFor(Province.BOE))
        assertEquals("https://mjtbapps.github.io/OpoAlert/plazos/convocatorias.json", DeadlineStore.urlFor(Province.VALENCIA))
    }
}
