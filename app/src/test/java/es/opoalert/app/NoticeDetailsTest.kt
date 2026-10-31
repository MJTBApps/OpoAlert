package es.opoalert.app

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class NoticeDetailsTest {
    @Test fun readsOnlyExplicitNumberOfPlaces() {
        assertEquals(5, NoticeDetails.placesInTitle("Convocatoria de 5 plazas de Policía Local"))
        assertEquals(4, NoticeDetails.placesInTitle("Se convocan 4 places de administratiu"))
        assertNull(NoticeDetails.placesInTitle("Bolsa de auxiliar administrativo plazas"))
        assertNull(NoticeDetails.placesInTitle("Bolsa de auxiliar administrativo"))
    }

    @Test fun readsPlacesWrittenInWords() {
        assertEquals(5, NoticeDetails.placesInTitle("Convocatoria de cinco plazas de bombero"))
        assertEquals(4, NoticeDetails.placesInTitle(
            "Cuatro plazas de profesorado de orquesta, instrumento viola, una reservada para el turno de discapacidad"
        ))
        assertEquals(1, NoticeDetails.placesInTitle("Bases para proveer una plaza de auxiliar administrativo"))
        assertEquals(3, NoticeDetails.placesInTitle("Convocatòria de tres places d'agent de la policia local"))
        assertEquals(2, NoticeDetails.placesInTitle("Procés selectiu de dues places de tècnic"))
        assertEquals(1, NoticeDetails.placesInTitle("Bases d'una plaça d'administratiu"))
    }

    @Test fun ignoresWordsThatAreNotNumbers() {
        assertNull(NoticeDetails.placesInTitle("Convocatoria de las plazas vacantes de bombero"))
        assertNull(NoticeDetails.placesInTitle("Creación de bolsa para diversas plazas"))
        assertNull(NoticeDetails.placesInTitle("Convocatoria de dos plazas y tres plazas de conserje"))
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

    @Test fun readsNumberInBracketsAndGalician() {
        assertEquals(2, NoticeDetails.placesInTitle(
            "Convocatoria para la selección, mediante oposición, de dos (2) plazas de Técnico/a de Administración General"))
        assertEquals(1, NoticeDetails.placesInTitle("Provisión dunha (1) praza de axudante de obras e servizos"))
        assertEquals(3, NoticeDetails.placesInTitle("Bases para tres prazas de auxiliar administrativo"))
        assertNull(NoticeDetails.placesInTitle("Convocatoria de dos (3) plazas de conserje"))
    }
}
