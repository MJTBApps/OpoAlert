"""Primera ronda del día: el boletín de hoy aún no está publicado (03/11/2026)."""
import sys
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import huesca_bop  # noqa: E402
import pais_vasco_bopv  # noqa: E402
from provincial_common import ProvincialCoverageError  # noqa: E402


def rss(title):
    body = ("<rss><channel><title>" + title + "</title>"
            + "<description>" + "x" * 900 + "</description></channel></rss>")
    response = mock.Mock(status_code=200, content=body.encode())
    session = mock.Mock()
    session.get.return_value = response
    return session


class BopvRssTest(unittest.TestCase):
    def test_rss_aun_con_el_boletin_anterior(self):
        with mock.patch.object(pais_vasco_bopv, "session",
                               return_value=rss("Boletín Nº 209, fecha 02/11/2026")):
            self.assertIsNone(pais_vasco_bopv.latest_rss(
                date(2026, 11, 3), 209, date(2026, 11, 2)))

    def test_rss_con_otro_boletin_sigue_siendo_error(self):
        with mock.patch.object(pais_vasco_bopv, "session",
                               return_value=rss("Boletín Nº 205, fecha 27/10/2026")):
            with self.assertRaises(ProvincialCoverageError):
                pais_vasco_bopv.latest_rss(date(2026, 11, 3), 209, date(2026, 11, 2))



class HuescaSinNumerar(unittest.TestCase):
    """04/11/2026: la ficha de hoy existe pero aún sin número («BOP núm. del ...»)."""

    def audit(self, error):
        today = date(2026, 11, 4)

        def reader(day):
            if day == today:
                raise ProvincialCoverageError(error)
            if day.weekday() >= 5:
                return None
            return {"date": day, "pages": 1, "read": 3, "notices": [],
                    "number": 180 + (day - date(2026, 10, 1)).days}

        # Numeración consecutiva solo en días laborables.
        numbers = {}
        n = 180
        for i in range(30):
            d = date(2026, 10, 6) + (date(2026, 10, 7) - date(2026, 10, 6)) * i
            if d.weekday() < 5:
                numbers[d] = n
                n += 1

        def numbered(day):
            ed = reader(day)
            if ed:
                ed["number"] = numbers[day]
            return ed

        with mock.patch.object(huesca_bop, "latest_issue_date", return_value=today):
            return huesca_bop.audit(today=today, reader=numbered, fetch_home=lambda url: "")

    def test_lee_hasta_el_anterior(self):
        data = self.audit("Huesca 2026-11-04: cabecera de edicion incorrecta BOP núm. del 04/11/2026")
        self.assertEqual(data["historyCoverage"]["publicationDates"][-1], "2026-11-03")
        self.assertIn("2026-11-04", data["historyCoverage"]["nonPublicationDates"])

    def test_otros_errores_siguen_fallando(self):
        with self.assertRaises(ProvincialCoverageError):
            self.audit("Huesca 2026-11-04: falta total de anuncios")


if __name__ == "__main__":
    unittest.main()
