CREATE TABLE IF NOT EXISTS mad_v5_jobs (
  job_id TEXT PRIMARY KEY CHECK(length(job_id) BETWEEN 8 AND 64),
  project_id TEXT NOT NULL CHECK(project_id='moksha_wellness'),
  prompt TEXT NOT NULL CHECK(length(prompt) BETWEEN 12 AND 600),
  mode TEXT NOT NULL CHECK(mode IN ('fixture','live','multimodal')),
  profile TEXT NOT NULL CHECK(profile IN ('synthetic_test','instagram_reel')),
  state TEXT NOT NULL CHECK(state IN ('queued','claimed','passed','failed')),
  claim_id TEXT, claimed_at INTEGER,
  attempts INTEGER NOT NULL DEFAULT 0 CHECK(attempts BETWEEN 0 AND 4),
  result_sha256 TEXT, result_run TEXT, last_error TEXT,
  created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL, expires_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS mad_v5_jobs_state_age ON mad_v5_jobs(state,created_at);
