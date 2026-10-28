"""Regression tests using real BOP calendar input ids from diagnostic JSON."""
import sys
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from history import _read_date_fields, _values_match, CoverageError, fill_date_range

class FakeInput:
    def __init__(self, value=''):
        self.value = value
        self.first = self
    def count(self):
        return 1
    def is_visible(self):
        return True
    def input_value(self):
        return self.value
    def get_attribute(self, name):
        return None
    def fill(self, value):
        self.value = value
    def click(self, **kwargs):
        return None
    def press(self, key):
        if key == 'Backspace':
            self.value = ''
    def type(self, value, **kwargs):
        self.value = value

class FakePage:
    def __init__(self, start='', end=''):
        self.inputs = {
            '[id="filtroCalendarioIni_input"]': FakeInput(start),
            '[id="filtroCalendarioFin_input"]': FakeInput(end),
        }
        self.used = []
    def locator(self, selector):
        self.used.append(selector)
        if selector not in self.inputs:
            raise AssertionError('unexpected selector: ' + selector)
        return self.inputs[selector]
    def wait_for_timeout(self, ms):
        pass

class HistoryCalendarTests(unittest.TestCase):
    def test_uses_exact_confirmed_calendar_ids(self):
        page = FakePage('28/09/2026', '27/10/2026')
        self.assertTrue(_values_match(page, date(2026,9,28), date(2026,10,27)))
        self.assertEqual(page.used, [
            '[id="filtroCalendarioIni_input"]',
            '[id="filtroCalendarioFin_input"]'
        ])

    def test_correct_diagnostic_values_accepted(self):
        page = FakePage('28/09/2026', '27/10/2026')
        # 0.5.1: ya no se rellenan inputs manualmente; el test de IDs antiguos
        # simula solo la seleccion del dia y verifica ambos campos oficiales.
        def select_day(page, base_id, wanted):
            selector = '[id="' + base_id + '_input"]'
            page.inputs[selector].value = wanted.strftime('%d/%m/%Y')
        with patch('history._choose_date', side_effect=select_day):
            fill_date_range(page, date(2026,9,28), date(2026,10,27))
        self.assertEqual(_read_date_fields(page)[0].input_value(), '28/09/2026')
        self.assertEqual(_read_date_fields(page)[1].input_value(), '27/10/2026')

    def test_different_date_rejected(self):
        page = FakePage('27/09/2026', '27/10/2026')
        self.assertFalse(_values_match(page, date(2026,9,28), date(2026,10,27)))

    def test_missing_field_blocks_unverified_search(self):
        page = FakePage()
        del page.inputs['[id="filtroCalendarioFin_input"]']
        with self.assertRaises((CoverageError, AssertionError)):
            _values_match(page, date(2026,9,28), date(2026,10,27))

if __name__ == '__main__':
    unittest.main()
