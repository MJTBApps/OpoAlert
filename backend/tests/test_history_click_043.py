"""Pruebas de regresion para calendario PrimeFaces tapando buscarBtn."""
import sys
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from history import search_date_range, CoverageError


class Input:
    def __init__(self, value=''):
        self.value = value
        self.first = self
    def count(self): return 1
    def is_visible(self): return True
    def is_enabled(self): return True
    def input_value(self): return self.value
    def get_attribute(self, name): return None
    def fill(self, value): self.value = value


class Button:
    def __init__(self):
        self.clicked = 0
        self.dispatched = 0
    def count(self): return 1
    def is_visible(self): return True
    def is_enabled(self): return True
    def click(self, **kwargs): self.clicked += 1
    def dispatch_event(self, event):
        assert event == 'click'
        self.dispatched += 1


class Popup:
    def __init__(self, visible): self.visible = visible
    def count(self): return 1
    def is_visible(self): return self.visible


class Dialog(Popup): pass


class Keyboard:
    def __init__(self, page): self.page = page
    def press(self, key):
        assert key == 'Escape'
        if self.page.dismiss_on_escape:
            self.page.popup.visible = False
        if self.page.reset_on_escape:
            self.page.start.value = ''


class Page:
    def __init__(self, *, popup_visible=True, dismiss_on_escape=False,
                 reset_on_escape=False, error_dialog=False):
        self.start = Input()
        self.end = Input()
        self.button = Button()
        self.popup = Popup(popup_visible)
        self.dismiss_on_escape = dismiss_on_escape
        self.reset_on_escape = reset_on_escape
        self.keyboard = Keyboard(self)
        self.dialog = Dialog(error_dialog)
        self.selectors = {
            '[id="filtroCalendarioIni_input"]': self.start,
            '[id="filtroCalendarioFin_input"]': self.end,
            '[id="buscarBtn"]': self.button,
            '[id="filtroCalendarioIni_panel"]': self.popup,
            '[id="filtroCalendarioFin_panel"]': Popup(False),
            '[id="dlgBusquedaError"]': self.dialog,
        }
    def locator(self, selector):
        if selector not in self.selectors:
            raise AssertionError('Unexpected selector ' + selector)
        return self.selectors[selector]
    def wait_for_timeout(self, _): pass


class SearchClickTests(unittest.TestCase):
    """Pruebas del clic que no dependen de un calendario falso obsoleto.

    El calendario real se prueba por separado en test_calendar_047.
    Aqui simulamos la fecha que el usuario ha elegido en el widget y
    verificamos que Buscar se activa sin usar el puntero ni pulsar Escape.
    """
    @staticmethod
    def select_day(page, base_id, wanted):
        field = page.start if base_id == 'filtroCalendarioIni' else page.end
        field.value = wanted.strftime('%d/%m/%Y')

    def test_popup_blocks_pointer_but_dom_dispatch_succeeds(self):
        page = Page(popup_visible=True, dismiss_on_escape=False)
        with patch('history._choose_date', side_effect=self.select_day):
            search_date_range(page, date(2026,9,28), date(2026,10,27))
        self.assertEqual(page.button.clicked, 0)
        self.assertEqual(page.button.dispatched, 1)

    def test_popup_is_not_closed_via_escape(self):
        page = Page(popup_visible=True, dismiss_on_escape=True)
        with patch('history._choose_date', side_effect=self.select_day):
            search_date_range(page, date(2026,9,28), date(2026,10,27))
        self.assertTrue(page.popup.visible)
        self.assertEqual(page.button.clicked, 0)
        self.assertEqual(page.button.dispatched, 1)

    def test_search_error_detected_and_not_published(self):
        page = Page(popup_visible=False, error_dialog=True)
        with patch('history._choose_date', side_effect=self.select_day):
            with self.assertRaises(CoverageError):
                search_date_range(page, date(2026,9,28), date(2026,10,27))
        self.assertEqual(page.button.dispatched, 1)

    def test_escape_would_reset_date_but_is_not_used(self):
        page = Page(popup_visible=True, reset_on_escape=True)
        with patch('history._choose_date', side_effect=self.select_day):
            search_date_range(page, date(2026,9,28), date(2026,10,27))
        self.assertEqual(page.start.value, '28/09/2026')
        self.assertEqual(page.button.clicked, 0)
        self.assertEqual(page.button.dispatched, 1)


if __name__ == '__main__':
    unittest.main()
