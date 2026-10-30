"""Pruebas sin red del lector del BOP de Jaén (backend/jaen_bop.py)."""
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import jaen_bop as ja  # noqa: E402
from provincial_common import ProvincialCoverageError  # noqa: E402

BASE = "https://bop.dipujaen.es/descargarws.dip"
WEEKDAYS = ("Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo")


def edict_link(day, number, year, supl=0):
    return (f"{BASE}?fechaBoletin={day.isoformat()}&numeroEdicto={number}&boletinSuplemento={supl}"
            f"&ejercicioBop={day.year}&tipo=bop&anioExpedienteEdicto={year}")


def article(day, number, year, title, supl=0, extra=""):
    return (f"<article><p class='edicto'>{title}\t\t\t</p>\t\t\t<p style='text-align: center'><a\n"
            f"\t\thref='{edict_link(day, number, year, supl)}' target='_blank' class='enlace'>"
            f"<img alt='Fichero Edicto BOP-{year}-{number}.pdf'> Edicto</a></p>{extra}</article>")


def day_page(day, number, body, header_day=None, sumario_number=None):
    """Página del BOP tal como la sirve el portal (codificada en ISO-8859-1)."""
    hd = header_day or day
    n2 = sumario_number or number
    head = (f"<div><p class='cabeceraSumario'><span>Bolet&iacute;n Nº: {number}</span>"
            f"{WEEKDAYS[hd.weekday()]}, {hd.day:02d} de {ja.MONTHS[hd.month - 1]} de {hd.year}</p></div>"
            f"<div id='ficheroCompleto'><a href='{BASE}?fechaBoletin={day.isoformat()}&ejercicioBop={day.year}"
            f"&numeroBoletin={number}&boletinSuplemento=0&tipo=bopCompleto'>Boletín completo</a>"
            f"<a href='{BASE}?fechaBoletin={day.isoformat()}&ejercicioBop={day.year}"
            f"&numeroBoletin={n2}&boletinSuplemento=0&tipo=bopSumario'>Sumario</a></div>")
    html = (f"<html><head><title>BOP Jaén</title></head><body><main>{head}"
            f"<div id='sumarioBoletin'>{body}</div></main></body></html>")
    return html.encode("latin-1")


def no_bulletin(day):
    return (f"<html><body><main><div id=\"noBoletin\"><h2>No hay ningún boletín publicado para el día "
            f"{day:%d-%m-%Y}</h2></div></main></body></html>").encode("latin-1")


DAY = date(2026, 10, 30)
SAMPLE_BODY = (
    "<section><p class='seccion'><a name='1'>Administración Local</a></p>"
    "<p class='subseccion'>DIPUTACIÓN PROVINCIAL DE JAÉN</p>"
    "<p class='departamento'>Área de Recursos Humanos.</p>"
    + article(DAY, 5073, 2026, "Res. núm. 3449, por la que se convoca y aprueban las Bases para la "
              "provisión de una plaza de Técnico de Administración General.")
    + "<p class='subseccion'>AYUNTAMIENTO DE ALCAUDETE (JAÉN)</p>"
    + article(DAY, 5105, 2026, "Listado definitivo de admitidos/as y fecha de examen de la convocatoria "
              "de una plaza de Operario de Cementerio.")
    + article(DAY, 6244, 2025, "Convocatoria para la constitución de una bolsa de trabajo de Auxiliar "
              "Administrativo.", extra="<p style='color:red'>Modificado por el edicto número: "
              "<a class='enlace' href='https://bop.dipujaen.es/edicto/124177/N'>2026/4706</a></p>")
    + "<p class='subseccion'>AYUNTAMIENTO DE MANCHA REAL (JAÉN)</p>"
    + article(DAY, 5101, 2026, "Convocatoria y plazo de presentación de solicitudes para la adjudicación "
              "de puestos vacantes en el mercadillo de esta localidad.")
    + "</section><section><p class='seccion'><a name='2'>Anuncios no Oficiales</a></p>"
    + article(DAY, 5200, 2026, "Junta general ordinaria de la comunidad de regantes.")
    + "</section>")


