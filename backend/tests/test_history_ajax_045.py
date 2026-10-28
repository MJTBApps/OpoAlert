"""Regresion 0.4.5: prueba ventanas, POST y criterios de cobertura.
Las pruebas son simuladas; la comprobacion real se hace en Windows con Playwright.
"""
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from history import (date_windows, _posted_date_values, _is_search_ajax,
                     verify_window, CoverageError)

class FakeRequest:
    def __init__(self, post, method='POST'):
        self.post_data = post
        self.method = method

class FakeResponse:
    def __init__(self, post, method='POST', url='https://bop.dival.es/bop/xhtml/portal.xhtml'):
        self.request = FakeRequest(post, method)
        self.url = url

class FakeAudit:
    def __init__(self, total, issues, complete=True):
        self.announcementsRead = total
        self.issue_numbers = issues
        self.complete = complete

class TestHistoryAjax045(unittest.TestCase):
    def test_windows_cover_all_thirty_days_in_five_day_windows(self):
        first, last = date(2026, 9, 28), date(2026, 10, 27)
        windows = date_windows(first, last, 5)
        self.assertEqual(len(windows), 6)
        self.assertEqual(windows[0], (date(2026,9,28),date(2026,10,2)))
        self.assertEqual(windows[-1], (date(2026,10,23),date(2026,10,27)))
        expanded = [d for a,b in windows for d in
                    (a + timedelta(days=i) for i in range((b-a).days+1))]
        self.assertEqual(len(expanded), 30)
        self.assertEqual(len(set(expanded)),30)
        self.assertEqual(expanded[0],first)
        self.assertEqual(expanded[-1],last)

    def test_date_post_fields_are_read_from_real_request(self):
        data = ('j_idt131=j_idt131&filtroCalendarioIni_input=28%2F09%2F2026&'
                'filtroCalendarioFin_input=27%2F10%2F2026&'
                'javax.faces.source=buscarBtn')
        self.assertEqual(_posted_date_values(data), ('28/09/2026', '27/10/2026'))
        self.assertTrue(_is_search_ajax(FakeResponse(data)))
        self.assertFalse(_is_search_ajax(FakeResponse(data,method='GET')))
        self.assertFalse(_is_search_ajax(FakeResponse(data.replace('buscarBtn','foo'))))

    def test_latest_window_rejects_stale_single_issue(self):
        end = date.today()
        start = end - timedelta(days=4)
        with self.assertRaisesRegex(CoverageError,'ultimo boletin'):
            verify_window([],FakeAudit(66,['206']),start,end,66,'206')

    def test_multi_issue_window_uses_all_notices_not_only_jobs(self):
        end = date.today()
        start = end - timedelta(days=4)
        found=[{'bulletin':'206','id':'2026/12950'}]
        self.assertEqual(verify_window(found,FakeAudit(200,['204','205','206']),
                                       start,end,200,'206'),{'204','205','206'})

    def test_paginator_total_mismatch_cannot_be_published(self):
        with self.assertRaisesRegex(CoverageError,'declara 100'):
            verify_window([],FakeAudit(66,['205','206']),
                          date(2026,10,23),date(2026,10,27),100,'206')

    def test_partial_paginations_must_stop(self):
        with self.assertRaisesRegex(CoverageError,'Paginador no confirmado'):
            verify_window([],FakeAudit(66,['205','206'],False),
                          date(2026,10,23),date(2026,10,27),66,'206')

if __name__ == '__main__':
    unittest.main()

class TestAllIssueCoverage(unittest.TestCase):
    def test_audit_tracks_bulletins_with_no_employment_notices(self):
        # Adapta el HTML de prueba a los campos usados por scan_browser.
        from bop_full import scan_browser
        from test_bop_full import FakePage, fixture, C, A
        html1 = fixture([('2026/13000', C, '205')], issue=206).replace('27/10/2026','26/10/2026')
        html2 = fixture([('2026/12950', A, '206')], issue=206)
        found, audit = scan_browser(FakePage([html1, html2]), polite_delay=0,
                                    date_range=(date(2026,10,23),date(2026,10,27)))
        self.assertEqual(len(found),1)
        self.assertEqual(audit.issue_numbers,['205','206'])
