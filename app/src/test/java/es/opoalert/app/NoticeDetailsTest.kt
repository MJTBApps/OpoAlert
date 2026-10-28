package es.opoalert.app

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class NoticeDetailsTest {
    @Test fun readsOnlyExplicitNumberOfPlaces() {
        assertEquals(5, NoticeDetails.placesInTitle("Convocatoria de 5 plazas de Policía Local"))
        assertEquals(4, NoticeDetails.placesInTitle("Se convocan 4 places de administratiu"))
        assertNull(NoticeDetails.placesInTitle("Convocatoria de cinco plazas de bombero"))
        assertNull(NoticeDetails.placesInTitle("Bolsa de auxiliar administrativo"))
    }

    @Test fun doesNotInventAmbiguousPlacesOrProcedures() {
        assertNull(NoticeDetails.placesInTitle("Convocatoria de 4 plazas y 2 plazas"))
        assertNull(NoticeDetails.placesInTitle("Modificación de las bases de 5 plazas de Policía Local"))
        assertNull(NoticeDetails.placesInTitle("Publicación de listado de admitidos"))
    }

    @Test fun groupMustBeExplicitlyMentioned() {
        assertEquals("C1", NoticeDetails.groupInTitle("Convocatoria de Grupo C1 de administrativos"))
        assertEquals("A2", NoticeDetails.groupInTitle("Subgrupo A2, turno libre"))
        assertNull(NoticeDetails.groupInTitle("Policía Local: convocatoria libre"))
        assertNull(NoticeDetails.groupInTitle("Oferta de empleo 2026"))
    }

    @Test fun neverGuessesApplicationDeadline() {
        assertEquals("Consultar bases", NoticeDetails.deadlineLabel())
    }
}
