import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import importlib.util

SRC = Path(__file__).resolve().parents[1] / "worker.py"
spec = importlib.util.spec_from_file_location("worker", SRC)
worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)


class WorkerPolicyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for name in ("key", "known_hosts"):
            (self.root / name).write_text("test", encoding="utf8")
            (self.root / name).chmod(0o600)
        self.config = {
            "host_id": "dell-linux",
            "gateway": "https://example.supabase.co/functions/v1/generic-linux-automator",
            "ssh_user": "generic-auto-exec",
            "ssh_key": str(self.root / "key"),
            "known_hosts": str(self.root / "known_hosts"),
            "token_file": str(self.root / "token"),
            "journal": str(self.root / "journal.sqlite"),
            "shell_enabled": False,
        }
        self.path = self.root / "config.json"
        self.write()

    def tearDown(self):
        self.tmp.cleanup()

    def write(self):
        self.path.write_text(json.dumps(self.config), encoding="utf8")
        self.path.chmod(0o600)

    def test_config_rejects_http_and_unknown_lane(self):
        self.config["gateway"] = "http://example.com/functions/v1/generic-linux-automator"
        self.write()
        with self.assertRaises(worker.Blocked):
            worker.load_config(str(self.path))
        self.config["gateway"] = "https://example.supabase.co/functions/v1/generic-linux-automator"
        self.config["host_id"] = "pine-manbirs-pc"
        self.write()
        with self.assertRaises(worker.Blocked):
            worker.load_config(str(self.path))

    def test_rejects_writable_config(self):
        self.path.chmod(0o666)
        with self.assertRaises(worker.Blocked):
            worker.load_config(str(self.path))

    def test_shell_jobs_are_denied_both_remote_and_locally(self):
        cfg = worker.load_config(str(self.path))
        job = {"id": "j1", "claim": "c1", "kind": "shell",
               "command": "touch /tmp/should-never-run", "timeout_seconds": 5}
        calls = []

        def fake_post(_cfg, endpoint, payload, _secret):
            calls.append((endpoint, payload))
            return {"ok": True, "job": job} if endpoint.endswith("/poll") else {"ok": True}

        with worker.database(cfg) as db:
            with patch.object(worker, "post", side_effect=fake_post), patch.object(worker, "exec_ssh") as ex:
                worker.once(cfg, db, "test" * 20)
                ex.assert_not_called()
        self.assertEqual(calls[-1][1]["status"], "failed")
        self.assertIn("disabled", calls[-1][1]["stderr"])

    def test_crashed_claim_is_not_reexecuted(self):
        cfg = worker.load_config(str(self.path))
        with worker.database(cfg) as db:
            db.execute("INSERT INTO journal VALUES ('old','claim1','claimed',NULL)")
            db.commit()
            results = []
            def fake_post(_cfg, ep, payload, _secret):
                results.append((ep, payload))
                return {"ok": True}
            with patch.object(worker, "post", side_effect=fake_post), patch.object(worker, "exec_ssh") as ex:
                worker.flush_results(cfg, db, "test" * 20)
                ex.assert_not_called()
            self.assertEqual(db.execute("SELECT count(*) FROM journal").fetchone()[0], 0)
            self.assertIn("uncertain", results[0][1]["stderr"])

    def test_pair_token_exclusive_file(self):
        f = str(self.root / "token")
        worker.write_private_new(f, "secret")
        self.assertEqual(os.stat(f).st_mode & 0o777, 0o600)
        with self.assertRaises(FileExistsError):
            worker.write_private_new(f, "overwrite")


if __name__ == "__main__":
    unittest.main()
