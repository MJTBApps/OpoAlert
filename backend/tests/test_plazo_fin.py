import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from plazo_fin import easter, end_for, estimate_end, starts_with_own_bulletin  # noqa: E402
from plazos import add_end_dates, problem  # noqa: E402


class StartTest(unittest.TestCase):
    def test_own_bop(self):
        t = ("El plazo de presentación de las instancias será de veinte días hábiles contados a partir "
             "del día siguiente al de la publicación en el “Boletín Oficial de la Provincia”.")
        self.assertTrue(starts_with_own_bulletin("huesca_bop.json", t))

    def test_boe_in_a_bop_is_not_own(self):
        t = ("El plazo será de diez días hábiles, contados a partir del siguiente al de la publicación "
             "del extracto de la convocatoria en el Boletín Oficial del Estado.")
        self.assertFalse(starts_with_own_bulletin("convocatorias.json", t))
        self.assertTrue(starts_with_own_bulletin("boe.json", t))

    def test_two_bulletins_named(self):
        t = ("Plazo de veinte días naturales a contar desde el día siguiente a la publicación en el BOP "
             "y en el Boletín Oficial del Estado.")
        self.assertFalse(starts_with_own_bulletin("toledo_bop.json", t))

    def test_last_publication(self):
        t = ("El termini serà de vint dies hàbils comptats a partir de l’endemà de la darrera publicació "
             "de l’anunci al BOPB.")
        self.assertFalse(starts_with_own_bulletin("barcelona_bop.json", t))

    def test_this_notice_without_bulletin(self):
        t = ("Las solicitudes se presentarán en el plazo de diez días naturales a contar desde el día "
             "siguiente a la publicación de este anuncio.")
        self.assertTrue(starts_with_own_bulletin("zamora_bop.json", t))

    def test_cut_quote_or_unknown_feed(self):
        t = ("…plazo de diez días hábiles a contar desde el día siguiente a la publicación de este anuncio "
             "en el Boletín Oficial de…")
        self.assertFalse(starts_with_own_bulletin("ciudad_real_bop.json", t))
        ok = "Plazo de diez días hábiles desde el día siguiente a la publicación de este anuncio."
        self.assertFalse(starts_with_own_bulletin("barcelona.json", ok))  # CIDO: catálogo, no boletín

    def test_other_regional_bulletin(self):
        t = ("El termini de presentació de sol·licituds és de vint dies hàbils, comptats des de l’endemà de "
             "la publicació de la convocatòria en el Diari Oficial de la Generalitat de Catalunya.")
        self.assertFalse(starts_with_own_bulletin("girona_bop.json", t))
        self.assertTrue(starts_with_own_bulletin("cataluna_dogc.json", t))


class EndTest(unittest.TestCase):
    def test_easter(self):
        self.assertEqual(easter(2026), date(2026, 4, 5))
        self.assertEqual(easter(2027), date(2027, 3, 28))

    def test_working_days_skip_weekends_and_national_holidays(self):
        self.assertEqual(estimate_end(date(2026, 11, 7), 10, "hábiles"), date(2026, 11, 20))
        # 8/12 es fiesta nacional; 6/12 cae en domingo.
        self.assertEqual(estimate_end(date(2026, 11, 13), 20, "hábiles"), date(2026, 12, 14))
        # Viernes Santo 2027: 26/3.
        self.assertEqual(estimate_end(date(2027, 3, 22), 4, "hábiles"), date(2027, 3, 29))

    def test_calendar_days(self):
        self.assertEqual(estimate_end(date(2026, 11, 12), 20, "naturales"), date(2026, 12, 2))

    def test_rejects_odd_values(self):
        self.assertIsNone(estimate_end(date(2026, 1, 1), 0, "hábiles"))
        self.assertIsNone(estimate_end(date(2026, 1, 1), 10, "meses"))

    def test_end_for_and_plazos_file(self):
        item = {"days": 10, "kind": "naturales", "page": 1,
                "text": "Plazo de diez días naturales desde el día siguiente a la publicación de este anuncio."}
        self.assertEqual(end_for("soria_bop.json", item, date(2026, 11, 20)), "2026-11-30")
        self.assertIsNone(end_for("soria_bop.json", item, None))
        items = {"https://x.es/a.pdf": dict(item, hasta="2000-01-01")}
        add_end_dates("soria_bop.json", items, {"https://x.es/a.pdf": date(2026, 11, 20)})
        self.assertEqual(items["https://x.es/a.pdf"]["hasta"], "2026-11-30")
        self.assertIsNone(problem("https://x.es/a.pdf", items["https://x.es/a.pdf"], {"https://x.es/a.pdf"}))
        self.assertEqual(problem("https://x.es/a.pdf", dict(item, hasta="30/11"), {"https://x.es/a.pdf"}),
                         "fecha estimada no válida")


if __name__ == "__main__":
    unittest.main()
