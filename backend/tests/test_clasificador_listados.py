import sys, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from provincial_common import classify  # noqa: E402


class ListadosTemporalesTest(unittest.TestCase):
    def test_listados_de_aspirantes_para_necesidades_temporales(self):
        # BOP Cádiz 221/2026, anuncio 408.364.
        t = ("Área de Función Pública y Recursos Humanos. Convocatoria para la constitución de "
             "listados de 50 personas aspirantes a la especialidad/categoría de TAE Economista, "
             "para atender necesidades temporales de la Diputación Provincial.")
        self.assertEqual(classify(t), "Bolsa de trabajo")

    def test_listas_de_admitidos_no_cuentan(self):
        t = "Convocatoria para necesidades temporales: lista provisional de admitidos y excluidos"
        self.assertIsNone(classify(t))


if __name__ == "__main__":
    unittest.main()
