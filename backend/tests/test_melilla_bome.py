import unittest,sys
from pathlib import Path
from datetime import date
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import melilla_bome
from provincial_common import ProvincialCoverageError

def ed(extra,n,day):
 url=f"https://bomemelilla.es/bome/BOME-{'BX' if extra else 'B'}-{day.year}-{n}"
 return url,(extra,n,day)

# Ventana real del cambio de año (17/12/2025-15/01/2026), del archivo oficial.
ARCHIVE={
 2025:dict([ed(False,6336,date(2025,12,16)),ed(True,76,date(2025,12,16)),ed(True,77,date(2025,12,17)),
            ed(True,78,date(2025,12,18)),ed(False,6337,date(2025,12,19)),ed(True,79,date(2025,12,19)),
            ed(False,6338,date(2025,12,23)),ed(True,80,date(2025,12,23)),ed(False,6339,date(2025,12,26)),
            ed(False,6340,date(2025,12,30))]),
 2026:dict([ed(False,6341,date(2026,1,2)),ed(False,6342,date(2026,1,6)),ed(False,6343,date(2026,1,9)),
            ed(False,6344,date(2026,1,13)),ed(False,6345,date(2026,1,16)),ed(True,1,date(2026,1,16))]),
}

class MelillaCalendarTest(unittest.TestCase):
 def run_calendar(self,archive,end):
  with mock.patch.object(melilla_bome,"archive",lambda year:dict(archive[year])):
   return melilla_bome.calendar(end)

 def test_edition_label(self):
  self.assertEqual(melilla_bome.edition_day("BOME EXTRA Nº 80 del martes, 23 de diciembre de 2025"),
                   (True,80,date(2025,12,23)))
  self.assertEqual(melilla_bome.edition_day("BOME  Nº 6341 del viernes, 2 de enero de 2026"),
                   (False,6341,date(2026,1,2)))

 def test_year_change(self):
  items=self.run_calendar(ARCHIVE,date(2026,1,15))
  labels=[("E" if v[0] else "")+str(v[1]) for _,v in items]
  self.assertEqual(labels,["E77","E78","6337","E79","6338","E80","6339","6340","6341","6342","6343","6344"])

 def test_missing_regular_fails(self):
  broken={y:dict(v) for y,v in ARCHIVE.items()}
  del broken[2026]["https://bomemelilla.es/bome/BOME-B-2026-6342"]
  with self.assertRaises(ProvincialCoverageError):self.run_calendar(broken,date(2026,1,15))

 def test_missing_first_extra_fails(self):
  broken={y:dict(v) for y,v in ARCHIVE.items()}
  del broken[2025]["https://bomemelilla.es/bome/BOME-BX-2025-77"]
  with self.assertRaises(ProvincialCoverageError):self.run_calendar(broken,date(2026,1,15))

 def test_stale_archive_fails(self):
  with self.assertRaises(ProvincialCoverageError):self.run_calendar(ARCHIVE,date(2026,1,25))

 def test_stable_source(self):
  self.assertEqual(melilla_bome.SOURCE,"https://bomemelilla.es/")

if __name__=="__main__":unittest.main()
