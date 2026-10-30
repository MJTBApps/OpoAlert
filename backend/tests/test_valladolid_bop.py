import json,sys,unittest
from datetime import date,timedelta
from pathlib import Path
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import valladolid_bop as vd
from provincial_common import ProvincialCoverageError

MES=vd.MONTHS
PDF="https://bop.sede.diputaciondevalladolid.es/boletines/{y}/{m}/{d:02d}/BOPVA-A-{y}-{n:05d}.pdf"

def issue_page(day,number,items):
    """items: [(n.º anuncio, organismo, título)] como la página oficial de una edición."""
    lis=[]
    for n,entity,title in items:
        url=PDF.format(y=day.year,m=MES[day.month-1],d=day.day,n=n)
        lis.append(f'''<li class="un_anuncio"><div class="col_izquierda">
<p class="bop_tit_articulo">{entity}</p>
<p class="bop_res_articulo"><a href="{url}" title="{title}" target="_blank">{title}</a></p>
<p class="bop_enlaces_articulo noprint"><a href="{url}" title="Versión pdf">PDF</a></p></div></li>''')
    return f'''<div id="un_bop"><h1 id="bop_sumario_tit">
BOLETIN Nº {day.year}/{number}
</h1><h2 id="bop_sumario_tit_fecha">{day.day:02d} de {MES[day.month-1]} de {day.year}</h2>
<div id="listado_anuncios"><ul class="listado_anuncios"><li class="una_seccion">
<p class="titulo_secc_boletin">III.-ADMINISTRACIÓN LOCAL</p><ul>{"".join(lis)}</ul></li></ul></div></div>'''

NOT_FOUND='<div id="un_bop"><h3>Boletín no encontrado</h3></div>'

def workdays(first,last):
    d=first
    while d<=last:
        if d.weekday()<5 and (d.month,d.day) not in ((1,1),(12,25)):yield d
        d+=timedelta(days=1)

def build(first,last,first_number,first_ann,per_issue=3,titles=None):
    """Portal simulado: calendario mensual + una edición por día laborable."""
    pages={};cal={};n=first_number;a=first_ann;prev_year=None
    for d in workdays(first,last):
        if prev_year is not None and d.year!=prev_year:n=1;a=1
        prev_year=d.year
        items=[]
        for i in range(per_issue):
            title=(titles or {}).get((d,i),"Aprobación definitiva de la ordenanza fiscal.")
            items.append((a,"AYUNTAMIENTO DE PRUEBA",title));a+=1
        pages[vd.issue_url(d)]=issue_page(d,n,items)
        cal.setdefault((d.year,d.month),[]).append(d.isoformat())
        n+=1
    for y,m in vd.months(first,last):
        pages[vd.calendar_url(y,m)]=json.dumps(cal.get((y,m),[]))
    return pages

def fake(pages):
    def fetch(url,attempts=3,pdf=False):
        if pdf:return b"%PDF-"
        if url not in pages:raise AssertionError("URL no prevista "+url)
        return pages[url]
    return fetch

class ParseTest(unittest.TestCase):
    def test_issue(self):
        d=date(2026,10,15)
        num,items=vd.parse_issue(issue_page(d,198,[(2993,"MANCOMUNIDAD X","Bases."),(2992,"DIPUTACIÓN","Otro.")]),d)
        self.assertEqual(num,198)
        self.assertEqual([x[0] for x in items],[2992,2993])
        self.assertTrue(items[0][3].endswith("/boletines/2026/octubre/15/BOPVA-A-2026-02992.pdf"))

    def test_not_found_fails(self):
        with self.assertRaises(ProvincialCoverageError):vd.parse_issue(NOT_FOUND,date(2026,10,17))

    def test_other_date_fails(self):
        with self.assertRaises(ProvincialCoverageError):
            vd.parse_issue(issue_page(date(2026,10,14),197,[(1,"A","B")]),date(2026,10,15))

    def test_foreign_pdf_fails(self):
        d=date(2026,10,15)
        page=issue_page(d,198,[(5,"A","B")]).replace("bop.sede.diputaciondevalladolid.es","example.org")
        with self.assertRaises(ProvincialCoverageError):vd.parse_issue(page,d)

    def test_calendar_other_month_fails(self):
        with self.assertRaises(ProvincialCoverageError):vd.parse_calendar('["2026-09-30"]',2026,10)

    def test_kind(self):
        self.assertEqual(vd.kind("Convocatoria y bases para la provisión de una plaza de Capataz mediante concurso-oposición."),"Plaza / oposición")
        self.assertEqual(vd.kind("Bases generales y convocatoria para la creación de una bolsa de trabajo de técnico de guardería."),"Bolsa de trabajo")
        for t in ("Resolución por la que se nombra personal funcionario de carrera en 20 plazas de Administrativo.",
                  "Aprobados en el proceso selectivo para la provisión de 2 plazas de Psicólogo/a.",
                  "Señalamiento de nueva fecha para la primera prueba de la fase de oposición.",
                  "Aprobación definitiva del presupuesto general."):
            self.assertIsNone(vd.kind(t),t)

