import unittest,sys
from pathlib import Path
from datetime import date,timedelta
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import asturias_bopa as A
from provincial_common import ProvincialCoverageError

MONTHS=["enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre"]
DAYS=["lunes","martes","miércoles","jueves","viernes","sábado","domingo"]

def html(day,number,prev,items,supplement=False):
 """Sumario sintético con la misma estructura que miPrincipado."""
 h1=f"Boletín Nº {number} del {DAYS[day.weekday()]} {day.day:02d} de {MONTHS[day.month-1]} de {day.year}"
 p=prev.strftime("%d%%2F%m%%2F%Y")
 sup=(f'<a class="gpa-link" href="/bopa/{day:%Y/%m/%d}/{day:%Y%m%d}Su1.pdf"> Enlace al PDF del suplemento 1 </a>'
      if supplement else "")
 body="".join(f'''<h4>{sec}</h4><h5>{h5}</h5><h6>{h6}</h6>{f'<p class="subAuthor">{sub}</p>' if sub else ""}
 <dl><dt>{title}&nbsp;<strong>[Cód. {code}]</strong></dt><dd><a href="https://miprincipado.asturias.es/x">Texto</a>
 <span class="pdfResultadoBopa"><a href="/bopa/{day:%Y/%m/%d}/{code}.pdf">PDF</a></span></dd></dl>'''
   for sec,h5,h6,sub,title,code in items)
 return f'''<html><body><div id="p_p_id_{A.PORTLET}_"><div class="portlet-body">
 <a class="btn" href="https://miprincipado.asturias.es/ast/bopa-sumario?p_r_p_summaryDate={p}&amp;p_r_p_summaryLastBopa=false"><span>Boletín del día anterior </span></a>
 <h1 class="gpa-mt-xl">{h1}</h1>{sup}<div id="bopa-boletin">{body}</div></div></div></body></html>'''

def item(code,title="Anuncio. Información pública.",h6="DE GIJÓN",h5="AYUNTAMIENTOS",sub=None):
 return ("IV. Administración Local",h5,h6,sub,title,code)

def workdays(first,last):
 d=first
 while d<=last:
  if d.weekday()<5:yield d
  d+=timedelta(days=1)

def fake_portal(editions):
 """editions: [(fecha, número)] en orden; días sin boletín muestran el último."""
 by={d:n for d,n in editions}
 days=sorted(by)
 def page(d):
  i=days.index(d);prev=days[i-1] if i else d-timedelta(days=1)
  return A.parse_summary(html(d,by[d],prev,[item(f"{d.year}-{d.toordinal()%100000:05d}")]))
 latest=page(days[-1])
 def loader(d):
  return page(d) if d in by else latest
 return loader,latest

class ParseTest(unittest.TestCase):
 def test_summary_fields(self):
  d=date(2026,10,23)
  p=A.parse_summary(html(d,206,date(2026,10,22),[
   item("2026-08565","Ley 7/2026.",h5="DISPOSICIONES GENERALES",h6="PRESIDENCIA DEL PRINCIPADO DE ASTURIAS"),
   item("2026-08408","Resolución por la que se convoca.",h5="AUTORIDADES Y PERSONAL",h6="CONSEJERÍA DE SALUD",
        sub="SERVICIO DE SALUD DEL PRINCIPADO DE ASTURIAS (SESPA)"),
   item("2026-08800",h6="DE EL FRANCO"),
   item("2026-08801",h5="COGERSA, S. A. U.",h6="")],supplement=True))
  self.assertEqual((p["number"],p["day"],p["previous"]),(206,d,date(2026,10,22)))
  self.assertEqual([x["code"] for x in p["items"]],["2026-08565","2026-08408","2026-08800","2026-08801"])
  self.assertEqual(p["items"][0]["entity"],"Presidencia del Principado de Asturias")
  self.assertEqual(p["items"][1]["entity"],"Servicio de Salud del Principado de Asturias (SESPA)")
  self.assertEqual(p["items"][2]["entity"],"Ayuntamiento de El Franco")
  self.assertEqual(p["items"][3]["entity"],"Cogersa, S. A. U.")
  self.assertEqual(p["items"][1]["url"],"https://www.asturias.es/bopa/2026/10/23/2026-08408.pdf")
  self.assertEqual(p["supplements"],["https://www.asturias.es/bopa/2026/10/23/20261023Su1.pdf"])

 def test_pdf_of_other_day_fails(self):
  d=date(2026,10,23)
  bad=html(d,206,date(2026,10,22),[item("2026-08565")]).replace("/bopa/2026/10/23/2026-08565","/bopa/2026/10/22/2026-08565")
  with self.assertRaises(ProvincialCoverageError):A.parse_summary(bad)

 def test_unknown_page_fails(self):
  with self.assertRaises(ProvincialCoverageError):
   A.parse_summary(f'<div id="p_p_id_{A.PORTLET}_">El formato de la fecha introducida es incorrecto.</div>')

