package es.opoalert.app

import org.junit.Assert.assertEquals
import org.junit.Test

class SyncSummaryTest {
    @Test fun oneSource() {
        assertEquals("61 anuncios · 1 boletín", SyncSummary.describe("VA: 61"))
    }

    @Test fun severalSourcesAndFailures() {
        assertEquals(
            "81 anuncios · 2 boletines · sin datos: Cuenca, Málaga",
            SyncSummary.describe("VA: 61 · AL: 20 · Sin datos verificados: Cuenca, Málaga")
        )
        assertEquals("1 anuncio · 1 boletín", SyncSummary.describe("CE: 1"))
    }

    @Test fun unknownTextIsKept() {
        assertEquals("Fuente sin formato", SyncSummary.describe("Fuente sin formato"))
    }
}
