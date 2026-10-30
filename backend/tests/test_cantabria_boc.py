import json,sys,unittest
from datetime import date,datetime,timedelta
from pathlib import Path
from unittest import mock
from zoneinfo import ZoneInfo
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cantabria_boc as cb
from provincial_common import ProvincialCoverageError

MES=("","enero","febrero","marzo","abril","mayo","junio","julio","agosto",
     "septiembre","octubre","noviembre","diciembre")
HTML={"Content-Type":"text/html;charset=ISO-8859-1"}

def label(d):
    return f"{d.day:02d} de {MES[d.month]} de {d.year}"

def row(kind,num,d,bid):
    milis=int(datetime(d.year,d.month,d.day,tzinfo=ZoneInfo("Europe/Madrid")).timestamp()*1000)
    return {"id":bid,"fecBol":"x","tipoBol":kind,"numBol":num,"fecBolString":label(d),"fecBolMilis":milis}

def day_page(d,extras):
    """Página oficial de un día con varios extraordinarios: extras=[(número, id)]."""
    out=['<div class="infor"><h1>Boletines Extraordinarios</h1>']
    for n,i in extras:
        out.append(f'<div><a name="contenido" href="verBoletinExtraordinario.do?id={i}" title="Boletin Extraordinario">'
                   f'\n <span class="negrita">\n  Bolet&iacute;n Extraordinario {label(d)} \n  N&uacute;mero {n}\n </span>\n</a></div><hr />')
    return "".join(out)

def issue_page(d,kind,number,items,refs=()):
    """items: [(sección, subsección, organismo, suborganismo, título, blob, cve)]."""
    tag="ORD" if kind==cb.ORD else "EXT"
    out=[f'<span class="titulo2">BOC {d:%d/%m/%Y} N&uacute;m. {number}</span>',
         f'<span class="titulo2">Bolet&iacute;n Oficial de Cantabria: {label(d)}, {tag}. N&uacute;m. {number}</span>',
         '<a href="verPdfAction.do?idBlob=1&amp;tipoPdf=0">(BOC-2026-1 - 2 Mb)</a>']
    last=(None,None,None)
    for sec,sub,h4,h6,title,blob,cve in items:
        if sec!=last[0]:out.append(f'<a name="s"></a>\n<span class="titulo2 margin-bottom-12">{sec}</span>')
        if sub and (sec,sub)!=last[:2]:out.append(f'<span class="spanH5">{sub}</span>')
        if (sec,sub,h4)!=last:out.append(f'<a name="d"></a><span class="spanH4">{h4}</span>\n<div class="margin-top-24"></div>')
        if h6:out.append(f'<span class="spanH6">{h6}</span>')
        out.append(f'<p>{title}</p>\n<div class="enlacesDoc">\n<div class="tipoPDFanuncio">\n'
                   f'<a href="verAnuncioAction.do?idAnuBlob={blob}" title="t" target="blank">PDF (BOC-{d.year}-{cve} - 300 Kb)</a>\n</div>')
        for lab,rb in refs:
            if rb==blob:out.append(f'<div class="tipoPDFanuncio">\n<span class="negritaAnuncio">{lab} </span>'
                                   f'<a href="verAnuncioAction.do?idAnuBlob={blob+900000}" title="t" target="blank">PDF (BOC-{d.year}-1 - 1 Kb)</a>\n</div>')
        out.append('</div>')
        last=(sec,sub,h4)
    out.append('</div>\n<footer>pie</footer>')
    return "\n".join(out)

def issue_xml(kind,year,items):
    tag="ORD" if kind==cb.ORD else "EXT"
    parts=[f'<?xml version="1.0" encoding="UTF-8"?><root><num_pag>1</num_pag><tipo_boletin>{tag}</tipo_boletin>'
           f'<num_disposiciones>{len(items)}</num_disposiciones><boletin><detalle_texto>']
    for *_,blob,cve in items:
        parts.append(f'<disposicion><numeroExp>CVE-{year}-{cve}\t</numeroExp><texto><p>x</p>'
                     f'<num_exp url="https://boc.cantabria.es/boces/verAnuncioAction.do?idAnuBlob={blob}">{year}/{cve}</num_exp></texto></disposicion>')
    return "".join(parts+["</detalle_texto></boletin></root>"])

S22=("2.Autoridades y Personal","2.2.Cursos, Oposiciones y Concursos")
S21=("2.Autoridades y Personal","2.1.Nombramientos, Ceses y Otras Situaciones")
S4=("4.Econom&iacute;a, Hacienda y Seguridad Social","4.1.Actuaciones en materia Presupuestaria")

