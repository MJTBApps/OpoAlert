import unittest,sys
from pathlib import Path
from datetime import date
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import gipuzkoa_bog as gp
import galicia_pontevedra as po
from provincial_common import ProvincialCoverageError

class GipuzkoaSinBoletinTest(unittest.TestCase):
    def test_dia_sin_numero_es_dia_sin_boletin(self):
        html=b'<div id="sumario"><h2>Bolet\xc3\xadn \r\n\t\t 11-11-2026</h2></div>'+b" "*100
        with mock.patch.object(gp,"request",return_value=html):
            self.assertIsNone(gp.read_day(date(2026,11,11)))
    def test_fecha_sin_numero_de_otro_dia_falla(self):
        html=b'<div id="sumario"><h2>Bolet\xc3\xadn 10-11-2026</h2></div>'
        with mock.patch.object(gp,"request",return_value=html):
            with self.assertRaises(ProvincialCoverageError):gp.read_day(date(2026,11,11))

class PontevedraNombrePdfTest(unittest.TestCase):
    def test_sufijo_largo(self):
        self.assertTrue(po.same_notice("2026078647","20260786471507798201515392787"))
        self.assertTrue(po.same_notice("2026078647","2026078647"))
        self.assertFalse(po.same_notice("2026078647","2026078648"))
        self.assertFalse(po.same_notice("2026078647","20260786471"))
        self.assertFalse(po.same_notice("2026078647","20260786481507798201515392787"))
