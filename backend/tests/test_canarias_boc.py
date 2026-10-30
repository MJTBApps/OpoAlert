import unittest,sys
from pathlib import Path
from datetime import date,timedelta
from bs4 import BeautifulSoup
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import canarias_boc as boc
from provincial_common import ProvincialCoverageError
WEEK=["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"]
def weekdays(a,b):
 d=a
 while d<=b:
  if d.weekday()<5:yield d
  d+=timedelta(days=1)
def year_page(year,days,skip=()):
 links="".join(f'<a href="/boc/{year}/{n:03}/index.html">BOC Nº {n} - {d.day} de {boc.MONTH_NAME[d.month]} de {year} - {WEEK[d.weekday()]}</a>'
               for n,d in enumerate(days,1) if n not in skip)
 return f"<html><body><a href='/boc/archivo/'>Archivo</a>{links}</body></html>"
class BocTest(unittest.TestCase):
 def setUp(self):
  self.pages={boc.SOURCE:"<a href='./2026/'>2026</a><a href='./2025/'>2025</a>"}
  self.old=boc.fetch
  boc.fetch=lambda url,pdf=False,retries=3:None if pdf else BeautifulSoup(self.pages[url],"html.parser")
 def tearDown(self):boc.fetch=self.old
 def test_calendar_crosses_year_and_restarts_numbering(self):
  d25=list(weekdays(date(2025,1,2),date(2025,12,31)));d26=list(weekdays(date(2026,1,2),date(2026,1,20)))
  self.pages[boc.SOURCE+"2025/"]=year_page(2025,d25);self.pages[boc.SOURCE+"2026/"]=year_page(2026,d26)
  rows=boc.calendar(date(2025,12,17),date(2026,1,15))
  self.assertEqual(rows[0],(len(d25)-10,date(2025,12,17)))
  self.assertEqual(rows[-1],(10,date(2026,1,15)))
  self.assertIn((1,date(2026,1,2)),rows)
 def test_gap_in_year_archive_fails(self):
  d26=list(weekdays(date(2026,1,2),date(2026,10,30)))
  self.pages[boc.SOURCE+"2026/"]=year_page(2026,d26,skip={200})
  with self.assertRaises(ProvincialCoverageError):boc.calendar(date(2026,10,1),date(2026,10,30))
 def test_missing_previous_year_fails(self):
  self.pages[boc.SOURCE]="<a href='./2026/'>2026</a>"
  self.pages[boc.SOURCE+"2026/"]=year_page(2026,list(weekdays(date(2026,1,2),date(2026,1,20))))
  with self.assertRaises(ProvincialCoverageError):boc.calendar(date(2025,12,17),date(2026,1,15))
 def test_issue_uses_issuer_heading(self):
  url="https://www.gobiernodecanarias.org/boc/2025/256/index.html"
  self.pages[url]="""<h2>BOC Nº 256. Lunes 29 de diciembre de 2025</h2><h4></h4>
   <h5>Universidad de La Laguna</h5>
   <li class="justificado_boc"><a href="https://sede.gobiernodecanarias.org/boc/boc-a-2025-256-4419.pdf">RESOLUCIÓN por la que se convoca concurso-oposición para cubrir una plaza de Técnico</a></li>
   <h5>Consejería de Sanidad</h5>
   <li class="justificado_boc"><a href="https://sede.gobiernodecanarias.org/boc/boc-a-2025-256-4420.pdf">ORDEN por la que se aprueba la modificación de un reglamento sanitario</a></li>"""
  d=boc.issue((256,date(2025,12,29)))
  self.assertEqual(d["read"],2)
  self.assertEqual([n["id"] for n in d["notices"]],["IC-2025-4419"])
  self.assertEqual(d["notices"][0]["entity"],"Universidad de La Laguna")
 def test_issue_wrong_date_fails(self):
  url="https://www.gobiernodecanarias.org/boc/2026/218/index.html"
  self.pages[url]="<h2>BOC Nº 218. Jueves 29 de octubre de 2026</h2>"
  with self.assertRaises(ProvincialCoverageError):boc.issue((218,date(2026,10,30)))
if __name__=="__main__":unittest.main()
