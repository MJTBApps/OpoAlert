"""Seguimiento de favoritas: parejas reales revisadas a mano (las mismas que comprueban Android e iOS)."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import seguimiento  # noqa: E402

CASES = json.loads((Path(__file__).with_name("seguimiento_casos.json")).read_text(encoding="utf-8"))["cases"]


def item(data):
    notice = {k: data[k] for k in ("title", "entity", "date", "url")}
    return seguimiento.item(notice, data["source"], data.get("cido", False), data.get("extract"))


class SeguimientoTest(unittest.TestCase):
    def test_casos_compartidos(self):
        self.assertGreaterEqual(len(CASES), 20)
        for case in CASES:
            with self.subTest(case["name"]):
                fav, cand = item(case["favorite"]), item(case["candidate"])
                self.assertEqual(seguimiento.is_followup(fav, cand), case["followUp"])
                if "step" in case:
                    self.assertEqual(cand["step"], case["step"])

    def test_sin_masculino_ni_femenino(self):
        self.assertEqual(seguimiento.job_key("una plaza de trabajador/a social"),
                         seguimiento.job_key("una plaza de trabajadora social"))
        self.assertEqual(seguimiento.job_key("tres plazas de Auxiliares Administrativos"),
                         seguimiento.job_key("una plaza de auxiliar administrativo/a"))

    def test_numero_de_plazas(self):
        self.assertEqual(seguimiento.plazas_count("de dues places de tècnic/a"), 2)
        self.assertEqual(seguimiento.plazas_count("Una (1) plaza de Traductor/a"), 1)
        self.assertIsNone(seguimiento.plazas_count("bolsa de trabajo de conserje"))

    def test_solo_organismos_locales(self):
        self.assertEqual(seguimiento.local_org({"entity": "Ayuntamiento de Colmenar Viejo (Madrid)", "title": ""}),
                         ("ayto", "colmenar viejo"))
        self.assertEqual(seguimiento.local_org({"entity": "AJUNTAMENT DE LA POBLA DE SEGUR (POBLA DE SEGUR, LA)", "title": ""}),
                         ("ayto", "pobla segur"))
        self.assertIsNone(seguimiento.local_org({"entity": "MINISTERIO DE HACIENDA", "title": ""}))
        self.assertIsNone(seguimiento.local_org({"entity": "Universidad de Málaga", "title": ""}))


if __name__ == "__main__":
    unittest.main()