class ParseDayTest(unittest.TestCase):
    def test_reads_all_edicts_with_entity_and_iso_8859_1(self):
        issue = ja.parse_day(ja.decode(day_page(DAY, 213, SAMPLE_BODY)), DAY)
        self.assertEqual(issue["number"], 213)
        self.assertEqual(len(issue["edicts"]), 5)
        first = issue["edicts"][0]
        self.assertEqual(first["entity"], "DIPUTACIÓN PROVINCIAL DE JAÉN. Área de Recursos Humanos")
        self.assertEqual((first["year"], first["number"]), (2026, 5073))
        self.assertTrue(first["url"].startswith(BASE + "?fechaBoletin=2026-10-30&numeroEdicto=5073"))
        # Al cambiar de organismo se olvida el departamento.
        self.assertEqual(issue["edicts"][1]["entity"], "AYUNTAMIENTO DE ALCAUDETE (JAÉN)")
        # Edicto con expediente del año anterior: el año es el del expediente.
        self.assertEqual((issue["edicts"][2]["year"], issue["edicts"][2]["number"]), (2025, 6244))
        # Sección sin organismo: la entidad es la sección.
        self.assertEqual(issue["edicts"][4]["entity"], "Anuncios no Oficiales")
        self.assertIn("tipo=bopSumario", issue["sumario"])

    def test_day_without_bulletin(self):
        d = date(2026, 10, 25)
        self.assertIsNone(ja.parse_day(ja.decode(no_bulletin(d)), d))

    def test_other_date_in_header_fails(self):
        html = ja.decode(day_page(DAY, 213, SAMPLE_BODY, header_day=DAY - timedelta(days=1)))
        with self.assertRaises(ProvincialCoverageError):
            ja.parse_day(html, DAY)

    def test_sumario_link_of_other_issue_fails(self):
        with self.assertRaises(ProvincialCoverageError):
            ja.parse_day(ja.decode(day_page(DAY, 213, SAMPLE_BODY, sumario_number=212)), DAY)

    def test_supplement_stops_reader(self):
        body = "<section><p class='seccion'>Administración Local</p>" + article(DAY, 1, 2026, "X", supl=1) + "</section>"
        with self.assertRaisesRegex(ProvincialCoverageError, "suplemento"):
            ja.parse_day(ja.decode(day_page(DAY, 213, body)), DAY)

    def test_duplicate_edict_fails(self):
        body = ("<section><p class='seccion'>Administración Local</p><p class='subseccion'>AYTO</p>"
                + article(DAY, 7, 2026, "A") + article(DAY, 7, 2026, "B") + "</section>")
        with self.assertRaises(ProvincialCoverageError):
            ja.parse_day(ja.decode(day_page(DAY, 213, body)), DAY)

    def test_foreign_pdf_link_fails(self):
        body = ("<section><p class='seccion'>Administración Local</p><p class='subseccion'>AYTO</p>"
                + article(DAY, 7, 2026, "A").replace("https://bop.dipujaen.es", "https://evil.example")
                + "</section>")
        with self.assertRaises(ProvincialCoverageError):
            ja.parse_day(ja.decode(day_page(DAY, 213, body)), DAY)

    def test_antibot_page_is_not_bypassed(self):
        with self.assertRaisesRegex(ProvincialCoverageError, "anti-robots"):
            ja.parse_day("<html><body>Please complete the CAPTCHA</body></html>", DAY)


class ClassificationTest(unittest.TestCase):
    def test_kind(self):
        self.assertEqual(ja.kind("Bases y convocatoria para la provisión de 1 plaza de Técnico/a Superior."),
                         "Plaza / oposición")
        self.assertEqual(ja.kind("Convocatoria para la constitución de una Bolsa de trabajo de Formadores."),
                         "Bolsa de trabajo")
        for title in ("Listado definitivo de admitidos/as y fecha de examen de la convocatoria de una plaza",
                      "Convocatoria para la adjudicación de puestos vacantes en el mercadillo",
                      "Aprobación definitiva del Presupuesto 2026, con sus Bases de Ejecución y Plantilla de personal",
                      "Resolución por la que se nombra funcionarios de carrera, en la plaza de Técnico",
                      "Aprobación inicial del Reglamento de las Bolsas de Trabajo de Personal Laboral"):
            self.assertIsNone(ja.kind(title), title)


def make_pdf(text):
    import pymupdf
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((40, 60), text, fontsize=9)
    data = doc.tobytes()
    doc.close()
    return data


class SumarioPdfTest(unittest.TestCase):
    def setUp(self):
        self.page = day_page(DAY, 213, SAMPLE_BODY)
        codes = "\n".join(f"BOP-{y}-{n}" for y, n in ((2026, 5073), (2026, 5105), (2025, 6244), (2026, 5101), (2026, 5200)))
        self.good = make_pdf(f"Numero 213\nViernes, 30 de octubre de 2026\nPag. 16208\n{codes}")

    def fake_fetch(self, pdf):
        def fetch(url, **kw):
            if "/bop/" in url:
                return self.page, {"Content-Type": "text/html; charset=iso-8859-1"}
            return pdf, {"Content-Type": "application/pdf"}
        return fetch

    def test_html_and_pdf_agree(self):
        with mock.patch.object(ja, "fetch", self.fake_fetch(self.good)), mock.patch.object(ja, "PAUSE", 0):
            issue = ja.read_day(DAY)
        self.assertEqual(len(issue["edicts"]), 5)

    def test_missing_edict_in_html_fails(self):
        pdf = make_pdf("Numero 213\nViernes, 30 de octubre de 2026\nBOP-2026-5073\nBOP-2026-5105\n"
                       "BOP-2025-6244\nBOP-2026-5101\nBOP-2026-5200\nBOP-2026-5300")
        with mock.patch.object(ja, "fetch", self.fake_fetch(pdf)), mock.patch.object(ja, "PAUSE", 0):
            with self.assertRaisesRegex(ProvincialCoverageError, "no coinciden"):
                ja.read_day(DAY)

    def test_pdf_of_other_issue_fails(self):
        pdf = make_pdf("Numero 212\nJueves, 29 de octubre de 2026\nBOP-2026-5073")
        with mock.patch.object(ja, "fetch", self.fake_fetch(pdf)), mock.patch.object(ja, "PAUSE", 0):
            with self.assertRaises(ProvincialCoverageError):
                ja.read_day(DAY)


