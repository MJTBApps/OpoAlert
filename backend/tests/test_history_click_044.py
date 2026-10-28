"""Pruebas de regresion del fallo real en PrimeFaces (fecha revertida con Escape)."""
import sys
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from history import search_date_range, CoverageError

class Input:
    def __init__(self): self.value = ''; self.first = self
    def count(self): return 1
    def is_visible(self): return True
    def input_value(self): return self.value
    def get_attribute(self, attr): return None
    def fill(self, value): self.value = value

class Button:
    def __init__(self): self.dispatched = 0; self.clicked = 0
    def count(self): return 1
    def is_visible(self): return True
    def is_enabled(self): return True
    def dispatch_event(self, name):
        if name != 'click': raise AssertionError(name)
        self.dispatched += 1
    def click(self, **kwargs): self.clicked += 1; raise AssertionError('No usar click fisico')

class Popup:
    def __init__(self, visible): self.visible = visible
    def count(self): return 1
    def is_visible(self): return self.visible

class Keyboard:
    def __init__(self, page): self.page=page; self.pressed=[]
    def press(self, key):
        self.pressed.append(key)
        if key == 'Escape': self.page.start.value = ''

class Page:
    def __init__(self, popup=True, error=False):
        self.start=Input(); self.end=Input(); self.button=Button()
        self.keyboard=Keyboard(self); self.waits=[]
        self.nodes = {
            '[id="filtroCalendarioIni_input"]':self.start,
            '[id="filtroCalendarioFin_input"]':self.end,
            '[id="buscarBtn"]':self.button,
            '[id="filtroCalendarioIni_panel"]':Popup(popup),
            '[id="filtroCalendarioFin_panel"]':Popup(False),
            '[id="dlgBusquedaError"]':Popup(error),
        }
    def locator(self, s): return self.nodes[s]
    def wait_for_timeout(self, ms): self.waits.append(ms)

class SearchTest(unittest.TestCase):
    """Regresion del calendario que reescribia fechas al presionar Escape.

    Se mockea solamente la eleccion del dia, NO el boton Buscar ni la
    validacion posterior de los inputs. Los tests reales del widget se
    mantienen en test_calendar_047 y los del servidor en test_history_ajax_045.
    """
    @staticmethod
    def select_day(page, base_id, wanted):
        field = page.start if base_id == 'filtroCalendarioIni' else page.end
        field.value = wanted.strftime('%d/%m/%Y')

    def test_calendar_open_escape_would_reset_date(self):
        p=Page(popup=True)
        with patch('history._choose_date', side_effect=self.select_day):
            search_date_range(p,date(2026,9,28),date(2026,10,27))
        self.assertEqual(p.keyboard.pressed, [])
        self.assertEqual(p.start.value,'28/09/2026')
        self.assertEqual(p.end.value,'27/10/2026')
        self.assertEqual(p.button.dispatched, 1)
        self.assertEqual(p.button.clicked, 0)

    def test_calendar_closed_no_pointer_click_either(self):
        p=Page(popup=False)
        with patch('history._choose_date', side_effect=self.select_day):
            search_date_range(p,date(2026,9,28),date(2026,10,27))
        self.assertEqual(p.button.dispatched,1)
        self.assertEqual(p.button.clicked,0)

    def test_error_dialog_does_not_pass(self):
        p=Page(error=True)
        with patch('history._choose_date', side_effect=self.select_day):
            with self.assertRaisesRegex(CoverageError,'error al buscar'):
                search_date_range(p,date(2026,9,28),date(2026,10,27))

    def test_dates_must_be_consistent(self):
        p=Page()
        def bad_end_date(page, base_id, wanted):
            if base_id == 'filtroCalendarioFin':
                page.end.value = '01/10/2026'
            else:
                page.start.value = wanted.strftime('%d/%m/%Y')
        with patch('history._choose_date', side_effect=bad_end_date):
            with self.assertRaises(CoverageError):
                search_date_range(p,date(2026,9,28),date(2026,10,27))
        self.assertEqual(p.button.dispatched,0)

if __name__ == '__main__': unittest.main()
