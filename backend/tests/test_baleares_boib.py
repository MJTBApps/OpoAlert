import unittest,sys
from pathlib import Path
from datetime import date
from unittest import mock
from bs4 import BeautifulSoup
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import baleares_boib as ib
from provincial_common import ProvincialCoverageError

def month_html(year,links):
 a="".join(f'<a href="/eboibfront/es/{y}/{uid}/">{t}</a>' for y,uid,t in links)
 return BeautifulSoup(f'<h1>Boletín Oficial de las Illes Balears</h1><a href="/eboibfront/es/{year}/99999/?lang=es">Último número</a>{a}',"html.parser")

class BaleresTest(unittest.TestCase):
 def test_months_cross_year(self):
  self.assertEqual(list(ib.months_between(date(2025,12,17),date(2026,1,15))),[(2025,12),(2026,1)])
  self.assertEqual(list(ib.months_between(date(2026,10,1),date(2026,10,30))),[(2026,10)])
 def test_month_url_is_zero_based_and_extras(self):
  html=month_html(2026,[(2026,12336,"1"),(2026,12339,"1*E"),(2026,12352,"29")])
  with mock.patch.object(ib,"html_page",return_value=html) as page:
   got=ib.parse_month(2026,10)
  page.assert_called_once_with(ib.ROOT+"/2026/mes/9")
  self.assertEqual(got,{12336:(date(2026,10,1),False),12339:(date(2026,10,1),True),12352:(date(2026,10,29),False)})
 def test_month_rejects_other_year(self):
  html=month_html(2026,[(2025,12336,"1")])
  with mock.patch.object(ib,"html_page",return_value=html):
   with self.assertRaises(ProvincialCoverageError):ib.parse_month(2026,1)
 def test_calendar_window(self):
  months={(2025,12):{1:(date(2025,12,16),False),2:(date(2025,12,18),False)},
          (2026,1):{3:(date(2026,1,15),False),4:(date(2026,1,17),False)}}
  with mock.patch.object(ib,"parse_month",side_effect=lambda y,m:months[(y,m)]):
   got=ib.parse_calendar(date(2025,12,17),date(2026,1,15))
  self.assertEqual([uid for uid,_ in got],[2,3])
 def test_edict_year(self):
  self.assertEqual(ib.edict_year(date(2026,1,3),14887),2025)
  self.assertEqual(ib.edict_year(date(2026,1,8),34),2026)
  self.assertEqual(ib.edict_year(date(2026,10,29),10800),2026)
 def test_pdf_urls(self):
  ib.validate_pdf_url("https://www.caib.es/eboibfront/eli/es-ib/o/2026/10/23/39/dof/spa/pdf",138,date(2026,10,29))
  ib.validate_pdf_url("https://www.caib.es/eboibfront/pdf/es/not/_L7ovkKJKZ_65EH7gdCpj_QxuzA5mQFLugmHggj8IcM=",120,date(2026,9,26))
  ib.validate_pdf_url("https://www.caib.es/eboibfront/pdf/es/2025/2/1209817",2,date(2026,1,3))
  for url,num,day in (("https://www.caib.es/eboibfront/pdf/es/2025/2/1209817",3,date(2026,1,3)),
                      ("https://www.caib.es/eboibfront/pdf/es/2025/120/1209817",120,date(2026,9,26)),
                      ("https://example.com/eboibfront/pdf/es/2026/2/1209817",2,date(2026,1,3))):
   with self.assertRaises(ProvincialCoverageError):ib.validate_pdf_url(url,num,day)
 def test_no_fixed_dates(self):
  src=Path(ib.__file__).read_text(encoding="utf-8")
  self.assertNotRegex(src,r"date\(20\d\d")
  self.assertNotIn("/2026/",src)

if __name__=="__main__":unittest.main()
