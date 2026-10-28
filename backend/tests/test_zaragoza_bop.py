import json
import sys
import unittest
from datetime import date,timedelta
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from zaragoza_bop import (
    SOURCE,PROVINCE,ProvincialCoverageError,
    pdf_url,safe_pdf,date_params,parse_json,parse_xml,
    compare_exports,classify_candidate,fetch_day,audit
)
DAY=date(2026,10,28)
URL=SOURCE+"?CMD=VEROBJ&MLKOB=1472319500303"
OTHER=SOURCE+"?CMD=VEROBJ&MLKOB=1472348790808"

def record(i=1,total=1,docn="000344663",url=URL):
    return {
      "NOrden":f"{i} de {total}","DOCN":docn,
      "FechaPublicacion":"20261028","Numeroboletin":"249",
      "Seccion":"VIII. Boletín Oficial de la Provincia de Zaragoza",
      "Subseccion":"SECCIÓN SEXTA" if i==1 else "SECCIÓN TERCERA",
      "Fechadisposicion":"","Rango":"","Emisor":"AYUNTAMIENTO DE AINZÓN",
      "Titulo":"Convocatoria de una plaza de auxiliar administrativo",
      "Texto":"Convocatoria para la cobertura de una plaza de auxiliar administrativo por oposición.",
      "UrlPdf":chr(96)+url+"´   ","UrlBCOM":chr(96)+OTHER+"´",
    }

def json_bytes(*rows):
    return json.dumps(list(rows),ensure_ascii=False).encode("ISO-8859-1")

def xml_bytes(*rows):
    import xml.etree.ElementTree as ET
    root=ET.Element("documento")
    for row in rows:
        reg=ET.SubElement(root,"registro")
        for tag,val in {
          "docn":row["DOCN"],"fecha":row["FechaPublicacion"],
          "seccion":row["Seccion"],"subseccion":row["Subseccion"],
          "emisor":row["Emisor"],"titulo":row["Titulo"],
          "texto":row["Texto"],"url":f"<enlace>{pdf_url(row['UrlPdf'])}</enlace>",
        }.items():
            ET.SubElement(reg,tag).text=val
    return ET.tostring(root,encoding="ISO-8859-1")

class ZaragozaTests(unittest.TestCase):
    def test_url_original_is_whitelisted(self):
        self.assertEqual(pdf_url(chr(96)+URL+"´"),URL)
        self.assertEqual(pdf_url("<enlace>"+URL+"</enlace>"),URL)
        self.assertTrue(safe_pdf(URL))
        for bad in [URL+"&extra=x",URL.replace("www.boa.aragon.es","evil.example"),
                    URL.replace("https:","http:"),URL+"#fragment"]:
            self.assertFalse(safe_pdf(bad))
        with self.assertRaises(ProvincialCoverageError):
            pdf_url("texto"+URL)
        with self.assertRaises(ProvincialCoverageError):
            pdf_url(URL+"&param=unknown")
    def test_params_scope_all_subsections(self):
        p=date_params(DAY)
        self.assertEqual(p["SECC-C"],"zaragoza")
        self.assertEqual(p["SUBS-C"],"")
        self.assertEqual(p["@PUBL-GE"],"20261028")
        self.assertEqual(p["@PUBL-LE"],"20261028")
        self.assertEqual(date_params(DAY,xml=True)["OUTPUTMODE"],"XML")
    def test_json_complete_ordinals_and_number(self):
        n,rows=parse_json(json_bytes(record()),DAY)
        self.assertEqual(n,249)
        self.assertEqual(len(rows),1)
        with self.assertRaises(ProvincialCoverageError):
            parse_json(json_bytes({**record(),"NOrden":"1 de 6"}),DAY)
        with self.assertRaises(ProvincialCoverageError):
            parse_json(json_bytes({**record(),"FechaPublicacion":"20261027"}),DAY)
        with self.assertRaises(ProvincialCoverageError):
            parse_json(json_bytes({**record(),"Seccion":"BOA nacional"}),DAY)
    def test_xml_reconciles_announcements_and_urls(self):
        a=record()
        n,rows=parse_json(json_bytes(a),DAY)
        xml=parse_xml(xml_bytes(a),DAY)
        compare_exports(DAY,n,rows,xml)
        with self.assertRaises(ProvincialCoverageError):
            compare_exports(DAY,n,rows,{})
        with self.assertRaises(ProvincialCoverageError):
            parse_xml(b"<html>Error durante la busqueda</html>",DAY)
    def test_classify_generic_heading_using_official_text(self):
        a=record()
        a["Titulo"]="Por Decreto de Alcaldia numero 123 se aprueba ..."
        self.assertEqual(classify_candidate(a),"Plaza / oposición")
        a["Texto"]="Se notifica la aprobacion de un padron del impuesto de bienes inmuebles."
        self.assertIsNone(classify_candidate(a))
    def test_fetch_day_uses_original_pdf(self):
        class Fake:
            def close(self):pass
        class FakeR:
            def __init__(self,data):
                self.content=data
                self.status_code=200
                self.url=SOURCE
                self.encoding="ISO-8859-1"
        def fake_get(session,params):
            a=record()
            return FakeR(xml_bytes(a) if params["OUTPUTMODE"]=="XML" else json_bytes(a))
        with patch("zaragoza_bop.get",side_effect=fake_get),patch("zaragoza_bop.verify_pdf") as check:
            result=fetch_day(DAY,session_factory=Fake)
            self.assertEqual(result["number"],249)
            self.assertEqual(result["notices"][0]["url"],URL)
            check.assert_called_once()
    def test_audit_counts_all_30_calendar_days_and_rejects_jump(self):
        end=DAY;start=end-timedelta(days=29)
        pub=[start+timedelta(days=i) for i in range(30)
             if (start+timedelta(days=i)).weekday()!=6]
        nums={d:223+i for i,d in enumerate(pub)}
        def fake_scan(d):
            if d not in nums:return None
            n=nums[d]
            idx=list(nums).index(d)
            return {"date":d,"number":n,"read":20,"pages":2,
            "sections":{"SECCIÓN SEXTA":18,"SECCIÓN TERCERA":2},
            "notices":[{"id":"ZA-"+f"{500000+idx:09d}","province":PROVINCE,
            "title":"Bases de la convocatoria de una plaza",
            "entity":"Ayuntamiento","date":d.strftime("%d/%m/%Y"),
            "bulletin":str(n),"type":"Plaza / oposición","url":URL}]}
        result=audit(30,end,scanner=fake_scan)
        self.assertEqual(result["historyCoverage"]["issuesRead"],len(pub))
        self.assertEqual(result["coverage"]["announcementsRead"],len(pub)*20)
        with self.assertRaises(ProvincialCoverageError):
            audit(30,end,scanner=lambda d:None)
        def gap(d):
            r=fake_scan(d)
            if r and d==pub[8]:r["number"]+=1
            return r
        with self.assertRaises(ProvincialCoverageError):
            audit(30,end,scanner=gap)
if __name__=="__main__":
    unittest.main()
