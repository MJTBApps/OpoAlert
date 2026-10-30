"""Pruebas sin red del lector del BOP de Lleida (eBOP)."""
import re
import sys
import unittest
from datetime import date,timedelta
from pathlib import Path
from unittest import mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import lleida_bop as L
from lleida_bop import ProvincialCoverageError

PDF="https://ebop.diputaciolleida.cat/aplicacions/bop/bopV1/fitxers/pdf/{y}/{n}/{y}{n}{s}{e}.pdf"

def edict(day,number,suffix,num,agency,title):
    url=PDF.format(y=day.year,n=number,s=suffix,e=num)
    return (f'<li class="edicte"><a href="{url}" target="new" class="linkAjuda">\n'
            f'   {num} - <span>{agency}</span> - {title}\n</a></li>')

def issue_html(day,number,blocks):
    """blocks: lista (una por edición /0, /1...) de listas (num, entidad, título)."""
    out=['<html><body><div class="row titol titol-principal"></div>']
    for suffix,rows in enumerate(blocks):
        out.append(f'<div class="row titol"><div class="col-6"><h1>\n Bop número: {number}/{suffix} - '
                   f'{day:%d/%m/%Y}\n</h1></div></div><div class="aplicacio"><section>'
                   '<h2 class="seccioTau">Administració Local - Ajuntaments</h2><ul>')
        out.extend(edict(day,number,suffix,*r) for r in rows)
        out.append('</ul></section></div>')
    out.append('<footer><a href="/bop">Últim número</a></footer></body></html>')
    return "".join(out)

JOB="Aprovació de les bases i la convocatòria del procés selectiu d'una plaça d'auxiliar administratiu/va"
OTHER="Aprovació inicial del pressupost general"

def portal(first,last,skip=()):
    """Portal falso: un BOP cada día laborable; numeración que vuelve a 1 cada enero."""
    pages={};by_year={};counter=1000;day=first;latest=None
    while day<=last:
        if day.weekday()<5:
            n=by_year.get(day.year,0)+1;by_year[day.year]=n
            rows=[(counter,"AJUNTAMENT DE TÀRREGA (TÀRREGA)",JOB),
                  (counter+1,"AJUNTAMENT DE BALAGUER (BALAGUER)",OTHER)]
            counter+=2
            if (day.year,n) not in skip:
                pages[L.issue_url(day.year,n)]=issue_html(day,n,[rows])
            latest=(day.year,n)
        day+=timedelta(days=1)
    pages[L.SOURCE]=pages[L.issue_url(*latest)]
    calls=[]
    def fetch(url):
        calls.append(url)
        return pages.get(url)
    fetch.calls=calls
    return fetch


