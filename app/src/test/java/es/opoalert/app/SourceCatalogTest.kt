package es.opoalert.app

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class SourceCatalogTest {
    @Test fun everyNonNationalSourceAppearsOnce() {
        val all = SourceCatalog.groups()
        val sources = all.flatMap { it.territories }.flatMap { it.sources }
        assertEquals(SourceCatalog.availableSources.size - 1, sources.size)
        assertEquals(sources.size, sources.toSet().size)
        assertFalse(Province.BOE in sources)
    }

    @Test fun communitiesAndProvincesAreGroupedInsteadOfFlatList() {
        val groups = SourceCatalog.groups()
        assertEquals(listOf("Comunidad Valenciana", "Cataluña", "Aragón", "Andalucía", "Comunidad de Madrid", "Castilla-La Mancha", "Castilla y León", "Extremadura", "Región de Murcia", "País Vasco", "Galicia"), groups.map { it.name })
        assertEquals(listOf("Valencia", "Alicante", "Castellón", "Diario autonómico"),
            groups[0].territories.map { it.name })
        assertEquals(listOf("Barcelona", "Girona", "Lleida", "Tarragona"),
            groups[1].territories.map { it.name })
        assertEquals(listOf(Province.BARCELONA_BOP, Province.BARCELONA),
            groups[1].territories.first().sources)
        assertEquals(listOf(Province.TARRAGONA_BOP, Province.TARRAGONA),
            groups[1].territories[3].sources)
        assertEquals(4, groups[0].sourceCount)
        assertEquals(7, groups[1].sourceCount)
        assertEquals(listOf("Huesca", "Teruel", "Zaragoza"), groups[2].territories.map { it.name })
        assertEquals(3, groups[2].sourceCount)
        assertEquals(listOf("Almería", "Cádiz", "Córdoba", "Granada", "Huelva", "Sevilla"), groups[3].territories.map { it.name })
        assertEquals(6, groups[3].sourceCount)
        assertEquals(listOf("Madrid"), groups[4].territories.map { it.name })
        assertEquals(1, groups[4].sourceCount)
        assertEquals(listOf("Ciudad Real", "Guadalajara", "Toledo", "Diario autonómico"), groups[5].territories.map { it.name })
        assertEquals(4, groups[5].sourceCount)
        assertEquals(listOf("Ávila", "León", "Palencia", "Soria", "Zamora", "Diario autonómico"), groups[6].territories.map { it.name })
        assertEquals(6, groups[6].sourceCount)
        assertEquals(listOf("Badajoz", "Cáceres", "Diario autonómico"), groups[7].territories.map { it.name })
        assertEquals(3, groups[7].sourceCount)
        assertEquals(listOf("Murcia"), groups[8].territories.map { it.name })
        assertEquals(1, groups[8].sourceCount)
        assertEquals(listOf("Bizkaia", "Gipuzkoa", "Diario autonómico"), groups[9].territories.map { it.name })
        assertEquals(3, groups[9].sourceCount)
        assertEquals(listOf("A Coruña", "Ourense", "Pontevedra", "Diario autonómico"), groups[10].territories.map { it.name })
        assertEquals(4, groups[10].sourceCount)
    }

    @Test fun sourcesWithoutDailyFeedAreHidden() {
        val shown = SourceCatalog.groups().flatMap { it.territories }.flatMap { it.sources }
        for (pending in SourceCatalog.pendingDailyFeed) {
            assertFalse("$pending no tiene feed diario", pending in shown)
            assertFalse(pending in SourceCatalog.availableSources)
        }
        assertTrue(Province.MADRID in shown)
        assertTrue(Province.GALICIA_DOG in shown)
    }

    @Test fun labelsKeepBopAndCidoApart() {
        assertEquals("BOE · toda España", SourceCatalog.sourceName(Province.BOE))
        assertEquals("BOP · boletín provincial", SourceCatalog.sourceName(Province.VALENCIA))
        assertEquals("CIDO · procesos selectivos", SourceCatalog.sourceName(Province.LLEIDA))
        assertEquals("BOCM · diario autonómico", SourceCatalog.sourceName(Province.MADRID))
        assertEquals("DOCM · diario autonómico", SourceCatalog.sourceName(Province.CLM_DOCM))
        assertEquals("BOCYL · diario autonómico", SourceCatalog.sourceName(Province.CYL_BOCYL))
        assertEquals("DOE · diario autonómico", SourceCatalog.sourceName(Province.EXTREMADURA_DOE))
        assertEquals("BORM · boletín autonómico y provincial", SourceCatalog.sourceName(Province.MURCIA_BORM))
        assertEquals("BOPV · diario autonómico", SourceCatalog.sourceName(Province.PAIS_VASCO_BOPV))
        assertEquals("BOTHA · boletín territorial de Álava", SourceCatalog.sourceName(Province.ALAVA_BOTHA))
        assertEquals("BOB · boletín territorial de Bizkaia", SourceCatalog.sourceName(Province.BIZKAIA_BOB))
        assertEquals("BOG · boletín territorial de Gipuzkoa", SourceCatalog.sourceName(Province.GIPUZKOA_BOG))
        assertEquals("DOG · diario autonómico", SourceCatalog.sourceName(Province.GALICIA_DOG))
        assertEquals("BOA · diario autonómico", SourceCatalog.sourceName(Province.ARAGON_BOA))
        assertEquals("BOJA · diario autonómico", SourceCatalog.sourceName(Province.ANDALUCIA_BOJA))
        assertEquals("DOGV · diario autonómico", SourceCatalog.sourceName(Province.VALENCIA_DOGV))
        assertEquals("DOGC · diario autonómico", SourceCatalog.sourceName(Province.CATALUNA_DOGC))
        assertEquals("BOIB · boletín autonómico e insular", SourceCatalog.sourceName(Province.BALEARES_BOIB))
        assertEquals("BOC · diario autonómico", SourceCatalog.sourceName(Province.CANARIAS_BOC))
        assertEquals("BOME · boletín de la ciudad autónoma", SourceCatalog.sourceName(Province.MELILLA_BOME))
        assertEquals("BOR · diario autonómico", SourceCatalog.sourceName(Province.RIOJA_BOR))
        assertEquals("BON · boletín de Navarra", SourceCatalog.sourceName(Province.NAVARRA_BON))
        assertEquals("BOPA · diario autonómico", SourceCatalog.sourceName(Province.ASTURIAS_BOPA))
        assertEquals("BOCCE · boletín de la ciudad autónoma", SourceCatalog.sourceName(Province.CEUTA_BOCCE))
        assertEquals("BOP · boletín provincial", SourceCatalog.sourceName(Province.GALICIA_OURENSE))
        assertTrue(SourceCatalog.isCido(Province.BARCELONA))
        assertFalse(SourceCatalog.isCido(Province.BARCELONA_BOP))
    }
}
