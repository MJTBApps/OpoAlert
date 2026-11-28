package es.opoalert.app

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class FollowUpsTest {
    private val bases = Notice("PL-2026-1", "Bases y convocatoria del proceso selectivo de siete plazas de Oficial de la Policía Local, " +
        "mediante concurso-oposición de promoción interna", "Palencia", "20/11/2026", "210", "Plaza / oposición",
        "https://bop.dip-palencia.es/1.pdf", Province.PALENCIA_BOP.label)
    private val correction = Notice("PL-2026-2", "Corrección de error al anuncio publicado el día 20 de noviembre de 2026, por el que " +
        "se aprueban las bases y convocatoria del proceso selectivo de siete plazas de Oficial de la Policía Local", "Palencia",
        "25/11/2026", "213", "Plaza / oposición", "https://bop.dip-palencia.es/2.pdf", Province.PALENCIA_BOP.label)
    private val other = Notice("PL-2026-3", "Bases de una plaza de conserje", "Ayuntamiento de Dueñas", "25/11/2026", "213",
        "Plaza / oposición", "https://bop.dip-palencia.es/3.pdf", Province.PALENCIA_BOP.label)

    @Test fun firstSearchDoesNotNotifyLaterOnesDo() {
        val (first, fresh1) = FollowUps.update(listOf(bases), listOf(bases, correction, other), emptyMap(), emptyMap())
        assertTrue(fresh1.isEmpty())
        val state = first.getValue(bases.id)
        assertTrue(state.initialized)
        assertEquals(listOf(correction.id), state.items.map { it.notice.id })
        assertEquals("Corrección de errores", state.items.first().step)
        assertFalse(state.items.first().unread)

        // Ya buscada: lo que aparece después sí es novedad.
        val (second, fresh2) = FollowUps.update(listOf(bases), listOf(bases, correction, other), emptyMap(),
            mapOf(bases.id to FollowUpState(true, emptyList())))
        assertEquals(listOf(correction.id), fresh2.map { it.second.notice.id })
        assertEquals(1, second.getValue(bases.id).unreadCount)
    }

    @Test fun noHidesForeverAndAnswersSurviveASearch() {
        val hidden = FollowUpState(true, listOf(FollowUpItem(correction, "Corrección de errores", FollowUpItem.NO)))
        val (next, fresh) = FollowUps.update(listOf(bases), listOf(correction), emptyMap(), mapOf(bases.id to hidden))
        assertTrue(fresh.isEmpty())
        assertTrue(next.getValue(bases.id).visible.isEmpty())

        val searched = mapOf(bases.id to FollowUpState(true, listOf(FollowUpItem(correction, "Corrección de errores", unread = true))))
        val answered = mapOf(bases.id to FollowUpState(true, listOf(FollowUpItem(correction, "Corrección de errores", FollowUpItem.YES))))
        val kept = FollowUps.keepAnswers(searched, answered).getValue(bases.id).items.single()
        assertEquals(FollowUpItem.YES, kept.state)
        assertFalse(kept.unread)
    }

    @Test fun storedAsJson() {
        val stored = FollowUps.Stored(123L, mapOf(bases.id to FollowUpState(true,
            listOf(FollowUpItem(correction, "Corrección de errores", FollowUpItem.YES, unread = true)))))
        assertEquals(stored, FollowUps.parse(FollowUps.encode(stored)))
        assertEquals(FollowUps.Stored(0, emptyMap()), FollowUps.parse("no es json"))
    }

    @Test fun communitySourcesWithoutCido() {
        val sources = SourceCatalog.followUpSources(Province.BARCELONA_BOP, Province.entries.toList())
        assertTrue(Province.CATALUNA_DOGC in sources)
        assertTrue(Province.BOE in sources)
        assertFalse(Province.BARCELONA in sources)
        assertFalse(Province.VALENCIA in sources)
    }
}
