import unittest,sys
from pathlib import Path
from datetime import date,timedelta
from unittest import mock
from urllib.parse import urlsplit,parse_qs
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from defusedxml import ElementTree as ET
import rioja_bor
from provincial_common import ProvincialCoverageError

def workdays(first,last):
 d=first
 while d<=last:
  if d.weekday()<5:yield d
  d+=timedelta(days=1)

def fake_calendar(editions):
 """editions: {(año, mes): [(día, número), ...]} -> fetch() simulado de tipo=3."""
 def fetch(url,pdf=False,attempts=3):
  q=parse_qs(urlsplit(url).query)
  assert q["tipo"]==["3"]
  rows=editions.get((int(q["anio"][0]),int(q["mes"][0])),[])
  xml="<aplication status='ok'>"+"".join(
   f'<day value="{d.strftime("%d/%m/%Y")}" numero="{n}"/>' for d,n in rows)+"</aplication>"
  return ET.fromstring(xml)
 return fetch

def numbered(days,first):
 return [(d,first+i) for i,d in enumerate(days)]

class RiojaCalendarTest(unittest.TestCase):
 def test_months_cross_year(self):
  self.assertEqual(rioja_bor.months(date(2025,12,17),date(2026,1,15)),[(2025,12),(2026,1)])
  self.assertEqual(rioja_bor.months(date(2026,10,1),date(2026,10,30)),[(2026,10)])

 def test_year_change_numbering_restarts(self):
  dec=numbered([d for d in workdays(date(2025,12,1),date(2025,12,31)) if d!=date(2025,12,25)],233)
  jan=numbered([d for d in workdays(date(2026,1,2),date(2026,1,31)) if d!=date(2026,1,6)],1)
  with mock.patch.object(rioja_bor,"fetch",fake_calendar({(2025,12):dec,(2026,1):jan})):
   items=rioja_bor.calendar(date(2026,1,15))
  self.assertEqual(items[0][0],date(2025,12,17))
  self.assertEqual(items[-1],(date(2026,1,15),9))
  self.assertIn((date(2026,1,2),1),items)

 def test_gap_in_numbering_fails(self):
  oct_=numbered(list(workdays(date(2026,10,1),date(2026,10,30))),189)
  del oct_[5]
  with mock.patch.object(rioja_bor,"fetch",fake_calendar({(2026,10):oct_})):
   with self.assertRaises(ProvincialCoverageError):rioja_bor.calendar(date(2026,10,30))

 def test_stale_calendar_fails(self):
  oct_=numbered(list(workdays(date(2026,10,1),date(2026,10,22))),189)
  with mock.patch.object(rioja_bor,"fetch",fake_calendar({(2026,10):oct_})):
   with self.assertRaises(ProvincialCoverageError):rioja_bor.calendar(date(2026,10,30))

 def test_pdf_url_only_official_viewer(self):
  url=rioja_bor.pdf_url("42998127-1-PDF-580507")
  self.assertTrue(url.startswith("https://ias1.larioja.org/boletin/Bor_Boletin_visor_Servlet?"))
  with self.assertRaises(ProvincialCoverageError):rioja_bor.pdf_url("../x")

if __name__=="__main__":unittest.main()
