"""Pruebas sin red del lector de BOP Málaga (acumula cada día el sumario público)."""
import gzip,json,sys,tempfile,unittest
from datetime import date,timedelta
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import malaga_bop as mg
from provincial_common import ProvincialCoverageError

HERE=Path(__file__).resolve().parent
REAL=gzip.decompress((HERE/"fixture_malaga_portada_2026_11_27.html.gz").read_bytes()).decode("utf-8")
DIAS=["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"]

def portada(day,number,calendar,edicts=None,pdf_number=None):
    """Portada sintética con la estructura real: calendario del mes, PDF y sumario.
    calendar: {fecha: número} de los días del mes de «day» publicados hasta ese día."""
    cells="".join(
        f'<td><a href="index.php?fecha={d:%d-%m-%Y}" title="BOP {n}: {DIAS[d.weekday()]}, {d.day} de x de {d.year}" '
        f'rel="nofollow"><time datetime="{d.isoformat()}">{d.day:02d}</time></a></td>'
        for d,n in sorted(calendar.items()))
    edicts=edicts if edicts is not None else [
        ("AYUNTAMIENTO","Marbella",f"Bases de la convocatoria para 2 plazas de Policía Local.",1),
        ("AYUNTAMIENTO","Ronda","Aprobación inicial de la modificación de créditos.",2),
        ("MANCOMUNIDADES","Vélez-Málaga","Delegación de funciones.",3)]
    sections={}
    for sec,town,title,k in edicts:
        code=f"{day:%Y%m%d}-{4000+k:05d}-{day.year}-01"
        links=(f'<span class="span_enlaces"><a href="/edicto.php?edicto={code}&id=1.ab">Ver edicto {4000+k}/{day.year}</a>'
               f'<a href="/verificacion.php?archivo={code}.pdf&id=1.ab">Descargar PDF</a></span>')
        sections.setdefault(sec,[]).append(
            f'<article><p class="vista_edicto">ADMINISTRACIÓN LOCAL\n{town.upper()}\nEdicto\n{title}{links}</p>'
            f'<p class="vista_sumario"><b>{town}</b>. {title}{links}</article>')
    body="".join(f"<section><h3>{s}</h3>{''.join(a)}</section>" for s,a in sections.items())
    pn=number if pdf_number is None else pdf_number
    return (f'<html><body><table id="table_calendario"><tbody><tr>{cells}</tr></tbody></table>'
            f'<section id="lista_pdf"><header>Boletín del <time datetime="{day.isoformat()}">x</time>:</header><ul>'
            f'<li><a href="verificacion.php?archivo={day:%d%m%y}{pn}.pdf">Boletín nº {pn} en pdf</a></li></ul></section>'
            f'<div id="main"><header><h2>Sumario del día <time datetime="{day.isoformat()}">x</time>:</h2></header>'
            f'<div id="seccionSumario">{body}</div></div></body></html>')

def publication_days(start,end,holidays=()):
    d=start;out=[]
    while d<=end:
        if d.weekday()<5 and d not in holidays:out.append(d)
        d+=timedelta(days=1)
    return out

def simulate(folder,start,end,holidays=(),skip_runs=(),not_yet_today=False):
    """Una ronda al día (también fines de semana: la portada sigue con el último BOP)."""
    days=publication_days(start-timedelta(days=10),end,holidays)
    # Numeración fija: boletines desde el 1 de enero (vuelve a 1 cada año).
    numbers={d:len(publication_days(date(d.year,1,1),d,holidays)) for d in days}
    obs=start-timedelta(days=10)
    while obs<=end:
        if obs not in skip_runs:
            out=[d for d in days if d<=obs and not (not_yet_today and obs==end and d==end)]
            last=out[-1]
            month={d:numbers[d] for d in out if (d.year,d.month)==(last.year,last.month)}
            mg.accumulate(folder,obs,portada(last,numbers[last],month))
        obs+=timedelta(days=1)
    return numbers