def workdays(first,last):
    d=first
    while d<=last:
        if d.weekday()<5:yield d
        d+=timedelta(days=1)

class Portal:
    """Portal falso: listados mensuales, páginas de día, sumarios, XML y PDF."""
    def __init__(self):
        self.urls={}
        self.months={}
        self.issues={}
        self.next_id=50000
        self.cve=100
    def bid(self):
        self.next_id+=1;return self.next_id
    def add_month(self,y,m,rows):
        self.months.setdefault((y,m),[]).extend(rows)
    def add_issue(self,d,kind,number,bid,items):
        self.issues[(d,kind,number)]=(bid,items)
        self.urls[cb.issue_url(kind,bid)]=(issue_page(d,kind,number,items).encode("latin-1","xmlcharrefreplace"),HTML)
        self.urls[cb.xml_url(bid)]=(issue_xml(kind,d.year,items).encode("utf-8"),{"Content-Type":"text/xml"})
        for *_,blob,cve in items:
            self.urls[f"https://boc.cantabria.es/boces/verAnuncioAction.do?idAnuBlob={blob}"]=(
                b"%PDF-1.7 ...",{"Content-Type":"application/pdf","Content-Disposition":f"inline; filename={d.year}-{cve}.pdf"})
    def items(self,d,with_candidate):
        self.cve+=2
        out=[(*S4,"Ayuntamiento de Noja","","Aprobaci&oacute;n definitiva del presupuesto general.",self.cve*10,self.cve)]
        if with_candidate:
            out.append((*S22,"Ayuntamiento de Laredo","",
                        "Bases reguladoras y convocatoria del proceso selectivo para cubrir una plaza de Auxiliar Administrativo.",
                        self.cve*10+1,self.cve+1))
        return out
    def fetch(self,url,attempts=3,limit=0):
        for (y,m),rows in self.months.items():
            if url==cb.month_url(y,m):return json.dumps(rows).encode(),{"Content-Type":"application/json"}
        if url not in self.urls:raise AssertionError("URL no prevista "+url)
        return self.urls[url]

def year_change_portal(gap=False,hide_varios=False):
    """Diciembre de 2025 y enero de 2026: ordinarios, un extraordinario y un día con varios."""
    p=Portal()
    dec=list(workdays(date(2025,11,28),date(2025,12,31)))
    jan=list(workdays(date(2026,1,2),date(2026,1,15)))
    numbers=[(d,239+i) for i,d in enumerate(dec)]+[(d,1+i) for i,d in enumerate(jan)]
    if gap:numbers=[(d,n+1 if d>=date(2026,1,9) else n) for d,n in numbers]
    for d,n in numbers:
        bid=p.bid();p.add_month(d.year,d.month,[row(cb.ORD,n,d,bid)])
        p.add_issue(d,cb.ORD,n,bid,p.items(d,d.day%3==0))
    # Extraordinarios: 25 antes de la ventana, 26 en la ventana, 27-28 el mismo día (tipo 3), 1 en enero.
    def extra(d,n,kind):
        bid=p.bid()
        if kind is not None:p.add_month(d.year,d.month,[row(kind,n,d,bid)])
        p.add_issue(d,cb.EXT,n,bid,p.items(d,False))
        return bid
    extra(date(2025,12,10),25,cb.EXT)
    extra(date(2025,12,19),26,cb.EXT)
    d=date(2025,12,29)
    b27=extra(d,27,cb.EXTS);b28=extra(d,28,None)
    shown=[(27,b27)] if hide_varios else [(27,b27),(28,b28)]
    p.urls[cb.day_url(d)]=(day_page(d,shown).encode("latin-1"),HTML)
    extra(date(2026,1,13),1,cb.EXT)
    return p

