import json
from pathlib import Path
import sys
import tempfile
import unittest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
from bop_full import scan_browser, CoverageError, publish_result
from scan import extract_index


def fixture(rows, issue=206):
    items = []
    for reg, title, num in rows:
        items.append(f'''<section><p>Municipis</p><p>Ajuntament de Benaguasil</p>
          <div>Anunci de l'Ajuntament de Benaguasil sobre {title}.</div>
          <span>Núm. registre: {reg}</span>
          <span>Data publicació: 27/10/2026</span><span>Butlletí: {num}</span></section>''')
    return f'<html><body><h1>Butlletí Núm. {issue}</h1>{"".join(items)}</body></html>'


class FakeControl:
    def __init__(self, browser):
        self.browser = browser
    def is_visible(self):
        return True
    def is_disabled(self):
        return self.browser.i == len(self.browser.pages) - 1
    def get_attribute(self, name):
        return 'ui-state-disabled' if name == 'class' and self.is_disabled() else None
    def click(self, timeout=None):
        if not self.browser.stuck:
            self.browser.i += 1


class FakeLocator:
    def __init__(self, browser, selector):
        self.browser = browser
        self.selector = selector
    def count(self):
        if not self.browser.has_paginator:
            return 0
        return int(self.selector == '.ui-paginator-next')
    def nth(self, i):
        return FakeControl(self.browser)


class FakePage:
    def __init__(self, pages, has_paginator=True, stuck=False):
        self.pages, self.has_paginator, self.stuck, self.i = pages, has_paginator, stuck, 0
    def content(self):
        return self.pages[self.i]
    def locator(self, selector):
        return FakeLocator(self, selector)
    def wait_for_timeout(self, ms):
        pass


A = 'l’aprovació de les bases de la convocatòria per a la constitució d’una borsa per a treballador/a social'
B = 'la convocatòria per a una plaça de tècnic/a de gestió'
C = 'el nomenament com a funcionari de carrera en una plaça de policia local'
D = 'la convocatòria de subvencions per a associacions'

class FullBopTests(unittest.TestCase):
    def test_two_pages_with_correction_original_from_another_bulletin(self):
        page1 = fixture([
            ('2026/12950', A, '206'),
            ('2026/12951', C, '206'),
            ('2026/12333', B, '205'),
        ])
        page2 = fixture([
            ('2026/12953', A, '206'),
            ('2026/13055', B, '206'),
            ('2026/13066', D, '206'),
        ])
        opportunities, audit = scan_browser(FakePage([page1, page2]), polite_delay=0)
        self.assertEqual({e['id'] for e in opportunities}, {'2026/12950','2026/12953','2026/13055'})
        self.assertTrue(audit.complete)
        self.assertEqual(audit.pagesVisited, 2)
        self.assertEqual(audit.announcementsRead, 5)
        self.assertEqual(audit.opportunities, 3)

    def test_no_paginator_cannot_be_called_complete(self):
        notices, audit = scan_browser(FakePage([fixture([('2026/12950', A, '206')])], has_paginator=False))
        self.assertFalse(audit.complete)
        self.assertEqual(len(notices), 1)
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)/'data.json'
            with self.assertRaises(CoverageError):
                publish_result(target, notices, audit)
            self.assertFalse(target.exists())

    def test_pagination_click_no_effect_raises(self):
        rows = [('2026/12950', A, '206')]
        with self.assertRaisesRegex(CoverageError, 'no cambio'):
            scan_browser(FakePage([fixture(rows), fixture([('2026/12953', B, '206')])], stuck=True))

    def test_retain_historical_opportunities(self):
        notice1, audit1 = scan_browser(FakePage([fixture([('2026/12950', A, '206')])]))
        notice2, audit2 = scan_browser(FakePage([fixture([('2026/12953', B, '207')], issue=207)]))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'feed.json'
            self.assertEqual(publish_result(path, notice1, audit1), 1)
            self.assertEqual(publish_result(path, notice2, audit2), 2)
            data = json.loads(path.read_text(encoding='utf-8'))
            self.assertEqual({r['id'] for r in data['notices']}, {'2026/12950','2026/12953'})
            self.assertTrue(data['coverage']['complete'])

    def test_supplement_metadata(self):
        html = '''<html><body><h1>Butlletí Núm. 206</h1>
        Anunci de l'Ajuntament de Xàtiva sobre les bases de constitució d'una borsa de treball.
        Núm. registre: 2026/13333 Data publicació: 27/10/2026 Suplement: 206-01</body></html>'''
        entries, issue = extract_index(html)
        self.assertEqual(issue, '206')
        self.assertEqual(entries[0]['bulletin'], '206-01')
        self.assertEqual(entries[0]['type'], 'Bolsa de trabajo')

if __name__ == '__main__':
    unittest.main()
