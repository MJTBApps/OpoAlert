"""Pruebas sin red del lector del BOP de Cuenca (www.dipucuenca.es/boletin1)."""
import sys,unittest
from datetime import date,timedelta
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cuenca_bop as cu
from provincial_common import ProvincialCoverageError

P=cu.BULLETINS
DAYS_ES=["lunes","martes","miércoles","jueves","viernes","sábado","domingo"]

def detail_url(aid):
    return (f"https://www.dipucuenca.es/boletin1?p_p_id=as_asac_bulletins_web_BulletinsWebPortlet_INSTANCE_LuthFM11tPwH"
            f"&p_p_lifecycle=0&{P}_mvcPath=%2Fpublisher%2Fdetail.jsp&{P}_articleId={aid}")

def card(day,label,aid):
    sub=f"{DAYS_ES[day.weekday()]}, {day.day:02d} de {cu.MONTHS[day.month-1]} {day.year}"
    u=detail_url(aid).replace("&","&amp;")
    return (f'<div class="card card-box"><a class="image-wrapper" href="{u}"></a><div class="card-body">'
            f'<span class="card-text">{label}</span><a href="{u}"><span class="card-subtitle">{sub}</span></a></div></div>')

def listing(cards,total=None):
    total=len(cards) if total is None else total
    shown=len(cards)
    return (f'<div class="row">{"".join(cards)}</div>'
            f'<p class="pagination-results">Mostrando el intervalo 1 - {shown} de {total} resultados.</p>')

def calendar(days):
    out=[]
    for d in days:
        v=d.strftime("%d%%2F%m%%2F%Y")
        out.append(f'<a href="https://www.dipucuenca.es/boletin1?p_p_id=x&amp;p_r_p_endDate={v}&amp;p_r_p_startDate={v}">{d.day}</a>')
    # enlaces a otros meses y años: se ignoran
    out.append('<a href="https://www.dipucuenca.es/boletin1?p_r_p_endDate=31%2F10%2F2025&amp;p_r_p_startDate=01%2F10%2F2025">2025</a>')
    return "".join(out)

def detail(day,entries,supplement=False,folder="2177570",full="81f6fd36-0d87-6c0e-1f90-7f2a23d9ac16"):
    """entries: [(sección, organismo, título)] -> ficha con PDF 1..N."""
    title=f"Boletín {day.isoformat()}"+("-SUPLEMENTO" if supplement else "")
    html=[f'<article class="template template-detail template-boletin-detail">'
          f'<div class="portlet-title-wrapper"><div class="portlet-title h3">{title}</div></div>'
          f'<span class="image-wrapper-panel-info"><a href="/documents/34525/{full}?t=1793345470587">BOP completo</a></span>']
    k=0
    for i,(section,agency,t) in enumerate(entries):
        k+=1
        html.append(f'<div class="card card-clean"><div class="card-title h4">{section}</div><div class="collapse">'
                    f'<div class="h5 title-wrapper">{agency}.</div><ul><li class="document-entry">'
                    f'<a class="document" href="/documents/34525/{folder}/{k}.pdf/53c0dfbc-9244-2e87-e074-882a8446c29e?t=1">'
                    f'<span class="title ml-2">{t}</span></a></li></ul></div></div>')
    html.append("</article>")
    return "".join(html)

def notice_pdf(bulletin,day,num,supplement=False):
    wd=DAYS_ES[day.weekday()].capitalize()
    pre="SUPLEMENTO - " if supplement else ""
    return (f"B O L E T I N O F I C I A L D E L A P R O V I N C I A D E C U E N C A\nNúm. {bulletin}\t\n"
            f"{pre}{wd} {day.day} de {cu.MONTHS[day.month-1]} de {day.year}\t\nPág. 3\nNÚM. {num}\n"
            f"AYUNTAMIENTO\nA N U N C I O\nResolución de 2 de enero de 2020 ...\n")

