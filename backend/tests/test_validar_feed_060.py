"""Pruebas de regresion con el feed REAL auditado el 28/10/2026."""
import copy
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from validar_feed import validate_feed, FeedValidationError
from publicar_feed import publicar


class FeedAuditedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original=json.loads((ROOT/'backend/tests/fixture_feed_2026_10_28.json').read_text(encoding='utf-8'))

    def valid(self, feed=None):
        return validate_feed(feed or self.original,
            expected_end=date(2026,10,28),
            now=datetime(2026,10,28,12,tzinfo=timezone.utc))

    def test_real_user_feed_has_full_30_days(self):
        detail=self.valid()
        self.assertEqual(detail['daysWithBulletin'],21)
        self.assertEqual(detail['pages'],54)
        self.assertEqual(detail['announcements'],1270)
        self.assertEqual(detail['opportunities'],50)

    def test_reject_incomplete_history(self):
        data=copy.deepcopy(self.original)
        data['historyCoverage']['complete']=False
        with self.assertRaises(FeedValidationError): self.valid(data)

    def test_reject_missing_calendar_day(self):
        data=copy.deepcopy(self.original)
        data['historyCoverage']['chunks'][0]['publishedDates'].pop()
        with self.assertRaises(FeedValidationError): self.valid(data)

    def test_reject_missing_window(self):
        data=copy.deepcopy(self.original)
        data['historyCoverage']['chunks'].pop()
        with self.assertRaises(FeedValidationError): self.valid(data)

    def test_reject_duplicate_notices(self):
        data=copy.deepcopy(self.original)
        data['notices'][1]['id']=data['notices'][0]['id']
        with self.assertRaises(FeedValidationError): self.valid(data)

    def test_reject_out_of_range_notice(self):
        data=copy.deepcopy(self.original)
        data['notices'][0]['date']='26/08/2026'
        with self.assertRaises(FeedValidationError): self.valid(data)

    def test_reject_mismatched_registered_url(self):
        data=copy.deepcopy(self.original)
        data['notices'][0]['url']=data['notices'][1]['url']
        with self.assertRaises(FeedValidationError): self.valid(data)

    def test_reject_mismatched_total(self):
        data=copy.deepcopy(self.original)
        data['historyCoverage']['announcementsRead']=12
        with self.assertRaises(FeedValidationError): self.valid(data)

    def test_reject_unexpected_source(self):
        data=copy.deepcopy(self.original)
        data['source']='https://example.org/'
        with self.assertRaises(FeedValidationError): self.valid(data)

    def test_reject_historial_de_29_dias(self):
        data=copy.deepcopy(self.original)
        data['historyCoverage']['rangeStart']='2026-09-30'
        with self.assertRaises(FeedValidationError): self.valid(data)

    def test_reject_outdated_history(self):
        with self.assertRaises(FeedValidationError):
            validate_feed(self.original,expected_end=date(2026,10,29),
                    now=datetime(2026,10,29,12,tzinfo=timezone.utc))

    def test_reject_old_timestamp_when_auto_publishing(self):
        with self.assertRaises(FeedValidationError):
            validate_feed(self.original,max_age=timedelta(minutes=10),
                    now=datetime(2026,10,28,9,tzinfo=timezone.utc))

    def test_validator_accepts_rolling_window_on_a_new_day(self):
        data=copy.deepcopy(self.original)
        shift=timedelta(days=1)
        hc=data['historyCoverage']
        for key in ('rangeStart','rangeEnd'):
            hc[key]=(date.fromisoformat(hc[key])+shift).isoformat()
        hc['verifiedUTC']='2026-10-29T10:05:00+00:00'
        data['lastCheckedUTC']='2026-10-29T10:06:00+00:00'
        for chunk in hc['chunks']:
            for key in ('requestedStart','requestedEnd','start','end'):
                if key in chunk:
                    chunk[key]=(date.fromisoformat(chunk[key])+shift).isoformat()
            for key in ('publishedDates','nonPublicationDates'):
                if key in chunk:
                    chunk[key]=[(date.fromisoformat(x)+shift).isoformat() for x in chunk[key]]
        from datetime import datetime as dt
        for item in data['notices']:
            item['date']=(dt.strptime(item['date'],'%d/%m/%Y').date()+shift).strftime('%d/%m/%Y')
        report=validate_feed(data,expected_end=date(2026,10,29),
                    max_age=timedelta(hours=3),
                    now=datetime(2026,10,29,11,tzinfo=timezone.utc))
        self.assertEqual(report['opportunities'],50)

    def test_publicar_requires_whole_coherent_history(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            d=Path(d)
            good=d/'good.json'; bad=d/'bad.json'; target=d/'feed.json'
            good.write_text(json.dumps(self.original),encoding='utf-8')
            self.assertEqual(publicar(good,target,True),50)
            old=target.read_bytes()
            data=copy.deepcopy(self.original)
            data['historyCoverage']['chunks'][1]['complete']=False
            bad.write_text(json.dumps(data),encoding='utf-8')
            with self.assertRaises(Exception): publicar(bad,target,True)
            self.assertEqual(target.read_bytes(),old)

if __name__=='__main__': unittest.main()
