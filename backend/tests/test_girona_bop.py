import sys
import unittest
from datetime import date,timedelta
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from girona_bop import parse_issue,audit,ProvincialCoverageError,BASE,PROVINCE


def issue_html(number:int, day:date, extra=""):
    pdf=f"https://ssl4.ddgi.cat/bopV1/pdf/{day.year}/{number}/{day.year}{number:03d}09310.pdf"
    return (
      '<html><title>BOP - Butlletí Oficial de la Província de Girona</title><body>'
      f'<h1>Bop número: {number}/0 - {day:%d/%m/%Y}</h1>'
      '<ul>'
      f'<li class="edicte"><a class="linkAjuda" href="{pdf}">'
      "9310 - <span>AJUNTAMENT DE LLANARS</span> - Aprovació de les bases i la convocatòria"
      " del procés selectiu d'una plaça de secretaria intervenció"
      '</a></li>'
      '</ul></body></html>'
    ).replace("9310 - <span>", "9310 - <span>")


class GironaBOPTests(unittest.TestCase):
    def test_parse_real_shape(self):
        day=date(2026,10,28)
        result=parse_issue(issue_html(208,day),208)
        self.assertEqual(result["read"],1)
        self.assertEqual(len(result["notices"]),1)
        self.assertEqual(result["notices"][0]["id"],"GI-2026-208-09310")
        self.assertEqual(result["notices"][0]["province"],PROVINCE)

    def test_reject_wrong_issue_and_fake_pdf(self):
        html=issue_html(208,date(2026,10,28))
        with self.assertRaises(ProvincialCoverageError):
            parse_issue(html,207)
        with self.assertRaises(ProvincialCoverageError):
            parse_issue(html.replace("ssl4.ddgi.cat","evil.example"),208)
        with self.assertRaises(ProvincialCoverageError):
            parse_issue(html.replace("202620809310.pdf","202620809311.pdf"),208)

    def test_official_secondary_pdf_series(self):
        html=issue_html(208,date(2026,10,28)).replace(
            "202620809310.pdf","202620819310.pdf")
        parsed=parse_issue(html,208)
        self.assertEqual(parsed["read"],1)
        self.assertEqual(parsed["notices"][0]["id"],"GI-2026-208-09310")

    def test_full_30_days_by_consecutive_issues(self):
        end=date(2026,10,28)
        weekdays=[end-timedelta(days=i) for i in range(32) if (end-timedelta(days=i)).weekday()<5]
        issues={208-i:issue_html(208-i,day) for i,day in enumerate(weekdays)}
        def fake(url):
            if url==BASE:return issues[208]
            num=int(url.rstrip("/").split("/")[-1])
            return issues[num]
        output=audit(today=end,fetch=fake)
        self.assertEqual((date.fromisoformat(output["historyCoverage"]["rangeEnd"]) -
                          date.fromisoformat(output["historyCoverage"]["rangeStart"])).days,29)
        self.assertEqual(output["coverage"]["opportunities"],len(output["notices"]))
        self.assertEqual(len(output["historyCoverage"]["publicationDates"]) +
                         len(output["historyCoverage"]["nonPublicationDates"]),30)

    def test_fails_incomplete_issues(self):
        end=date(2026,10,28)
        html=issue_html(208,end)
        def fake(url):
            if url==BASE:return html
            return html
        with self.assertRaises(ProvincialCoverageError):
            audit(today=end,fetch=fake)

if __name__=="__main__":unittest.main()