class ParseTests(unittest.TestCase):
    def test_parse_real_shape_with_additional_edition(self):
        day=date(2026,9,21)
        html=issue_html(day,180,[
            [(7811,"AJUNTAMENT DE LA SEU D'URGELL (SEU D'URGELL, LA)",
              "Anunci Bases convocatòries de places d'operaris/àries brigada d'obres"),
             (7743,"AJUNTAMENT DE LES BORGES BLANQUES (BORGES BLANQUES, LES)",
              "CONVOCATÒRIA PER A LA CONCESSIÓ DE SUBVENCIONS A ESPORTISTES")],
            [(7714,"AJUNTAMENT DE LA SEU D'URGELL (SEU D'URGELL, LA)","BOP Setembre 2026 Exp. 3719/2026")],
        ])
        got=L.parse_issue(html,2026,180)
        self.assertEqual((got["number"],got["day"],got["editions"],got["read"]),(180,day,2,3))
        self.assertEqual(len(got["notices"]),1)
        n=got["notices"][0]
        self.assertEqual(n["id"],"LE-202618007811")
        self.assertEqual(n["entity"],"AJUNTAMENT DE LA SEU D'URGELL (SEU D'URGELL, LA)")
        self.assertEqual(n["url"],PDF.format(y=2026,n=180,s=0,e=7811))
        self.assertEqual((n["province"],n["bulletin"],n["date"],n["type"]),
                         ("Lleida (BOP)","180","21/09/2026","Plaza / oposición"))
        self.assertTrue(re.fullmatch(r"LE-\d{7,14}",n["id"]))

    def test_rejects_inconsistent_pages(self):
        day=date(2026,10,29)
        good=issue_html(day,207,[[(8900,"CONSELL COMARCAL DEL SEGRIÀ",JOB)]])
        L.parse_issue(good,2026,207)
        with self.assertRaises(ProvincialCoverageError):L.parse_issue(good,2026,206)
        with self.assertRaises(ProvincialCoverageError):L.parse_issue(good,2025,207)
        bad={
          "host":good.replace("ebop.diputaciolleida.cat/aplicacions","evil.example/aplicacions"),
          "ruta":good.replace("/bopV1/fitxers/pdf/","/bopV1/altres/"),
          "pdf de otro edicto":good.replace("202620708900.pdf","202620708901.pdf"),
          "pdf de otra edición":good.replace("pdf/2026/207/","pdf/2026/206/"),
          "sin cabecera":good.replace("Bop número","Butlletí"),
          "sin entidad":good.replace("<span>CONSELL COMARCAL DEL SEGRIÀ</span>",""),
          "http":good.replace("https://ebop","http://ebop"),
        }
        for name,html in bad.items():
            with self.subTest(name),self.assertRaises(ProvincialCoverageError):
                L.parse_issue(html,2026,207)
        empty=issue_html(day,207,[[(8900,"CONSELL COMARCAL DEL SEGRIÀ",JOB)],[]])
        with self.assertRaises(ProvincialCoverageError):L.parse_issue(empty,2026,207)
        jump=good.replace("207/0 -","207/1 -")
        with self.assertRaises(ProvincialCoverageError):L.parse_issue(jump,2026,207)
        dup=issue_html(day,207,[[(8900,"A",OTHER),(8900,"A",OTHER)]])
        with self.assertRaises(ProvincialCoverageError):L.parse_issue(dup,2026,207)

    def test_short_ids_of_first_bulletins_of_the_year(self):
        # BOP 5, edicto 35: el PDF se llama 20265035.pdf (sin ceros a la izquierda).
        html=issue_html(date(2026,1,9),5,[[(35,"AJUNTAMENT DE PONTS (PONTS)",JOB)]])
        self.assertTrue(any(re.fullmatch(r"LE-\d{7,14}",n["id"]) for n in L.parse_issue(html,2026,5)["notices"]))
        # Si el edicto no es candidata no hay identificador que publicar.
        html=issue_html(date(2026,1,9),5,[[(35,"AJUNTAMENT DE PONTS (PONTS)",OTHER)]])
        self.assertEqual(L.parse_issue(html,2026,5)["read"],1)

    def test_candidate_filter_in_catalan(self):
        yes={
          "Bases i convocatòria d'una plaça d'Encarregat de brigada, mitjançant promoció interna":"Plaza / oposición",
          "Convocatòria i bases borsa intermunicipal auxiliars administratius":"Bolsa de trabajo",
          "ANUNCI CREACIÓ BORSA TREBALL AJUNTAMENT DE MALDÀ":"Bolsa de trabajo",
          "Anunci convocatòria i bases promocions internes a C1":"Plaza / oposición",
          "Anunci aprovació de la convocatòria i de les bases reguladores que han de regir el procés per "
          "proveir mitjançant nomenament provisional el lloc de treball de secretari/ària-interventor/a":"Plaza / oposición",
          "Aprobacion bases plaça tècnic/a llar d'infants":"Plaza / oposición",
        }
        for title,kind in yes.items():
            with self.subTest(title):self.assertEqual(L.candidate(title),kind)
        no=(
          "Anunci relatiu a la resolució de la llista provisional de persones admeses i excloses",
          "Convocatòria per a la concessió de subvencions a esportistes",
          "Anunci relatiu al nomenament de personal funcionari de carrera en la plaça de Conserge",
          "Convocatòria de Jutge de Pau titular",
          "CONVOCATÒRIA JUNTA GENERAL ORDINÀRIA",
          "Aprovació de les bases i la convocatòria del XXIX è premi de Poesia",
          "Correcció d’error material de les bases i la convocatòria d’una plaça temporal",
          "Anunci de resolució de la convocatòria per a la provisió definitiva del lloc de treball",
          "Aprovació definitiva Projecte de millora de la zona de jocs infantils de la Plaça Firal",
          "Convocatòria de beques per als estudiants residents",
        )
        for title in no:
            with self.subTest(title):self.assertIsNone(L.candidate(title))


