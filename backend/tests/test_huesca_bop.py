import sys
import unittest
from datetime import date,timedelta
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from huesca_bop import (
    HOME, INDEX, PDF_PATH, PROVINCE, ProvincialCoverageError,
    parse_index,parse_pdf,scan,audit,latest_issue_date,
)


def sample_index(day:date,number:int=207,entries:int=2,page:int=1)->str:
    begin=(page-1)*20+1
    end=begin+entries-1
    rows=[]
    for i in range(begin,end+1):
        title="Bases y convocatoria para cubrir una plaza de técnico informático" if i==1 else "Anuncio de padrón fiscal"
        rows.append(f"""
        <li class="elementoListado">
          <a class="enlace_elemento" href="/publica/buscador-anuncios/anuncio/anuncio-{i}/">Ir al detalle</a>
          <div class="fecha_elemento"><div class="container">{day:%d/%m/%Y}</div></div>
          <h3 class="titulo_elemento">{title}</h3>
          <div class="campo_1"><div class="container">Ayuntamiento de Huesca</div></div>
          <div class="campo_3">BOPH-{day.year}-{number:03d}{i:03d}</div>
        </li>""")
    return (f'<html><head><title>BOP - {day:%d/%m/%Y}</title></head>'
            f'<body><h2>BOP núm. {number} del {day:%d/%m/%Y}</h2>'
            f'<p>Resultados del {begin} al {end} de {entries}</p>'
            +''.join(rows)+'</body></html>')


def detail(day:date)->str:
    return (f'<html><body><h1 class="titulo_detalle">Bases y convocatoria para cubrir una plaza de técnico informático.</h1>'
            f'<p>Fecha de publicación {day:%d/%m/%Y}</p>'
            '<a href="/export/sites/bop/.galleries/Documentos-Anuncios-en-PDF/firmado-123-final-abc.pdf">'
            'PDF</a></body></html>')


class HuescaBOPTests(unittest.TestCase):
    def test_parse_index_full_and_registry(self):
        day=date(2026,10,28)
        num,total,rows=parse_index(sample_index(day),day)
        self.assertEqual(num,207)
        self.assertEqual(total,2)
        self.assertEqual(rows[0]["id"],"BOPH-2026-207001")
        with self.assertRaises(ProvincialCoverageError):
            parse_index(sample_index(day).replace("207001","208001"),day)

    def test_pdf_official_with_date_and_title(self):
        day=date(2026,10,28)
        link=parse_pdf(detail(day),day,"Bases y convocatoria para cubrir una plaza de técnico informático")
        self.assertTrue(link.startswith("https://bop.dphuesca.es"+PDF_PATH))
        with self.assertRaises(ProvincialCoverageError):
            parse_pdf(detail(day).replace("bop/.galleries/Documentos-Anuncios-en-PDF",
                "bop/.galleries/Otros-Documentos"),day,
                "Bases y convocatoria para cubrir una plaza de técnico informático")

    def test_scan_checks_document_and_counts(self):
        day=date(2026,10,28)
        def get(url,allow_missing=False):
            if "anuncio/anuncio-1" in url:return detail(day)
            return sample_index(day)
        res=scan(day,reader=get)
        self.assertEqual(res["read"],2)
        self.assertEqual(res["number"],207)
        self.assertEqual(len(res["notices"]),1)
        self.assertEqual(res["notices"][0]["id"],"HU-2026-207001")

    def test_home_and_30_calendar_days_with_nonpublication(self):
        end=date(2026,10,28)
        start=end-timedelta(days=29)
        published=[start+timedelta(days=i) for i in range(30)
                   if (start+timedelta(days=i)).weekday()<5]
        issue_for_day={day:177+i for i,day in enumerate(published)}
        def get_issue(day):
            if day not in issue_for_day:return None
            n=issue_for_day[day]
            return {"date":day,"number":n,"read":1,"pages":1,"notices":[{
              "id":f"HU-{day.year}-{n:03d}001","province":PROVINCE,
              "title":"Bases oposición","entity":"Ayuntamiento","date":day.strftime("%d/%m/%Y"),
              "bulletin":str(n),"type":"Plaza / oposición",
              "url":"https://bop.dphuesca.es"+PDF_PATH+"original.pdf",
            }]}
        homepage=f'<a href="{INDEX.format(end.strftime("%d-%m-%Y"))}">BOP ultimo</a>'
        self.assertEqual(latest_issue_date(homepage),end)
        result=audit(today=end,reader=get_issue,fetch_home=lambda _:homepage)
        self.assertEqual(result["historyCoverage"]["rangeEnd"],end.isoformat())
        self.assertEqual(len(result["historyCoverage"]["publicationDates"])+
                         len(result["historyCoverage"]["nonPublicationDates"]),30)

    def test_hole_in_sequence_fails_closed(self):
        end=date(2026,10,28)
        def issue(day):
            if day.weekday()>=5:return None
            return {"date":day,"number":day.day+130,"read":1,"pages":1,"notices":[]}
        with self.assertRaises(ProvincialCoverageError):
            audit(today=end,reader=issue,
                  fetch_home=lambda _:f'<a href="{INDEX.format(end.strftime("%d-%m-%Y"))}">BOP</a>')


if __name__=="__main__":unittest.main()
