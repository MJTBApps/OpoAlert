import unittest,sys
from pathlib import Path
from datetime import date
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import salamanca_bop as sa
from provincial_common import ProvincialCoverageError

class SalamancaTest(unittest.TestCase):
 def test_url_follows_year(self):
  self.assertEqual(sa.pdf_url(date(2025,12,31),7),
   "https://www.lasalina.es/documentacion/bop/2025/20251231/BOP-SA-20251231-007.pdf")
  sa.official_url(sa.pdf_url(date(2027,1,4),0))
  with self.assertRaises(ProvincialCoverageError):
   sa.official_url("https://www.lasalina.es/documentacion/bop/2026/20261030/otro.pdf")
 def test_misprinted_cve_kept_in_sequence(self):
  day=date(2025,12,18)
  text=("CVE: BOP-SA-20251218-000\nUno.\nCVE: BOP-SA-20251218-001\n"
        "Dos.\nCVE: BOP-SA-20251216-002\nTres.\nCVE: BOP-SA-20251218-0003\n")
  self.assertEqual(sa.extract_entry_info(text,day),[1,2,3])
 def test_gap_or_duplicate_rejected(self):
  day=date(2026,10,30)
  with self.assertRaises(ProvincialCoverageError):
   sa.extract_entry_info("CVE: BOP-SA-20261030-001\nCVE: BOP-SA-20261030-003\n",day)
  with self.assertRaises(ProvincialCoverageError):
   sa.extract_entry_info("CVE: BOP-SA-20261030-001\nCVE: BOP-SA-20261029-001\n",day)
 def test_calendar_new_year(self):
  days=[date(2025,12,29),date(2025,12,30),date(2025,12,31),date(2026,1,2)]
  pub=[{"day":d,"number":n} for d,n in zip(days,[249,250,251,1])]
  old=sa.MIN_ISSUES;sa.MIN_ISSUES=3
  try:
   sa.check_calendar(pub,(date(2025,12,26),248),date(2025,12,27),date(2026,1,2))
   with self.assertRaises(ProvincialCoverageError):  # edition 248 missing
    sa.check_calendar(pub,(date(2025,12,26),247),date(2025,12,27),date(2026,1,2))
  finally:sa.MIN_ISSUES=old

if __name__=="__main__":unittest.main()
