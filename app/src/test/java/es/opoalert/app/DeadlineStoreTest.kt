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

    @Test fun oneFilePerSource() {
        assertEquals("https://mjtbapps.github.io/OpoAlert/plazos/boe.json", DeadlineStore.urlFor(Province.BOE))
        assertEquals("https://mjtbapps.github.io/OpoAlert/plazos/convocatorias.json", DeadlineStore.urlFor(Province.VALENCIA))
    }
}
