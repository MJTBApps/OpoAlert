"""Aviso silencioso de Firebase tras publicar feeds (1.54.0)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import aviso_fcm  # noqa: E402


class AvisoFcmTest(unittest.TestCase):
    def write(self, folder, name, ids, checked="2026-11-06T10:00:00Z"):
        notices = [{"id": i, "title": "x"} for i in ids]
        (Path(folder) / name).write_text(json.dumps({"lastCheckedUTC": checked, "notices": notices}))

    def test_huella_ignora_hora_de_revision(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            self.write(a, "va.json", ["1", "2"])
            self.write(b, "va.json", ["2", "1"], checked="2026-11-06T12:00:00Z")
            (Path(b) / "version.json").write_text('{"versionName": "1.54.0"}')
            self.assertEqual(aviso_fcm.fingerprint(Path(a)), aviso_fcm.fingerprint(Path(b)))
            self.write(b, "va.json", ["1", "2", "3"])
            self.assertNotEqual(aviso_fcm.fingerprint(Path(a)), aviso_fcm.fingerprint(Path(b)))

    def test_cuando_enviar(self):
        self.assertFalse(aviso_fcm.should_send({}, "h1", 10_000))
        self.assertFalse(aviso_fcm.should_send({"fingerprint": "h1", "sent_at": 0}, "h1", 10_000))
        self.assertTrue(aviso_fcm.should_send({"fingerprint": "h1", "sent_at": 0}, "h2", 10_000))
        self.assertFalse(aviso_fcm.should_send({"fingerprint": "h1", "sent_at": 9_500}, "h2", 10_000))

    def test_mensaje_silencioso(self):
        msg = aviso_fcm.message()["message"]
        self.assertEqual(msg["topic"], "convocatorias")
        self.assertNotIn("notification", msg)
        self.assertEqual(msg["apns"]["headers"]["apns-push-type"], "background")
        self.assertEqual(msg["apns"]["payload"]["aps"]["content-available"], 1)
        self.assertEqual(msg["android"]["priority"], "high")

    def test_sin_secreto_no_hace_nada(self):
        with tempfile.TemporaryDirectory() as d:
            state = Path(d) / "estado.json"
            self.assertEqual(aviso_fcm.main(["--docs", d, "--state", str(state)]), 0)
            self.assertFalse(state.exists())


if __name__ == "__main__":
    unittest.main()
