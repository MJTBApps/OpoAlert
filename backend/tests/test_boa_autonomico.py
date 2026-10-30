import json
import sys
import unittest
from datetime import date,timedelta
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from provincial_common import ProvincialCoverageError
import boa_autonomico as boa

URL=boa.SOURCE+"?CMD=VEROBJ&MLKOB=1472319500303"


def row(i,total,docn,day,num):
    return {"NOrden":f"{i} de {total}","DOCN":docn,"FechaPublicacion":day.strftime("%Y%m%d"),
            "Numeroboletin":num,"Seccion":"II. Autoridades y Personal","Titulo":"ORDEN de prueba",
            "Emisor":"DEPARTAMENTO","Texto":"Texto completo","UrlPdf":"`"+URL+"´"}


def weekdays(start,end,first,skip=()):
    out=[];n=first;day=start
    while day<=end:
        if day.weekday()<5 and day not in skip:
            if day.year!=(out[-1][0].year if out else day.year):n=1
            out.append((day,str(n)));n+=1
        day+=timedelta(days=1)
    return out


class BoaTest(unittest.TestCase):
    def test_window(self):
        self.assertEqual(boa.window(date(2026,1,15)),(date(2025,12,17),date(2026,1,15)))

    def test_no_fixed_dates_left(self):
        src=Path(boa.__file__).read_text(encoding="utf-8")
        for fixed in ("2026","190","210","0930"):
            self.assertNotIn(fixed,src)

    def test_year_change_with_extraordinary(self):
        start,end=date(2025,12,17),date(2026,1,15)
        hol={date(2025,12,25),date(2026,1,1),date(2026,1,6)}
        keys=weekdays(start,end,243,hol)
        keys.append((date(2026,1,2),"1 Extraordinario"))
        keys.append((date(2026,1,14),"2 Extraordinario"))
        keys.sort(key=lambda k:(k[0],"Extra" in k[1]))
        boa.check_issues(keys,start,end)
        with self.assertRaises(ProvincialCoverageError):
            boa.check_issues(keys+[(date(2026,1,15),"4 Extraordinario")],start,end)

    def test_missing_issue_or_edges_fail(self):
        start,end=date(2026,10,1),date(2026,10,30)
        keys=weekdays(start,end,191)
        boa.check_issues(keys,start,end)
        with self.assertRaises(ProvincialCoverageError):
            boa.check_issues(keys[:5]+keys[6:],start,end)
        with self.assertRaises(ProvincialCoverageError):
            boa.check_issues(keys[3:],start,end)
        # Última edición el martes 27 con hoy viernes 30: 3 días, admitido.
        boa.check_issues(keys[:-3],start,end)
        with self.assertRaises(ProvincialCoverageError):
            boa.check_issues(keys[:-4],start,end)

    def test_json_dates_must_be_in_window(self):
        start,end=date(2025,12,17),date(2026,1,15)
        days=[start+timedelta(days=i) for i in range(30)]
        items=[row(i+1,200,f"{i+1:09d}",days[i%30],"5") for i in range(200)]
        out=boa.read_json(json.dumps(items).encode("ISO-8859-1"),start,end)
        self.assertEqual(len(out),200)
        items[10]["FechaPublicacion"]="20251216"
        with self.assertRaises(ProvincialCoverageError):
            boa.read_json(json.dumps(items).encode("ISO-8859-1"),start,end)
        items[10]["FechaPublicacion"]="20251217";items[11]["Numeroboletin"]="5 bis"
        with self.assertRaises(ProvincialCoverageError):
            boa.read_json(json.dumps(items).encode("ISO-8859-1"),start,end)


if __name__=="__main__":
    unittest.main()
