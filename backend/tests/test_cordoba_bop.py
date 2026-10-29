import unittest,sys
from datetime import date,timedelta
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cordoba_bop import parse_issue,pdf_valid,audit
from provincial_common import ProvincialCoverageError

DAY=date(2026,10,28)
HTML="""<html><head><title>Boletín Oficial de la Provincia de Córdoba del día 28-10-2026</title></head>
<h2>BOLETÍN número 209</h2>
<a href="/visor-pdf/28-10-2026/BOP-S-2026-209.pdf">Sumario del BOP</a>
<ul><li class="emisor"><h2>Ayuntamiento de Lucena</h2><ul>
<li class="announcement"><p>Bases de la convocatoria para proveer una plaza de Administrativo</p>
<p class="ps-2"><a class="pdf" href="/visor-pdf/28-10-2026/BOP-A-2026-3644.pdf">PDF BOP-A-2026-3644</a></p></li>
<li class="announcement"><p>Aprobación inicial del presupuesto</p>
<p class="ps-2"><a class="pdf" href="/visor-pdf/28-10-2026/BOP-A-2026-3645.pdf">PDF BOP-A-2026-3645</a></p></li>
</ul></li></ul></html>"""
class CordobaTests(unittest.TestCase):
 def test_parse_issue_and_pdf_path(self):
  entry=parse_issue(HTML,DAY)
  self.assertEqual(entry["number"],209)
  self.assertEqual(entry["read"],2)
  self.assertEqual(entry["rows"][0]["entity"],"Ayuntamiento de Lucena")
  self.assertEqual(entry["rows"][0]["id"],"CO-2026-3644")
  self.assertEqual(entry["rows"][0]["type"],"Plaza / oposición")
  self.assertTrue(pdf_valid(entry["rows"][0]["url"],DAY)[0])
  self.assertFalse(pdf_valid(entry["rows"][0]["url"],DAY-timedelta(days=1))[0])
 def test_fail_closed(self):
  with self.assertRaises(ProvincialCoverageError):
   parse_issue(HTML.replace("BOP-A-2026-3645.pdf","BOP-A-2025-3645.pdf"),DAY)
  with self.assertRaises(ProvincialCoverageError):
   parse_issue(HTML.replace("BOLETÍN número 209","BOLETÍN número 208"),DAY)
  empty="""<title>Boletín Oficial de la Provincia de Córdoba del día 28-10-2026</title>"""
  self.assertIsNone(parse_issue(empty,DAY))
 def test_audit_and_number_gap(self):
  end=date(2026,10,29)
  start=end-timedelta(days=29)
  pub=[start+timedelta(days=i) for i in range(30) if (start+timedelta(days=i)).weekday()<5]
  def fake(d):
   if d not in pub:return None
   n=190+pub.index(d)
   return {"date":d,"number":n,"read":4,"pages":1,
     "pdf":f"https://bop.dipucordoba.es/visor-pdf/{d:%d-%m-%Y}/BOP-S-2026-{n}.pdf",
     "notices":[{"id":f"CO-2026-{3600+n}","province":"Córdoba",
     "title":"Bases de la convocatoria de una plaza","entity":"Ayuntamiento",
     "date":d.strftime("%d/%m/%Y"),"bulletin":str(n),"type":"Plaza / oposición",
     "url":f"https://bop.dipucordoba.es/visor-pdf/{d:%d-%m-%Y}/BOP-A-2026-{3600+n}.pdf"}]}
  data=audit(30,end,fake)
  self.assertEqual(len(data["historyCoverage"]["publicationDates"]),len(pub))
  def broken(d):
   x=fake(d)
   if x and d==pub[4]:x["number"]+=2
   return x
  with self.assertRaises(ProvincialCoverageError):audit(30,end,broken)
if __name__=="__main__":unittest.main()
