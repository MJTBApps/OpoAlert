"""Pruebas sin red del lector del BOP de Burgos (portal simulado con HTML real abreviado)."""
import unittest,sys
from pathlib import Path
from datetime import date,timedelta
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import burgos_bop as bu
from provincial_common import ProvincialCoverageError

BASE="https://bopbur.diputaciondeburgos.es"
PUB=BASE+"/sites/default/files/private/publicado/"
DIAS=("lunes","martes","miércoles","jueves","viernes","sábado","domingo")

def anuncio(slug,n,title,level=2):
    return (f'<li id="bopbur-anuncio-{n}" class="bopbur-anuncio bopbur-anuncio-level-{level}"><p>{title}</p><p></p>'
            f'<p class="bopbur-filefield-file"><a href="{PUB}{slug}/{slug}-anuncio-{n}.pdf" type="application/pdf">'
            f'Anuncio {n} (BOPBUR-x - 120 KB)</a></p></li>')

def issue_html(slug,number,day,announcements,extra=False,full_pdf=None):
    """Página de un boletín como la del portal: cabecera, PDF completo y anuncios por sección/organismo."""
    base=slug if not extra else slug.rsplit("-",1)[0]
    full=full_pdf or (f"{PUB}{slug}/{slug}.pdf" if not extra else f"{PUB}{base}/{base}_0.pdf")
    fecha=f"{DIAS[day.weekday()]}, {day.day} de {bu.MONTHS[day.month-1]} de {day.year}"
    especial='<span class="title-especial"><a href="/x">Extraordinario</a></span>' if extra else ""
    local="".join(anuncio(slug,n,t) for n,t in announcements[1:])
    return f"""<html><body><div id="bopbur-top-boletin-1" class="bopbur-top-boletin">
<h1 class="title-bigger"><span class="title-boletin"><a href="/{slug}">Boletín Oficial de la Provincia de Burgos</a></span>{especial}</h1>
<h1 class="title-numberdate"><span class="title-number"><a href="/{slug}">núm. {number}</a></span>
<span class="title-date"><a href="/{slug}">{fecha}</a></span></h1></div>
<div class="bopbur-content-boletin"><p class="bopbur-filefield-file"><a href="{full}">Boletín Completo</a></p>
<p class="bopbur-filefield-file"><a href="{PUB}{base}/{base}-sumario.pdf">Sumario</a></p></div>
<ul class="bopbur-categorias-anuncios"><li id="bopbur-categoria-196" class="bopbur-categoria bopbur-categoria-level-0">
<h2>II. Administración Autonómica</h2>
<ul class="bopbur-categorias-anuncios"><li id="bopbur-categoria-243" class="bopbur-categoria bopbur-categoria-level-1">
<h3>Junta de Castilla y León</h3>
<ul class="bopbur-categorias-anuncios"><li id="bopbur-categoria-2369" class="bopbur-categoria bopbur-categoria-level-2">
<h4>Servicio Territorial de Agricultura</h4>
<ul class="bopbur-categorias-anuncios">{anuncio(slug,announcements[0][0],announcements[0][1],3)}</ul></li></ul></li></ul></li>
<li id="bopbur-categoria-197" class="bopbur-categoria bopbur-categoria-level-0"><h2>III. Administración Local </h2>
<ul class="bopbur-categorias-anuncios"><li id="bopbur-categoria-276" class="bopbur-categoria bopbur-categoria-level-1">
<h3>Ayuntamiento de Miranda de Ebro</h3><ul class="bopbur-categorias-anuncios">{local}</ul></li></ul></li></ul>
</body></html>"""

def month_html(entries):
    links="".join(f'<td><a href="/{slug}">Boletín BOPBUR-{d.year}-{n:03d} - {d:%d/%m/%Y}</a></td>'
                  for slug,n,d,_ in entries)
    return f'<html><body><a href="/hemeroteca/2026">Año</a><table>{links}</table></body></html>'

