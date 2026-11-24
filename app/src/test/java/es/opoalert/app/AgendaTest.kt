package es.opoalert.app

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.time.LocalDate

/** Plazo orientativo, agenda de favoritas, recordatorio, valoración, actualización y compartir (1.57.0). */
class AgendaTest {
    private val url = "https://www.boe.es/boe/dias/2026/10/31/pdfs/BOE-A-2026-22836.pdf"
    private val quote = "El plazo de presentación de solicitudes será de veinte días hábiles."
    private fun file(extra: String) =
        """{"schemaVersion":1,"items":{"$url":{"days":20,"kind":"hábiles","page":1,"text":"$quote"$extra}}}"""

    private fun notice(id: String) = Notice(id, "Convocatoria $id", "Ayuntamiento", "24/11/2026", "1", "Plaza", url)

    @Test fun readsTheEstimatedEndOnlyWhenWellFormed() {
        assertEquals(LocalDate.of(2026, 12, 14), DeadlineStore.parse(file(""","hasta":"2026-12-14""""), url)!!.until)
        assertNull(DeadlineStore.parse(file(""","hasta":"14/12/2026""""), url)!!.until)
        assertNull(DeadlineStore.parse(file(""","hasta":"2026-13-40""""), url)!!.until)
        assertNull(DeadlineStore.parse(file(""), url)!!.until)
    }

    @Test fun favoritesEndingSoonGoFirst() {
        val today = LocalDate.of(2026, 11, 24)
        val favorites = listOf(notice("A"), notice("B"), notice("C"), notice("D"), notice("E"))
        val agenda = mapOf(
            "A" to AgendaEntry(until = LocalDate.of(2026, 12, 20)),
            "B" to AgendaEntry(),                                               // sin fecha
            "C" to AgendaEntry(until = LocalDate.of(2026, 11, 27)),
            "D" to AgendaEntry(until = LocalDate.of(2026, 11, 1)),               // ya pasado
            "E" to AgendaEntry(until = LocalDate.of(2026, 11, 26), submitted = true),
        )
        assertEquals(listOf("C", "A", "B", "D", "E"), FavoriteAgenda.sort(favorites, agenda, today).map { it.id })
    }

    @Test fun reminderComesTwoDaysBeforeAndNeverLate() {
        val today = LocalDate.of(2026, 11, 24)
        assertEquals(LocalDate.of(2026, 12, 12), DeadlineReminder.remindDay(LocalDate.of(2026, 12, 14), today))
        assertEquals(today, DeadlineReminder.remindDay(LocalDate.of(2026, 11, 25), today))
        assertEquals(today, DeadlineReminder.remindDay(today, today))
        assertNull(DeadlineReminder.remindDay(LocalDate.of(2026, 11, 23), today))
    }

    @Test fun reviewIsAskedOnlyToRegularUsersAndRarely() {
        assertTrue(ReviewPrompt.shouldAsk(opened = 5, days = 3, installedDays = 3, times = 0, daysSinceLast = 0))
        assertFalse(ReviewPrompt.shouldAsk(4, 3, 3, 0, 0))
        assertFalse(ReviewPrompt.shouldAsk(5, 2, 3, 0, 0))
        assertFalse(ReviewPrompt.shouldAsk(5, 3, 2, 0, 0))
        assertFalse(ReviewPrompt.shouldAsk(50, 9, 99, 1, 30))
        assertTrue(ReviewPrompt.shouldAsk(50, 9, 99, 1, 120))
        assertFalse(ReviewPrompt.shouldAsk(50, 9, 999, 3, 999))
    }

    @Test fun playUpdateIsOfferedUnlessSnoozed() {
        val now = 10_000_000_000L
        assertTrue(PlayUpdate.shouldOffer(80, 79, 0, 0, now))
        assertFalse(PlayUpdate.shouldOffer(79, 79, 0, 0, now))
        assertFalse(PlayUpdate.shouldOffer(80, 79, 80, now - 1000, now))
        assertTrue(PlayUpdate.shouldOffer(80, 79, 80, now - PlayUpdate.SNOOZE_MS, now))
        assertTrue(PlayUpdate.shouldOffer(81, 79, 80, now - 1000, now))
    }

    @Test fun sharedTextHasOfficialLinkDeadlineAndApp() {
        val text = ShareText.message(notice("BOE-A-2026-1"), Deadline(20, "hábiles", quote, 1))
        assertTrue(text.contains(url))
        assertTrue(text.contains("20 días hábiles (según el anuncio)"))
        assertTrue(text.endsWith(ShareText.APP_LINK))
        assertTrue(text.contains("BOE "))
        assertFalse(ShareText.message(notice("X-1")).contains("Plazo"))
    }
}
