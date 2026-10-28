import unittest
from datetime import date,timedelta
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from boe_nacional import parse_summary, build_history, category, official_pdf, BoeCoverageError


def fixture(day: date):
    ident="BOE-A-2026-22556"
    return {
        "status":{"code":200,"text":"ok"},
        "data":{"sumario":{
            "metadatos":{"publicacion":"BOE","fecha_publicacion":day.strftime("%Y%m%d")},
            "diario":[{
                "numero":"266",
                "seccion":[
                    {"codigo":"2A","departamento":[{"nombre":"Personal",
                         "epigrafe":[{"item":[{"titulo":"Nombramiento de funcionario"}]}]}]},
                    {"codigo":"2B","departamento":[{"nombre":"MINISTERIO DE HACIENDA",
                         "epigrafe":[{"nombre":"Personal laboral",
                          "item":[{"identificador":ident,
                                   "titulo":"Resolucion por la que se convoca proceso selectivo para personal laboral fijo",
                                   "url_pdf":{"texto":"https://www.boe.es/boe/dias/"+day.strftime("%Y/%m/%d")+
                                              "/pdfs/"+ident+".pdf"}}]}]}]}
                ]
            }]
        }}
    }


class BoeSpainTests(unittest.TestCase):
    def setUp(self):
        self.day=date(2026,10,28)

    def test_only_section_2b_is_read(self):
        result=parse_summary(fixture(self.day),self.day)
        self.assertEqual(result["read"],1)
        self.assertEqual(len(result["notices"]),1)
        self.assertEqual(result["notices"][0]["province"],"España (BOE)")
        self.assertEqual(result["notices"][0]["id"],"BOE-A-2026-22556")

    def test_bad_date_fails_closed(self):
        with self.assertRaises(BoeCoverageError):
            parse_summary(fixture(self.day),date(2026,10,27))

    def test_missing_pdf_fails_closed(self):
        data=fixture(self.day)
        item=data["data"]["sumario"]["diario"][0]["seccion"][1]["departamento"][0]["epigrafe"][0]["item"][0]
        item["url_pdf"]["texto"]="https://evil.example/malware.pdf"
        with self.assertRaises(BoeCoverageError):
            parse_summary(data,self.day)

    def test_numero_and_identifier_strict(self):
        self.assertTrue(official_pdf(
            "https://www.boe.es/boe/dias/2026/10/28/pdfs/BOE-A-2026-22556.pdf",
            "BOE-A-2026-22556",self.day))
        self.assertFalse(official_pdf(
            "https://www.boe.es/boe/dias/2026/10/27/pdfs/BOE-A-2026-22556.pdf",
            "BOE-A-2026-22556",self.day))

    def test_filter_does_not_include_procedural_lists(self):
        self.assertIsNone(category("Resolucion por la que se publica lista de admitidos y excluidos"))
        self.assertIsNone(category("Nombramiento de un funcionario"))
        self.assertIsNotNone(category("Se convoca proceso selectivo para personal laboral fijo"))

    def test_all_30_days_required_and_sundays_acceptable(self):
        end=self.day
        seen=[]
        def fake(day):
            seen.append(day)
            if day.weekday()==6:return None
            record=fixture(day)
            record["data"]["sumario"]["diario"][0]["seccion"][1]["departamento"][0]["epigrafe"][0]["item"][0]["identificador"]=f"BOE-A-2026-{day.day+30000}"
            record["data"]["sumario"]["diario"][0]["seccion"][1]["departamento"][0]["epigrafe"][0]["item"][0]["url_pdf"]["texto"]=(
                "https://www.boe.es/boe/dias/"+day.strftime("%Y/%m/%d")+
                f"/pdfs/BOE-A-2026-{day.day+30000}.pdf")
            return record
        data=build_history(30,end,fake)
        self.assertEqual(len(seen),30)
        self.assertEqual(len(data["historyCoverage"]["publicationDates"])+
                         len(data["historyCoverage"]["nonPublicationDates"]),30)
        self.assertEqual(len(data["notices"]),len(data["historyCoverage"]["publicationDates"]))

    def test_fail_on_unjustified_missing_workday(self):
        def fake(day):return None
        with self.assertRaises(BoeCoverageError):
            build_history(30,self.day,fake)

    def test_fail_on_duplicate_ids_across_days(self):
        def fake(day):
            if day.weekday()==6:return None
            data=fixture(day)
            # Same ID but different PDF path across days is valid individually, not across dates.
            return data
        with self.assertRaises(BoeCoverageError):
            build_history(30,self.day,fake)


if __name__=="__main__":
    unittest.main()
