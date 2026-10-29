import unittest,sys
from pathlib import Path
from datetime import date
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cyl_bocyl import parse_day,days_in_calendar
from provincial_common import ProvincialCoverageError
D=date(2026,10,29)
H="""<h2>Sumario BOCYL  nº 210/2026</h2><div id="resultados">
<h5>CONSEJERÍA DE SANIDAD</h5>
<p>RESOLUCIÓN por la que se convocan pruebas selectivas para 2 plazas de Administrativo</p>
<ul class="descargaBoletin"><li><a href="/boletines/2026/10/29/pdf/BOCYL-D-29102026-210-1.pdf">Descarga PDF</a></li></ul>
<h5>AYUNTAMIENTO DE SALAMANCA</h5><p>Información pública de aprobación de una ordenanza</p>
<ul class="descargaBoletin"><li><a href="/boletines/2026/10/29/pdf/BOCYL-D-29102026-210-2.pdf">PDF</a></li></ul>
</div>"""
class BOCYLTest(unittest.TestCase):
 def test_records(self):
  x=parse_day(H,D)
  self.assertEqual(x["number"],"210")
  self.assertEqual(x["read"],2)
  self.assertEqual(len(x["notices"]),1)
  self.assertEqual(x["notices"][0]["id"],"CY-20261029-1")
 def test_reject_wrong_date(self):
  with self.assertRaises(ProvincialCoverageError):parse_day(H,date(2026,10,28))
 def test_calendar(self):
  h='<a href="/boletin.do?fechaBoletin=29/10/2026">29</a>'
  self.assertEqual(days_in_calendar(h,D,D),{D})
if __name__=="__main__":unittest.main()
