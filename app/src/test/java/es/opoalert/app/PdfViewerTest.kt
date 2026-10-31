package es.opoalert.app

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class PdfViewerTest {
    @Test fun opensAtThePageOfTheNotice() {
        assertEquals(29, PdfViewerActivity.startPage("https://www.bopcadiz.es/x/BOP210_30-10-26.pdf#page=29"))
        assertEquals(1, PdfViewerActivity.startPage("https://www.boe.es/boe/dias/2026/10/31/pdfs/BOE-A-2026-22836.pdf"))
        assertEquals(1, PdfViewerActivity.startPage("https://x.es/a.pdf#page=0"))
    }

    @Test fun onlyRealPdfsAreShownInside() {
        assertTrue(PdfViewerActivity.looksLikePdf("%PDF-1.7".toByteArray()))
        assertFalse(PdfViewerActivity.looksLikePdf("<!DOCTYPE html>".toByteArray()))
        assertFalse(PdfViewerActivity.looksLikePdf(ByteArray(0)))
    }
}