class AuditTest(unittest.TestCase):
    def run_audit(self,pages,today):
        with mock.patch.object(vd,"fetch",fake(pages)),mock.patch.object(vd.time,"sleep"):
            return vd.audit(today=today)

    def test_window_and_feed(self):
        today=date(2026,10,30)
        first=today-timedelta(days=40)
        titles={(today,0):"Convocatoria y bases para la provisión de una plaza de Peón mediante concurso-oposición."}
        feed=self.run_audit(build(first,today,170,2600,titles=titles),today)
        h=feed["historyCoverage"]
        self.assertEqual(h["rangeStart"],"2026-10-01");self.assertEqual(h["rangeEnd"],"2026-10-30")
        self.assertEqual(h["announcementsRead"],3*h["issuesRead"])
        self.assertEqual(len(feed["notices"]),1)
        n=feed["notices"][0]
        self.assertRegex(n["id"],r"^VD-2026-\d+$")
        self.assertTrue(vd.ID_RE.fullmatch(n["id"]))
        self.assertEqual(feed["source"],vd.SOURCE)
        self.assertEqual(n["bulletin"],h["bulletins"][-1])

    def test_year_change(self):
        today=date(2026,1,15)
        titles={(date(2026,1,2),0):"Bases y convocatoria para el acceso a una plaza de Auxiliar, por el sistema de concurso-oposición."}
        feed=self.run_audit(build(date(2025,12,1),today,229,3814,titles=titles),today)
        h=feed["historyCoverage"]
        self.assertEqual(h["rangeStart"],"2025-12-17")
        self.assertIn("1",h["bulletins"])
        self.assertEqual(feed["notices"][0]["id"],"VD-2026-1")

    def test_missing_issue_fails(self):
        today=date(2026,10,30)
        pages=build(today-timedelta(days=40),today,170,2600)
        # El calendario omite un día: falta un boletín y la numeración salta.
        key=vd.calendar_url(2026,10)
        days=json.loads(pages[key]);days.remove("2026-10-15");pages[key]=json.dumps(days)
        with self.assertRaises(ProvincialCoverageError):self.run_audit(pages,today)

    def test_missing_announcement_fails(self):
        today=date(2026,10,30)
        pages=build(today-timedelta(days=40),today,170,2600)
        url=vd.issue_url(date(2026,10,15))
        page=pages[url];cut=page.index('<li class="un_anuncio">',page.index('<li class="un_anuncio">')+1)
        end=page.index("</li>",cut)+5
        pages[url]=page[:cut]+page[end:]
        with self.assertRaises(ProvincialCoverageError):self.run_audit(pages,today)

    def test_calendar_day_without_issue_fails(self):
        today=date(2026,10,30)
        pages=build(today-timedelta(days=40),today,170,2600)
        pages[vd.issue_url(date(2026,10,15))]=NOT_FOUND
        with self.assertRaises(ProvincialCoverageError):self.run_audit(pages,today)

    def test_no_dates_hardcoded(self):
        src=(Path(vd.__file__)).read_text(encoding="utf-8")
        self.assertNotRegex(src,r"\b20[2-3]\d\b")

if __name__=="__main__":
    unittest.main()
