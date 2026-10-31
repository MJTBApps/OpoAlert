"""La app iOS valida los feeds con las mismas reglas que Android.

Su lista de fuentes (ios/OpoAlertCore/Sources/OpoAlertCore/Fuentes.generated.swift)
se genera desde Province.kt y SourceCatalog.kt. Si se cambia una fuente en
Android hay que volver a generarla: python scripts/generar_fuentes_ios.py
"""
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class FuentesIosTest(unittest.TestCase):
    def test_fuentes_ios_al_dia_con_android(self):
        result = subprocess.run([sys.executable, str(ROOT / "scripts/generar_fuentes_ios.py"), "--check"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_mismas_fuentes_que_province_kt(self):
        swift = (ROOT / "ios/OpoAlertCore/Sources/OpoAlertCore/Fuentes.generated.swift").read_text(encoding="utf-8")
        kotlin = (ROOT / "app/src/main/java/es/opoalert/app/Province.kt").read_text(encoding="utf-8")
        self.assertEqual(swift.count("Source("), kotlin.count("Regex("))


if __name__ == "__main__":
    unittest.main()