class ParseTest(unittest.TestCase):
    D=date(2026,10,30)
    def test_listing_and_supplement(self):
        h=listing([card(self.D,"125",1),card(date(2026,6,29),"73-1",2)])
        rows=cu.parse_listing(h)
        self.assertEqual([(d,n) for d,n,_ in rows],[(self.D,"125"),(date(2026,6,29),"73-1")])
        self.assertEqual(cu.main_number("73-1"),(73,1))
        self.assertEqual(cu.main_number("125"),(125,0))
    def test_listing_must_be_complete(self):
        with self.assertRaises(ProvincialCoverageError):
            cu.parse_listing(listing([card(self.D,"125",1)],total=2))
        with self.assertRaises(ProvincialCoverageError):
            cu.parse_listing(listing([card(self.D,"12a",1)]))
    def test_calendar(self):
        days=[date(2026,10,2),date(2026,10,30)]
        self.assertEqual(cu.calendar_days(calendar(days),2026,10),set(days))
        self.assertEqual(cu.calendar_days(calendar(days),2026,9),set())
    def test_issue(self):
        full,rows=cu.parse_issue(detail(self.D,[("DIPUTACIÓN PROVINCIAL DE CUENCA","Servicio de Personal",
            "Bases de la convocatoria de 2 plazas de sargento"),("ADMINISTRACIÓN LOCAL","Ayuntamiento de Cuenca","Ordenanza fiscal")]),self.D)
        self.assertEqual(full,"https://www.dipucuenca.es/documents/34525/81f6fd36-0d87-6c0e-1f90-7f2a23d9ac16")
        self.assertEqual(len(rows),2)
        self.assertEqual(rows[0][0],"Servicio de Personal")
        self.assertEqual(rows[1][2],"https://www.dipucuenca.es/documents/34525/2177570/2.pdf/53c0dfbc-9244-2e87-e074-882a8446c29e")
        self.assertEqual(rows[1][3],2)
    def test_issue_rejects(self):
        e=[("S","Ayuntamiento de A","Anuncio")]
        with self.assertRaises(ProvincialCoverageError):cu.parse_issue(detail(self.D,e),self.D-timedelta(days=2))
        with self.assertRaises(ProvincialCoverageError):cu.parse_issue(detail(self.D,e,supplement=True),self.D)
        dup=detail(self.D,e*3).replace("/2.pdf/","/1.pdf/")
        with self.assertRaises(ProvincialCoverageError):cu.parse_issue(dup,self.D)
        # Hueco en la numeración de los PDF (anuncio retirado): se admite, lo decide el BOP completo.
        gap=detail(self.D,e*3).replace("/2.pdf/","/7.pdf/")
        self.assertEqual(len(cu.parse_issue(gap,self.D)[1]),3)
        other=detail(self.D,e).replace("/documents/34525/2177570/","/otra/")
        with self.assertRaises(ProvincialCoverageError):cu.parse_issue(other,self.D)
    def test_notice_number(self):
        self.assertEqual(cu.notice_number(notice_pdf(125,self.D,2556),self.D,125),2556)
        blank=notice_pdf(125,self.D,"")
        self.assertIsNone(cu.notice_number(blank,self.D,125))
        no_date=notice_pdf(125,self.D,2556).replace("Viernes 30 de octubre de 2026","﻿")
        self.assertEqual(cu.notice_number(no_date,self.D,125),2556)
        with self.assertRaises(ProvincialCoverageError):cu.notice_number(notice_pdf(124,self.D,2556),self.D,125)
        with self.assertRaises(ProvincialCoverageError):
            cu.notice_number(notice_pdf(125,self.D-timedelta(days=2),2556),self.D,125)
        typo=notice_pdf(125,self.D,1886).replace("NÚM. 1886","NÍM. 1886")
        self.assertEqual(cu.notice_number(typo,self.D,125),1886)
        self.assertEqual(cu.notice_number(notice_pdf(125,self.D,1891).replace("NÚM. 1891","NÚM 1891"),self.D,125),1891)
    def test_full_pdf_counts(self):
        pages=["SUMARIO\nDIPUTACIÓN\nServicio de Personal.— Bases de\nla convocatoria.\nAyuntamiento de A.— Ordenanza.",
               notice_pdf(125,self.D,1)+notice_pdf(125,self.D,""),notice_pdf(125,self.D,3)]
        self.assertEqual(cu.full_pdf_counts(pages),(2,3))
        with self.assertRaises(ProvincialCoverageError):cu.full_pdf_counts(pages[1:])
    def test_kind(self):
        self.assertIsNone(cu.kind("Aprobación definitiva presupuesto general, bases de ejecución y plantilla de personal 2026."))
        self.assertEqual(cu.kind("Bases de la convocatoria de 3 plazas operario/a mantenimiento por concurso-oposición."),"Plaza / oposición")
        self.assertEqual(cu.kind("Bases de la convocatoria para constitución de bolsa de trabajo de limpieza"),"Bolsa de trabajo")
        self.assertIsNone(cu.kind("Aprobación definitiva de aspirantes admitidos y excluidos de dos plazas de policía local"))

class FakeResponse:
    def __init__(self,text):self.text=text