class WalkTest(unittest.TestCase):
 def test_sunday_and_month_change(self):
  eds=[(d,150+i) for i,d in enumerate(workdays(date(2026,9,1),date(2026,10,30)))]
  loader,latest=fake_portal(eds)
  pages=A.walk(date(2026,10,18),latest,loader)
  self.assertEqual(pages[-1]["day"],date(2026,10,16))
  self.assertEqual(pages[0]["day"],date(2026,9,21))
  self.assertTrue(all(b["number"]==a["number"]+1 for a,b in zip(pages,pages[1:])))

 def test_year_change_numbering_restarts(self):
  dec=[d for d in workdays(date(2025,12,1),date(2025,12,31)) if d!=date(2025,12,25)]
  jan=[d for d in workdays(date(2026,1,2),date(2026,1,31)) if d!=date(2026,1,6)]
  eds=[(d,230+i) for i,d in enumerate(dec)]+[(d,1+i) for i,d in enumerate(jan)]
  loader,latest=fake_portal(eds)
  pages=A.walk(date(2026,1,15),latest,loader)
  self.assertEqual(pages[0]["day"],date(2025,12,17))
  self.assertEqual((pages[-1]["day"],pages[-1]["number"]),(date(2026,1,15),9))

 def test_gap_in_numbering_fails(self):
  eds=[(d,150+i) for i,d in enumerate(workdays(date(2026,9,1),date(2026,10,30)))]
  del eds[30]
  loader,latest=fake_portal(eds)
  with self.assertRaises(ProvincialCoverageError):A.walk(date(2026,10,30),latest,loader)

 def test_fallback_not_latest_fails(self):
  eds=[(d,150+i) for i,d in enumerate(workdays(date(2026,9,1),date(2026,10,30)))]
  loader,latest=fake_portal(eds)
  stale=dict(latest,number=1)
  with self.assertRaises(ProvincialCoverageError):A.walk(date(2026,10,18),stale,loader)

 def test_stale_portal_fails(self):
  eds=[(d,150+i) for i,d in enumerate(workdays(date(2026,9,1),date(2026,10,20)))]
  loader,latest=fake_portal(eds)
  with self.assertRaises(ProvincialCoverageError):A.walk(date(2026,10,30),latest,loader)

class ClassifyTest(unittest.TestCase):
 def test_new_calls(self):
  for t in ("Anuncio. Bases y convocatoria para la selección de un/a Técnico Medio de Gestión, en el marco de los contratos formativos.",
            "Anuncio. Convocatoria y bases del Plan de Empleo 2026-27 del Ayuntamiento de Soto del Barco.",
            "Resolución de 14 de octubre de 2026, por la que se deja sin efecto la Resolución de 11 de septiembre y se convocan pruebas selectivas para la citada categoría.",
            "Anuncio. Convocatoria y bases para la constitución de una bolsa de empleo adicional de Auxiliar de Ayuda a Domicilio."):
   self.assertIsNotNone(A.classify(t),t)
  self.assertEqual(A.classify("Anuncio. Convocatoria y bases para la constitución de una bolsa de empleo de Auxiliar."),"Bolsa de trabajo")

 def test_follow_up_acts(self):
  for t in ("Resolución por la que se hace pública la relación de plazas a adjudicar en el proceso selectivo para el acceso a 39 plazas.",
            "Resolución por la que se resuelve el proceso selectivo para la cobertura de un puesto.",
            "Resolución por la que se aprueba la bolsa de trabajo de personal laboral temporal.",
            "Anuncio. Rectificación de las bases para la constitución de una bolsa de empleo.",
            "Extracto de la Resolución por la que se aprueba la convocatoria de ayudas para compensación de gastos del personal docente.",
            "Resolución por la que se nombran funcionarios de carrera a los aspirantes que han superado las pruebas selectivas."):
   self.assertIsNone(A.classify(t),t)

 def test_urls_and_case(self):
  self.assertEqual(A.pdf_url(date(2026,1,2),"2025-11075"),"https://www.asturias.es/bopa/2026/01/02/2025-11075.pdf")
  with self.assertRaises(ProvincialCoverageError):A.pdf_url(date(2026,1,2),"../x")
  self.assertEqual(A.smart_case('INSTITUTO ASTURIANO DE ADMINISTRACIÓN PÚBLICA "ADOLFO POSADA"'),
                   'Instituto Asturiano de Administración Pública "Adolfo Posada"')
  self.assertTrue(A.summary_url(date(2026,10,5)).startswith(A.SOURCE+"?"))
  self.assertIn("p_r_p_summaryDate=05%2F10%2F2026",A.summary_url(date(2026,10,5)))

if __name__=="__main__":unittest.main()
