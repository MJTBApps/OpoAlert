import unittest,sys
from pathlib import Path
from datetime import date
from unittest import mock
from bs4 import BeautifulSoup
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import boja_autonomico as bj
from provincial_common import ProvincialCoverageError

def h1(text):
 return BeautifulSoup(f"<h1>Boletín Oficial de la Junta de Andalucía - Sede Electrónica del BOJA {text}</h1>","html.parser")

class BojaTest(unittest.TestCase):
 def test_labels(self):
  self.assertEqual(bj.label(("O",2026,210,None)),"210")
  self.assertEqual(bj.label(("C",2026,210,2)),"210-C2")
  self.assertEqual(bj.label(("E",2026,511,None)),"E11")
 def test_headers(self):
  self.assertEqual(bj.header(h1("Boletín número 1 de 02/01/2026"),("O",2026,1,None)),date(2026,1,2))
  self.assertEqual(bj.header(h1("Boletín 210 Complementario nº 1 de 29/10/2026"),("C",2026,210,1)),date(2026,10,29))
  self.assertEqual(bj.header(h1("Boletín Extraordinario número 11 de 04/07/2026"),("E",2026,511,None)),date(2026,7,4))
  with self.assertRaises(ProvincialCoverageError):bj.header(h1("Boletín número 210 de 29/10/2026"),("O",2026,211,None))
  with self.assertRaises(ProvincialCoverageError):bj.header(h1("Boletín número 1 de 02/01/2026"),("O",2025,1,None))
 def test_pdf_patterns(self):
  self.assertTrue(bj.pdf_pattern(("O",2026,1,None)).fullmatch("/eboja/2026/1/BOJA26-001-00035-17442-01_00331039.pdf"))
  self.assertTrue(bj.pdf_pattern(("C",2026,210,1)).fullmatch("/eboja/2026/210/c01/BOJA26-221001-00005-14379-01_00345609.pdf"))
  self.assertTrue(bj.pdf_pattern(("E",2026,511,None)).fullmatch("/eboja/2026/511/BOJA26-511-00001-9144-01_00340377.pdf"))
  self.assertFalse(bj.pdf_pattern(("O",2026,210,None)).fullmatch("/eboja/2026/210/BOJA26-211-00002-14210-01_00345442.pdf"))
 def test_day_page(self):
  html=BeautifulSoup('<a href="2026/210/">Boletín número 210</a><a href="2026/210/c01/">C1</a>'
                     '<a href="2026/518/">Extra</a><a href="/eboja/index.html">x</a>',"html.parser")
  with mock.patch.object(bj,"http",return_value=html):
   got=bj.editions_of_day(date(2026,10,29),"https://www.juntadeandalucia.es/eboja/20261029.html")
  self.assertEqual(got,[("O",2026,210,None),("C",2026,210,1),("E",2026,518,None)])
  self.assertEqual(bj.editions_of_day(date(2026,10,30),"https://www.juntadeandalucia.es/eboja/2026/211/index.html"),
                   [("O",2026,211,None)])
 def test_no_fixed_dates(self):
  src=Path(bj.__file__).read_text(encoding="utf-8")
  self.assertNotRegex(src,r"date\(20\d\d")
  self.assertNotIn("2026",src)

if __name__=="__main__":unittest.main()
