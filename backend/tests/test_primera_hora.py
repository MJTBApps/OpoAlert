"""Primera ronda del día: el boletín de hoy aún no está publicado (03/11/2026)."""
import sys
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

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


if __name__ == "__main__":
    unittest.main()
