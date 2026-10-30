import unittest,sys
from pathlib import Path
from datetime import date,timedelta
from urllib.parse import urlsplit,parse_qs
from bs4 import BeautifulSoup
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import canarias_bop_provincial as bop
from provincial_common import ProvincialCoverageError
def schedule(a,b,holidays=()):
 """Lunes, miércoles y viernes; numeración desde 1 cada enero."""
 out={};d=date(a.year,1,1);n=0
 while d<=b:
  if d.month==1 and d.day==1:n=0
  if d.weekday() in (0,2,4) and d not in holidays:
   n+=1
   if d>=a:out[d]=n
  d+=timedelta(days=1)
 return out
def sumario(day,n,zero=False):
 stamp=f"{day.day}-{day.month}-{day.year%100:02}"
 pdf=f'<a href="../boletines/{day.year}/{stamp}/{stamp}.pdf">Descargar Boletín</a>'
 if n is None:
  return f"<p>SUMARIO DEL BOLETÍN Nº {'0' if zero else ''} , DE FECHA {stamp}</p>{pdf}"
 return (f"<p>SUMARIO DEL BOLETÍN Nº {n} , DE FECHA {stamp}</p>{pdf}<table><tr><td>"
         "<b><i>ILUSTRE AYUNTAMIENTO DE MOGÁN</i></b><br>- Bases y convocatoria para cubrir 2 plazas de Policía Local por oposición<br>"
         "- Modificación de la ordenanza fiscal reguladora de la tasa<br>"
         "- Aprobación inicial del expediente de modificación de crédito<br>"
         "- Calendario laboral del Ayuntamiento para el próximo año<br>"
         "</td></tr></table>")
class BopTest(unittest.TestCase):
 def setUp(self):
  self.issues={};self.calendar=set();self.zero=set()
  self.old=bop.fetch
  def fake(url,host,pdf=False,retries=3):
   if pdf:return None
   u=urlsplit(url)
   if u.path.endswith("main1.php"):
    links="".join(f'<a href="sumario.php?codigopub=1&fecha_mas_reciente={d.isoformat()}"> {d.day} </a>' for d in sorted(self.calendar))
    return BeautifulSoup(links,"html.parser")
   day=date.fromisoformat(parse_qs(u.query)["fecha_mas_reciente"][0])
   return BeautifulSoup(sumario(day,self.issues.get(day),day in self.zero),"html.parser")
  bop.fetch=fake
 def tearDown(self):bop.fetch=self.old
 def test_january_window_restarts_numbering(self):
  end=date(2026,1,15)
  self.issues=schedule(date(2025,11,1),date.today(),holidays={date(2026,1,1),date(2026,1,6)})
  self.zero={date(2026,1,1)}
  self.calendar={d for d in self.issues if d>=date.today().replace(day=1)-timedelta(days=31)}
  feed=bop.audit("tf",today=end)
  h=feed["historyCoverage"]
  self.assertEqual(h["rangeStart"],"2025-12-17")
  self.assertIn("1",h["bulletins"])
  import re
  self.assertTrue(all(re.fullmatch(r"TF-\d{4}\d{4}-\d{3}",n["id"]) for n in feed["notices"]))
  self.assertIn("TF-20260102-001",{n["id"] for n in feed["notices"]})
  self.assertEqual(feed["source"],"https://www.bopsantacruzdetenerife.es/bopsc2/main1.php")
 def test_missing_issue_inside_window_fails(self):
  end=date(2026,10,15)
  self.issues=schedule(date(2026,8,1),date.today())
  del self.issues[date(2026,10,7)]
  with self.assertRaises(ProvincialCoverageError):bop.audit("lp",today=end)
 def test_calendar_disagreement_fails(self):
  end=date.today()
  self.issues=schedule(end-timedelta(days=60),end)
  self.calendar=set(self.issues)|{max(self.issues)-timedelta(days=1)}
  with self.assertRaises(ProvincialCoverageError):bop.audit("lp",today=end)
 def test_probe_number_zero_is_no_issue(self):
  self.zero={date(2026,1,1)}
  self.assertEqual(bop.probe(date(2026,1,1),bop.CONFIG["tf"])[1],None)
if __name__=="__main__":unittest.main()
