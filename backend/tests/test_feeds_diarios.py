import json,re,sys,tempfile,unittest
from datetime import date,datetime,timedelta,timezone
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import feeds_diarios as fd

KOTLIN=fd.ROOT/"app/src/main/java/es/opoalert/app"
# Fuentes que ya tenían su propio workflow revisar-*.yml antes del registro común.
LEGACY={"VA","AL","CS","ES","CB","CG","CL","CT","TB","BB","BG","HU","TE","ZA","AM","CO","GR","SV","CA"}

def enum_codes():
    text=(KOTLIN/"Province.kt").read_text(encoding="utf-8")
    return dict(re.findall(r'\n\s{4}([A-Z_]+)\(\s*"([A-Z]{2})"',text))

def pending_codes():
    text=(KOTLIN/"SourceCatalog.kt").read_text(encoding="utf-8")
    block=re.search(r"pendingDailyFeed: Set<Province> = setOf\((.*?)\)",text,re.S)[1]
    names=re.findall(r"Province\.([A-Z_]+)",block)
    codes=enum_codes()
    return {codes[n] for n in names}

def feed(today,**changes):
    days=[today-timedelta(days=i) for i in range(29,-1,-1) if (today-timedelta(days=i)).weekday()<5]
    data={"schemaVersion":1,"province":"Madrid","source":"https://www.bocm.es/listado-de-boletines",
        "lastCheckedUTC":datetime.now(timezone.utc).isoformat(),
        "coverage":{"complete":True,"status":"complete","bulletin":str(len(days)),
            "pagesVisited":len(days),"announcementsRead":len(days)*10,"opportunities":1},
        "historyCoverage":{"complete":True,"rangeStart":(today-timedelta(days=29)).isoformat(),
            "rangeEnd":today.isoformat(),"bulletins":[str(i+1) for i in range(len(days))],
            "publicationDates":[d.isoformat() for d in days],"nonPublicationDates":[],
            "issuesRead":len(days),"announcementsRead":len(days)*10,"opportunities":1},
        "notices":[{"id":"MD-20261030-123","province":"Madrid","title":"Convocatoria de una plaza",
            "entity":"Ayuntamiento","date":days[-1].strftime("%d/%m/%Y"),"bulletin":str(len(days)),
            "type":"Plaza / oposición","url":"https://www.bocm.es/boletin/CM_Orden_BOCM/2026/10/30/x.PDF"}]}
    for key,value in changes.items():data[key]=value
    return data

class FeedsDiariosTest(unittest.TestCase):
    def test_registry_matches_app(self):
        codes=set(enum_codes().values());pending=pending_codes()
        self.assertFalse(set(fd.SOURCES)&pending,"Una fuente con feed diario no debe estar oculta")
        self.assertEqual(codes-pending-LEGACY,set(fd.SOURCES),
            "Toda fuente visible en la app necesita feed diario, y viceversa")
        rules=fd.app_rules()
        for code,(script,_,name) in fd.SOURCES.items():
            self.assertTrue((fd.ROOT/"backend"/script).exists(),script)
            self.assertEqual(Path(rules[code]["feed"]).name,name)

    def write(self,folder,data,name="f.json"):
        p=Path(folder)/name;p.write_text(json.dumps(data,ensure_ascii=False),encoding="utf-8");return p

    def test_valid_feed_passes_and_bad_ones_fail(self):
        today=date.today()
        with tempfile.TemporaryDirectory() as tmp:
            ok=self.write(tmp,feed(today))
            self.assertEqual(fd.validate("MD",ok,today=today)["notices"],1)
            bad=feed(today);bad["notices"][0]["url"]="https://example.com/boletin/CM_Orden_BOCM/x.pdf"
            with self.assertRaises(fd.FeedError):fd.validate("MD",self.write(tmp,bad),today=today)
            with self.assertRaises(fd.FeedError):
                fd.validate("MD",self.write(tmp,feed(today-timedelta(days=5))),today=today)
            old=feed(today);old["coverage"]["announcementsRead"]*=3
            prev=self.write(tmp,old,"prev.json")
            with self.assertRaises(fd.FeedError):fd.validate("MD",ok,previous=prev,today=today)

if __name__=="__main__":
    unittest.main()
