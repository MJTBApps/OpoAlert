"""Pruebas basadas en la estructura HTML observada en el BOP el 27/10/2026.
No se incluye en el proyecto el HTML de sesion proporcionado por el usuario.
"""
import sys
import unittest
from pathlib import Path
from datetime import date
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scan import extract_index, datagrid_row_count
from bop_full import _index_for_range, CoverageError

BOUNDS=(date(2026,9,28),date(2026,10,2))


def make_page(n=25, related=(23,24), invalid_main=None):
    rows=[]
    for i in range(n):
        day='15/10/2026' if i==invalid_main else '29/09/2026'
        related_item=''
        if i in related:
            related_item=(
                "<div class='anuncio-relacionado'>"
                "<div class='sumario'><a>Anunci de l'Ajuntament de Sagunt "
                "sobre la correcció d'errors d'una convocatòria.</a></div>"
                "<span>Núm. registre: 2026/12360</span>"
                "<span>Data publicació: 15/10/2026</span>"
                "<span>Butlletí: 198</span></div>"
            ).replace('2026/12360',f'2026/{12360+i}')
        rows.append(f'''<div class="ui-g"><div class="ui-datagrid-column ui-g-12 ui-md-12">
        <div class="ui-panel anuncio"><div class="sumario">
        <a>Anunci de l'Ajuntament de Sagunt sobre l'aprovació de les bases
        de la convocatòria per a una plaça de tècnic/a.</a></div>
        <span class="info"><span>Núm. registre: </span>2026/{11000+i}
        <span>Data publicació: </span><a>{day}</a>
        <span>Butlletí: </span><a>187</a>{related_item}</span>
        </div></div></div>''')
    return (f'<html><body><div id="list_paginator_top">Mostrant del 1 al {n} de 296</div>'
            '<div id="list_content">'+''.join(rows)+'</div></body></html>')


class Datagrid050(unittest.TestCase):
    def test_exactly_25_main_rows_not_27_related_metadata(self):
        html=make_page()
        rows,_=extract_index(html)
        self.assertEqual(datagrid_row_count(html),25)
        self.assertEqual(len(rows),25)
        self.assertNotIn('2026/12383',{x['id'] for x in rows})
        self.assertEqual(len({x['id'] for x in rows}),25)
    def test_25_valid_rows_pass_strict_pagination(self):
        rows,_=_index_for_range(make_page(),BOUNDS)
        self.assertEqual(len(rows),25)
        self.assertTrue(all(r['date']=='29/09/2026' for r in rows))
    def test_out_of_range_main_row_is_not_ignored(self):
        with self.assertRaisesRegex(CoverageError,'fichas principales'):
            _index_for_range(make_page(invalid_main=13),BOUNDS)
    def test_bad_paginator_is_not_ignored(self):
        html=make_page().replace('Mostrant del 1 al 25 de 296','Mostrant del 1 al 24 de 296')
        with self.assertRaisesRegex(CoverageError,'declara 24'):
            _index_for_range(html,BOUNDS)
    def test_related_correction_inside_same_interval_does_not_inflate_rows(self):
        html=make_page().replace('15/10/2026','30/09/2026')
        entries,_=_index_for_range(html,BOUNDS)
        self.assertEqual(len(entries),25)
        self.assertTrue(all(int(e['id'].split('/')[1]) < 12000 for e in entries))
    def test_nonstandard_title_still_counted_as_bop_notice(self):
        html=make_page().replace("Anunci de l'Ajuntament de Sagunt sobre l'aprovació de les bases",
                                  "Edicte sobre l'aprovació de les bases")
        entries,_=_index_for_range(html,BOUNDS)
        self.assertEqual(len(entries),25)
        self.assertTrue(entries[0]['title'].startswith('Edicte'))
    def test_structural_rows_require_paginator(self):
        html=make_page().replace('Mostrant del 1 al 25 de 296', 'Paginador no disponible')
        with self.assertRaisesRegex(CoverageError,'No hay contador'):
            _index_for_range(html,BOUNDS)

    def test_missing_metadata_main_row_aborts(self):
        html=make_page().replace('Núm. registre: </span>2026/11013','Registro sin metadatos </span>2026/11013')
        with self.assertRaisesRegex(ValueError,'Ficha principal'):
            extract_index(html)

if __name__=='__main__':unittest.main()
