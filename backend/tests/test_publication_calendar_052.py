"""OpoAlert 0.5.2: regression contra calendario OFICIAL real (27/10/2026).
No conectarse a la web ni depender de librerias de testing externas.
"""
from datetime import date, timedelta
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from history import (CoverageError, published_days_in_month,
                     publication_windows, official_published_days,
                     verify_window)

SOURCE = Path(__file__).with_name('fixture_calendario_oficial_oct_2026.html').read_text(encoding='utf-8')


class OfficialCalendarTests(unittest.TestCase):
    def test_real_calendar_disables_saturday_3_october(self):
        days = published_days_in_month(SOURCE, 2026, 10)
        self.assertIn(date(2026,10,2), days)
        self.assertNotIn(date(2026,10,3), days)
        self.assertNotIn(date(2026,10,4), days)
        self.assertIn(date(2026,10,5), days)

    def test_real_calendar_excludes_nonpublication_friday_9(self):
        days = published_days_in_month(SOURCE, 2026, 10)
        self.assertIn(date(2026,10,8), days)
        self.assertNotIn(date(2026,10,9), days)
        self.assertNotIn(date(2026,10,10), days)
        self.assertNotIn(date(2026,10,11), days)
        self.assertIn(date(2026,10,12), days)  # El portal si lo habilita.

    def test_windows_never_start_or_end_on_disabled_publication_day(self):
        first,last = date(2026,9,29),date(2026,10,28)
        official = [date(2026,9,29),date(2026,9,30)]
        official += sorted(published_days_in_month(SOURCE, 2026,10))
        official += [date(2026,10,28)]  # La captura era del dia 27.
        plan=publication_windows(first,last,sorted(official),5)
        self.assertEqual(len(plan),6)
        self.assertEqual((plan[0]['start'],plan[0]['end']),
                         (date(2026,9,29),date(2026,10,2)))
        self.assertEqual((plan[1]['start'],plan[1]['end']),
                         (date(2026,10,5),date(2026,10,8)))
        self.assertIn(date(2026,10,3),plan[0]['nonPublicationDates'])
        self.assertIn(date(2026,10,4),plan[1]['nonPublicationDates'])
        self.assertIn(date(2026,10,9),plan[2]['nonPublicationDates'])
        self.assertEqual(sorted(d for w in plan for d in w['publishedDates']), sorted(official))
        self.assertEqual((plan[-1]['start'],plan[-1]['end']),
                         (date(2026,10,26),date(2026,10,28)))

    def test_skip_window_only_if_calendar_certifies_no_publication(self):
        first,last = date(2026,10,2),date(2026,10,7)
        plan=publication_windows(first,last,[date(2026,10,2),date(2026,10,7)],2)
        self.assertIsNone(plan[1]['start'])
        self.assertEqual(plan[1]['nonPublicationDates'], [date(2026,10,4),date(2026,10,5)])
        self.assertEqual(sorted(d for w in plan for d in w['publishedDates']),
                         [date(2026,10,2),date(2026,10,7)])

    def test_refuse_empty_duplicate_or_outside_published_dates(self):
        first,last=date(2026,9,29),date(2026,10,3)
        with self.assertRaises(CoverageError):
            publication_windows(first,last,[],5)
        with self.assertRaises(CoverageError):
            publication_windows(first,last,[date(2026,9,29)]*2,5)
        with self.assertRaises(CoverageError):
            publication_windows(first,last,[date(2026,10,4)],5)

    def test_full_interval_verified_against_all_official_edition_dates(self):
        class Audit:
            complete=True
            announcementsRead=25
            issue_numbers=['187','188']
            issue_dates=['2026-09-29','2026-09-30']
        verify_window([],Audit(),date(2026,9,29),date(2026,9,30),25,'207',
                      expected_published_dates=[date(2026,9,29),date(2026,9,30)])
        with self.assertRaisesRegex(CoverageError,'exactamente las fechas'):
            verify_window([],Audit(),date(2026,9,29),date(2026,10,2),25,'207',
                          expected_published_dates=[date(2026,9,29),date(2026,9,30),date(2026,10,2)])

    def test_current_month_parsing_with_full_captured_calendar(self):
        # La fixture NO contiene ViewState, cookies ni ID de sesion.
        self.assertNotIn('jsessionid', SOURCE)
        self.assertNotIn('javax.faces.ViewState', SOURCE)
        self.assertEqual(min(published_days_in_month(SOURCE,2026,10)),date(2026,10,1))


class FakePrev:
    def __init__(self,panel): self.panel=panel
    def count(self): return 1
    def is_visible(self): return True
    def click(self,timeout=0): self.panel.month=(self.panel.month[0],self.panel.month[1]-1)

class FakePanel:
    def __init__(self): self.month=(2026,10)
    def count(self): return 1
    def is_visible(self): return True
    def locator(self,selector):
        assert selector=='.ui-datepicker-prev'
        return FakePrev(self)
    def inner_html(self):
        if self.month == (2026,10): return SOURCE
        if self.month == (2026,9):
            return ('<table class="ui-datepicker-calendar"><tr>'
                    '<td><a class="ui-state-default">28</a></td>'
                    '<td><a class="ui-state-default">29</a></td>'
                    '<td><a class="ui-state-default">30</a></td>'
                    '</tr></table>')
        raise AssertionError('unexpected month')

class FakePage:
    def __init__(self): self.panel=FakePanel()
    def locator(self,selector):
        assert selector=='[id="calen_panel"]'
        return self.panel
    def wait_for_timeout(self,ms): pass

class CalendarTraversalTests(unittest.TestCase):
    def test_traverses_all_months_and_does_not_choose_saturday(self):
        from unittest.mock import patch
        page=FakePage()
        with patch('history._visible_calendar_month', lambda p:p.month):
            days=official_published_days(page,date(2026,9,29),date(2026,10,27))
        self.assertEqual(page.panel.month,(2026,9))
        self.assertIn(date(2026,9,29),days)
        self.assertIn(date(2026,10,2),days)
        self.assertNotIn(date(2026,10,3),days)
        self.assertNotIn(date(2026,10,9),days)

if __name__ == '__main__': unittest.main()