class ParseTest(unittest.TestCase):
    def test_real_home_27_11_2026(self):
        x=mg.parse_home(REAL)
        self.assertEqual((x["date"],x["number"]),("2026-11-27",229))
        self.assertEqual(x["pdfs"],["271126229.pdf","271126229a01.pdf"])
        self.assertEqual(len(x["edicts"]),36)
        self.assertEqual(x["calendarMonth"],"2026-11")
        self.assertEqual(x["calendar"]["2026-11-27"],229)
        self.assertNotIn("2026-11-28",x["calendar"])  # sábado sin BOP
        e={e["code"]:e for e in x["edicts"]}["20261127-04410-2026-00"]
        self.assertEqual((e["section"],e["town"]),("MANCOMUNIDADES","Vélez-Málaga"))
        self.assertEqual(e["title"],"Avocación de la atribución especial en materia de comunicación.")
        kinds={e["town"]:mg.kind(e) for e in x["edicts"] if mg.kind(e)}
        self.assertEqual(kinds.get("Teba"),"Plaza / oposición")
        self.assertEqual(kinds.get("Monda"),"Bolsa de trabajo")
        self.assertNotIn("Alhaurín de la Torre",kinds)  # puestos del mercadillo
        self.assertNotIn("Viñuela",kinds)               # listas de admitidos

    def test_rejects_inconsistent_pages(self):
        d=date(2026,11,27)
        ok=portada(d,229,{d:229})
        self.assertEqual(mg.parse_home(ok)["number"],229)
        with self.assertRaises(ProvincialCoverageError):mg.parse_home(portada(d,229,{d:229},pdf_number=228))
        with self.assertRaises(ProvincialCoverageError):mg.parse_home(portada(d,229,{d-timedelta(days=1):228}))
        dup=[("AYUNTAMIENTO","A","x",1),("AYUNTAMIENTO","B","y",1)]
        with self.assertRaises(ProvincialCoverageError):mg.parse_home(portada(d,229,{d:229},edicts=dup))
        with self.assertRaises(ProvincialCoverageError):mg.parse_home(portada(d,229,{d:229},edicts=[]))

    def test_links_never_go_to_pdf_or_signed_token(self):
        url=mg.notice_url("20261127-04410-2026-00")
        self.assertEqual(url,"https://www.bopmalaga.es/edicto.php?edicto=20261127-04410-2026-00")
        self.assertNotIn("verificacion",url);self.assertNotIn("id=",url)
        with self.assertRaises(ProvincialCoverageError):mg.notice_url("../x")

class AccumulateTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.dir=Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()

    def test_same_bulletin_on_weekend_is_idempotent_and_never_shrinks(self):
        fri=date(2026,11,27)
        mg.accumulate(self.dir,fri,portada(fri,229,{fri:229}))
        mg.accumulate(self.dir,fri+timedelta(days=1),portada(fri,229,{fri:229}))
        mg.accumulate(self.dir,fri+timedelta(days=2),portada(fri,229,{fri:229}))
        self.assertEqual(len(list((self.dir/"boletines").glob("*.json"))),1)
        self.assertEqual(len(list((self.dir/"calendario").glob("*.json"))),3)
        fewer=[("AYUNTAMIENTO","Marbella","Bases de la convocatoria para 2 plazas de Policía Local.",1)]
        with self.assertRaises(ProvincialCoverageError):
            mg.accumulate(self.dir,fri,portada(fri,229,{fri:229},edicts=fewer))
        with self.assertRaises(ProvincialCoverageError):
            mg.accumulate(self.dir,fri,portada(fri,230,{fri:230}))

    def test_full_window_across_month_change_with_holiday(self):
        today=date(2026,11,6)  # ventana 08/10–06/11: cruza el cambio de mes
        numbers=simulate(self.dir,today-timedelta(days=29),today,holidays={date(2026,10,12)})
        feed,info=mg.build(self.dir,today)
        self.assertIsNotNone(feed,info)
        hist=feed["historyCoverage"]
        self.assertEqual((hist["rangeStart"],hist["rangeEnd"]),("2026-10-08","2026-11-06"))
        self.assertNotIn("2026-10-12",hist["publicationDates"])  # festivo nacional
        self.assertIn("2026-10-12",hist["nonPublicationDates"])
        self.assertEqual(hist["bulletins"],[str(numbers[date.fromisoformat(d)]) for d in hist["publicationDates"]])
        n=feed["notices"][0]
        self.assertRegex(n["id"],r"^MA-\d{8}-\d{5}-\d{2}$")
        self.assertEqual(n["entity"],"AYUNTAMIENTO · Marbella")
        self.assertTrue(n["url"].startswith("https://www.bopmalaga.es/edicto.php?edicto="))
        self.assertEqual(len(feed["notices"]),len(hist["publicationDates"]))  # una candidata por boletín
        self.assertEqual(hist["announcementsRead"],3*len(hist["publicationDates"]))

    def test_missed_day_keeps_accumulating(self):
        today=date(2026,11,6)
        simulate(self.dir,today-timedelta(days=29),today,skip_runs={date(2026,10,20)})
        feed,info=mg.build(self.dir,today)
        self.assertIsNone(feed)
        self.assertEqual(info["missingIssues"],[d for d in info["missingIssues"] if d.startswith("2026-10-20")])
        self.assertEqual(len(info["missingIssues"]),1)
        # 30 días después del hueco, la ventana vuelve a estar completa.
        later=date(2026,11,20)
        simulate(self.dir,date(2026,11,7),later)
        self.assertIsNotNone(mg.build(self.dir,later)[0])

    def test_first_days_are_not_enough(self):
        today=date(2026,11,28)
        mg.accumulate(self.dir,today,REAL)
        feed,info=mg.build(self.dir,today)
        self.assertIsNone(feed)
        self.assertEqual(info["unknownDays"][0],"2026-10-30")
        self.assertIn("2026-11-26 (BOP 228)",info["missingIssues"])
        rc=mg.main(["--estado",str(self.dir),"--sin-acumular","--output",str(self.dir/"x.json")])
        self.assertEqual(rc,mg.STILL_ACCUMULATING)
        self.assertFalse((self.dir/"x.json").exists())

    def test_first_round_before_todays_bulletin(self):
        today=date(2026,11,6)
        simulate(self.dir,today-timedelta(days=29),today,not_yet_today=True)
        feed,_=mg.build(self.dir,today)
        self.assertIsNotNone(feed)
        self.assertEqual(feed["historyCoverage"]["publicationDates"][-1],"2026-11-05")

    def test_month_change_first_days_without_bulletin(self):
        # Sábado 31 y domingo 1: la portada sigue con el BOP del viernes 30 y el calendario
        # de octubre; el de noviembre aún no tiene ningún boletín.
        sun=date(2026,11,1);fri=date(2026,10,30)
        for obs in (fri,fri+timedelta(days=1),sun):
            mg.accumulate(self.dir,obs,portada(fri,210,{fri:210}))
        bops,unknown=mg.official_days(mg.load_state(self.dir)[1],date(2026,10,30),sun)
        self.assertEqual(bops,{"2026-10-30":210})
        self.assertEqual(unknown,[])  # el último día (hoy) puede no estar aún

    def test_new_year_numbering(self):
        today=date(2027,1,15)
        simulate(self.dir,today-timedelta(days=29),today,holidays={date(2026,12,25),date(2027,1,1),date(2027,1,6)})
        feed,info=mg.build(self.dir,today)
        self.assertIsNotNone(feed,info)
        dates=feed["historyCoverage"]["publicationDates"];nums=feed["historyCoverage"]["bulletins"]
        self.assertEqual(nums[dates.index("2027-01-04")],"1")

class ValidatorTest(unittest.TestCase):
    def test_built_feed_passes_the_app_rules(self):
        import feeds_diarios as fd
        today=date.today()
        with tempfile.TemporaryDirectory() as tmp:
            simulate(tmp,today-timedelta(days=29),today)
            feed,info=mg.build(tmp,today)
            self.assertIsNotNone(feed,info)
            out=Path(tmp)/"malaga_bop.json";mg.write_output(out,feed)
            self.assertGreater(fd.validate("MA",out,today=today)["notices"],0)

if __name__=="__main__":
    unittest.main()
