"""Pruebas de regresion fechas. Actualizadas en 0.4.7: la seleccion se hace
mediante el calendario de PrimeFaces; ya no debe llamarse a fill() o Tab.
"""
import sys
import unittest
from datetime import date
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from history import fill_date_range, _normalized_date, CoverageError

class DatesTests(unittest.TestCase):
    def test_date_normalization(self):
        self.assertEqual(_normalized_date('27/10/2026'), '2026-10-27')
        self.assertEqual(_normalized_date('2026-10-27'), '2026-10-27')
        self.assertEqual(_normalized_date('27-10-2026'), '2026-10-27')
        self.assertIsNone(_normalized_date('fecha invalida'))

    def test_dates_selected_in_calendar_not_typed(self):
        import history
        visited = []
        orig_choose = history._choose_date
        orig_match = history._values_match
        try:
            history._choose_date = lambda p, k, d: visited.append((k, d))
            history._values_match = lambda p, a, b: True
            fill_date_range(None, date(2026, 9, 28), date(2026, 10, 27))
        finally:
            history._choose_date = orig_choose
            history._values_match = orig_match
        self.assertEqual([v[0] for v in visited], ['filtroCalendarioFin', 'filtroCalendarioIni'])

    def test_rejects_calendar_that_reverts_dates(self):
        import history
        orig_choose = history._choose_date
        orig_match = history._values_match
        try:
            history._choose_date = lambda p, k, d: None
            history._values_match = lambda p, a, b: False
            with self.assertRaisesRegex(CoverageError, 'cambio una fecha'):
                fill_date_range(None, date(2026, 9, 28), date(2026, 10, 27))
        finally:
            history._choose_date = orig_choose
            history._values_match = orig_match

if __name__ == '__main__':
    unittest.main()