class FakePortal:
    """Boletín ordinario de lunes a viernes (numeración que vuelve a 1 cada año) y extraordinarios opcionales."""
    def __init__(self,first,last,extras=(),skip=(),festivos=()):
        self.issues={};self.requests=[]
        n=0;year=None;seq=0
        d=first
        while d<=last:
            if d.year!=year:year=d.year;n=0
            if d.weekday()<5 and d not in festivos:
                n+=1
                if n not in skip or d.year!=first.year:
                    self.add(f"bopbur-{d.year}-{n:03d}",n,d,False,seq)
                seq+=1
            d+=timedelta(days=1)
        for k,(num,d) in enumerate(extras):
            self.add(f"bopbur-{d.year}-{num:03d}-0",num,d,True,1000+k)
    def add(self,slug,n,d,extra,seq):
        ann=[(f"{d.year}{seq:05d}0","Toma de posesión de fincas de reemplazo"),
             (f"{d.year}{seq:05d}1","Aprobación definitiva del presupuesto general para el ejercicio de "+str(d.year))]
        if not extra and d.weekday()==1:
            ann.append((f"{d.year}{seq:05d}2","Bases de la convocatoria para cubrir en propiedad una plaza vacante "
                        "de notificador/a, mediante oposición libre"))
            ann.append((f"{d.year}{seq:05d}3","Listado definitivo de aspirantes admitidos y excluidos de la "
                        "convocatoria de una plaza de conserje"))
        self.issues[slug]=(n,d,extra,ann)
    def get(self,url):
        self.requests.append(url)
        path=url[len(BASE):]
        if path.startswith("/hemeroteca/"):
            y,m=map(int,path.rsplit("/",1)[1].split("-"))
            return month_html(sorted(((s,)+v[:3] for s,v in self.issues.items() if (v[1].year,v[1].month)==(y,m)),
                                     key=lambda x:x[2]))
        slug=path.strip("/")
        n,d,extra,ann=self.issues[slug]
        return issue_html(slug,n,d,ann,extra)

def run(portal,today):
    return bu.audit(today=today,get=portal.get,workers=1,check_pdfs=False)

class ParseTest(unittest.TestCase):
    def test_issue_entities_titles_and_pdfs(self):
        html=issue_html("bopbur-2026-207",207,date(2026,10,30),
            [("202604611","Toma de posesión provisional de las nuevas fincas"),
             ("202604609","Bases y convocatoria para cubrir una plaza de auxiliar administrativo")])
        x=bu.parse_issue(html,BASE+"/bopbur-2026-207",207,date(2026,10,30))
        self.assertFalse(x["extra"])
        a,b=x["announcements"]
        self.assertEqual(a["entity"],"Junta de Castilla y León – Servicio Territorial de Agricultura")
        self.assertEqual(b["entity"],"Ayuntamiento de Miranda de Ebro")
        self.assertEqual(b["url"],PUB+"bopbur-2026-207/bopbur-2026-207-anuncio-202604609.pdf")

    def test_extraordinary_header(self):
        html=issue_html("bopbur-2026-001-0",1,date(2026,10,12),[("202604417","Edicto")],extra=True)
        x=bu.parse_issue(html,BASE+"/bopbur-2026-001-0",1,date(2026,10,12))
        self.assertTrue(x["extra"])
        self.assertEqual(bu.label(True,1),"Extraordinario 1")

    def test_header_must_match_listing(self):
        html=issue_html("bopbur-2026-207",207,date(2026,10,30),[("202604611","Edicto")])
        with self.assertRaises(ProvincialCoverageError):
            bu.parse_issue(html,BASE+"/bopbur-2026-207",206,date(2026,10,30))

    def test_pdf_of_another_issue_rejected(self):
        html=issue_html("bopbur-2026-207",207,date(2026,10,30),[("202604611","Edicto")]).replace(
            "bopbur-2026-207/bopbur-2026-207-anuncio","bopbur-2026-206/bopbur-2026-206-anuncio")
        with self.assertRaises(ProvincialCoverageError):
            bu.parse_issue(html,BASE+"/bopbur-2026-207",207,date(2026,10,30))

    def test_pager_and_captcha_rejected(self):
        html=issue_html("bopbur-2026-207",207,date(2026,10,30),[("202604611","Edicto")])
        with self.assertRaises(ProvincialCoverageError):
            bu.parse_issue(html.replace("</body>",'<ul class="pager"><li><a href="?page=1">2</a></li></ul></body>'),
                           BASE+"/bopbur-2026-207",207,date(2026,10,30))
        self.assertTrue(bu.anti_robot('<div class="g-recaptcha">'))

    def test_month_listing(self):
        html=month_html([("bopbur-2026-001-0",1,date(2026,10,12),True),("bopbur-2026-194",194,date(2026,10,13),False)])
        self.assertEqual([(u.rsplit("/",1)[1],n) for u,n,_ in bu.parse_month(html,2026,10)],
                         [("bopbur-2026-001-0",1),("bopbur-2026-194",194)])
        with self.assertRaises(ProvincialCoverageError):
            bu.parse_month(html,2026,11)       # boletín de otro mes

    def test_only_official_host(self):
        self.assertTrue(bu.official(BASE+"/bopbur-2026-207"))
        self.assertFalse(bu.official("http://bopbur.diputaciondeburgos.es/x"))
        self.assertFalse(bu.official("https://evil.example/bopbur-2026-207"))

