import unittest,sys
from pathlib import Path
from datetime import date
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from avila_bop import issues,parse
from provincial_common import ProvincialCoverageError
class AvilaTest(unittest.TestCase):
 def test_parse(self):
  html="""<h3>Ficha del boletín [ 28/10/2026 ]</h3>
   <div>B.O.P. 205/26 Completo</div>
   <div class="listado"><span>AYUNTAMIENTO DE ÁVILA</span>
   <ul><li><p class="num">nº 2162/26</p><p><a href="https://www.diputacionavila.es/bops/2026/28-10-2026/28-10-2026_216226.pdf">Convocatoria de una plaza de Administrativo mediante oposición</a></p></li>
   <li><p class="num">nº 2163/26</p><p><a href="https://www.diputacionavila.es/bops/2026/28-10-2026/28-10-2026_216326.pdf">Modificación de la ordenanza fiscal</a></p></li></ul></div>"""
  d=parse(html,date(2026,10,28))
  self.assertEqual(d["number"],"205")
  self.assertEqual(d["read"],2)
  self.assertEqual(len(d["notices"]),1)
  self.assertEqual(d["notices"][0]["id"],"AV-2026-2162")
 def test_reject_invalid(self):
  with self.assertRaises(ProvincialCoverageError):parse("<h3>Ficha del boletín [ 27/10/2026 ]</h3>",date(2026,10,28))
if __name__=="__main__":unittest.main()
