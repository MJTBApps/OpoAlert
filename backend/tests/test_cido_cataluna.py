import sys
from pathlib import Path
from datetime import date
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cido_cataluna import build_feeds, normalize_record, query, CidoCoverageError, BASE


def record(area,ident,day="2026-10-28",pool=False):
    return {"type":"oposicions","id":str(ident),"attributes":{
        "idAmbit":area,"idEstat":1,
        "titol":"1 plaça d'Auxiliar administratiu",
        "institucioDesenvolupat":"Ajuntament de prova",
        "urlCido":f"https://cido.diba.cat/oposicions/{ident}",
        "borsaTreball":pool,
        "maxDataPublicacioDocument":day
    }}


class CidoReaderTests(unittest.TestCase):
    def test_query_filters_only_verified_territories(self):
        url=query(date(2026,9,29),date(2026,10,28))
        self.assertIn("filter%5BidAmbit%5D=5%2C6%2C7%2C8",url)
        self.assertIn("filter%5BmaxDataPublicacioDocument%5D%5BLE%5D=2026-10-28",url)

    def test_one_result_per_catalan_province(self):
        items=[record(i,10000+i,pool=i==7) for i in range(5,9)]
        def fake(url):
            return {"data":items,"meta":{"totalResourceCount":4},"links":{}}
        feeds=build_feeds(30,date(2026,10,28),fake)
        self.assertEqual(set(feeds),{"barcelona","girona","lleida","tarragona_cido"})
        self.assertEqual(feeds["lleida"]["notices"][0]["type"],"Bolsa de trabajo")
        self.assertTrue(feeds["tarragona_cido"]["historyCoverage"]["complete"])

    def test_missing_notice_or_external_url_is_rejected(self):
        row=record(5,1452)
        row["attributes"]["urlCido"]="https://random.test/oposicions/1452"
        with self.assertRaises(CidoCoverageError):
            normalize_record(row,date(2026,9,29),date(2026,10,28))
        row["attributes"]["urlCido"]="https://cido.diba.cat/oposicions/1452"
        row["attributes"]["maxDataPublicacioDocument"]="2026-11-01"
        with self.assertRaises(CidoCoverageError):
            normalize_record(row,date(2026,9,29),date(2026,10,28))

    def test_incomplete_page_refuses_publication(self):
        def fake(url):
            return {"data":[record(5,12)],"meta":{"totalResourceCount":2},"links":{}}
        with self.assertRaises(CidoCoverageError):
            build_feeds(30,date(2026,10,28),fake)

    def test_duplicate_refuses_publication(self):
        def fake(url):
            return {"data":[record(5,12),record(5,12)],"meta":{"totalResourceCount":2},"links":{}}
        with self.assertRaises(CidoCoverageError):
            build_feeds(30,date(2026,10,28),fake)

if __name__=="__main__":unittest.main()