class AuditTest(unittest.TestCase):
    def test_window_with_extraordinary(self):
        today=date(2026,10,30)
        portal=FakePortal(date(2026,1,1),today,extras=[(1,date(2026,10,12))])
        feed=run(portal,today)
        h=feed["historyCoverage"]
        self.assertEqual((h["rangeStart"],h["rangeEnd"]),("2026-10-01","2026-10-30"))
        self.assertIn("Extraordinario 1",h["bulletins"])
        self.assertEqual(feed["coverage"]["announcementsRead"],sum(len(v[3]) for v in portal.issues.values()
                                                               if date(2026,10,1)<=v[1]<=today))
        for n in feed["notices"]:
            self.assertRegex(n["id"],r"^BU-\d{4}-\d{6,10}$")
            self.assertTrue(n["url"].startswith(PUB))
            self.assertEqual(n["province"],"Burgos")
            self.assertNotIn("admitidos",n["title"])
        self.assertEqual(len(feed["notices"]),4)       # un martes por semana
        self.assertEqual(feed["source"],"https://bopbur.diputaciondeburgos.es/")

    def test_year_change(self):
        today=date(2026,1,15)
        portal=FakePortal(date(2025,11,1),today,festivos={date(2025,12,8),date(2025,12,25),date(2026,1,1),date(2026,1,6)})
        feed=run(portal,today)
        b=feed["historyCoverage"]["bulletins"]
        self.assertIn("1",b)
        self.assertEqual(feed["historyCoverage"]["rangeStart"],"2025-12-17")
        self.assertTrue(any(n["id"].startswith("BU-2025-") for n in feed["notices"]))
        self.assertTrue(any(n["id"].startswith("BU-2026-") for n in feed["notices"]))

    def test_missing_ordinary_fails(self):
        today=date(2026,10,30)
        portal=FakePortal(date(2026,9,1),today,skip={30})     # numeración desde el 1/9: el 30 cae en octubre
        with self.assertRaises(ProvincialCoverageError):run(portal,today)

    def test_missing_previous_extraordinary_fails(self):
        today=date(2026,10,30)
        portal=FakePortal(date(2026,1,1),today,extras=[(2,date(2026,10,12))])   # falta el núm. 1
        with self.assertRaises(ProvincialCoverageError):run(portal,today)
        ok=FakePortal(date(2026,1,1),today,extras=[(1,date(2026,3,2)),(2,date(2026,10,12))])
        self.assertIn("Extraordinario 2",run(ok,today)["historyCoverage"]["bulletins"])

    def test_stale_portal_fails(self):
        portal=FakePortal(date(2026,9,1),date(2026,10,20))
        with self.assertRaises(ProvincialCoverageError):run(portal,date(2026,10,30))

    def test_duplicate_announcement_fails(self):
        today=date(2026,10,30)
        portal=FakePortal(date(2026,9,1),today)
        slugs=sorted(s for s,v in portal.issues.items() if v[1]>=date(2026,10,5))
        n,d,e,ann=portal.issues[slugs[1]]
        portal.issues[slugs[1]]=(n,d,e,[portal.issues[slugs[0]][3][0]]+ann[1:])
        with self.assertRaises(ProvincialCoverageError):run(portal,today)

    def test_no_fixed_dates_in_source(self):
        src=Path(bu.__file__).read_text(encoding="utf-8")
        code="\n".join(l for l in src.splitlines() if not l.lstrip().startswith("#") and "MIN_ISSUES=" not in l)
        code=code.split('"""',2)[2]     # sin el docstring
        self.assertNotRegex(code,r"\b20[2-3]\d\b")

if __name__=="__main__":
    unittest.main()