class AuditTests(unittest.TestCase):
    def test_full_window_matches_daily_validator_rules(self):
        today=date(2026,10,30)
        fetch=portal(date(2026,1,1),today)
        feed=L.audit(today=today,fetch=fetch)
        h=feed["historyCoverage"];c=feed["coverage"]
        self.assertEqual((h["rangeStart"],h["rangeEnd"]),("2026-10-01","2026-10-30"))
        self.assertEqual(feed["source"],"https://ebop.diputaciolleida.cat/bop/")
        self.assertEqual(feed["province"],"Lleida (BOP)")
        self.assertEqual(h["issuesRead"],22)
        self.assertEqual(h["publicationDates"][0],"2026-10-01")
        self.assertEqual(h["publicationDates"][-1],"2026-10-30")
        nums=list(map(int,h["bulletins"]))
        self.assertEqual(nums,list(range(nums[0],nums[0]+22)))
        self.assertEqual(c["announcementsRead"],44)
        self.assertEqual(len(feed["notices"]),22)
        self.assertGreater(c["pagesVisited"],h["issuesRead"])  # incluye la edición anterior a la ventana
        for n in feed["notices"]:
            self.assertRegex(n["id"],r"^LE-\d{7,14}$")
            self.assertTrue(n["url"].startswith("https://ebop.diputaciolleida.cat/aplicacions/bop/bopV1/fitxers/pdf/"))
        self.assertTrue(all("2026-01-01/2026/" in u for u in fetch.calls if "mostra-bop" in u))

    def test_missing_issue_fails(self):
        today=date(2026,10,30)
        fetch=portal(date(2026,1,1),today,skip={(2026,200)})
        with self.assertRaises(ProvincialCoverageError):L.audit(today=today,fetch=fetch)

    def test_stale_portal_fails(self):
        fetch=portal(date(2026,1,1),date(2026,10,20))
        with self.assertRaises(ProvincialCoverageError):L.audit(today=date(2026,10,30),fetch=fetch)

    def test_year_change_window_and_past_date(self):
        fetch=portal(date(2025,1,1),date(2026,10,30))
        feed=L.audit(today=date(2026,1,15),fetch=fetch)
        h=feed["historyCoverage"]
        self.assertEqual((h["rangeStart"],h["rangeEnd"]),("2025-12-17","2026-01-15"))
        self.assertIn("1",h["bulletins"])
        i=h["bulletins"].index("1")
        self.assertEqual(h["publicationDates"][i],"2026-01-01")
        self.assertEqual(h["publicationDates"][i-1],"2025-12-31")
        self.assertEqual(h["publicationDates"][-1],"2026-01-15")


class DownloadTests(unittest.TestCase):
    def response(self,status,body=b"",location=None):
        r=mock.Mock(status_code=status,content=body,encoding="utf-8",headers={})
        if location:r.headers={"Location":location}
        return r

    def test_not_found_redirect_and_blocks(self):
        s=mock.Mock()
        with mock.patch.object(L,"session",return_value=s):
            s.get.return_value=self.response(302,location="https://ebop.diputaciolleida.cat/bop/?No+trobo+el+BOP+2026%2F0%2Fnull")
            self.assertIsNone(L.download(L.issue_url(2026,0)))
            s.get.return_value=self.response(302,location="https://example.org/bop/?No+trobo")
            with self.assertRaises(ProvincialCoverageError):L.download(L.issue_url(2026,1))
            s.get.return_value=self.response(200,b"<html>Please solve the reCAPTCHA</html>")
            with self.assertRaises(ProvincialCoverageError):L.download(L.issue_url(2026,1))
            s.get.return_value=self.response(403)
            with self.assertRaises(ProvincialCoverageError):L.download(L.issue_url(2026,1))
        with self.assertRaises(ProvincialCoverageError):L.download("https://evil.example/bop/")


if __name__=="__main__":
    unittest.main()