class ParseTest(unittest.TestCase):
    def test_month_listing(self):
        d=date(2026,10,30)
        rows=cb.parse_month(json.dumps([row(0,209,d,47365),row(3,19,date(2026,10,5),46967)]),2026,10)
        self.assertEqual(rows,[(0,209,d,47365),(3,19,date(2026,10,5),46967)])

    def test_month_listing_rejects_wrong_date(self):
        bad=row(0,209,date(2026,10,30),1);bad["fecBolMilis"]-=86_400_000
        with self.assertRaises(ProvincialCoverageError):cb.parse_month(json.dumps([bad]),2026,10)
        with self.assertRaises(ProvincialCoverageError):
            cb.parse_month(json.dumps([row(2,1,date(2026,10,30),1)]),2026,10)

    def test_day_with_several_extraordinaries(self):
        d=date(2026,10,5)
        self.assertEqual(cb.parse_day(day_page(d,[(20,46985),(19,46967)]),d),[(19,46967),(20,46985)])
        with self.assertRaises(ProvincialCoverageError):cb.parse_day(day_page(d,[(19,46967)]),date(2026,10,6))

    def test_issue_page_sections_entities_and_corrections(self):
        d=date(2026,10,30)
        items=[(*S22,"Ayuntamiento de Santo&ntilde;a","","Bases y convocatoria de una plaza de Conserje.",442371,8450),
               (*S22,"Consejer&iacute;a de Salud","Servicio C&aacute;ntabro de Salud","Lista definitiva de admitidos.",442372,8451),
               (*S4,"Ayuntamiento de Ruesga","","Presupuesto general de 2026.",442438,8503)]
        html=issue_page(d,cb.ORD,209,items,refs=[("Corrige a",442372),("Es corregido por",442438)])
        out=cb.parse_issue(html,d,cb.ORD,209)
        self.assertEqual([(y,c,b) for y,c,b,*_ in out],[(2026,8450,442371),(2026,8451,442372),(2026,8503,442438)])
        self.assertEqual(out[0][4],"Ayuntamiento de Santoña")
        self.assertEqual(out[1][4],"Consejería de Salud. Servicio Cántabro de Salud")
        self.assertEqual(out[0][5],"2.2.Cursos, Oposiciones y Concursos")
        self.assertEqual(cb.parse_xml(issue_xml(cb.ORD,2026,items).encode(),cb.ORD,209),
                         {(2026,8450):442371,(2026,8451):442372,(2026,8503):442438})

    def test_issue_page_inconsistencies_fail(self):
        d=date(2026,10,30)
        items=[(*S22,"Ayuntamiento de Noja","","Bases y convocatoria.",1,2)]
        html=issue_page(d,cb.ORD,209,items)
        for bad_day,kind,num in ((date(2026,10,29),cb.ORD,209),(d,cb.EXT,209),(d,cb.ORD,208)):
            with self.assertRaises(ProvincialCoverageError):cb.parse_issue(html,bad_day,kind,num)
        with self.assertRaises(ProvincialCoverageError):   # título sin PDF
            cb.parse_issue(html.replace("<div class=\"enlacesDoc\">","<p>Otro</p><div class=\"enlacesDoc\">"),d,cb.ORD,209)
        with self.assertRaises(ProvincialCoverageError):   # enlace extra no reconocido
            cb.parse_issue(html.replace("</footer>","</footer>").replace("<footer>",'<a href="verAnuncioAction.do?idAnuBlob=9">x</a><footer>'),d,cb.ORD,209)
        with self.assertRaises(ProvincialCoverageError):   # referencia desconocida
            cb.parse_issue(issue_page(d,cb.ORD,209,items,refs=[("Anexo de",1)]),d,cb.ORD,209)
        with self.assertRaises(ProvincialCoverageError):   # XML con otro número de disposiciones
            cb.parse_xml(issue_xml(cb.ORD,2026,items).replace("<num_disposiciones>1<","<num_disposiciones>2<").encode(),cb.ORD,209)

    def test_classification_is_conservative(self):
        sec="2.2.Cursos, Oposiciones y Concursos"
        yes={"Bases y convocatoria para la formación de una bolsa de empleo de personal Conserje-Notificador.":"Bolsa de trabajo",
             "Bases específicas y convocatoria del procedimiento de selección para el nombramiento, como funcionario/a interino/a, de una plaza de Arquitecto.":"Plaza / oposición",
             "Orden PRE/142/2026, por la que se convoca el proceso selectivo para el ingreso por el turno libre, mediante el sistema de oposición, en el Cuerpo de Gestión.":"Plaza / oposición"}
        for title,kind in yes.items():self.assertEqual(cb.kind(title,sec),kind,title)
        for title in ("Lista definitiva de personas aspirantes admitidas y excluidas del proceso selectivo de una plaza de Arquitecto.",
                      "Resolución por la que se hace pública la relación de aspirantes que han superado las pruebas selectivas.",
                      "Resolución por la que se hace pública la bolsa de trabajo de Ayudante de Museos.",
                      "Resolución de modificación del número de plazas convocadas de Bomberos por caducidad de tres plazas.",
                      "Apertura del plazo de presentación de solicitudes para la cobertura del cargo de Juez de Paz Titular.",
                      "Orden PRE/153/2026, por la que se convoca la provisión, mediante el sistema de libre designación, del puesto 7646.",
                      "Nombramiento del Tribunal Calificador y fecha del primer ejercicio del proceso selectivo."):
            self.assertIsNone(cb.kind(title,sec),title)
        self.assertIsNone(cb.kind("Bases y convocatoria de una bolsa de empleo de Conserje.","2.1.Nombramientos, Ceses y Otras Situaciones"))
        self.assertIsNone(cb.kind("Convocatoria para la selección del cartel del Carnaval 2027.","6.Subvenciones y Ayudas"))

