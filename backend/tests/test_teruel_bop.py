import sys
import unittest
from datetime import date,timedelta
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from teruel_bop import (
    HOME,NOTICE_PREFIX,PROVINCE,ProvincialCoverageError,parse_home,
    parse_page,parse_detail,next_page_trigger,post_form,scan,audit,
)

DAY=date(2026,10,28)
LINK="0/78AF45C9E931954CC1258E9D0035774E"

def results(day=DAY,total=1,page=1):
    rows=[]
    start=(page-1)*10
    for n in range(start,min(total,start+10)):
        id_=f"{day.year}-{3129+n:04d}"
        name="Bases de convocatoria para una plaza de técnico municipal"
        rows.append(f'''<span id="Busquedas:_id1:_id53:viewPanel1:{n}:vtitulo:_internalViewText">
          <a class="link_anuncio" href="0/{78+n:032X}">{name}</a></span>
          <span id="Busquedas:_id1:_id53:viewPanel1:{n}:vemisor:_internalViewText">
          <span class="campo_seccion">Administración Local</span>
          <span class="campo_seccion">Ayto. de Teruel</span></span>
          <span id="Busquedas:_id1:_id53:viewPanel1:{n}:viewColumn4:_internalViewText">
          <span class="campo_numbop_v">Anuncio #{id_} ({day:%d}/Octubre/{day:%Y})</span></span>''')
    nav='' if total<=10 else '''<a id="Busquedas:_id1:_id53:viewPanel1:pager1__Group__lnk__1"
      href="#" title="Go to page 2">2</a>'''
    return f'''<html><form id="Busquedas:_id1"><input type="hidden" name="$$viewid" value="!test!"/>
      <span id="Busquedas:_id1:_id53:computedField1">
      (FIELD ffecha_a >= {day:%d/%m/%Y}) AND (FIELD ffecha_a &lt;= {day:%d/%m/%Y})</span>
      <span id="Busquedas:_id1:_id53:computedField2">Se han encontrado {total} anuncios:</span>
      {nav}{''.join(rows)}</form></html>'''

def detail(number=207):
    return f"""<html><body><div>Anuncio # 2026-3129
      Bases de convocatoria para una plaza de técnico municipal.
      Publicado el 28/10/26 , BOP número {number}.
      Datos del Anunciante Órgano Emisor: Ayto. de Teruel
      </div></body></html>"""

class TeruelTests(unittest.TestCase):
    def test_home_reads_issue_number(self):
        text="<html><body>BOP del día 28 de Octubre de 2026 . BOP número 207 .</body></html>"
        self.assertEqual(parse_home(text),(DAY,207))
        with self.assertRaises(ProvincialCoverageError):
            parse_home(text.replace("Octubre","Novirmbre"))

    def test_complete_search_metadata_and_rows(self):
        n,rows,_=parse_page(results(),DAY)
        self.assertEqual(n,1)
        self.assertEqual(rows[0]["id"],"2026-3129")
        self.assertEqual(rows[0]["entity"],"Ayto. de Teruel")
        self.assertEqual(rows[0]["url"],NOTICE_PREFIX+f"{78:032X}")
        singular=results().replace("Se han encontrado 1 anuncios:", "Se ha encontrado 1 anuncio:")
        self.assertEqual(parse_page(singular,DAY)[0],1)
        with self.assertRaises(ProvincialCoverageError):
            parse_page(results().replace("28/10/2026) AND", "27/10/2026) AND"),DAY)

    def test_pagination_selects_xpages_link(self):
        n,rows,soup=parse_page(results(total=16),DAY)
        self.assertEqual((n,len(rows)),(16,10))
        self.assertEqual(next_page_trigger(soup,2),
                         "Busquedas:_id1:_id53:viewPanel1:pager1__Group__lnk__1")
        n,rows,_=parse_page(results(total=16,page=2),DAY,total=16)
        self.assertEqual(len(rows),6)
        with self.assertRaises(ProvincialCoverageError):
            parse_page(results(total=100),DAY)

    def test_two_official_notices_can_share_announcement_number(self):
        html=results(total=2).replace("Anuncio #2026-3130", "Anuncio #2026-3129")
        n,rows,_=parse_page(html,DAY)
        self.assertEqual(n,2)
        self.assertEqual(rows[0]["id"],rows[1]["id"])
        self.assertNotEqual(rows[0]["url"],rows[1]["url"])

    def test_post_has_date_filter_and_viewid(self):
        _,_,soup=parse_page(results(),DAY)
        d=post_form(soup,"fake-event",DAY)
        self.assertEqual(d["$$xspsubmitid"],"fake-event")
        self.assertEqual(d["Busquedas:_id1:_id53:inputText2"],"28/10/2026")

    def test_details_and_untrusted_url(self):
        r={"id":"2026-3129","title":"Bases de convocatoria para una plaza de técnico municipal",
           "entity":"Ayto. de Teruel"}
        self.assertEqual(parse_detail(detail(),r,DAY),207)
        self.assertEqual(parse_detail(detail().replace("28/10/26","28/10/2026"),r,DAY),207)
        self.assertEqual(parse_detail(detail().replace("28/10/26","28/10/26"),r,DAY),207)
        with self.assertRaises(ProvincialCoverageError):
            parse_detail(detail().replace("28/10/26","27/10/26"),r,DAY)
        with self.assertRaises(ProvincialCoverageError):
            parse_detail(detail(208).replace("28/10/26","27/10/26"),r,DAY)

    def test_scan_checks_count_and_official_detail(self):
        first=results()
        sample=NOTICE_PREFIX+f"{78:032X}"
        class Fake:
            def close(self):pass
        def read(session,url,data=None):
            return (first if data is None else first) if url.endswith("busquedas.xsp") else detail()
        with patch("teruel_bop.request",side_effect=read):
            got=scan(DAY,lambda:Fake())
        self.assertEqual(got["number"],207)
        self.assertEqual(got["read"],1)
        self.assertEqual(len(got["notices"]),1)
        self.assertEqual(got["notices"][0]["url"],sample)

    def test_audit_rejects_missing_bulletins(self):
        home="<html>BOP del día 28 de Octubre de 2026 . BOP número 207 .</html>"
        end=DAY
        start=end-timedelta(days=29)
        published=[start+timedelta(days=i) for i in range(30)
                   if (start+timedelta(days=i)).weekday()<5]
        ids={d:n for n,d in enumerate(published,186)}
        def fake_scan(d):
            if d not in ids:return None
            return {"date":d,"number":ids[d],"read":1,"pages":1,"notices":[{
                "id":f"TE-{d.year}-{2000+ids[d]}","province":PROVINCE,
                "title":"Bases y convocatoria plaza auxiliar",
                "entity":"Ayuntamiento", "date":d.strftime("%d/%m/%Y"),
                "bulletin":str(ids[d]),"type":"Plaza / oposición",
                "url":NOTICE_PREFIX+f"{ids[d]:032X}"}]}
        class Fake:
            def close(self):pass
        with patch("teruel_bop.request",return_value=home):
            result=audit(30,end,scanner=fake_scan,session_factory=Fake)
            self.assertEqual(result["historyCoverage"]["issuesRead"],len(published))
            self.assertEqual(result["historyCoverage"]["rangeStart"],str(start))
            with self.assertRaises(ProvincialCoverageError):
                audit(30,end,scanner=lambda d:None,session_factory=Fake)

if __name__=="__main__":
    unittest.main()
