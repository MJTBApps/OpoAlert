"""Regression tests against the real 2026 portal HTML structure (minimal fixture)."""
import sys
from pathlib import Path
import unittest
from datetime import date
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from alicante import parse_issue as alicante
from castellon import parse_issue as castellon
from provincial_common import classify,ProvincialCoverageError,VerifiedIssue
from province_history import valid_issues,parse_cs_label,make_json

ALI = '''<html><table class="dipu_tabla tabla-edictos-inner">
<tr><th>Fecha</th><th>Nº BOP</th><th>Edicto</th><th>Extracto</th><th>Localidad</th><th>Organismo</th><th>Erratas</th></tr>
<tr><td>28/10/2026</td><td>205</td><td>8223</td><td><a href="https://www.dip-alicante.es/bop2/pdftotal/2026/10/28_205/2026_008223.pdf">CONVOCATORIA CONCURSO DE MÉRITOS PROVISIÓN DE 1 DOTACIÓN PUESTO TRABAJO CONDUCTOR/A</a></td><td>Alicante/Alacant</td><td>AYUNTAMIENTO ALICANTE</td><td></td></tr>
<tr><td>28/10/2026</td><td>205</td><td>7995</td><td><a href="https://www.dip-alicante.es/bop2/pdftotal/2026/10/28_205/2026_007995.pdf">PADRÓN DE AGUA Y ALCANTARILLADO 1º TRIM</a></td><td>Almoradí</td><td>AYUNTAMIENTO ALMORADÍ</td><td></td></tr>
</table></html>'''
CAS = '''<html><form id="busquedaBoletinesForm">
<table><tr><td><label>Sumario BOP Nº 130</label></td><td>27/10/2026</td></tr></table>
<span class="titulo2">Diputació Provincial de Castelló / Diputación Provincial de Castellón</span>
<a href="https://bop.dipcas.es/PortalBOP/api/descargarAnuncio?idAnuncio=168667&amp;idioma=es">PDF</a>
<span class="titulo4">Lista Provisional aspirantes concurso-oposición Profesor Ciencias de la Actividad Física y Deporte</span>
<span class="titulo3">AJUNTAMENT DE VINARÒS</span>
<a href="https://bop.dipcas.es/PortalBOP/api/descargarAnuncio?idAnuncio=168678&amp;idioma=es">PDF</a>
<span class="titulo4">BASES Y CONVOCATORIA DOS PLAZAS DE AUXILIAR ADMINISTRATIVO</span>
</form></html>'''

class ProvincialTests(unittest.TestCase):
    def test_alicante_complete_rows(self):
        a=alicante(ALI,'28/10/2026')
        self.assertEqual((a.number,a.announcements_read,len(a.opportunities)),('205',2,1))
        self.assertEqual(a.opportunities[0]['id'],'AL-2026-8223')
        self.assertIn('www.dip-alicante.es',a.opportunities[0]['url'])
    def test_alicante_reject_missing_data(self):
        with self.assertRaises(ProvincialCoverageError):alicante(ALI.replace('<td>8223</td>','<td></td>'))
        with self.assertRaises(ProvincialCoverageError):alicante(ALI,'27/10/2026')
        with self.assertRaises(ProvincialCoverageError):alicante(ALI.replace('www.dip-alicante.es','malicioso.example'))
        with self.assertRaises(ProvincialCoverageError):alicante('<html/>')
    def test_castellon_complete_pdf_pairing(self):
        c=castellon(CAS,'27/10/2026','130')
        self.assertEqual((c.number,c.announcements_read,len(c.opportunities)),('130',2,1))
        self.assertEqual(c.opportunities[0]['id'],'CS-168678')
        self.assertEqual(c.opportunities[0]['entity'],'AJUNTAMENT DE VINARÒS')
    def test_castellon_reject_missing_title_or_date(self):
        with self.assertRaises(ProvincialCoverageError):castellon(CAS.replace('span class="titulo4"','span class="otra"',1))
        with self.assertRaises(ProvincialCoverageError):castellon(CAS,'28/10/2026')
        with self.assertRaises(ProvincialCoverageError):castellon(CAS.replace('168678','168667'))
    def test_classification(self):
        for title,expected in (
            ('CONVOCATORIA PLAZAS DE ADMINISTRATIVO','Plaza / oposición'),
            ('CONVOCATORIA PUESTOS DE TRABAJO POR LIBRE DESIGNACIÓN','Plaza / oposición'),
            ('BASES BOLSA DE TRABAJO DE CELADOR','Bolsa de trabajo'),
            ('BASES BORSA DE TREBALL DE MONITOR','Bolsa de trabajo'),
            ('CONVOCATORIA DE SUBVENCIONES CULTURALES',None),
            ('Lista Provisional aspirantes oposición',None),
            ('ANUNCIO NOMBRAMIENTO FUNCIONARIOS DE CARRERA',None),
        ):
            with self.subTest(title=title):self.assertEqual(classify(title),expected)
    def test_carousel_dates_and_numbering(self):
        self.assertEqual(parse_cs_label('Nº 130\nmartes 27\nOctubre\n2026'),('130',date(2026,10,27)))
        issues=[VerifiedIssue('Castellón','27/10/2026','130',27,()),VerifiedIssue('Castellón','24/10/2026','129',34,())]
        with self.assertRaises(ProvincialCoverageError):valid_issues(issues,'Castellon',date(2026,9,29),date(2026,10,28))
    def test_json_manifest_preserves_province_and_official_pdf(self):
        issue=alicante(ALI,'28/10/2026')
        result=make_json([issue],'Alicante','https://sede.diputacionalicante.es/consultas.bop/',date(2026,10,28),date(2026,10,28))
        self.assertTrue(result['coverage']['complete'])
        self.assertEqual(result['province'],'Alicante')
        self.assertEqual(result['historyCoverage']['announcementsRead'],2)
        self.assertEqual(len(result['notices']),1)

if __name__=='__main__':unittest.main()
