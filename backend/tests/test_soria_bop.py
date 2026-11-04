import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import soria_bop  # noqa: E402

APP_ID = re.compile(r"SR-\d{4}-\d{1,6}")  # Province.kt


class NumeroDeAnuncio(unittest.TestCase):
    def test_numero_normal(self):
        self.assertEqual(soria_bop.notice_number("2887"), 2887)

    def test_numero_con_letra(self):
        # BOP de Soria del 04/11/2026: anuncios «2087a» y «2087b».
        self.assertEqual(soria_bop.notice_number("2087a"), 208701)
        self.assertEqual(soria_bop.notice_number("2087b"), 208702)
        self.assertTrue(APP_ID.fullmatch(f"SR-2026-{soria_bop.notice_number('9999z')}"))

    def test_enlace_con_letra(self):
        path = ("/index.php/mod.documentos/mem.descargar/"
                "fichero.documentos_2087b_76dde3f8%232E%23pdf")
        self.assertEqual(soria_bop._DOC.fullmatch(path)[1], "2087b")


if __name__ == "__main__":
    unittest.main()
