import unittest,sys
from pathlib import Path
from datetime import date
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import ceuta_bocce as ce
from provincial_common import ProvincialCoverageError

M={12:"1964-diciembre",11:"1963-noviembre",1:"1966-enero"}
def ed(extra,n,day,ident,cat=None):
    cat=cat or M[day.month]
    slug=f"{ident}-bocce-{'extra%02d'%n if extra else n}-{day:%d-%m-%Y}"
    return f"https://www.ceuta.es/ceuta/component/jdownloads/finish/{cat}/{slug}?Itemid=534",(extra,n,day)

# Archivo real del cambio de año (ventana 17/12/2025-15/01/2026).
ARCHIVE={
 (2025,11):dict([ed(False,6569,date(2025,11,28),22994),ed(True,61,date(2025,11,28),22995),
                 ed(False,6570,date(2025,12,2),22996,cat="1963-noviembre")]),   # copia mal archivada
 (2025,12):dict([ed(False,6570,date(2025,12,2),22998),ed(True,62,date(2025,12,5),23001),
                 ed(False,6571,date(2025,12,5),23002),ed(True,63,date(2025,12,9),23003),
                 ed(False,6572,date(2025,12,9),23004),ed(True,64,date(2025,12,10),23113),
                 ed(False,6573,date(2025,12,12),23009),ed(False,6574,date(2025,12,16),23012),
                 ed(False,6575,date(2025,12,19),23013),ed(True,65,date(2025,12,19),23014),
                 ed(True,66,date(2025,12,22),23015),ed(False,6576,date(2025,12,23),23016),
                 ed(False,6577,date(2025,12,26),23017),ed(True,67,date(2025,12,26),23018),
                 ed(True,68,date(2025,12,29),23019),ed(False,6578,date(2025,12,30),23020)]),
 (2026,1):dict([ed(False,6579,date(2026,1,2),23021),ed(False,6580,date(2026,1,6),23022),
                ed(False,6581,date(2026,1,9),23023),ed(False,6582,date(2026,1,13),23024),
                ed(True,1,date(2026,1,14),23025),ed(False,6583,date(2026,1,16),23034)]),
}
def listing(archive):
    return lambda y,m:dict(archive.get((y,m),{}))
def lab(items):
    return [("E" if e else "")+str(n) for _,e,n,_ in items]

class CeutaCalendarTest(unittest.TestCase):
    def test_year_change(self):
        items=ce.calendar(date(2026,1,15),listing(ARCHIVE))
        self.assertEqual(lab(items),["6575","E65","E66","6576","6577","E67","E68","6578",
                                     "6579","6580","6581","6582","E1"])

    def test_misfiled_copy_is_ignored(self):
        items=ce.calendar(date(2025,12,31),listing(ARCHIVE))
        urls=[u for u,_,n,_ in items if n==6570]
        self.assertEqual(len(urls),1)
        self.assertIn("/1964-diciembre/22998-",urls[0])

    def test_missing_regular_fails(self):
        broken={k:dict(v) for k,v in ARCHIVE.items()}
        del broken[(2026,1)][ed(False,6580,date(2026,1,6),23022)[0]]
        with self.assertRaises(ProvincialCoverageError):ce.calendar(date(2026,1,15),listing(broken))

    def test_missing_extra_before_window_fails(self):
        broken={k:dict(v) for k,v in ARCHIVE.items()}
        del broken[(2025,12)][ed(True,64,date(2025,12,10),23113)[0]]
        with self.assertRaises(ProvincialCoverageError):ce.calendar(date(2026,1,15),listing(broken))

    def test_stale_archive_fails(self):
        with self.assertRaises(ProvincialCoverageError):ce.calendar(date(2026,1,25),listing(ARCHIVE))

    def test_listing_rejects_unknown_bocce_name(self):
        from bs4 import BeautifulSoup
        html='<a href="/ceuta/component/jdownloads/finish/1982-octubre/1-bocce-6658-bis-06-10-2026?Itemid=534">x</a>'
        with self.assertRaises(ProvincialCoverageError):
            ce.parse_listing(BeautifulSoup(html,"html.parser"),"1982-octubre",2026,10)

