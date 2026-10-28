import sys
import unittest
from datetime import date, timedelta
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tarragona import (
    parse_index, extract_pdf, build_history, scan_day,
    ProvincialCoverageError, ROOT,
)


def fixture(day, entries, total=None, first=1, duplicate=False):
    total = len(entries) if total is None else total
    result = ("Se encontraron %s resultados sobre su búsqueda. Se muestran del %s al %s" %
              (total, first, first+len(entries)-1)) if total > 1 else (
              "Se ha encontrado 1 resultado sobre su búsqueda" if total == 1 else
              "No se han encontrado resultados")
    cards = []
    for number, title in entries:
        cards.append(f"""<div class="card bg-white"><div class="card-body">
          <h3 class="card-title h6"><a href="/bopt/web/anuncio/{number}/titulo">AJUNTAMENT TEST</a></h3>
          <p>{title}</p><ul><li>Registro : 2026-{number:05d}</li>
          <li>Fecha de publicación : {day.strftime('%d/%m/%Y')}</li></ul>
          </div></div>""")
    return ("<html><head><title>El Boletín Oficial del día " + day.strftime("%d/%m/%Y") +
            " - Butlletí Oficial de la Província de Tarragona (BOPT)</title></head><body>" +
            result + "".join(cards) + "</body></html>")


class TarragonaTests(unittest.TestCase):
    def setUp(self):
        self.day = date(2026, 10, 23)

    def test_one_correct_notice(self):
        total, rows = parse_index(fixture(self.day, [(365703, "Convocatòria de plaça d'administratiu")]), self.day)
        self.assertEqual(total, 1)
        self.assertEqual(rows[0]["registry"], "2026-36570")

    def test_three_pages_expected_from_total(self):
        entries = [(30000+i, "Convocatoria de plaza auxiliar") for i in range(20)]
        total, rows = parse_index(fixture(self.day, entries, 41), self.day)
        self.assertEqual(total, 41)
        self.assertEqual(len(rows), 20)
        with self.assertRaises(ProvincialCoverageError):
            parse_index(fixture(self.day, entries[:19], 41), self.day)

    def test_refuse_wrong_date_and_missing_count(self):
        html = fixture(self.day, [(36570, "Convocatoria de plaza")])
        with self.assertRaises(ProvincialCoverageError):
            parse_index(html, self.day - timedelta(days=1))
        with self.assertRaises(ProvincialCoverageError):
            parse_index(html.replace("Se ha encontrado 1 resultado", "Resultados desconocidos"), self.day)

    def test_detail_pdf_official(self):
        html = (f"<p>Fecha de publicación: 23/10/2026</p><p>Número de Registro: 2026-09890</p>"
                f"<a href='/bopt/web/anuncio/descargar-pdf/365703'>Descargar el anuncio</a>")
        pdf = extract_pdf(html, "365703", "2026-09890", self.day)
        self.assertEqual(pdf, ROOT + "/bopt/web/anuncio/descargar-pdf/365703")
        with self.assertRaises(ProvincialCoverageError):
            extract_pdf(html.replace("365703", "365704"), "365703", "2026-09890", self.day)

    def test_scan_checks_all_pages_and_details(self):
        entries = [(36500+i, "Convocatòria d'una plaça d'administratiu") for i in range(21)]
        base = fixture(self.day, entries[:20], 21)
        second = fixture(self.day, entries[20:], 21, first=21)
        def fake(url):
            if url.endswith("/2"): return second
            if "/anuncio/" in url: return (f"<p>Fecha de publicación: 23/10/2026</p>"
                f"<p>Número de Registro: 2026-{int(url.split('/')[6]):05d}</p>"
                f"<a href='/bopt/web/anuncio/descargar-pdf/{url.split('/')[6]}'>PDF</a>")
            return base
        result = scan_day(self.day, fake)
        self.assertEqual(result["total"], 21)
        self.assertEqual(result["pages"], 2)
        self.assertEqual(len(result["notices"]), 21)

    def test_audits_all_30_dates(self):
        end=self.day
        visited=[]
        def fake(day):
            visited.append(day)
            return {"date":day, "total":1 if day.weekday() < 5 else 0,
                    "pages":1, "notices":[]}
        result=build_history(30,end,fake)
        self.assertEqual(len(visited),30)
        self.assertEqual(len(result["historyCoverage"]["publicationDates"]) +
                         len(result["historyCoverage"]["nonPublicationDates"]),30)

    def test_failure_does_not_produce_partial_feed(self):
        def bad(day):
            raise ProvincialCoverageError("Portal no disponible")
        with self.assertRaises(ProvincialCoverageError):
            build_history(30,self.day,bad)


if __name__=="__main__":
    unittest.main()
