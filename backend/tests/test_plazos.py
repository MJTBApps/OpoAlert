"""Plazo de presentación leído del texto del anuncio (frases reales de octubre de 2026)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import plazos  # noqa: E402


class FindDeadlineTest(unittest.TestCase):
    def found(self, text):
        result = plazos.find_in_text(text)
        return (result["days"], result["kind"]) if result else None

    def test_frases_reales(self):
        cases = [
            ("El plazo de presentación de solicitudes será de veinte días hábiles a contar desde el siguiente al de "
             "la publicación de esta resolución en el «Boletín Oficial del Estado».", (20, "hábiles")),
            ("Se abre el plazo de presentación de solicitudes, que será de 7 días hábiles a contar desde el día "
             "siguiente en la publicación de este anuncio en el Boletín Oficial de la Provincia de Valencia.", (7, "hábiles")),
            ("Se establece un plazo de veinte (20) días hábiles para la presentación de solicitudes, contados a partir "
             "del día siguiente al de la publicación del extracto de la convocatoria en el Boletín Oficial del Estado.",
             (20, "hábiles")),
            ("El termini per a presentar les sol·licituds junt a la documentació serà de DEU DIES HÀBILS, a partir del "
             "dia següent al de la publicació de la convocatòria en el Butlletí Oficial de la Província.", (10, "hábiles")),
            ("El plazo para la presentación de solicitudes será de 15 días naturales, contados a partir del día "
             "siguiente al de la publicación de esta convocatoria en el Diari Oficial de la Generalitat Valenciana.",
             (15, "naturales")),
            ("Las solicitudes se presentarán en el Registro General del Ayuntamiento o en la forma prevista en el "
             "artículo 16.4 de la Ley 39/2015, de 1 de octubre, del Procedimiento Administrativo Común de las "
             "Administraciones Públicas, en el plazo de 20 días hábiles contados a partir del siguiente al de la "
             "publicación del extracto de la convocatoria en el Boletín Oficial del Estado.", (20, "hábiles")),
            ("Plazo de presentación: Será de diez días hábiles, contados a partir del siguiente al de publicación de "
             "la presente resolución en el Boletín Oficial de la Junta de Andalucía.", (10, "hábiles")),
            ("El plazo de presentación de solicitudes comenzará el día siguiente al de la publicación del presente "
             "anuncio y tendrá una duración de cinco días naturales.", (5, "naturales")),
        ]
        for text, expected in cases:
            with self.subTest(text=text[:60]):
                self.assertEqual(self.found(text), expected)

    def test_otros_plazos_no_son_el_de_solicitudes(self):
        for text in [
            # Recomendación, no el plazo.
            "Se recomienda realizar esta solicitud al menos dos días hábiles antes de la finalización del plazo de "
            "presentación de solicitudes.",
            # Embarazo o parto: aporte de informe médico.
            "Adjuntando informe médico oficial, junto con la solicitud de la aspirante, en un plazo máximo de quince "
            "días naturales a partir de la fecha del examen.",
            # Subsanación, alegaciones, documentación del seleccionado, toma de posesión.
            "Los aspirantes excluidos dispondrán de un plazo de diez días hábiles para subsanar la falta.",
            "Se concede un plazo de tres días hábiles para presentar alegaciones a la lista provisional.",
            "Se requiere a la persona seleccionada para que en plazo de 10 días hábiles presente la documentación.",
            "El plazo de toma de posesión será de tres días hábiles si no implica cambio de residencia.",
            # Sin decir si son hábiles o naturales.
            "El plazo de presentación de solicitudes será de diez días desde la publicación.",
            # Dos cifras distintas: ambiguo.
            "El plazo de presentación de solicitudes será de diez días hábiles o de veinte días naturales.",
        ]:
            with self.subTest(text=text[:60]):
                self.assertIsNone(self.found(text))

    def test_cita_literal_recortada(self):
        relleno = "Antecedentes del expediente y de su tramitación administrativa ordinaria " * 6
        result = plazos.find_in_text(relleno + "y el plazo de presentación de solicitudes será de veinte días "
                                     "hábiles desde la publicación en el BOE.")
        self.assertTrue(result["text"].startswith("…"))
        self.assertIn("veinte días hábiles", result["text"])
        self.assertLessEqual(len(result["text"]), 330)

    def test_palabras_partidas_por_linea(self):
        self.assertEqual(self.found("El plazo de presentación de solicitudes será de veinte días há-\nbiles desde "
                                    "la publicación."), (20, "hábiles"))


class UpdateTest(unittest.TestCase):
    def test_lee_solo_anuncios_nuevos_y_descarta_los_viejos(self):
        frase = ("El plazo de presentación de solicitudes será de veinte días hábiles a contar desde el siguiente al "
                 "de la publicación en el Boletín Oficial del Estado.")
        with tempfile.TemporaryDirectory() as tmp:
            docs = Path(tmp)
            feed = {"notices": [
                {"id": "1", "type": "Plaza / oposición", "url": "https://x.es/a.pdf"},
                {"id": "2", "type": "Bolsa de trabajo", "url": "https://x.es/b.pdf"},
                {"id": "3", "type": None, "url": "https://x.es/c.pdf"},          # no candidata
                {"id": "4", "type": "Plaza / oposición", "url": "https://x.es/d.pdf#page=4"},  # boletín entero
            ]}
            (docs / "boe.json").write_text(json.dumps(feed), encoding="utf-8")
            pages = {"https://x.es/a.pdf": frase, "https://x.es/b.pdf": "Sin plazo."}
            with mock.patch.object(plazos, "download", side_effect=lambda url: url.encode()), \
                    mock.patch.object(plazos, "find_in_pdf",
                                      side_effect=lambda data: dict(plazos.find_in_text(pages[data.decode()]) or {}, page=1)
                                      if plazos.find_in_text(pages[data.decode()]) else None):
                stats = plazos.update(docs, limit=10)
                self.assertEqual((stats["leidos"], stats["con_plazo"]), (2, 1))
                saved = json.loads((docs / "plazos" / "boe.json").read_text(encoding="utf-8"))
                self.assertEqual(saved["items"]["https://x.es/a.pdf"]["days"], 20)
                self.assertEqual(saved["none"], ["https://x.es/b.pdf"])
                # Segunda vez: no se vuelve a descargar nada.
                self.assertEqual(plazos.update(docs, limit=10)["leidos"], 0)
            # El anuncio sale del feed (más de 30 días): se borra su plazo.
            feed["notices"] = feed["notices"][1:]
            (docs / "boe.json").write_text(json.dumps(feed), encoding="utf-8")
            plazos.update(docs, limit=10)
            saved = json.loads((docs / "plazos" / "boe.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["items"], {})

    def test_la_cita_debe_contener_los_dias(self):
        urls = {"https://x.es/a.pdf"}
        good = {"days": 20, "kind": "hábiles", "page": 1, "text": "El plazo será de veinte días hábiles desde…"}
        self.assertIsNone(plazos.problem("https://x.es/a.pdf", good, urls))
        self.assertIsNotNone(plazos.problem("https://x.es/a.pdf", dict(good, days=15), urls))
        self.assertIsNotNone(plazos.problem("https://otro.es/a.pdf", good, urls))
        self.assertIsNotNone(plazos.problem("https://x.es/a.pdf", dict(good, kind="lectivos"), urls))


class FindSedeTest(unittest.TestCase):
    """Direcciones reales de anuncios de noviembre de 2026."""

    def test_sedes_escritas_en_el_anuncio(self):
        cases = [
            ("Las solicitudes se presentarán en la sede electrónica https://lietor.sedipualba.es/, apartado…",
             "https://lietor.sedipualba.es/"),
            ("a través de la sede electrónica del Ayuntamiento [http://ribadedeva.sedelectronica.es].",
             "https://ribadedeva.sedelectronica.es/"),
            ("disponible en https://casavieja.\nsedelectronica.es/board.", "https://casavieja.sedelectronica.es/"),
            ("tablón de la sede (https://www.daimiel.es/sede).", "https://www.daimiel.es/sede"),
            ("https://www.seu-e.cat/ca/web/bascara/tramits-i-gestions", "https://www.seu-e.cat/ca/web/bascara"),
            ("en la sede electrónica de este Ayuntamiento (www.villarrobledo.com).", "https://www.villarrobledo.com/"),
        ]
        for text, link in cases:
            with self.subTest(text=text[:40]):
                self.assertEqual(plazos.find_sedes_in_text(text)[:1], [link])

    def test_no_son_sedes(self):
        for text in [
            "Puede verificarse en https://sede.dipucr.es/verificador?csv=XYZ",
            "Más información en www.ayuntamiento.es/empleo",           # web sin decir que es la sede
            "https://lietor.sedi-",                                     # cortada al final de la línea
            "Protección de datos: https://sedeagpd.gob.es",
            "Firmado con www.svc.cat",
        ]:
            with self.subTest(text=text):
                self.assertEqual(plazos.find_sedes_in_text(text), [])

    def test_la_sede_propia_gana_a_la_web_general(self):
        self.assertEqual(plazos.find_sedes_in_text("sede electrónica www.motril.es o https://sede.motril.es.")[0],
                         "https://sede.motril.es/")

    def test_pie_del_boletin_y_dominio_del_anuncio_no_cuentan(self):
        raw = {f"https://bop.x.es/{i}.pdf": ["https://sede.dipux.es/"] for i in range(8)}
        raw["https://bop.x.es/1.pdf"] = ["https://sede.dipux.es/", "https://pueblo.sedelectronica.es/"]
        raw["https://bop.x.es/9.pdf"] = ["https://bop.x.es/"]
        chosen = plazos.choose_sedes(raw, set(raw))
        self.assertEqual(chosen, {"https://bop.x.es/1.pdf": "https://pueblo.sedelectronica.es/"})

    def test_lee_la_sede_de_anuncios_ya_leidos_una_sola_vez(self):
        with tempfile.TemporaryDirectory() as tmp:
            docs = Path(tmp)
            feed = {"notices": [{"id": "1", "type": "Plaza / oposición", "url": "https://x.es/a.pdf"}]}
            (docs / "boe.json").write_text(json.dumps(feed), encoding="utf-8")
            (docs / "plazos").mkdir()
            (docs / "plazos" / "boe.json").write_text(json.dumps(
                {"schemaVersion": 1, "items": {}, "none": ["https://x.es/a.pdf"], "tries": {}}), encoding="utf-8")
            with mock.patch.object(plazos, "download", return_value=b"%PDF-"), \
                    mock.patch.object(plazos, "find_in_pdf", return_value=None), \
                    mock.patch.object(plazos, "find_sedes_in_pdf", return_value=["https://pueblo.sedelectronica.es/"]):
                self.assertEqual(plazos.update(docs, limit=10)["leidos"], 1)
                saved = json.loads((docs / "plazos" / "boe.json").read_text(encoding="utf-8"))
                self.assertEqual(saved["sedes"], {"https://x.es/a.pdf": "https://pueblo.sedelectronica.es/"})
                self.assertEqual(saved["none"], ["https://x.es/a.pdf"])
                self.assertEqual(plazos.update(docs, limit=10)["leidos"], 0)

    def test_validacion_de_la_sede(self):
        urls = {"https://x.es/a.pdf"}
        self.assertIsNone(plazos.sede_problem("https://x.es/a.pdf", "https://pueblo.sedelectronica.es/", urls))
        self.assertIsNotNone(plazos.sede_problem("https://x.es/a.pdf", "http://pueblo.sedelectronica.es/", urls))
        self.assertIsNotNone(plazos.sede_problem("https://otro.es/a.pdf", "https://pueblo.sedelectronica.es/", urls))


class FindProveerTest(unittest.TestCase):
    """Extractos reales del BOE de noviembre de 2026 (seguimiento de favoritas, 1.59.0)."""

    LUGO = ("Resolución de 21 de octubre de 2026, del Ayuntamiento de Rábade (Lugo), referente a la convocatoria "
            "para proveer una plaza. En el «Boletín Oficial de la Provincia de Lugo» número 236, de 15 de octubre "
            "de 2026, se han publicado las bases que han de regir la convocatoria para proveer: Una plaza de "
            "Administrativo/a adscrito/a al Servicio de Contabilidad y Tesorería, perteneciente a la escala de "
            "Administración General, subescala Administrativa, por el sistema de oposición, en turno libre. Dichas "
            "bases fueron rectificadas en los términos publicados en el «Boletín Oficial de la Provincia de Lugo» "
            "número 241, de 21 de octubre de 2026. El plazo de presentación de solicitudes será de veinte días hábiles.")
    GOJAR = ("Resolución de 13 de noviembre de 2026, del Ayuntamiento de Gójar (Granada), referente a la convocatoria "
             "para proveer varias plazas. En el «Boletín Oficial de la Provincia de Granada» número 218, de 11 de "
             "noviembre de 2026, se han publicado las bases que han de regir la convocatoria para proveer: Una plaza "
             "de oficial electricista de la plantilla de personal laboral fijo, por el sistema de concurso-oposición, "
             "en turno libre. Una plaza de oficial de jardinería de la plantilla de personal laboral fijo, por el "
             "sistema de concurso-oposición, en turno libre. El plazo de presentación de solicitudes será de veinte "
             "días naturales.")

    def test_una_plaza_y_boletin_de_las_bases(self):
        found = plazos.find_proveer_in_text(self.LUGO)
        self.assertEqual(len(found["items"]), 1)
        self.assertTrue(found["items"][0].startswith("Una plaza de Administrativo/a adscrito/a"))
        self.assertNotIn("rectificadas", found["items"][0])
        self.assertEqual(found["bases"], {"diario": "Boletín Oficial de la Provincia de Lugo",
                                          "numero": "236", "fecha": "15/10/2026"})

    def test_varias_plazas(self):
        found = plazos.find_proveer_in_text(self.GOJAR)
        self.assertEqual([item[:30] for item in found["items"]],
                         ["Una plaza de oficial electrici", "Una plaza de oficial de jardin"])
        self.assertEqual(found["bases"]["fecha"], "11/11/2026")

    def test_sin_formula_no_hay_extracto(self):
        self.assertIsNone(plazos.find_proveer_in_text(
            "Resolución de 6 de noviembre de 2026, de la Universidad de Alcalá, por la que se convoca concurso."))
        self.assertIsNone(plazos.find_proveer_in_pdf(b"no es un pdf"))

    def test_validacion(self):
        url = "https://www.boe.es/boe/dias/2026/11/28/pdfs/BOE-A-2026-25057.pdf"
        good = plazos.find_proveer_in_text(self.LUGO)
        self.assertIsNone(plazos.proveer_problem(url, good, {url}))
        self.assertIsNotNone(plazos.proveer_problem("https://x.es/a.pdf", good, {"https://x.es/a.pdf"}))
        self.assertIsNotNone(plazos.proveer_problem(url, {"items": []}, {url}))
        self.assertIsNotNone(plazos.proveer_problem(url, dict(good, bases={"fecha": "2026-10-15"}), {url}))

    def test_lee_el_extracto_de_anuncios_del_boe_ya_leidos_una_vez(self):
        url = "https://www.boe.es/boe/dias/2026/11/28/pdfs/BOE-A-2026-25057.pdf"
        with tempfile.TemporaryDirectory() as tmp:
            docs = Path(tmp)
            feed = {"notices": [{"id": "BOE-A-2026-25057", "type": "Plaza / oposición", "url": url}]}
            (docs / "boe.json").write_text(json.dumps(feed), encoding="utf-8")
            (docs / "plazos").mkdir()
            (docs / "plazos" / "boe.json").write_text(json.dumps(
                {"schemaVersion": 1, "items": {}, "none": [url], "tries": {}, "sinSede": [url]}), encoding="utf-8")
            with mock.patch.object(plazos, "download", return_value=b"%PDF-"), \
                    mock.patch.object(plazos, "find_in_pdf", return_value=None), \
                    mock.patch.object(plazos, "find_sedes_in_pdf", return_value=[]), \
                    mock.patch.object(plazos, "find_proveer_in_pdf",
                                      return_value=plazos.find_proveer_in_text(self.LUGO)):
                self.assertEqual(plazos.update(docs, limit=10)["leidos"], 1)
                saved = json.loads((docs / "plazos" / "boe.json").read_text(encoding="utf-8"))
                self.assertEqual(saved["proveer"][url]["bases"]["fecha"], "15/10/2026")
                self.assertEqual(saved["sinProveer"], [])
                self.assertEqual(plazos.update(docs, limit=10)["leidos"], 0)


if __name__ == "__main__":
    unittest.main()
