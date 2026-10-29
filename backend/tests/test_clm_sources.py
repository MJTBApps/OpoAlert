"""Offline regression tests for DOCM, BOP Toledo and Guadalajara parsing."""
import sys,unittest
from pathlib import Path
from datetime import date
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from provincial_common import ProvincialCoverageError
from clm_docm import parse_issue as parse_docm,calendar as calendar_docm
from clm_toledo import parse_issue as parse_toledo,dates_from_calendar
from clm_guadalajara import parse_day,parse_date_number,pdf_link_from_article
D=date(2026,10,29)
class SourcesTest(unittest.TestCase):
 def test_docm(self):
  h="""<html><body>
  AÑO XLV Jueves, 29 de octubre de 2026 Núm. 208
  <h4 class="tituloOrganismo">Servicio de Salud</h4>
  <p class="sumario"><a href="./descargarArchivo.do?ruta=2026/10/29/pdf/2026_7856.pdf&amp;tipo=rutaDocm">Bolsa de Trabajo. Convocatoria para crear bolsa de trabajo de enfermería</a>. [NID 2026/7856]</p>
  <h4 class="tituloOrganismo">Consejería de Obras</h4>
  <p class="sumario"><a href="./descargarArchivo.do?ruta=2026/10/29/pdf/2026_7755.pdf&amp;tipo=rutaDocm">Ordenanza urbanística</a>. [NID 2026/7755]</p>
  </body></html>"""
  d=parse_docm(h,"20261029",D)
  self.assertEqual(d["number"],"208")
  self.assertEqual(d["read"],2)
  self.assertEqual(d["notices"][0]["id"],"CM-2026-7856")
  self.assertEqual(d["notices"][0]["entity"],"Servicio de Salud")
  self.assertEqual(len(d["notices"]),1)
  with self.assertRaises(ProvincialCoverageError):parse_docm(h,"20261028",D.replace(day=28))
 def test_docm_calendar_extra(self):
  h="""<a href="/docm/cambiarBoletin.do?fecha=20261028">Ord.</a>
  <a href="/docm/cambiarBoletin.do?fecha=20261028-ext-2&amp;numDogv=2">Ext.</a>
  <a href="/docm/cambiarBoletin.do?fecha=20261029">Ord.</a>"""
  d=calendar_docm(h,date(2026,10,28),D)
  self.assertEqual(len(d),3)
 def test_toledo(self):
  h="""<div id="searchResult">
  <a href="DocGet?bop=207&amp;insert_year=2026&amp;publication_date=29102026&amp;anexo=0">Descargar Boletín 207 completo</a>
  <h3 class="publisherBlock">Anunciante : AYUNTAMIENTO DE TOLEDO</h3>
  <div class="announce"><ul><li><strong>Número de inserción :</strong> 4897
  <a href="DocGet?id=26104873;0&amp;insert_number=4897&amp;insert_year=2026">Ver anuncio</a></li>
  <li><strong>Resumen/Asunto : </strong>Convocatoria y bases para una plaza de Administrativo</li></ul></div></div>"""
  d=parse_toledo(h,D)
  self.assertEqual(d["number"],"207")
  self.assertEqual(d["read"],1)
  self.assertEqual(d["notices"][0]["id"],"TO-2026-4897")
  self.assertEqual(d["notices"][0]["entity"],"AYUNTAMIENTO DE TOLEDO")
  self.assertEqual(d["notices"][0]["type"],"Plaza / oposición")
  self.assertIn("DocGet?id=26104873;0",d["notices"][0]["url"])
 def test_toledo_calendar(self):
  h='<a href="ebopResumen.jsp?publication_date=29/10/2026&amp;publication_date_to=29/10/2026">29</a>'
  self.assertEqual(dates_from_calendar(h,D,D),[D])
 def test_guadalajara(self):
  h="""<html><h2 class=genericItemTitle><a href="/boletin/index.php/9-general/66386-BOP-207">Boletin Oficial de la Provincia de Guadalajara num. 207 de jueves, 29 de Octubre de 2026</a></h2></html>"""
  self.assertEqual(len(parse_day(h,D)),1)
  self.assertEqual(parse_date_number("Boletin Oficial de la Provincia de Guadalajara num. 207 de jueves, 29 de Octubre de 2026",D),207)
  article="""<h2 class="itemTitle">PROCEDIMIENTO SELECTIVO PARA UNA BOLSA DE TÉCNICO/A AUXILIAR</h2>
  <a href="/boletin/pdf/pdf2026_2795.pdf">Descargar pdf Anuncio</a>"""
  self.assertEqual(pdf_link_from_article(article,D,2795,"PROCEDIMIENTO SELECTIVO PARA UNA BOLSA DE TÉCNICO/A AUXILIAR"),
   "https://boletin.dguadalajara.es/boletin/pdf/pdf2026_2795.pdf")

if __name__=="__main__":unittest.main()
