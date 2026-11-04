import json,sys,tempfile,unittest
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import salud_feeds

UTC=timezone.utc

class SaludFeeds(unittest.TestCase):
    def test_fin_de_semana_no_cuenta(self):
        # viernes 17:00 → lunes 07:00: 7 + 7 horas laborables
        self.assertEqual(salud_feeds.weekday_hours(datetime(2026,10,30,17,tzinfo=UTC),datetime(2026,11,2,7,tzinfo=UTC)),14)

    def test_detecta_feed_viejo_y_ausente(self):
        with tempfile.TemporaryDirectory() as d:
            names=salud_feeds.feeds()
            for n in names:
                p=Path(d)/n;p.parent.mkdir(parents=True,exist_ok=True)
                p.write_text(json.dumps({"lastCheckedUTC":"2026-11-04T07:00:00+00:00"}))
            now=datetime(2026,11,4,12,tzinfo=UTC)
            self.assertEqual(salud_feeds.check(d,now),[])
            (Path(d)/names[0]).write_text(json.dumps({"lastCheckedUTC":"2026-11-02T07:00:00Z"}))
            (Path(d)/names[1]).unlink()
            stale=salud_feeds.check(d,now)
            self.assertEqual(len(stale),2)
            self.assertTrue(stale[0].startswith(names[0]) or stale[1].startswith(names[0]))

    def test_feeds_publicados_al_dia(self):
        self.assertGreater(len(salud_feeds.feeds()),60)

if __name__=="__main__":unittest.main()
