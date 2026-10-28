import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scan import classify, extract, entity_from_title

class BopTests(unittest.TestCase):
    def test_real_titles(self):
        html = (ROOT / 'tests' / 'fixture_bop_2026_10_27.html').read_text(encoding='utf-8')
        notices = extract(html)
        self.assertEqual({n['id'] for n in notices}, {'2026/12950', '2026/12953'})
        self.assertTrue(all(n['type'] == 'Bolsa de trabajo' for n in notices))
        self.assertTrue(all(n['entity'] == 'Ayuntamiento de Benaguasil' for n in notices))
        self.assertTrue(all('anuncioNumReg' in n['url'] for n in notices))

    def test_exclude_notices_not_opening_jobs(self):
        self.assertIsNone(classify('Convocatòria de subvencions destinades a entitats esportives'))
        self.assertIsNone(classify('Nomenament com a funcionari de carrera de cinc places'))
        self.assertIsNone(classify('Relació definitiva de persones admeses al procés selectiu per a una plaça'))
        self.assertIsNone(classify('Convocatòria pública per a jutge de pau substitut'))

    def test_accept_spanish_and_valencian(self):
        self.assertEqual(classify('Aprobación de las bases de la convocatoria de una plaza de administrativo'), 'Plaza / oposición')
        self.assertEqual(classify('Convocatòria per a constitució d’una borsa de treball de personal auxiliar'), 'Bolsa de trabajo')

    def test_entity_local_menor_from_real_notice(self):
        title = ("Anunci de l'Entitat Local Menor del Perelló sobre la "
                 "convocatòria corresponent a la cobertura definitiva de la plaça "
                 "de personal laboral fix conserge poliesportiu.")
        self.assertEqual(entity_from_title(title), "Entidad Local Menor del Perelló")

    def test_four_real_notices_from_206(self):
        # Muestra real aportada para la auditoria de 27/10/2026.
        data = __import__('json').loads((ROOT / 'tests' / 'bop_206_sample.json').read_text(encoding='utf-8'))
        expected = {
            '2026/12979': ('Ayuntamiento de Tavernes de la Valldigna', 'Plaza / oposición'),
            '2026/12959': ('Entidad Local Menor del Perelló', 'Plaza / oposición'),
            '2026/12953': ('Ayuntamiento de Benaguasil', 'Bolsa de trabajo'),
            '2026/12950': ('Ayuntamiento de Benaguasil', 'Bolsa de trabajo'),
        }
        self.assertEqual({x['id'] for x in data['notices']}, set(expected))
        for n in data['notices']:
            self.assertEqual((entity_from_title(n['title']), classify(n['title'])), expected[n['id']])

    def test_failure_if_no_announcement(self):
        with self.assertRaises(ValueError):
            extract('<html><body>Sin anuncios disponibles</body></html>')

if __name__ == '__main__':
    unittest.main()
