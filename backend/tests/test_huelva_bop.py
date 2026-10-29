import unittest,sys
from pathlib import Path
from datetime import date
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from huelva_bop import parse_day,original_pdf
from provincial_common import ProvincialCoverageError
D=date(2026,10,28)
def data():
 return {"success":True,"fecha_publicacion":D.isoformat(),"fecha_elegida":D.isoformat(),
 "Indice":{"idbop":"871","num_bop":"208","documento":"IndiceBOP_208_2026.pdf"},
 "TieneAnuncios":True,"Anuncios":[
 {"num_expe":381433,"documento":"Anuncio_381433_BOP-208_2026.pdf",
 "titulo":"Aprobación de las Bases de la convocatoria para cubrir por promoción interna una plaza de Técnico de administración",
 "entidad_anunciante":"Ayuntamiento de Almonaster la Real","trabajo_firma":39691,"fecha_publicacion":"2026-10-28T10:10:10Z"},
 {"num_expe":383443,"documento":"Anuncio_383443_BOP-208_2026.pdf",
 "titulo":"Aprobación inicial del presupuesto","entidad_anunciante":"Ayuntamiento de Cartaya",
 "trabajo_firma":39693,"fecha_publicacion":"2026-10-28T10:10:10Z"}]}
class HuelvaTest(unittest.TestCase):
 def test_day_and_notice(self):
  r=parse_day(data(),D)
  self.assertEqual(r["read"],2)
  self.assertEqual(r["number"],"208")
  self.assertEqual(len(r["notices"]),1)
  self.assertEqual(r["notices"][0]["id"],"HB-2026-381433")
  self.assertEqual(r["notices"][0]["type"],"Plaza / oposición")
  self.assertTrue(r["notices"][0]["url"].startswith("https://s2.diphuelva.es/portalweb/bope/anuncios/"))
 def test_empty_day(self):
  self.assertIsNone(parse_day({"success":False,"fecha_elegida":D.isoformat()},D))
 def test_wrong_pdf_and_date(self):
  x=data();x["Anuncios"][0]["documento"]="Anuncio_381433_BOP-207_2026.pdf"
  with self.assertRaises(ProvincialCoverageError):parse_day(x,D)
  with self.assertRaises(ProvincialCoverageError):parse_day(data(),date(2026,10,27))
  with self.assertRaises(ProvincialCoverageError):original_pdf("../../abc.pdf")
if __name__=="__main__":unittest.main()
