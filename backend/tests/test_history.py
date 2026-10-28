import json
import tempfile
from pathlib import Path
from datetime import date
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bop_full import CoverageError, scan_browser, publish_result
from history import merge_history
from publicar_feed import publicar
from test_bop_full import FakePage, fixture, A, B

class HistoryTests(unittest.TestCase):
    def test_date_range_collects_two_issues(self):
        page1 = fixture([('2026/12950', A, '206')], issue=206)
        page2 = fixture([('2026/12953', B, '205')], issue=206).replace('27/10/2026', '26/10/2026')
        found, audit = scan_browser(FakePage([page1, page2]), polite_delay=0,
             date_range=(date(2026,10,1), date(2026,10,27)))
        self.assertEqual(len(found), 2)
        self.assertTrue(audit.complete)
        self.assertEqual(audit.bulletin, 'varios')

    def test_range_rejects_outside_date(self):
        page = fixture([('2026/12950', A, '206')])
        with self.assertRaisesRegex(CoverageError, 'fuera del rango'):
            scan_browser(FakePage([page]), date_range=(date(2026,10,1), date(2026,10,26)))

    def test_range_saves_metadata_and_no_duplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp)/'feed.json'
            daily, audit_daily = scan_browser(FakePage([fixture([('2026/12950',A,'206')])]))
            publish_result(db,daily,audit_daily)
            historic = [daily[0], {
                **daily[0], 'id': '2026/12953', 'bulletin': '205', 'date': '26/10/2026'
            }]
            audit_h = type('FakeAudit', (), {'complete': True, 'pagesVisited': 2,
               'announcementsRead': 50, 'status': 'paginator_last_page'})()
            total, issues = merge_history(db,historic,audit_h,date(2026,10,1),date(2026,10,27))
            self.assertEqual(total, 2)
            self.assertEqual(issues, 2)
            data=json.loads(db.read_text(encoding='utf-8'))
            self.assertTrue(data['historyCoverage']['complete'])
            self.assertEqual(len(data['notices']),2)
            # Se conserva la auditoria historica al actualizar el ultimo boletin
            publish_result(db,daily,audit_daily)
            self.assertIn('historyCoverage', json.loads(db.read_text(encoding='utf-8')))

    def test_publication_rejects_unverified_historical(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_path=Path(tmp)/'in.json'; output_path=Path(tmp)/'docs.json'
            input_path.write_text('{"coverage":{"complete":true},"notices":[]}', encoding='utf-8')
            with self.assertRaises(CoverageError):
                publicar(input_path, output_path, require_history=True)
            self.assertFalse(output_path.exists())

if __name__ == '__main__':
    unittest.main()