class AuditTest(unittest.TestCase):
    """Portal simulado: lunes, miércoles y viernes, numeración que vuelve a 1 en enero."""
    def build(self,first,last,supplement_on=None):
        self.issues={};number={};n=180;aid=1000
        d=first
        while d<=last:
            if d.month==1 and d.day==1:n=0
            if d.weekday() in (0,2,4) and not (d.month==1 and d.day==1):
                n+=1;aid+=1
                self.issues[aid]=(d,str(n),False)
                if d==supplement_on:
                    aid+=1;self.issues[aid]=(d,f"{n}-1",True)
            d+=timedelta(days=1)
    def fake_get(self,url,allowed,**kw):
        q=parse_qs(urlsplit(url).query)
        if P+"_articleId" in q:
            d,label,sup=self.issues[int(q[P+"_articleId"][0])]
            ents=[("ADMINISTRACIÓN LOCAL","Ayuntamiento de Tarancón","Bases convocatoria 6 plazas policía local por oposición libre."),
                  ("ADMINISTRACIÓN LOCAL","Ayuntamiento de Huete","Ordenanza fiscal de la tasa de agua.")]
            return FakeResponse(detail(d,ents,supplement=sup,folder=str(int(q[P+"_articleId"][0]))))
        st=date(*reversed([int(x) for x in q["p_r_p_startDate"][0].split("/")]))
        en=date(*reversed([int(x) for x in q["p_r_p_endDate"][0].split("/")]))
        sel=[(a,x) for a,x in sorted(self.issues.items()) if st<=x[0]<=en]
        cal=[x[0] for a,x in self.issues.items() if (x[0].year,x[0].month)==(st.year,st.month)]
        return FakeResponse(listing([card(x[0],x[1],a) for a,x in sel])+calendar(sorted(set(cal))))
    def fake_pdf(self,url,pages=1):
        if pages is None:   # BOP completo: sumario con 2 entradas y 2 anuncios
            return ["SUMARIO\nAyuntamiento de Tarancón.— Bases.\nAyuntamiento de Huete.— Ordenanza.","NÚM. 1\nx\nNÚM. 2\n"]
        folder=int(urlsplit(url).path.split("/")[3])
        d,label,sup=self.issues[folder]
        main=cu.main_number(label)[0]
        return [notice_pdf(main,d,folder % 100000,supplement=sup)]
    def run_audit(self,today):
        old=(cu.get,cu.pdf_pages)
        cu.get,cu.pdf_pages=self.fake_get,lambda url,pages=1:self.fake_pdf(url,pages)
        try:return cu.audit(today=today)
        finally:cu.get,cu.pdf_pages=old
    def test_sunday_window(self):
        self.build(date(2026,9,1),date(2026,11,1))
        f=self.run_audit(date(2026,11,1))
        h=f["historyCoverage"]
        self.assertEqual(h["rangeStart"],"2026-10-03");self.assertEqual(h["rangeEnd"],"2026-11-01")
        self.assertEqual(h["issuesRead"],12);self.assertEqual(h["announcementsRead"],24)
        self.assertEqual(len(f["notices"]),12)
        self.assertTrue(all(n["id"].startswith("CU-2026-") for n in f["notices"]))
        self.assertEqual(f["source"],"https://www.dipucuenca.es/boletin1")
    def test_year_change_and_supplement(self):
        self.build(date(2025,12,1),date(2026,1,20),supplement_on=date(2026,1,7))
        f=self.run_audit(date(2026,1,15))
        b=f["historyCoverage"]["bulletins"]
        self.assertIn("1",b);self.assertIn("3-1",b)
        self.assertEqual(b[b.index("3")+1],"3-1")
    def test_missing_bulletin_fails(self):
        self.build(date(2026,9,1),date(2026,10,30))
        gone=[a for a,x in self.issues.items() if x[0]==date(2026,10,14)][0]
        d,label,sup=self.issues.pop(gone)
        with self.assertRaises(ProvincialCoverageError):self.run_audit(date(2026,10,30))
    def test_full_pdf_mismatch_fails(self):
        self.build(date(2026,9,1),date(2026,10,30))
        old=self.fake_pdf
        # La web lista 2 anuncios; el BOP completo trae 3 en el sumario y 3 cabeceras.
        self.fake_pdf=lambda url,pages=1:(["SUMARIO\nA.— a\nB.— b\nC.— c","NÚM. 1\nNÚM. 2\nNÚM. 3\n"]
                                          if pages is None else old(url,pages))
        with self.assertRaises(ProvincialCoverageError):self.run_audit(date(2026,10,30))
    def test_full_pdf_one_count_differs(self):
        # El sumario impreso omite un anuncio pero las cabeceras cuadran: se acepta.
        self.build(date(2026,9,1),date(2026,10,30))
        old=self.fake_pdf
        self.fake_pdf=lambda url,pages=1:(["SUMARIO\nA.— a","NÚM. 1\nNÚM. 2\n"] if pages is None else old(url,pages))
        self.assertEqual(self.run_audit(date(2026,10,30))["historyCoverage"]["announcementsRead"],26)

if __name__=="__main__":unittest.main()
