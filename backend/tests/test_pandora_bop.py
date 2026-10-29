import sys
import unittest
from datetime import date,timedelta
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pandora_bop import (
    ALMERIA,JAEN,ProvincialCoverageError,archive_url,pdf_url,text_url,
    issue_entry,index_page,parse_date_header,split_ocr,identify,audit,
)

DAY=date(2026,10,15)
AL_PDF="https://app.dipalme.org/pandora/high.raw?id=0000392773&name=00000001.original.pdf"
JA_PDF="https://bophistorico.dipujaen.es/high.raw?id=0001747120&name=00000001.original.pdf&attachment=0001747120.pdf"
AL_OCR="""Número: 200
Jueves, 15 de octubre de 2026
Boletín Oficial de la Provincia de Almería
SUMARIO
ADMINISTRACIÓN LOCAL
002761-26 002765-26
DIPUTACIÓN PROVINCIAL DE ALMERÍA
EXTRACTO DE LA CONVOCATORIA DE SUBVENCIONES
AYUNTAMIENTO DE NÍJAR
BASES DE CONVOCATORIA DE UNA PLAZA DE ADMINISTRATIVO
Pág. 1
2761/26
DIPUTACIÓN PROVINCIAL DE ALMERÍA
A N U N C I O
EXTRACTO DE LA CONVOCATORIA DE SUBVENCIONES PARA LA INVERSIÓN RURAL.
Pág. 2
2765/26 AYUNTAMIENTO DE NÍJAR
A N U N C I O
BASES DE CONVOCATORIA DE UNA PLAZA DE ADMINISTRATIVO DE ADMINISTRACIÓN GENERAL POR OPOSICIÓN.
"""
JA_OCR="""Número 191
Jueves, 15 de octubre de 2026
ADMINISTRACIÓN LOCAL
DIPUTACIÓN PROVINCIAL DE JAÉN
Aprobación de plan de empleo.
AYUNTAMIENTO DE ALCALÁ LA REAL (JAÉN)
Bases de convocatoria de dos plazas de administrativo.
Pág. 13000
BOP-2026-4568 BOP-2026-4560
Número 191
Jueves, 15 de octubre de 2026
ADMINISTRACIÓN LOCAL
DIPUTACIÓN PROVINCIAL DE JAÉN
Pág. 13001
2026/4568 Aprobación de plan de empleo.

Anuncio
Se aprueba un plan de empleo.
Número 191
Jueves, 15 de octubre de 2026
AYUNTAMIENTO DE ALCALÁ LA REAL (JAÉN)
Pág. 13002
2026/4560 Bases de convocatoria de dos plazas de administrativo.

Anuncio
Se convocan dos plazas de administrativo por concurso oposición.
"""

def card(g,ed_id,day,pages):
    if g.almeria:
        url=f"high.raw?id={ed_id}&name=00000001.original.pdf"
    else:
        url=f"high.raw?id={ed_id}&name=00000001.original.pdf&attachment={ed_id}.pdf"
    return (f'<div class="list-frame" id="frame-{ed_id}">'
      f'Ejemplar Boletín Oficial de la Provincia de {g.name}. '
      f'{day:%d}/{day:%m}/{day:%Y} ({pages} páginas).'
      f'<a href="{url}">Descargar</a></div>')

class PandoraTests(unittest.TestCase):
    def test_original_pdf_whitelist(self):
        self.assertEqual(pdf_url(ALMERIA,"high.raw?id=0000392773&name=00000001.original.pdf"),
                         (AL_PDF,"0000392773"))
        self.assertEqual(pdf_url(JAEN,"high.raw?id=0001747120&name=00000001.original.pdf&attachment=0001747120.pdf"),
                         (JA_PDF,"0001747120"))
        self.assertIn("text.vm?id=0001747120",text_url(JAEN,"0001747120"))
        for bad in ["https://evil.example/high.raw?id=0001747120&name=00000001.original.pdf",
                    "high.raw?id=invalid&name=00000001.original.pdf",
                    "high.raw?id=0001747120&name=evil.pdf"]:
            with self.assertRaises(ProvincialCoverageError):
                pdf_url(JAEN,bad)

    def test_archive_index_requires_original_document_and_count(self):
        html='<html><head><title>Boletín Oficial de la Provincia de Almería</title></head><body><form id="wide-sheet">Resultados: 48.184 '+card(ALMERIA,"0000392773",DAY,22)+'</form></body></html>'
        count,items=index_page(ALMERIA,html)
        self.assertEqual(count,48184)
        self.assertEqual(items[0]["date"],DAY)
        self.assertEqual(items[0]["pages"],22)
        self.assertEqual(items[0]["id"],"0000392773")
        with self.assertRaises(ProvincialCoverageError):
            index_page(ALMERIA,html.replace("48.184","42.000"),48184)

    def test_ocr_dates_and_summary_body_reconcile(self):
        self.assertEqual(parse_date_header(ALMERIA,AL_OCR,DAY),200)
        self.assertEqual(parse_date_header(JAEN,JA_OCR,DAY),191)
        al,read=split_ocr(ALMERIA,AL_OCR,DAY)
        self.assertEqual(read,2)
        self.assertEqual(len(al),1)
        self.assertEqual(al[0]["code"],2765)
        self.assertIn("NÍJAR",al[0]["agency"])
        ja,read=split_ocr(JAEN,JA_OCR,DAY)
        self.assertEqual(read,2)
        self.assertEqual(len(ja),1)
        self.assertEqual(ja[0]["code"],4560)
        self.assertIn("ALCALÁ",ja[0]["agency"])

    def test_missing_body_edict_rejects_audit(self):
        with self.assertRaises(ProvincialCoverageError):
            split_ocr(ALMERIA,AL_OCR.split("2765/26")[0],DAY)
        with self.assertRaises(ProvincialCoverageError):
            split_ocr(JAEN,JA_OCR.replace("2026/4560","2026/4561"),DAY)
        with self.assertRaises(ProvincialCoverageError):
            parse_date_header(ALMERIA,AL_OCR,DAY-timedelta(days=1))

    def test_audit_30_days_and_bop_number_continuity(self):
        end=date(2026,10,29)
        start=end-timedelta(days=29)
        selected=[start+timedelta(days=i) for i in range(30)
                  if (start+timedelta(days=i)).weekday()<5]
        def indexer(g,s,e,client):
            return [{"date":d,"pages":20,"pdf":AL_PDF,"id":f"{393000+i:010d}"}
                    for i,d in enumerate(selected)],48184,3
        def scanner(g,row):
            idx=selected.index(row["date"])
            return {"date":row["date"],"number":190+idx,"pages":20,
                    "read":8,"notices":[{"id":f"AM-2026-{2000+idx:05d}","province":"Almería",
                      "title":"Bases para la convocatoria de una plaza","entity":"Ayuntamiento",
                      "date":row["date"].strftime("%d/%m/%Y"),"bulletin":str(190+idx),
                      "url":AL_PDF,"type":"Plaza / oposición"}],
                    "pdf":AL_PDF}
        result=audit(ALMERIA,30,end,indexer,scanner)
        self.assertEqual(result["historyCoverage"]["issuesRead"],len(selected))
        self.assertEqual(len(result["notices"]),len(selected))
        with self.assertRaises(ProvincialCoverageError):
            audit(ALMERIA,20,end,indexer,scanner)
        def bad(g,row):
            data=scanner(g,row)
            if row["date"]==selected[8]:data["number"]+=2
            return data
        with self.assertRaises(ProvincialCoverageError):
            audit(ALMERIA,30,end,indexer,bad)

if __name__=="__main__":
    unittest.main()
