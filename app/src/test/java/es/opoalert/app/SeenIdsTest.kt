package es.opoalert.app

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class SeenIdsTest {
    @Test fun keepsNewestFirstWithoutDuplicates() {
        assertEquals(listOf("c", "a", "b"), SeenIds.merge(listOf("c", "a"), listOf("a", "b")))
    }

    @Test fun noticesFromFailedSourcesStaySeen() {
        // Si un feed falla en una revisión, sus anuncios no deben volver a avisar después.
        val seen = SeenIds.merge(listOf("VA-1"), listOf("VA-1", "AL-1"))
        assertTrue("AL-1" in seen)
    }

    @Test fun holdsMoreThanTheListCache() {
        // Con todas las fuentes, los feeds suman más de 5000 anuncios: todos deben seguir vistos.
        val fresh = (1..6000).map { "ID-$it" }
        val seen = SeenIds.merge(fresh, emptyList())
        assertEquals(6000, seen.size)
        assertTrue(fresh.all { it in seen })
    }

    @Test fun isBounded() {
        val seen = SeenIds.merge((1..SeenIds.MAX + 10).map { "N-$it" }, listOf("old"))
        assertEquals(SeenIds.MAX, seen.size)
        assertEquals("N-1", seen.first())
    }

    @Test fun roundTripsAndToleratesDamage() {
        val ids = listOf("BOE-A-2026-1", "CN-2026-8113")
        assertEquals(ids, SeenIds.parse(SeenIds.encode(ids)))
        assertEquals(emptyList<String>(), SeenIds.parse("no es json"))
    }
}
