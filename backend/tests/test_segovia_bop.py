import unittest,sys
from pathlib import Path
from datetime import date
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import segovia_bop as sg
from provincial_common import ProvincialCoverageError

GHOST=("BOLETÍN OFICIAL DE LA PROVINCIA DE SEGOVIA\nAÑO 2025.— NÚMERO 127\nSUMARIO\nLUNES, 3 DE NOVIEMBRE\n"
       "Extractos de los acuerdos adoptados por la Junta de Gobierno, sesión de 28 de octubre de 2025 .... 3\n")

class SegoviaTest(unittest.TestCase):
 def test_cover_number_ignores_template_header(self):
  cover=GHOST+"SUMARIO\nMIÉRCOL ES, 21 DE ENEROAÑO 2026.— NÚMERO 9\n"
  self.assertEqual(sg.cover_number(cover,date(2026,1,21)),9)
  cover=GHOST+"SUMARIO\nMARTES, 20 DE ENEROAÑO 2026.— NÚMERO EXTRAORDINARIO\n"
  self.assertEqual(sg.cover_number(cover,date(2026,1,20)),sg.EXTRA)
  # The template header itself is only accepted on its own date.
  with self.assertRaises(ProvincialCoverageError):sg.cover_number(GHOST,date(2025,10,28))
 def test_card_number(self):
  self.assertEqual(sg.card_number(" 130 "),130)
  self.assertEqual(sg.card_number("EXTRAORDINARIO"),sg.EXTRA)
  with self.assertRaises(ProvincialCoverageError):sg.card_number("13 bis")
 def test_month_chunks(self):
  self.assertEqual(list(sg.month_chunks(date(2025,12,17),date(2026,1,15))),
   [(date(2025,12,17),date(2025,12,31)),(date(2026,1,1),date(2026,1,15))])
  self.assertEqual(len(list(sg.month_chunks(date(2027,1,30),date(2027,3,1)))),3)
 def test_sequence_new_year_and_extraordinary(self):
  res=[{"day":date(2025,12,31),"number":"157"},{"day":date(2026,1,2),"number":"1"},
       {"day":date(2026,1,20),"number":sg.EXTRA},{"day":date(2026,1,21),"number":"2"}]
  old=sg.MIN_ISSUES;sg.MIN_ISSUES=3
  try:
   sg.check_sequence(res,(date(2025,12,29),156))
   with self.assertRaises(ProvincialCoverageError):sg.check_sequence(res,(date(2025,12,29),155))
  finally:sg.MIN_ISSUES=old

if __name__=="__main__":unittest.main()
