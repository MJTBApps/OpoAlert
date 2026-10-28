import sys
import unittest
from datetime import date,timedelta
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from barcelona_bop import parse_index,official_pdf,audit,publishes,ProvincialCoverageError


def fixture(day:date,regs:list[str],total:int|None=None,page:int=1)->str:
    total=total if total is not None else len(regs)
    first=(page-1)*20+1;last=first+len(regs)-1
    cards=[]
    for i,reg in enumerate(regs):
        cards.append(
            f'<div class="card bg-white"><div class="card-body">'
            f'<h3 class="card-title h6"><a href="/anunci/{4000000+i}/anunci-de-prova">Ajuntament de prova</a></h3>'
            f'<p>Convocatòria per cobrir una plaça de tècnic informàtic</p>'
            f'<ul><li>Registre : {reg}</li><li>Data de publicació : {day:%d/%m/%Y}</li></ul>'
            '</div></div>')
    return (f'<html><head><title>El Butlletí Oficial del dia {day:%d/%m/%Y} - BOP Barcelona</title></head>'
            '<body>' + f"S'han trobat {total} resultats per la seva cerca, mostrant del {first} al {last}"
            +''.join(cards)+'</body></html>')


class BopBarcelonaTests(unittest.TestCase):
    def setUp(self):self.day=date(2026,10,28)

    def test_one_page(self):
        n,records=parse_index(fixture(self.day,["202610159954","202610159955"]),self.day)
        self.assertEqual(n,2)
        self.assertEqual(records[0]["reg"],"202610159954")

    def test_partial_page_refused(self):
        with self.assertRaises(ProvincialCoverageError):
            parse_index(fixture(self.day,["202610159954"],total=21),self.day)
        with self.assertRaises(ProvincialCoverageError):
            parse_index(fixture(self.day,["202610159954"]).replace("2026-10-28","2026-10-27"),self.day-timedelta(days=1))

    def test_original_pdf_and_registry(self):
        html=("<p>Data de publicació: 28/10/2026</p>"
              "<p>Número de Registre: 202610159954</p>"
              "<a href='/anunci/descarrega-pdf/4007735'>PDF oficial</a>")
        got=official_pdf(html,"4007735","202610159954",self.day)
        self.assertEqual(got,"https://bop.diba.cat/anunci/descarrega-pdf/4007735")
        with self.assertRaises(ProvincialCoverageError):
            official_pdf(html,"4007734","202610159954",self.day)

    def test_2026_holiday_not_falsely_published(self):
        self.assertFalse(publishes(date(2026,10,12)))
        self.assertFalse(publishes(date(2026,9,24)))
        self.assertFalse(publishes(date(2026,10,24)))
        self.assertTrue(publishes(self.day))

    def test_audits_all_30_dates(self):
        visited=[]
        def fake(day):
            visited.append(day)
            return {"date":day,"total":2,"pages":1,"notices":[{
                "id":"BA-"+day.strftime("%Y%m%d")+"0001",
                "title":"Convocatòria d'una plaça tècnica","entity":"Ajuntament prova",
                "date":day.strftime("%d/%m/%Y"),"bulletin":day.strftime("%d/%m/%Y"),
                "province":"Barcelona (BOP)","type":"Plaza / oposición",
                "url":"https://bop.diba.cat/anunci/descarrega-pdf/4007735"
            }]}
        feed=audit(today=self.day,reader=fake)
        self.assertEqual(len(visited),len(feed["historyCoverage"]["publicationDates"]))
        self.assertEqual(len(feed["historyCoverage"]["publicationDates"])+
                         len(feed["historyCoverage"]["nonPublicationDates"]),30)
        self.assertTrue(feed["coverage"]["complete"])

if __name__=="__main__":unittest.main()
