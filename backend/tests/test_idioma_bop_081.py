"""Regresion del idioma oficial CAS y del extractor de titulos en castellano."""
import sys
import unittest
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from idioma_bop import seleccionar_castellano, IdiomaBOPError
from scan import extract_index, classify, entity_from_title


class Control:
    def __init__(self, page, kind):
        self.page = page
        self.kind = kind
        self.first = self

    def count(self):
        if self.kind == 'cas_active':
            return int(self.page.spanish)
        return int(not self.page.spanish and self.page.has_cas_link)

    def is_visible(self):
        return self.count() > 0

    def click(self, timeout=None):
        assert self.kind == 'cas_link' and self.count() == 1
        self.page.spanish = True
        self.page.clicks += 1


class Page:
    def __init__(self, spanish=False, has_cas_link=True):
        self.spanish = spanish
        self.has_cas_link = has_cas_link
        self.clicks = 0
        self.waits = 0

    def locator(self, query):
        if query.startswith('span.ui-state-disabled:'):
            return Control(self, 'cas_active')
        if query.startswith('a[title='):
            return Control(self, 'cas_link')
        raise AssertionError('selector no esperado: ' + query)

    def wait_for_function(self, javascript, timeout=None):
        self.waits += 1
        assert self.spanish, 'Se habria verificado la version valenciana por error'
        assert 'Anuncio' in javascript


class OfficialCastilianTests(unittest.TestCase):
    def test_selected_from_valencian(self):
        page = Page()
        self.assertTrue(seleccionar_castellano(page))
        self.assertEqual(page.clicks, 1)
        self.assertEqual(page.waits, 1)

    def test_not_clicked_twice_if_already_selected(self):
        page = Page(spanish=True)
        self.assertFalse(seleccionar_castellano(page))
        self.assertEqual(page.clicks, 0)
        self.assertEqual(page.waits, 1)

    def test_missing_locale_fails_closed(self):
        with self.assertRaises(IdiomaBOPError):
            seleccionar_castellano(Page(spanish=False, has_cas_link=False))

    def test_read_official_castilian_notice_and_keep_id(self):
        html = '''<h1>Boletín Nº 207</h1><div id="list_content">
          <div class="ui-datagrid-column">
            <div class="sumario">Anuncio del Ayuntamiento de Xàtiva sobre la aprobación de las bases
            de la convocatoria para la constitución de una bolsa de trabajo de auxiliar administrativo.</div>
            <div>Nº registro: 2026/12345</div>
            <div>Fecha publicación: 28/10/2026</div>
            <div>Boletín: 207</div>
          </div>
        </div>'''
        rows, heading = extract_index(html)
        self.assertEqual(heading, '207')
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['id'], '2026/12345')
        self.assertTrue(rows[0]['title'].startswith('Anuncio del Ayuntamiento'))
        self.assertEqual(rows[0]['entity'], 'Ayuntamiento de Xàtiva')
        self.assertEqual(rows[0]['type'], 'Bolsa de trabajo')
        self.assertTrue(rows[0]['url'].endswith('anuncioNumReg=2026%2F12345&lang=es'))

    def test_supplemental_cases_in_spanish_classifier(self):
        self.assertEqual(classify(
            'Anuncio del Ayuntamiento de Ontinyent sobre la aprobación de las '
            'bases para la convocatoria de dos plazas de administrativo.'
        ), 'Plaza / oposición')


if __name__ == '__main__':
    unittest.main()
