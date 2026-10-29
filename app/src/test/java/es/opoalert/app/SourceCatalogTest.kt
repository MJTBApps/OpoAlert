package es.opoalert.app

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class SourceCatalogTest {
    @Test fun everyNonNationalSourceAppearsOnce() {
        val all = SourceCatalog.groups()
        val sources = all.flatMap { it.territories }.flatMap { it.sources }
        assertEquals(Province.entries.size - 1, sources.size)
        assertEquals(sources.size, sources.toSet().size)
        assertFalse(Province.BOE in sources)
    }

    @Test fun communitiesAndProvincesAreGroupedInsteadOfFlatList() {
        val groups = SourceCatalog.groups()
        assertEquals(listOf("Comunidad Valenciana", "Cataluña", "Aragón", "Andalucía", "Comunidad de Madrid"), groups.map { it.name })
        assertEquals(listOf("Valencia", "Alicante", "Castellón"),
            groups[0].territories.map { it.name })
        assertEquals(listOf("Barcelona", "Girona", "Lleida", "Tarragona"),
            groups[1].territories.map { it.name })
        assertEquals(listOf(Province.BARCELONA_BOP, Province.BARCELONA),
            groups[1].territories.first().sources)
        assertEquals(listOf(Province.TARRAGONA_BOP, Province.TARRAGONA),
            groups[1].territories.last().sources)
        assertEquals(3, groups[0].sourceCount)
        assertEquals(7, groups[1].sourceCount)
        assertEquals(listOf("Huesca", "Teruel", "Zaragoza"), groups[2].territories.map { it.name })
        assertEquals(3, groups[2].sourceCount)
        assertEquals(listOf("Almería", "Cádiz", "Córdoba", "Granada", "Sevilla"), groups[3].territories.map { it.name })
        assertEquals(5, groups[3].sourceCount)
        assertEquals(listOf("Madrid"), groups[4].territories.map { it.name })
        assertEquals(1, groups[4].sourceCount)
    }

    @Test fun labelsKeepBopAndCidoApart() {
        assertEquals("BOE · toda España", SourceCatalog.sourceName(Province.BOE))
        assertEquals("BOP · boletín provincial", SourceCatalog.sourceName(Province.VALENCIA))
        assertEquals("CIDO · procesos selectivos", SourceCatalog.sourceName(Province.LLEIDA))
        assertEquals("BOCM · diario autonómico", SourceCatalog.sourceName(Province.MADRID))
        assertTrue(SourceCatalog.isCido(Province.BARCELONA))
        assertFalse(SourceCatalog.isCido(Province.BARCELONA_BOP))
    }
}
