import unittest,sys
from pathlib import Path
from datetime import date
from unittest import mock
from bs4 import BeautifulSoup
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import alava_botha as ar
from provincial_common import ProvincialCoverageError
def cal_html(month,year,days,untitled=None,head=None):
 links="".join(f'<a href="SGBO5001.aspx?FechaBotha={d:02d}/{month:02d}/{year}" title="Boletín Nº{n}">{d}</a>' for d,n in days)
 if untitled:links+=f'<a href="SGBO5001.aspx?FechaBotha={untitled:02d}/{month:02d}/{year}">{untitled}</a>'
 return BeautifulSoup(f"<h2>Consulta</h2>{'<h2>'+head+'</h2>' if head else ''}{links}","html.parser")
class AlavaTest(unittest.TestCase):
 def test_sumario(self):
  s=BeautifulSoup("<h2>Sumario del Boletin nº 125 del viernes, 30 de octubre de 2026</h2>","html.parser")
  self.assertEqual(ar.sumario(s),(125,date(2026,10,30)))
  self.assertIsNone(ar.sumario(BeautifulSoup("<h2>Consulta</h2>","html.parser")))
 def test_calendar_untitled_latest(self):
  s=cal_html(10,2026,[(26,123),(28,124)],untitled=30)
  self.assertEqual(ar.calendar(s,date(2026,10,15)),{date(2026,10,26):123,date(2026,10,28):124,date(2026,10,30):None})
 def test_archive_year_change(self):
  dec=cal_html(12,2025,[(17,143),(19,144),(22,145),(26,146),(29,147)])
  jan=cal_html(1,2026,[(2,1),(5,2),(7,3),(9,4),(12,5),(14,6),(16,7)])
  pages={"17/12/2025":dec,"15/01/2026":jan}
  with mock.patch.object(ar,"fetch",side_effect=lambda u:pages[u.split("=")[-1]]):
   entries=ar.archive(date(2026,1,15))
  self.assertEqual([n for _,n in entries],[143,144,145,146,147,1,2,3,4,5,6])
 def test_archive_gap_fails(self):
  oct_=cal_html(10,2026,[(2,113),(5,114),(9,116),(12,117),(14,118),(16,119),(19,120),(21,121),(23,122),(26,123),(28,124),(30,125)])
  with mock.patch.object(ar,"fetch",return_value=oct_):
   with self.assertRaises(ProvincialCoverageError):ar.archive(date(2026,10,30))
 def test_parse_sumario(self):
  html="""<h2>Sumario del Boletin nº 1 del viernes, 2 de enero de 2026</h2>
  <div class="titulo_bloque_resultados">AYUNTAMIENTO DE VITORIA-GASTEIZ</div>
  <table><tr><td><span id="x_lblAnuResumen"><a>Convocatoria del proceso selectivo de dos plazas de agente</a></span>
  <a id="x_panPdf" href="../Boletines/2026/001/2026_001_03938_C.pdf">pdf</a></td></tr>
  <tr><td><span id="y_lblAnuResumen"><a>Ordenanza fiscal</a></span>
  <a id="y_panPdf" href="../Boletines/2026/001/2026_001_03903_C.pdf">pdf</a></td></tr></table>"""
  d=ar.parse_sumario(BeautifulSoup(html,"html.parser"),date(2026,1,2),1)
  self.assertEqual(d["read"],2)
  self.assertEqual([n["id"] for n in d["notices"]],["AR-2026-03938"])
  with self.assertRaises(ProvincialCoverageError):
   ar.parse_sumario(BeautifulSoup(html,"html.parser"),date(2026,1,2),2)
if __name__=="__main__":unittest.main()
