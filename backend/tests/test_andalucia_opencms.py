import sys,unittest
from pathlib import Path
from datetime import date,timedelta
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from andalucia_opencms_bop import (
 GRANADA,SEVILLA,parse_page,detail_pdf,audit,pdf_url_ok,daily_url)
from provincial_common import ProvincialCoverageError

DAY=date(2026,10,29)
PDF="https://bop.dipgra.es/export/sites/bop/.galleries/Documentos-Anuncios-en-PDF/firmado-111-final.pdf"
EDITION="https://bop.dipgra.es/export/sites/bop/.galleries/Documentos-BOPs-en-PDF/bop-29_10_2026-123.pdf"
HTML="""<html><h2>BOP núm. 210 del 29/10/2026</h2><p>Resultados del 1 al 2 de 2</p>
<a href="/export/sites/bop/.galleries/Documentos-BOPs-en-PDF/bop-29_10_2026-123.pdf">PDF</a>
<li class="elementoListado">
<a class="enlace_elemento" href="/publica/buscador-anuncios/anuncio/seleccion/">Ir al detalle</a>
<div class="fecha_elemento">29/10/2026</div>
<h3 class="titulo_elemento">Bases de la convocatoria para una plaza de administrativo</h3>
<div class="campo_1">Ayuntamiento de Loja</div>
<div class="campo_3">BOP-GRA-2026-210001</div>
</li>
<li class="elementoListado">
<a class="enlace_elemento" href="/publica/buscador-anuncios/anuncio/credito/">Ir al detalle</a>
<div class="fecha_elemento">29/10/2026</div>
<h3 class="titulo_elemento">Aprobacion de credito extraordinario</h3>
<div class="campo_1">Ayuntamiento de Granada</div>
<div class="campo_3">BOP-GRA-2026-210002</div>
</li></html>"""
DETAIL="""<html><h1 class="titulo_detalle">Bases de la convocatoria para una plaza de administrativo</h1>
<span>Fecha de publicación 29/10/2026</span>
<a href="/export/sites/bop/.galleries/Documentos-Anuncios-en-PDF/firmado-111-final.pdf">PDF</a></html>"""

class ReaderTests(unittest.TestCase):
 def test_day_parser_and_official_links(self):
  item=parse_page(GRANADA,HTML,DAY)
  self.assertEqual(item["number"],210)
  self.assertEqual(item["total"],2)
  self.assertEqual(len(item["rows"]),2)
  self.assertEqual(item["rows"][0]["entity"],"Ayuntamiento de Loja")
  self.assertTrue(pdf_url_ok(GRANADA,PDF))
  self.assertFalse(pdf_url_ok(SEVILLA,PDF))
  self.assertIn("BOP-29-10-2026",daily_url(GRANADA,DAY))
 def test_pdf_fails_closed(self):
  title,url=detail_pdf(GRANADA,DETAIL,DAY,
       "Bases de la convocatoria para una plaza de administrativo")
  self.assertTrue(title.startswith("Bases"))
  self.assertEqual(url,PDF)
  with self.assertRaises(ProvincialCoverageError):
   detail_pdf(GRANADA,DETAIL.replace("29/10/2026","28/10/2026"),DAY,title)
  with self.assertRaises(ProvincialCoverageError):
   parse_page(GRANADA,HTML.replace("Resultados del 1 al 2 de 2","Resultados del 1 al 3 de 3"),DAY)
  with self.assertRaises(ProvincialCoverageError):
   parse_page(GRANADA,HTML.replace("210002","210001"),DAY)
 def test_thirty_day_month_and_number_continuity(self):
  end=date(2026,10,29)
  start=end-timedelta(days=29)
  valid=[start+timedelta(days=i) for i in range(30) if (start+timedelta(days=i)).weekday()<5]
  def fake(s,d):
   if d not in valid:return None
   n=190+valid.index(d)
   return {"date":d,"number":n,"read":10,"pages":1,"pdf":EDITION,
      "notices":[{"id":f"GR-2026-{n:03d}001","date":d.strftime("%d/%m/%Y"),
      "province":"Granada","title":"Bases de la convocatoria para una plaza",
      "entity":"Ayuntamiento de Loja","bulletin":str(n),
      "type":"Plaza / oposición","url":PDF}]}
  result=audit(GRANADA,30,end,fake)
  self.assertEqual(len(result["historyCoverage"]["publicationDates"]),len(valid))
  self.assertEqual(len(result["notices"]),len(valid))
  def bad(s,d):
   x=fake(s,d)
   if x and d==valid[6]:x["number"]+=4
   return x
  with self.assertRaises(ProvincialCoverageError):
   audit(GRANADA,30,end,bad)
  with self.assertRaises(ProvincialCoverageError):
   audit(GRANADA,20,end,fake)
if __name__=="__main__":unittest.main()
