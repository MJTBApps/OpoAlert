"""Regresiones basadas en diagnostico 0.4.7 (27 entradas, 25 filas BOP)."""
from datetime import date
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bop_full import _index_for_range, CoverageError, scan_browser
from test_bop_full import FakePage, fixture, A

RANGE = (date(2026, 9, 28), date(2026, 10, 2))


def page_data(n=25, old_dates=('21/08/2026', '31/08/2026'), displayed=25,
              first=1, total=296, after_dates=()):
    def item(reg, day, bulletin):
        return (f"<section><div>Anunci de l'Ajuntament de Benaguasil sobre {A}.</div>"
                f"<span>Núm. registre: {reg}</span>"
                f"<span>Data publicació: {day}</span>"
                f"<span>Butlletí: {bulletin}</span></section>")
    rows=[]
    for i in range(n):
        rows.append(item(f'2026/{12000+i}', '28/09/2026', '188'))
    for i, day in enumerate(old_dates):
        rows.append(item(f'2026/{11000+i}', day, '160' if i % 2 == 0 else '166'))
    for i, day in enumerate(after_dates):
        rows.append(item(f'2026/{13000+i}', day, '206'))
    return ('<html><body><h1>Butlletí Núm. 206</h1>'
            f'<div>Mostrant del {first} al {first+displayed-1} de {total}</div>'
            + ''.join(rows) + '</body></html>')


class EarlierOriginalTests(unittest.TestCase):
    def test_27_records_with_25_in_range_are_audited_as_25(self):
        html=page_data()
        entries, group = _index_for_range(html, RANGE)
        self.assertEqual(len(entries),25)
        self.assertEqual(group,'varios')
        self.assertTrue(all(row['bulletin']=='188' for row in entries))

    def test_dates_outside_range_without_paginator_still_fail(self):
        html=page_data().replace('Mostrant del 1 al 25 de 296','Sin contador')
        with self.assertRaisesRegex(CoverageError,'fuera del rango'):
            _index_for_range(html,RANGE)

    def test_24_in_range_with_2_older_fail(self):
        with self.assertRaisesRegex(CoverageError, 'muestra 25'):
            _index_for_range(page_data(n=24),RANGE)

    def test_newer_external_reference_with_25_valid_rows_is_excluded(self):
        entries, _ = _index_for_range(page_data(old_dates=('21/08/2026',),
                                       after_dates=('27/10/2026',)),RANGE)
        self.assertEqual(len(entries), 25)
        self.assertTrue(all(e['date'] == '28/09/2026' for e in entries))

    def test_paginator_inconsistent_count_fails(self):
        with self.assertRaisesRegex(CoverageError,'muestra 24'):
            _index_for_range(page_data(n=25, old_dates=(),displayed=24),RANGE)

    def test_scan_page_validates_mixed_originals(self):
        page=FakePage([page_data()],has_paginator=True)
        found,audit=scan_browser(page,date_range=RANGE,polite_delay=0)
        self.assertEqual(audit.announcementsRead,25)
        self.assertTrue(audit.complete)
        self.assertEqual(audit.issue_numbers,['188'])

    def test_second_page_with_linked_old_originals(self):
        page1=page_data()
        page2=page_data(n=10,old_dates=('31/08/2026',),displayed=10,first=26,total=35)
        # Distinct in-range register numbers per page.
        page2=page2.replace('2026/12','2026/14')
        page=FakePage([page1,page2],has_paginator=True)
        found,audit=scan_browser(page,date_range=RANGE,polite_delay=0)
        self.assertTrue(audit.complete)
        self.assertEqual(audit.announcementsRead,35)


if __name__=='__main__': unittest.main()