class CeutaPdfTest(unittest.TestCase):
    SUMARIO=("Boletín Oficial\nCiudad de Ceuta\nMartes\n6 de Octubre de 2026\nBOCCE\nNº6.658\nORDINARIO\nSUMARIO\n"
             "AUTORIDADES Y PERSONAL\nCIUDAD AUTÓNOMA DE CEUTA\n"
             "681.- Decreto por el que se aprueban las bases de la convocatoria para la provisión de\n"
             "5 plazas de Ayudante Educativo, mediante el sistema de oposición en turno libre.\nPág.3592\n"
             "682- Decreto por el que se nombra a los aprobados de la convocatoria para la provisión de\n"
             "2 plazas de Conductor, en el marco del Programa 2021-\n2025-.\nPág.xxxx\n"
             "OTRAS DISPOSICIONES Y ACUERDOS\nSERVICIO PÚBLICO DE EMPLEO ESTATAL.\nDIRECCIÓN PROVINCIAL EN CEUTA\n"
             "683.- Tercera relación de trabajadores sustituidos.\nPág.3622\n")
    BODY="BOCCE nº 6.658\nMartes 6 de Octubre de 2026\n681.-DECRETO ...\n682.-DECRETO ...\n683.-Relación ..."

    def test_sumario(self):
        edicts,k=ce.sumario([ce.norm(self.SUMARIO),self.BODY])
        self.assertEqual(k,1)
        self.assertEqual([n for n,_,_ in edicts],[681,682,683])
        self.assertEqual(edicts[0][2],"Ciudad Autónoma de Ceuta")
        self.assertEqual(edicts[2][2],"Servicio Público de Empleo Estatal. Dirección Provincial en Ceuta")
        self.assertTrue(edicts[1][1].endswith("2021- 2025-."))
        self.assertEqual(ce.kind(edicts[0][1]),"Plaza / oposición")
        self.assertIsNone(ce.kind(edicts[1][1]))
        self.assertIsNone(ce.kind(edicts[2][1]))

    def test_header(self):
        pages=[ce.norm(self.SUMARIO),self.BODY]
        self.assertTrue(ce.header_ok(pages,False,6658,date(2026,10,6)))
        self.assertFalse(ce.header_ok(pages,False,6659,date(2026,10,6)))
        self.assertFalse(ce.header_ok(pages,False,6658,date(2026,10,9)))
        extra=["BOCCE\nNº51\nEXTRAORDINARIO\n28 de Octubre de 2026"]
        self.assertTrue(ce.header_ok(extra,True,51,date(2026,10,28)))

    def test_chain_gap_fails(self):
        a={"extra":False,"number":6657,"day":date(2026,10,2),"first":670,"last":680}
        b={"extra":False,"number":6658,"day":date(2026,10,6),"first":682,"last":684}
        with self.assertRaises(ProvincialCoverageError):ce.check_chain([a,b])
        b["first"]=681;ce.check_chain([a,b])
        c={"extra":False,"number":6579,"day":date(2026,1,2),"first":1,"last":2}
        ce.check_chain([{**a,"day":date(2025,12,30)},c])

class CeutaAuditTest(unittest.TestCase):
    def fake_reader(self,ordinary_edicts,extra_edicts):
        state={False:ordinary_edicts,True:extra_edicts}
        def read(item):
            url,extra,n,day=item
            first=state[extra]
            if day.year==2026 and first>100:first=1
            job="Decreto por el que se aprueban las bases de la convocatoria para la provisión de 1 plaza de Peón, mediante oposición libre."
            other="Decreto por el que se concede una subvención."
            titles=(other,job) if extra else (job,other)   # convocatoria: impares en ordinarios, pares en extras
            ed=[(first,titles[0],"Ciudad Autónoma de Ceuta"),(first+1,titles[1],"Ciudad Autónoma de Ceuta")]
            state[extra]=first+2
            return {"edicts":ed,"pages":3,"first":first,"last":first+1,"url":url,"extra":extra,
                    "number":n,"day":day,"sha256":"0"*64,"bytes":1000}
        return read

    def test_audit_feed(self):
        ce.WORKERS=1
        feed=ce.audit(date(2026,1,15),listing(ARCHIVE),self.fake_reader(820,200))
        self.assertEqual(feed["source"],"https://www.ceuta.es/ceuta/bocce")
        self.assertEqual(feed["province"],"Ceuta (BOCCE)")
        self.assertEqual(feed["coverage"]["announcementsRead"],26)
        self.assertEqual(feed["historyCoverage"]["rangeStart"],"2025-12-17")
        self.assertIn("EXTRA01",feed["historyCoverage"]["bulletins"])
        for n in feed["notices"]:
            self.assertRegex(n["id"],r"^CE-\d{4}-E?\d{3,4}$")
            self.assertEqual(n["id"].split("-")[2].startswith("E"),n["bulletin"].startswith("EXTRA"))
            self.assertTrue(n["url"].startswith("https://www.ceuta.es/ceuta/component/jdownloads/finish/"))

    def test_same_number_in_both_series_gets_distinct_ids(self):
        # Ordinarios y extraordinarios numeran sus edictos aparte: la E evita que choquen.
        ce.WORKERS=1
        feed=ce.audit(date(2026,1,15),listing(ARCHIVE),self.fake_reader(820,819))
        ids=[n["id"] for n in feed["notices"]]
        self.assertEqual(len(ids),len(set(ids)))

if __name__=="__main__":unittest.main()
