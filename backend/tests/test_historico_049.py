"""Regresiones del diagnostico real del 27/10: 27 metadatos frente a 25 filas.

Estos ensayos simulan el DOM del BOP: no reemplazan una comprobacion con la
web oficial. Ejercitan el conteo final (296), los enlaces ajenos y el filtro.
"""
from datetime import date
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bop_full import _index_for_range, CoverageError, scan_browser
from test_bop_full import FakePage, A

START, END = date(2026, 9, 28), date(2026, 10, 2)


def sample(first=1, size=25, total=296, attachments=(), valid_date='29/09/2026'):
    things = []
    for number in range(first, first + size):
        things.append((f'2026/{10000+number}', valid_date, '187'))
    things.extend(attachments)
    fragments = []
    for reg, day, issue in things:
        fragments.append(
            f'<article><div>Anunci de l\'Ajuntament de Xàtiva sobre {A}.</div>'
            f'<span>Núm. registre: {reg}</span>'
            f'<span>Data publicació: {day}</span>'
            f'<span>Butlletí: {issue}</span></article>')
    return (f'<html><body><h1>Butlletí Núm. 206</h1>'
            f'<div>Mostrant del {first} al {first+size-1} de {total}</div>'
            + ''.join(fragments) + '</body></html>')


class History49(unittest.TestCase):
    def test_real_case_27_extracted_25_displayed_later_links(self):
        html = sample(attachments=(('2026/12374', '15/10/2026', '198'),
                                   ('2026/12375', '15/10/2026', '198')))
        entries, _ = _index_for_range(html, (START, END))
        self.assertEqual(len(entries), 25)
        self.assertNotIn('2026/12374', {e['id'] for e in entries})

    def test_mixed_old_and_future_links_are_excluded_if_counts_match(self):
        html = sample(attachments=(('2026/11111', '21/08/2026', '160'),
                                   ('2026/12374', '15/10/2026', '198')))
        entries, _ = _index_for_range(html, (START, END))
        self.assertEqual(len(entries), 25)

    def test_missing_an_entry_does_not_silently_pass(self):
        html = sample(size=24, attachments=(('2026/12374', '15/10/2026', '198'),))
        html = html.replace('Mostrant del 1 al 24 de 296',
                            'Mostrant del 1 al 25 de 296')
        with self.assertRaisesRegex(CoverageError, 'muestra 25'):
            _index_for_range(html, (START, END))

    def test_duplicate_extra_not_counted(self):
        html = sample(attachments=(('2026/12374', '15/10/2026', '198'),))
        entries, _ = _index_for_range(html, (START, END))
        self.assertEqual(len(entries), 25)

    def test_full_12_pages_must_match_296_results(self):
        pages = []
        for first in range(1, 297, 25):
            count = min(25, 297 - first)
            attachments = ((f'2026/{32000+first}', '15/10/2026', '198'),)
            pages.append(sample(first, count, 296, attachments))
        found, audit = scan_browser(FakePage(pages), date_range=(START, END),
                                    polite_delay=0, max_pages=15)
        self.assertTrue(audit.complete)
        self.assertEqual(audit.announcementsRead, 296)
        self.assertEqual(audit.pagesVisited, 12)
        self.assertEqual(audit.opportunities, 296)
        self.assertEqual(len(found), 296)


if __name__ == '__main__':
    unittest.main()
