import unittest,sys
from pathlib import Path
from datetime import date,timedelta
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import navarra_bon as nb
from provincial_common import ProvincialCoverageError

MES=("","enero","febrero","marzo","abril","mayo","junio","julio","agosto",
     "septiembre","octubre","noviembre","diciembre")

def label(d):
    return f"{d.day} de {MES[d.month]} de {d.year}"

def month_page(rows):
    """rows: [(fecha, número, extraordinario)] como la página mensual oficial."""
    out=[]
    for d,n,extra in sorted(rows,key=lambda r:-r[1]):
        tail="\n    <br/>EXTRAORDINARIO" if extra else ""
        out.append(f'<a href="https://bon.navarra.es/es/boletin/-/sumario/{d.year}/{n}" '
                   f'title="Nº {n} |  {label(d)}{tail}">\n  Nº {n} |  {label(d)}{tail}\n</a>')
    return "<table>"+"".join(out)+"</table>"

def summary_page(year,number,day,items):
    """items: [(sección, denominación, título)]."""
    body=[f'<p id="numero_boletin" class="hd r-hn2">\n BOLETÍN Nº {number} - {label(day)}\n</p>',
          '<p class="hd r-hn3 b-ambito">\n 2. Administración Local de Navarra\n</p>']
    for i,(sec,den,title) in enumerate(items):
        body.append(f'<p class="hd r-hn4 b-seccion">\n 2.1. {sec}\n</p>')
        if den:body.append(f'<p class="hd r-hn6 b-denominacion">\n {den}\n</p>')
        body.append(f'<p>\n <a href="https://bon.navarra.es/es/anuncio/-/texto/{year}/{number}/{i}" '
                    f'title="{title}">\n   {title}\n </a>\n</p>')
    return "\n".join(body)

def workdays(first,last):
    d=first
    while d<=last:
        if d.weekday()<5:yield d
        d+=timedelta(days=1)

class NavarraCalendarTest(unittest.TestCase):
    def fake(self,pages):
        def fetch(url,attempts=3):
            if url not in pages:raise AssertionError("URL no prevista "+url)
            return pages[url]
        return fetch

    def test_months_cross_year(self):
        self.assertEqual(nb.months(date(2025,12,17),date(2026,1,15)),[(2025,12),(2026,1)])

    def test_year_change_and_extraordinary(self):
        dec=[(d,240+i,False) for i,d in enumerate(workdays(date(2025,12,1),date(2025,12,31)))]
        dec.append((date(2025,12,31),dec[-1][1]+1,True))
        jan=[(d,1+i,False) for i,d in enumerate(workdays(date(2026,1,2),date(2026,1,30)))]
        pages={nb.month_url(2025,12):month_page(dec),nb.month_url(2026,1):month_page(jan)}
        with mock.patch.object(nb,"fetch",self.fake(pages)):
            start,issues=nb.calendar(date(2026,1,15))
        self.assertEqual(start,date(2025,12,17))
        self.assertEqual(issues[0][0],date(2025,12,17))
        self.assertIn((date(2025,12,31),dec[-1][1],True),issues)
        self.assertEqual(issues[-1][0],date(2026,1,15))

    def test_gap_fails(self):
        oct_=[(d,189+i,False) for i,d in enumerate(workdays(date(2026,10,1),date(2026,10,30)))]
        del oct_[5]
        with mock.patch.object(nb,"fetch",self.fake({nb.month_url(2026,10):month_page(oct_),
                                                     nb.month_url(2026,9):month_page([])})):
            with self.assertRaises(ProvincialCoverageError):nb.calendar(date(2026,10,30))

    def test_stale_index_fails(self):
        oct_=[(d,189+i,False) for i,d in enumerate(workdays(date(2026,10,1),date(2026,10,22)))]
        sep=[(date(2026,9,30),188,False)]
        with mock.patch.object(nb,"fetch",self.fake({nb.month_url(2026,10):month_page(oct_),
                                                     nb.month_url(2026,9):month_page(sep)})):
            with self.assertRaises(ProvincialCoverageError):nb.calendar(date(2026,10,30))

class NavarraSummaryTest(unittest.TestCase):
    def test_summary_and_ids(self):
        day=date(2026,1,9)
        page=summary_page(2026,5,day,[
            ("Oposiciones y concursos. Oferta Pública de Empleo","HUARTE","Concurso-oposición de dos plazas de animador/a"),
            ("Disposiciones y anuncios ordenados por localidad","BERA",'Aprobación de la "Ordenanza" de caminos'),
            ("Oposiciones y concursos. Oferta Pública de Empleo","PAMPLONA",
             "Convocatoria para la constitución de una relación de aspirantes a la contratación temporal de conserje"),
            ("Oposiciones y concursos. Oferta Pública de Empleo","BURLADA","Recurso de alzada frente a la oposición de dos plazas"),
        ])
        with mock.patch.object(nb,"fetch",lambda url,attempts=3:page):
            issue=nb.read_issue((day,5,False))
        self.assertEqual(issue["read"],4)
        self.assertEqual([n["id"] for n in issue["notices"]],["NA-2026-005-0","NA-2026-005-2"])
        self.assertEqual([n["type"] for n in issue["notices"]],["Plaza / oposición","Bolsa de trabajo"])
        self.assertEqual(issue["notices"][0]["entity"],"HUARTE")
        self.assertEqual(issue["notices"][1]["url"],"https://bon.navarra.es/es/anuncio/-/texto/2026/5/2")
        for n in issue["notices"]:self.assertTrue(nb.ID_RE.fullmatch(n["id"]))

    def test_wrong_issue_fails(self):
        page=summary_page(2026,5,date(2026,1,9),[("Otros","BERA","Anuncio")])
        with self.assertRaises(ProvincialCoverageError):nb.parse_summary(page,2026,6,date(2026,1,9))
        with self.assertRaises(ProvincialCoverageError):nb.parse_summary(page,2026,5,date(2026,1,8))

    def test_missing_announcement_fails(self):
        page=summary_page(2026,5,date(2026,1,9),[("Otros","BERA","Uno"),("Otros","BERA","Dos")])
        page=page.replace("/texto/2026/5/1","/texto/2026/5/3")
        with self.assertRaises(ProvincialCoverageError):nb.parse_summary(page,2026,5,date(2026,1,9))

    def test_foreign_url_rejected(self):
        with self.assertRaises(ProvincialCoverageError):nb.fetch("https://evil.example/es/boletin")
        with self.assertRaises(ProvincialCoverageError):nb.fetch("http://bon.navarra.es/es/indice-boletines")

if __name__=="__main__":unittest.main()