def fake_archive(end, first_number=100, skip=(), weekend=True, reset_on=None):
    """Lector falso: boletín de lunes a viernes con numeración seguida."""
    issues = {}
    n = first_number
    d = end - timedelta(days=45)
    while d <= end:
        if d.weekday() < 5 or not weekend:
            if reset_on and d == reset_on:
                n = 1
            if n not in skip:
                title = "Bases y convocatoria para la provisión de una plaza de Auxiliar Administrativo."
                issues[d] = {"day": d, "number": n, "sumario": "",
                             "edicts": [{"year": d.year, "number": 9000 + n, "title": title,
                                         "entity": "AYUNTAMIENTO DE PRUEBA (JAÉN)", "section": "Administración Local",
                                         "url": edict_link(d, 9000 + n, d.year)},
                                        {"year": d.year, "number": 19000 + n, "title": "Padrón de agua.",
                                         "entity": "AYUNTAMIENTO DE PRUEBA (JAÉN)", "section": "Administración Local",
                                         "url": edict_link(d, 19000 + n, d.year)}]}
            n += 1
        d += timedelta(days=1)
    return lambda day: issues.get(day)


class AuditTest(unittest.TestCase):
    def setUp(self):
        self.checked = []

    def pdf_check(self, url, year, number):
        self.checked.append((year, number))

    def test_dynamic_window_and_counters(self):
        end = date(2026, 10, 30)
        feed = ja.audit(today=end, reader=fake_archive(end), pdf_check=self.pdf_check)
        hist = feed["historyCoverage"]
        self.assertEqual(hist["rangeStart"], "2026-10-01")
        self.assertEqual(hist["rangeEnd"], "2026-10-30")
        self.assertEqual(feed["province"], "Jaén")
        self.assertEqual(feed["source"], "https://bop.dipujaen.es/")
        self.assertEqual(hist["issuesRead"], 22)
        self.assertEqual(feed["coverage"]["announcementsRead"], 44)
        self.assertEqual(len(feed["notices"]), 22)
        self.assertEqual(len(self.checked), 22)
        self.assertRegex(feed["notices"][0]["id"], r"^JA-\d{4}-\d{1,6}$")
        self.assertTrue(all(n["url"].startswith(BASE) for n in feed["notices"]))

    def test_numbering_gap_fails(self):
        end = date(2026, 10, 30)
        with self.assertRaisesRegex(ProvincialCoverageError, "numeración"):
            ja.audit(today=end, reader=fake_archive(end, skip={120}), pdf_check=self.pdf_check)

    def test_gap_with_previous_issue_fails(self):
        end = date(2026, 10, 30)
        reader = fake_archive(end)
        start = end - timedelta(days=29)

        def without_previous(day):
            return None if start - timedelta(days=10) <= day < start else reader(day)
        with self.assertRaises(ProvincialCoverageError):
            ja.audit(today=end, reader=without_previous, pdf_check=self.pdf_check)

    def test_new_year_restarts_numbering(self):
        end = date(2026, 1, 15)
        feed = ja.audit(today=end, reader=fake_archive(end, reset_on=date(2026, 1, 1)), pdf_check=self.pdf_check)
        self.assertIn("1", feed["historyCoverage"]["bulletins"])
        self.assertEqual(feed["historyCoverage"]["rangeStart"], "2025-12-17")

    def test_duplicate_edict_across_issues_fails(self):
        end = date(2026, 10, 30)
        reader = fake_archive(end)

        def dup(day):
            x = reader(day)
            if x and day == end:
                x = dict(x, edicts=x["edicts"] + [dict(reader(end - timedelta(days=1))["edicts"][0])])
            return x
        with self.assertRaisesRegex(ProvincialCoverageError, "repetido"):
            ja.audit(today=end, reader=dup, pdf_check=self.pdf_check)

    def test_stale_archive_fails(self):
        end = date(2026, 10, 30)
        reader = fake_archive(end)

        def stale(day):
            return None if day > end - timedelta(days=6) else reader(day)
        with self.assertRaises(ProvincialCoverageError):
            ja.audit(today=end, reader=stale, pdf_check=self.pdf_check)


if __name__ == "__main__":
    unittest.main()
