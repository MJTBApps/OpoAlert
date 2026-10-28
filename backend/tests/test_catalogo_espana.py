import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.data=json.loads((ROOT/"fuentes_espana.json").read_text(encoding="utf-8"))

    def test_catalogue_is_complete_without_fake_coverage(self):
        self.assertEqual(len(self.data["territories"]),52)
        self.assertEqual(len(self.data["communities"]),19)
        codes=[x["ine"] for x in self.data["territories"]]
        self.assertEqual(len(codes),len(set(codes)))
        self.assertEqual(set(codes),{f"{n:02d}" for n in range(1,53)})

    def test_only_validated_provincial_feeds_are_active(self):
        sources=self.data["nationalSources"]
        active={x["code"] for x in sources if x["state"]=="active"}
        self.assertEqual(active,{"VA","AL","CS","ES","CB","CG","CL","CT","TB","BB","BG","HU","TE","ZA","CA"})
        cido=[x for x in sources if x["kind"]=="catalogo_empleo"]
        self.assertEqual(len(cido),4)
        self.assertTrue(all("no equivale al BOP" in x["scope"] for x in cido))
        boe=[x for x in sources if x["code"]=="ES"]
        self.assertEqual(len(boe),1)
        self.assertEqual(boe[0]["state"],"active")
        self.assertEqual(boe[0]["kind"],"boe")

    def test_every_community_refers_to_known_ine_codes(self):
        allcodes={x["ine"] for x in self.data["territories"]}
        visited=[]
        for community in self.data["communities"]:
            self.assertTrue(community["provinces"])
            self.assertTrue(set(community["provinces"])<=allcodes)
            visited.extend(community["provinces"])
        self.assertEqual(len(visited),52)
        self.assertEqual(set(visited),allcodes)

    def test_uniprovincial_gazettes_not_invented_bops(self):
        province={x["name"]:x for x in self.data["territories"]}
        for name in ["Madrid","Murcia","Asturias","Cantabria","Navarra","La Rioja","Illes Balears"]:
            self.assertEqual(province[name]["primaryGazette"],"diario_autonomico")
        for city in ["Ceuta","Melilla"]:
            self.assertEqual(province[city]["primaryGazette"],"boletin_ciudad")

if __name__=="__main__":unittest.main()
