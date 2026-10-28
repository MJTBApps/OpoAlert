import sys
import unittest
from datetime import date,timedelta
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cadiz_bop import (
    HOME,PROVINCE,ProvincialCoverageError,
    validate_doc,validate_full_pdf,available_issues,parse_issue,audit
)

ISSUE=208
FULL="https://www.bopcadiz.es/.boletines_pdf/2026/10_octubre/BOP208_28-10-26.pdf"
SUM="https://www.bopcadiz.es/.boletines_pdf/2026/10_octubre/SU-208_28-10-26.pdf"
DOC="https://www.bopcadiz.es/export/sites/default/.boletines_pdf/2026/10_octubre/BOP208_28-10-26.pdf#page=7"
def html():
    return f"""
    <html><p class="fecha">Wed Oct 28 08:00:00 CET 2026</p><h2>Boletín número 208 del año 2026</h2>
    <p><span><a href="{SUM}">Sumario PDF</a></span></p>
    <p><span><a href="{FULL}">Boletín PDF</a></span></p>
    <h3>JUNTA DE ANDALUCIA</h3>
    <p><a href="/export/sites/default/.boletines_pdf/2026/10_octubre/BOP208_28-10-26.pdf#page=4">
        <strong>250.620.- Consejería de Industria.</strong> Autorización de instalación eléctrica.</a></p>
    <h3>ADMINISTRACION LOCAL</h3>
    <p><a href="/export/sites/default/.boletines_pdf/2026/10_octubre/BOP208_28-10-26.pdf#page=7">
        <strong>354.710.- Ayuntamiento de Alcalá del Valle.</strong>
        Bases de convocatoria para una plaza de Administrativo por oposición libre.</a></p>
    <h2>Calendario de boletines</h2>
    <p><a href="/boletin/Boletin-numero-207-del-ano-2026/">Otro boletín</a></p>
    """

class CadizTests(unittest.TestCase):
    def test_original_pdf_links_strict_and_fragment(self):
        self.assertTrue(validate_doc(DOC))
        self.assertTrue(validate_full_pdf(FULL))
        self.assertFalse(validate_doc(FULL))
        self.assertFalse(validate_doc(DOC.replace("www.bopcadiz.es","false.invalid")))
        self.assertFalse(validate_doc(DOC.replace("#page=7","#frag=1")))
        self.assertFalse(validate_doc(DOC+"&another=1"))
    def test_covers_all_sections_and_reads_issuer(self):
        x=parse_issue(html(),2026,208)
        self.assertEqual(x["count"],2)
        self.assertEqual(x["date"],date(2026,10,28))
        self.assertEqual(x["number"],208)
        self.assertEqual(x["sections"],["JUNTA DE ANDALUCIA","ADMINISTRACION LOCAL"])
        self.assertEqual(len(x["candidates"]),1)
        n=x["candidates"][0]
        self.assertEqual(n["id"],"CA-2026-354710")
        self.assertIn("Alcalá del Valle",n["entity"])
        self.assertEqual(n["url"],DOC)
    def test_rejects_mismatched_edition_and_dates(self):
        with self.assertRaises(ProvincialCoverageError):
            parse_issue(html(),2026,207)
        with self.assertRaises(ProvincialCoverageError):
            parse_issue(html().replace("28-10-26","27-10-26"),2026,208)
        with self.assertRaises(ProvincialCoverageError):
            parse_issue(html().replace("#page=7","#page=bogus"),2026,208)
    def test_root_index_contiguous(self):
        root="<h2>Boletín número 208 del año 2026</h2>"
        root+="".join(f"<a href='/boletin/Boletin-numero-{n}-del-ano-2026/'>BOP</a>" for n in range(169,209))
        latest,values=available_issues(root)
        self.assertEqual(latest,208)
        self.assertEqual(len(values),40)
        with self.assertRaises(ProvincialCoverageError):
            available_issues(root.replace("numero-201-","numero-2018-"))
    def test_audit_requires_30_dates_and_consistent_numbering(self):
        latest=208
        root="<h2>Boletín número 208 del año 2026</h2>"
        root+="".join(f"<a href='/boletin/Boletin-numero-{n}-del-ano-2026/'>BOP</a>" for n in range(169,209))
        class Dummy:
            def close(self):pass
        class R:
            text=root
        def lookup(num,year):
            d=date(2026,10,28)-timedelta(days=latest-num)
            return {"number":num,"date":d,"count":8,"candidates":[{
                "id":f"CA-2026-{300000+num}","province":PROVINCE,
                "title":"Bases convocatoria una plaza de auxiliar","entity":"Ayuntamiento",
                "bulletin":str(num),"date":d.strftime("%d/%m/%Y"),
                "type":"Plaza / oposición","url":DOC,
            }],"sections":["ADMINISTRACION LOCAL"]}
        with patch("cadiz_bop.get",return_value=R()):
            found=audit(30,date(2026,10,28),scanner=lookup,session_factory=Dummy)
        self.assertEqual(found["historyCoverage"]["issuesRead"],30)
        self.assertEqual(found["historyCoverage"]["rangeStart"],"2026-09-29")
        self.assertEqual(len(found["notices"]),30)
        with patch("cadiz_bop.get",return_value=R()),self.assertRaises(ProvincialCoverageError):
            audit(30,date(2026,10,28),scanner=lambda num,year:None,session_factory=Dummy)
if __name__=="__main__":
    unittest.main()
