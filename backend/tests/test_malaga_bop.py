import sys,unittest
from pathlib import Path
from datetime import date
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from malaga_bop import calendar,parse_issue,pdf_from_edicto
from provincial_common import ProvincialCoverageError
D=date(2026,10,20)
HTML="""<html><h2>Sumario del día <time datetime="2026-10-20">20 de octubre de 2026</time></h2>
<table id="table_calendario"><tr><td><a href="?fecha=20-10-2026" title="BOP 202: Martes, 20 de Octubre de 2026"><time datetime="2026-10-20">20</time></a></td></tr></table>
<section><h3>AYUNTAMIENTO</h3><article><p><b>Marbella</b>. Convocatoria para cubrir 15 plazas de Técnico/a de Administración General. [<a href="edicto.php?edicto=20261020-04031-2026-01">Edicto 4031/2026</a>]</p></article>
<article><p><b>Ronda</b>. Modificación de crédito. [<a href="edicto.php?edicto=20261020-03998-2026-01">Edicto 3998/2026</a>]</p></article></section>
<section id="lista_pdf"><li><a href="verificacion.php?archivo=201026202.pdf">Boletín nº 202 en pdf</a></li></section>
</html>"""
DETAIL="""<title>Edicto 4031/2026 - BOPMA</title><h2>Edicto 4031/2026</h2>
<a href="verificacion.php?archivo=20261020-04031-2026-01.pdf">20261020-04031-2026-01.pdf</a>"""
class MalagaTest(unittest.TestCase):
 def test_calendar_and_data(self):
  self.assertEqual(calendar(HTML,D,D),{D:202})
  x=parse_issue(HTML,D,202,lambda url:DETAIL)
  self.assertEqual(x["read"],2)
  self.assertEqual(len(x["notices"]),1)
  self.assertEqual(x["notices"][0]["id"],"MA-20261020-04031")
  self.assertEqual(x["notices"][0]["entity"],"AYUNTAMIENTO · Marbella")
  self.assertEqual(x["notices"][0]["type"],"Plaza / oposición")
  self.assertEqual(x["notices"][0]["url"],"https://www.bopmalaga.es/verificacion.php?archivo=20261020-04031-2026-01.pdf")
 def test_reject_wrong_date_and_pdf(self):
  with self.assertRaises(ProvincialCoverageError):parse_issue(HTML,D,203,lambda url:DETAIL)
  with self.assertRaises(ProvincialCoverageError):parse_issue(HTML,date(2026,10,21),202,lambda url:DETAIL)
  with self.assertRaises(ProvincialCoverageError):
   pdf_from_edicto(DETAIL.replace("20261020-04031","20261019-04031"),D,4031,2026,"01")
if __name__=="__main__":unittest.main()
