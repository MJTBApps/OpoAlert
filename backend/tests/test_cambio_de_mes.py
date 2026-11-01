"""El día 1 de un mes (domingo y festivo, 1/11/2026) el mes nuevo aún no tiene boletines.

Varios lectores exigían un mínimo de ediciones también al mes en curso y fallaron
el 1/11/2026. Los meses completos siguen teniendo que estar completos.
"""
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import baleares_boib  # noqa: E402
import caceres_bop  # noqa: E402
from provincial_common import ProvincialCoverageError  # noqa: E402

END = date(2026, 11, 1)
START = END - timedelta(days=29)
OCTOBER = [date(2026, 10, d) for d in range(1, 32) if date(2026, 10, d).weekday() < 5]


class CaceresTest(unittest.TestCase):
    def calendar(self, november):
        def load(service, params):
            if params["mes"] == 10:
                return [{"diaBop": d.day, "idBoletin": 900 + i} for i, d in enumerate(OCTOBER)]
            return november
        return load

    def test_mes_en_curso_sin_boletines_el_dia_1(self):
        with mock.patch.object(caceres_bop, "load", side_effect=self.calendar([])), \
                mock.patch.object(caceres_bop, "numbering_ok", return_value=True):
            try:
                caceres_bop.archive(START, END)
            except ProvincialCoverageError as error:
                self.assertNotIn("calendario 2026-11", str(error))

    def test_un_mes_completo_corto_sigue_siendo_error(self):
        def load(service, params):
            return [{"diaBop": d.day, "idBoletin": 900 + i} for i, d in enumerate(OCTOBER[:10])]
        with mock.patch.object(caceres_bop, "load", side_effect=load):
            with self.assertRaisesRegex(ProvincialCoverageError, "calendario 2026-10 incompleto"):
                caceres_bop.archive(START, END)


class BalearesTest(unittest.TestCase):
    def months(self, november):
        def parse_month(year, month):
            if month == 10:
                return {700 + i: (d, False) for i, d in enumerate(OCTOBER)}
            return november
        return parse_month

    def test_mes_en_curso_vacio_los_primeros_dias(self):
        with mock.patch.object(baleares_boib, "parse_month", side_effect=self.months({})):
            editions = baleares_boib.parse_calendar(START, END)
        self.assertTrue(editions)
        self.assertTrue(all(day.month == 10 for _, (day, _) in editions))

    def test_mes_en_curso_vacio_a_mitad_de_mes_es_error(self):
        end = date(2026, 11, 12)
        with mock.patch.object(baleares_boib, "parse_month", side_effect=self.months({})):
            with self.assertRaisesRegex(ProvincialCoverageError, "sin ediciones"):
                baleares_boib.parse_calendar(end - timedelta(days=29), end)


if __name__ == "__main__":
    unittest.main()
