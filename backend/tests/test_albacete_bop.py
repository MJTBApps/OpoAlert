"""Pruebas sin red del lector del BOP de Albacete."""
import base64,json,sys,unittest
from pathlib import Path
from datetime import date,timedelta
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from provincial_common import ProvincialCoverageError
import albacete_bop as ab

D=date(2026,10,28)
ROW="""<li class="list-group-item"><div class="row m-0"><div class="col-12">{title}</div>
<div class="col-12 text-end"><a class="enlace_documento_bop_principal" target="_blank"
href="{href}" title="Descargar página 3">Ver página 3</a></div></div></li>"""

def sumario(number=126,day="28/10/2026",rows=None):
    rows=rows if rows is not None else [
        ("Bases de la convocatoria para cubrir una plaza de Policía Local por oposición",
         "https://bop.dipualba.es/servicesajax/descargararchivopaginaBOP/299645"),
        ("Aprobación inicial del presupuesto general",
         "https://bop.dipualba.es/servicesajax/descargararchivopaginaBOP/299646")]
    body="".join(ROW.format(title=t,href=h) for t,h in rows)
    # Mismo marcado (con la etiqueta mal cerrada) que sirve el portal.
    return f"""<div class="row m-0 p-0"<div class="col-12 m-0 mb-3 p-0"><h1>Boletín  Número {number} ({day})</h1></div>
<div class="col-12 text-end"><a href="https://bop.dipualba.es/servicesajax/descararchivobopcompleto/?a=22769">Descargar boletín completo</a></div>
<div class="card"><div class="card-header"><p class="h5">Sección segunda. Administración Autonómica</p></div>
<ul class="list-group"><li class="list-group-item"><span class="fw-bold">Diputación de Albacete</span>
<ul class="list-group list-group-flush"><li class="list-group-item"><span class="fw-bold">Servicio de Secretaría</span></li>
<li class="list-group-item"><ul class="list-group list-group-flush">
{ROW.format(title="Extracto de acuerdos del Pleno",href="https://bop.dipualba.es/servicesajax/descargararchivopaginaBOP/299623")}
</ul></li></ul></li>
<li class="list-group-item"><span class="fw-bold">Ayuntamientos</span>
<ul class="list-group list-group-flush"><li class="list-group-item"><span class="fw-bold">Caudete</span></li>
<li class="list-group-item"><ul class="list-group list-group-flush">{body}</ul></li></ul></li></ul></div>"""

def calendar_json(events):
    data=[{"id":str(9000+i),"start":d.isoformat(),"title":"","allDay":"true","display":"background",
           "idbop":str(n),"fechabop":d.strftime("%d/%m/%Y"),"cantidadAnuncios":"","extra":"",
           "descripcion":f"BOP {n} del {d:%d/%m/%Y}"} for i,(d,n) in enumerate(events)]
    return json.dumps({"codigoError":"","descripcionError":"",
                       "yedata":base64.b64encode(json.dumps(data).encode()).decode()})

class AlbaceteTest(unittest.TestCase):
    def test_parse_issue(self):
        i=ab.parse_issue(sumario(),D,126)
        self.assertEqual(i["read"],3)
        self.assertEqual(len(i["notices"]),1)
        n=i["notices"][0]
        self.assertEqual(n["id"],"AB-2026-299645")
        self.assertEqual(n["entity"],"Ayuntamiento de Caudete")
        self.assertEqual(n["bulletin"],"126")
        self.assertEqual(n["date"],"28/10/2026")
        self.assertEqual(n["type"],"Plaza / oposición")
        self.assertEqual(n["url"],"https://bop.dipualba.es/servicesajax/descargararchivopaginaBOP/299645")

    def test_entity_other_groups(self):
        from bs4 import BeautifulSoup
        s=BeautifulSoup(sumario(),"html.parser")
        names=[ab.entity_of(a) for a in s.select("a.enlace_documento_bop_principal")]
        self.assertEqual(names[0],"Diputación de Albacete. Servicio de Secretaría")

    def test_wrong_issue_rejected(self):
        with self.assertRaises(ProvincialCoverageError):ab.parse_issue(sumario(number=125),D,126)
        with self.assertRaises(ProvincialCoverageError):ab.parse_issue(sumario(day="26/10/2026"),D,126)

    def test_bad_links_rejected(self):
        for href in ("https://otro.example/servicesajax/descargararchivopaginaBOP/1",
                     "https://bop.dipualba.es/otra/ruta/1",
                     "http://bop.dipualba.es/servicesajax/descargararchivopaginaBOP/1"):
            with self.assertRaises(ProvincialCoverageError):
                ab.parse_issue(sumario(rows=[("Bases de una plaza de Policía Local",href)]),D,126)
        dup="https://bop.dipualba.es/servicesajax/descargararchivopaginaBOP/7"
        with self.assertRaises(ProvincialCoverageError):
            ab.parse_issue(sumario(rows=[("A",dup),("B",dup)]),D,126)

    def test_calendar(self):
        m=date(2026,10,1)
        ev=[(date(2026,10,26),125),(date(2026,10,28),126)]
        self.assertEqual(ab.parse_calendar(calendar_json(ev),m),ev)
        with self.assertRaises(ProvincialCoverageError):
            ab.parse_calendar(calendar_json([(date(2026,9,30),114)]),m)
        with self.assertRaises(ProvincialCoverageError):
            ab.parse_calendar(json.dumps({"codigoError":"1","descripcionError":"x","yedata":""}),m)

    def test_audit_dynamic_window(self):
        today=date.today()
        days=[today-timedelta(days=k) for k in range(0,40,2)][::-1]
        events=[(d,i+1) for i,d in enumerate(days)]
        def fake_get(url,allowed,**kw):
            r=mock.Mock()
            if "obtenerdiaspublicacion" in url:
                first=date.fromisoformat(url.split("a=")[1])
                r.text=calendar_json([e for e in events if (e[0].year,e[0].month)==(first.year,first.month)])
            else:
                n=int(url.split("a=")[1].split("&")[0])
                d=dict((b,a) for a,b in events)[n]
                r.text=json.dumps({"codigoError":"","descripcionError":"",
                                   "yedata":sumario(number=n,day=d.strftime("%d/%m/%Y"),rows=[
                                     ("Bases de una plaza de Policía Local por oposición",
                                      f"https://bop.dipualba.es/servicesajax/descargararchivopaginaBOP/{1000+n}")])})
            return r
        with mock.patch.object(ab,"get",fake_get),mock.patch.object(ab,"pdf_header",lambda *a:None):
            feed=ab.audit()
        h=feed["historyCoverage"]
        self.assertEqual(h["rangeEnd"],today.isoformat())
        self.assertEqual(h["rangeStart"],(today-timedelta(days=29)).isoformat())
        self.assertEqual(h["issuesRead"],15)
        self.assertEqual(h["announcementsRead"],30)
        self.assertEqual(len(feed["notices"]),15)
        # Un boletín ausente en la numeración del calendario invalida la auditoría.
        del events[10]
        with mock.patch.object(ab,"get",fake_get),mock.patch.object(ab,"pdf_header",lambda *a:None):
            with self.assertRaises(ProvincialCoverageError):ab.audit()

if __name__=="__main__":
    unittest.main()
