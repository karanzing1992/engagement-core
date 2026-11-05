#!/usr/bin/env python3
"""Owner-only Reel Engine user-beta reliability contracts (synthetic, offline).

No credentials, private user media, remote service calls, or write to production.
"""
import sqlite3
import unittest
from pathlib import Path

DIR = Path(__file__).resolve().parent
WORKFLOW = DIR.parents[2] / ".github/workflows/mad-v5-cloudflare-bridge.yml"


class UserBetaContracts(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.execute("""CREATE TABLE mad_v1_media_jobs(
            job_id TEXT PRIMARY KEY,
            upload_id TEXT NOT NULL,
            state TEXT NOT NULL CHECK(state IN ('queued','claimed','review_ready','failed')),
            created_at INTEGER DEFAULT 0,
            expires_at INTEGER DEFAULT 0
        )""")
        self.db.executescript((DIR / "012_one_active_job_per_upload.sql").read_text())

    def tearDown(self):
        self.db.close()

    def add(self, job_id, upload_id, state):
        self.db.execute(
            "INSERT INTO mad_v1_media_jobs(job_id,upload_id,state) VALUES (?,?,?)",
            (job_id,upload_id,state),
        )

    def test_one_upload_does_not_create_duplicate_queued_render(self):
        self.add("job-a","synthetic-source-a","queued")
        with self.assertRaises(sqlite3.IntegrityError):
            self.add("job-b","synthetic-source-a","queued")
        with self.assertRaises(sqlite3.IntegrityError):
            self.add("job-c","synthetic-source-a","claimed")
        self.assertEqual(self.db.execute("SELECT count(*) FROM mad_v1_media_jobs").fetchone()[0],1)

    def test_unrelated_uploads_queue_and_historical_renders_remain(self):
        self.add("historical","synthetic-source-a","review_ready")
        self.add("repeat","synthetic-source-a","queued")
        self.add("other","synthetic-source-b","queued")
        self.db.execute("UPDATE mad_v1_media_jobs SET state='review_ready' WHERE job_id='repeat'")
        self.add("next-version","synthetic-source-a","queued")
        self.assertEqual(self.db.execute("SELECT count(*) FROM mad_v1_media_jobs").fetchone()[0],4)
        self.db.executescript((DIR / "012_one_active_job_per_upload.sql").read_text())

    def test_wake_attempts_match_sqlite_constraint(self):
        self.db.executescript((DIR / "011_event_wake.sql").read_text())
        self.add("synthetic-job","synthetic-source-a","queued")
        self.db.execute("""INSERT INTO mad_v1_media_wakes(
            job_id,state,attempts,created_at,updated_at) VALUES (
            'synthetic-job','pending',0,0,0)""")
        self.db.execute("UPDATE mad_v1_media_wakes SET attempts=4 WHERE job_id='synthetic-job'")
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("UPDATE mad_v1_media_wakes SET attempts=5 WHERE job_id='synthetic-job'")
        wake=(DIR / "media_event_wake.mjs").read_text()
        self.assertIn("const MAX_ATTEMPTS=4;",wake)
        self.assertNotIn("const MAX_ATTEMPTS=6;",wake)

    def test_dispatch_uses_workers_supported_redirect_and_safe_error_classes(self):
        wake=(DIR/"media_event_wake.mjs").read_text()
        # Cloudflare Workers rejects redirect='error' *before* sending a request.
        self.assertIn("redirect:'manual'", wake)
        self.assertNotIn("method:'POST',redirect:'error'", wake)
        self.assertIn("GITHUB_DISPATCH_UNEXPECTED_REDIRECT", wake)
        self.assertIn("GITHUB_DISPATCH_FETCH_TYPE_ERROR", wake)
        self.assertIn("GITHUB_DISPATCH_TIMEOUT", wake)
        self.assertIn("const MAX_ATTEMPTS=4;", wake)

    def test_github_private_ffmpeg_install_is_bounded_without_apt(self):
        script=WORKFLOW.read_text()
        private=script.split("name: Install render dependencies for accepted real-media owner job",1)[1]
        private=private.split("name: Download verified private source",1)[0]
        self.assertIn("timeout 120 npm install",private)
        self.assertIn("command -v ffmpeg",private)
        self.assertIn("libx264",private)
        self.assertIn("drawtext",private)
        self.assertNotIn("sudo apt-get",private)
        self.assertIn("test -f /usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",private)

    def test_owner_api_is_not_public_and_project_cors_auth_is_readable(self):
        owner=(DIR/"worker.mjs").read_text()
        projects=(DIR/"reel_project_worker.mjs").read_text()
        render=(DIR/"project_render.mjs").read_text()
        self.assertIn("MAD_OWNER_CODE_SHA256",owner)
        self.assertIn("Forbidden origin",owner)
        self.assertIn("...headers",projects)
        self.assertIn("status:401",projects)
        self.assertIn("existing:true",render)
        self.assertIn("Render queue unavailable; no new render was created",render)


if __name__ == "__main__":
    unittest.main()
