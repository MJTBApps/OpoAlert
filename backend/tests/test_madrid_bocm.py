import unittest,sys
from pathlib import Path
from datetime import date,timedelta
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from provincial_common import ProvincialCoverageError
from madrid_bocm import archive,parse_xml,pdf_ok,parse_fallback_html,audit,issue_xml,issue_pdf

D=date(2026,10,28)
def xml(number=258,notices=2):
    items=""
    for n,t in [(1,"Bases de la convocatoria para cubrir una plaza de Administrativo"),(2,"Aprobación del presupuesto anual")][:notices]:
        items+=f"""<disposicion numero="{n}"><identificador>BOCM-20261028-{n}</identificador>
        <titulo>{t}</titulo><url_pdf>https://www.bocm.es/boletin/CM_Orden_BOCM/2026/10/28/BOCM-20261028-{n}.PDF</url_pdf>
        </disposicion>"""
    return f"""<sumario><metadatos><publicacion>BOCM</publicacion><numero>{number}</numero>
    <fecha_publicacion>2026/10/28</fecha_publicacion><url_xml_sumario>{issue_xml(D,number)}</url_xml_sumario>
    <url_pdf_diario>{issue_pdf(D,number)}</url_pdf_diario></metadatos>
    <diario numero="{number}"><secciones><seccion nombre="III. ADMINISTRACIÓN LOCAL AYUNTAMIENTOS">
    <organismo nombre="Ayuntamiento de Getafe">{items}</organismo></seccion></secciones></diario></sumario>""".encode()
def catalog(days,number_start=232):
    chunks=[]
    for i in range(days):
        day=date(2026,9,30)+timedelta(days=i)
        n=number_start+i
        chunks.append(f'<a href="/boletin/bocm-{day:%Y%m%d}-{n}">Boletín Nº {n} del 30 Septiembre con CVE: BOCM-{day:%Y%m%d}</a>')
    return "<html>"+ "\n".join(chunks)+"</html>"

class MadridTests(unittest.TestCase):
    def test_xml_and_pdf(self):
        x=parse_xml(xml(),D,258)
        self.assertEqual(x["read"],2)
        self.assertEqual(x["rows"][0]["entity"],"Ayuntamiento de Getafe")
        self.assertEqual(x["rows"][0]["id"],"MD-20261028-1")
        self.assertEqual(x["rows"][0]["type"],"Plaza / oposición")
        self.assertIsNone(x["rows"][1]["type"])
        self.assertTrue(pdf_ok(x["rows"][0]["url"],D))
        self.assertFalse(pdf_ok(x["rows"][0]["url"],D-timedelta(days=1)))
        with self.assertRaises(ProvincialCoverageError):parse_xml(xml(),D,259)
    def test_archive_two_editions_same_day(self):
        html='''<a href="/boletin/bocm-20260930-233">Boletín Nº 233 del 30 Septiembre con CVE: BOCM-20260930</a>'''
        for i in range(26):
            day=date(2026,10,1)+timedelta(days=i)
            html+=f'<a href="/boletin/bocm-{day:%Y%m%d}-{234+i}">Boletín Nº {234+i} del Día con CVE: BOCM-{day:%Y%m%d}</a>'
        html+='<a href="/boletin/bocm-20261026-260">Boletín Nº 260 del Día con CVE: BOCM-20261026</a>'
        data=archive(html,date(2026,9,30),date(2026,10,29))
        self.assertEqual(len(data),28)
        self.assertEqual(data[-1][0],date(2026,10,26))
        with self.assertRaises(ProvincialCoverageError):
            archive(html.replace("bocm-20261026-260","bocm-20261026-262").replace("Nº 260","Nº 262"),date(2026,9,30),date(2026,10,29))
    def test_fallback_extraordinary_json_ld(self):
        html='''<h2>BOCM Nº 259</h2><h3>PRESIDENCIA DE LA COMUNIDAD</h3>
        <a href="https://www.bocm.es/boletin/CM_Orden_BOCM/2026/10/28/BOCM-20261028-37.PDF">pdf</a>'''
        class Resp:
            def json(self):return {"legislationIdentifier":"BOCM-20261028-37","name":"Declaración luto oficial"}
        res=parse_fallback_html(html,D,259,lambda url:Resp())
        self.assertEqual(res["read"],1)
        self.assertEqual(res["method"],"html")
        self.assertEqual(res["rows"][0]["entity"],"PRESIDENCIA DE LA COMUNIDAD")

if __name__=="__main__":unittest.main()
