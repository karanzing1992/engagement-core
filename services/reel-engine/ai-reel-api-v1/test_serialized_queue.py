#!/usr/bin/env python3
"""Standalone SQLite regression for the owner Reel Engine queue migration.

Uses only Python stdlib, no user media, no Cloudflare API.
Run: python3 services/reel-engine/ai-reel-api-v1/test_serialized_queue.py
"""
from pathlib import Path
import sqlite3
import unittest

MIGRATION = Path(__file__).with_name("010_serialized_queue.sql")


class SerialQueueMigrationTest(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.executescript("""
            CREATE TABLE mad_v1_media_jobs(
              job_id TEXT PRIMARY KEY,
              state TEXT NOT NULL CHECK(state IN
                ('queued', 'claimed', 'review_ready', 'failed'))
            );
            CREATE UNIQUE INDEX mad_v1_one_active_media_job
              ON mad_v1_media_jobs((1))
              WHERE state IN ('queued','claimed');
            INSERT INTO mad_v1_media_jobs VALUES
              ('orphan-from-legacy-API','queued');
        """)

    def tearDown(self):
        self.db.close()

    def test_stale_global_queue_lock_is_reproduced(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute(
                "INSERT INTO mad_v1_media_jobs VALUES (?,?)",
                ("new-project", "queued"),
            )

    def test_queue_accepts_multiple_jobs_preserves_existing_and_serializes_claim(self):
        self.db.executescript(MIGRATION.read_text())
        self.db.execute(
            "INSERT INTO mad_v1_media_jobs VALUES ('new-project','queued')"
        )
        self.assertEqual(
            self.db.execute(
                "SELECT COUNT(*) FROM mad_v1_media_jobs WHERE state='queued'"
            ).fetchone()[0],
            2,
        )
        self.db.execute(
            "UPDATE mad_v1_media_jobs SET state='claimed'"
            " WHERE job_id='orphan-from-legacy-API'"
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute(
                "UPDATE mad_v1_media_jobs SET state='claimed'"
                " WHERE job_id='new-project'"
            )
        self.db.execute(
            "UPDATE mad_v1_media_jobs SET state='review_ready'"
            " WHERE job_id='orphan-from-legacy-API'"
        )
        self.db.execute(
            "UPDATE mad_v1_media_jobs SET state='claimed'"
            " WHERE job_id='new-project'"
        )
        self.assertEqual(
            dict(self.db.execute(
                "SELECT job_id,state FROM mad_v1_media_jobs"
            ).fetchall()),
            {
                "orphan-from-legacy-API": "review_ready",
                "new-project": "claimed",
            },
        )
        # Safe to rerun migration on an already migrated database.
        self.db.executescript(MIGRATION.read_text())
        self.assertEqual(
            self.db.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='index'"
                " AND name='mad_v1_one_claimed_media_job'"
            ).fetchone()[0],
            1,
        )


if __name__ == "__main__":
    unittest.main()
