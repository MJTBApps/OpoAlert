import sys
import unittest
from datetime import date,timedelta
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from provincial_common import ProvincialCoverageError
import dogc_autonomico as dc


def month_rows(year,month,published):
    """Calendario mensual simulado: published = {día: número}."""
    rows=[]
    for d in range(1,dc.days_in_month(year,month)+1):
        day=date(year,month,d)
        n=published.get(day)
        rows.append({"date":day.strftime("%d/%m/%Y"),"hasDOGC":n is not None,
                     "linkDOGC":f"https://dogc.gencat.cat/?anyDOGC={year}&numDOGC={n}&language=ca_ES" if n else ""})
    return rows


def weekdays(start,end,first,skip=()):
    out={};n=first;day=start
    while day<=end:
        if day.weekday()<5 and day not in skip:
            out[day]=str(n);n+=1
        day+=timedelta(days=1)
    return out


class WindowTest(unittest.TestCase):
    def test_window_and_months(self):
        self.assertEqual(dc.window(date(2026,1,15)),(date(2025,12,17),date(2026,1,15)))
        self.assertEqual(dc.months_between(date(2025,12,17),date(2026,1,15)),[(2025,12),(2026,1)])
        self.assertEqual(dc.months_between(date(2026,10,1),date(2026,10,30)),[(2026,10)])
        self.assertEqual(dc.days_in_month(2028,2),29)

    def test_no_fixed_dates_left(self):
        src=Path(dc.__file__).read_text(encoding="utf-8")
        for fixed in ("2026","9761","9783","(9,10)","setembre|octubre"):
            self.assertNotIn(fixed,src)

    def test_year_change_continuous_numbering(self):
        start,end=date(2025,12,17),date(2026,1,15)
        holidays={date(2025,12,25),date(2025,12,26),date(2026,1,1),date(2026,1,6)}
        pub=weekdays(start,end,9565,holidays)
        records={}
        records.update(dc.parse_calendar(month_rows(2025,12,pub),2025,12))
        records.update(dc.parse_calendar(month_rows(2026,1,pub),2026,1))
        sel=dc.select_window(records,start,end)
        self.assertEqual(len(sel),30)
        self.assertGreaterEqual(sum(n is not None for _,n in sel),dc.MIN_MAIN_ISSUES)

    def test_gap_or_late_edges_fail(self):
        start,end=date(2026,10,1),date(2026,10,30)
        pub=weekdays(start,end,9762)
        records=dc.parse_calendar(month_rows(2026,10,pub),2026,10)
        dc.select_window(records,start,end)
        broken=dict(records);broken[date(2026,10,14)]=None
        for d in [d for d in broken if broken[d] and d>date(2026,10,14)]:
            broken[d]=str(int(broken[d])+1)
        with self.assertRaises(ProvincialCoverageError):
            dc.select_window(broken,start,end)
        late={d:(n if d>=date(2026,10,6) else None) for d,n in records.items()}
        with self.assertRaises(ProvincialCoverageError):
            dc.select_window(late,start,end)

    def test_truncated_calendar_fails(self):
        with self.assertRaises(ProvincialCoverageError):
            dc.parse_calendar(month_rows(2026,10,{})[:-1],2026,10)

    def test_supplement_date_any_month(self):
        self.assertTrue(dc.supplement_date_ok("Dijous, 29 d’octubre de 2026",date(2026,10,29)))
        self.assertTrue(dc.supplement_date_ok("2 de gener de 2026",date(2026,1,2)))
        self.assertTrue(dc.supplement_date_ok("3 de març de 2027",date(2027,3,3)))
        self.assertFalse(dc.supplement_date_ok("2 de gener de 2025",date(2026,1,2)))
        self.assertFalse(dc.supplement_date_ok("31 de desembre de 2025",date(2026,1,2)))


if __name__=="__main__":
    unittest.main()
