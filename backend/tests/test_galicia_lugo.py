import unittest,sys
from pathlib import Path
from datetime import date
from unittest import mock
from bs4 import BeautifulSoup
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import galicia_lugo as lu
from provincial_common import ProvincialCoverageError
U="https://deputacionlugo.gal/gl/node/1"
class LugoTest(unittest.TestCase):
 def test_index_january_numbers(self):
  html="""<table><tr><td>11</td><td><a href="/gl/node/83800">BOP DE 15/01/2026</a></td><td>15/01/2026</td></tr>
  <tr><td>299</td><td><a href="/gl/node/83740">BOP DE 31/12/2025</a></td><td>31/12/2025</td></tr></table>"""
  rows=lu.parse_index(BeautifulSoup(html,"html.parser"),lu.SOURCE)
  self.assertEqual([(d,n) for d,n,_ in rows],[(date(2026,1,15),11),(date(2025,12,31),299)])
 def test_fix_numbers_confirmed_by_pdf(self):
  items=[(date(2026,10,1),225,U),(date(2026,10,2),226,U),(date(2026,10,3),225,U),(date(2026,10,6),228,U)]
  with mock.patch.object(lu,"pdf_confirms",return_value=True) as pc:
   fixed=lu.fix_numbers(items)
  pc.assert_called_once_with(date(2026,10,3),U,227)
  self.assertEqual([n for _,n,_ in fixed],[225,226,227,228])
 def test_fix_numbers_rejected(self):
  items=[(date(2026,10,1),225,U),(date(2026,10,2),226,U),(date(2026,10,3),225,U),(date(2026,10,6),228,U)]
  with mock.patch.object(lu,"pdf_confirms",return_value=False):
   with self.assertRaises(ProvincialCoverageError):lu.fix_numbers(items)
 def test_year_change_ok(self):
  items=[(date(2025,12,30),298,U),(date(2025,12,31),299,U),(date(2026,1,2),1,U),(date(2026,1,3),2,U)]
  with mock.patch.object(lu,"pdf_confirms",side_effect=AssertionError):
   self.assertEqual(lu.fix_numbers(items),items)
 def test_gap_fails(self):
  items=[(date(2026,10,1),225,U),(date(2026,10,2),226,U),(date(2026,10,6),228,U),(date(2026,10,7),229,U)]
  with mock.patch.object(lu,"pdf_confirms",side_effect=AssertionError):
   with self.assertRaises(ProvincialCoverageError):lu.fix_numbers(items)
 def test_parse_day(self):
  html="""<h2>BOP DE 07/01/2026</h2><h3>CONCELLO DE LUGO</h3>
  <a href="/sites/deputacionlugo.org/files/inline-files/07-01-2026.pdf#page=1">CONVOCATORIA E BASES PARA A SELECCIÓN DE PERSOAL LABORAL TEMPORAL (PÁX. 1, R. 0009)</a>
  <a href="/sites/deputacionlugo.org/files/inline-files/07-01-2026.pdf#page=2">APROBACIÓN DO PADRÓN FISCAL (PAG. 2, R. 0010)</a>"""
  d=lu.parse_day(BeautifulSoup(html,"html.parser"),date(2026,1,7),4,U)
  self.assertEqual(d["read"],2)
  self.assertEqual([n["id"] for n in d["notices"]],["LU-2026-0009"])
  self.assertEqual(d["notices"][0]["url"],"https://deputacionlugo.gal/sites/deputacionlugo.org/files/inline-files/07-01-2026.pdf")
  with self.assertRaises(ProvincialCoverageError):
   lu.parse_day(BeautifulSoup(html,"html.parser"),date(2026,1,8),5,U)
if __name__=="__main__":unittest.main()