class CalendarTest(unittest.TestCase):
    def run_calendar(self,portal,today):
        with mock.patch.object(cb,"fetch",portal.fetch),mock.patch.object(cb,"PAUSE",0):
            return cb.calendar(today)

    def test_year_change_extraordinary_series_and_varios(self):
        start,issues=self.run_calendar(year_change_portal(),date(2026,1,15))
        self.assertEqual(start,date(2025,12,17))
        ords=[n for _,k,n,_ in issues if k==cb.ORD]
        self.assertEqual(ords[0],239+len(list(workdays(date(2025,11,28),date(2025,12,16)))))
        self.assertEqual(ords[-len(list(workdays(date(2026,1,2),date(2026,1,15)))):][0],1)
        self.assertEqual([n for _,k,n,_ in issues if k==cb.EXT],[26,27,28,1])

    def test_missing_ordinary_fails(self):
        with self.assertRaises(ProvincialCoverageError):
            self.run_calendar(year_change_portal(gap=True),date(2026,1,15))

    def test_hidden_extraordinary_of_varios_day_fails(self):
        with self.assertRaises(ProvincialCoverageError):
            self.run_calendar(year_change_portal(hide_varios=True),date(2026,1,15))

    def test_window_is_dynamic(self):
        # Mismo portal, otro "hoy": la ventana se mueve con la fecha, sin nada fijo.
        start,issues=self.run_calendar(year_change_portal(),date(2026,1,9))
        self.assertEqual(start,date(2025,12,11))
        self.assertTrue(all(start<=d<=date(2026,1,9) for d,*_ in issues))

class AuditTest(unittest.TestCase):
    def test_full_audit_feed(self):
        p=year_change_portal()
        with mock.patch.object(cb,"fetch",p.fetch),mock.patch.object(cb,"PAUSE",0):
            feed=cb.audit(today=date(2026,1,15))
        h=feed["historyCoverage"]
        self.assertEqual(feed["province"],"Cantabria (BOC)")
        self.assertEqual(feed["source"],"https://boc.cantabria.es/boces/")
        self.assertEqual((h["rangeStart"],h["rangeEnd"]),("2025-12-17","2026-01-15"))
        self.assertEqual(h["extraordinaryBulletins"],["Ext. 26","Ext. 27","Ext. 28","Ext. 1"])
        self.assertEqual(h["issuesRead"],len(h["bulletins"]))
        self.assertEqual(feed["coverage"]["announcementsRead"],h["issuesRead"]+len(feed["notices"]))
        for n in feed["notices"]:
            self.assertRegex(n["id"],r"^CN-\d{4}-\d{1,6}$")
            self.assertTrue(n["url"].startswith("https://boc.cantabria.es/boces/verAnuncioAction.do?idAnuBlob="))
            self.assertEqual(n["type"],"Plaza / oposición")

    def test_html_and_xml_disagree_fails(self):
        p=year_change_portal()
        bid,_=p.issues[(date(2026,1,14),cb.ORD,9)]
        url=cb.xml_url(bid)
        body,headers=p.urls[url]
        p.urls[url]=(body.replace(b"<num_disposiciones>",b"<num_disposiciones>9"),headers)
        with mock.patch.object(cb,"fetch",p.fetch),mock.patch.object(cb,"PAUSE",0):
            with self.assertRaises(ProvincialCoverageError):cb.audit(today=date(2026,1,15))

    def test_pdf_must_match_cve(self):
        p=year_change_portal()
        _,items=p.issues[(date(2026,1,15),cb.ORD,10)]
        self.assertEqual(len(items),2)   # el 15 trae una candidata
        url=f"https://boc.cantabria.es/boces/verAnuncioAction.do?idAnuBlob={items[1][5]}"
        p.urls[url]=(b"%PDF-1.7",{"Content-Type":"application/pdf","Content-Disposition":"inline; filename=2025-1.pdf"})
        with mock.patch.object(cb,"fetch",p.fetch),mock.patch.object(cb,"PAUSE",0):
            with self.assertRaises(ProvincialCoverageError):cb.audit(today=date(2026,1,15))

if __name__=="__main__":
    unittest.main()
