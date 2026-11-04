-- Owner-only event-driven wake state. Store no credentials in D1.
-- Apply before deploying the corresponding API Worker code.
-- Wake acknowledgements are not proof of render completion.
CREATE TABLE IF NOT EXISTS mad_v1_media_wakes (
  job_id TEXT PRIMARY KEY REFERENCES mad_v1_media_jobs(job_id),
  state TEXT NOT NULL DEFAULT 'pending' CHECK (state IN ('pending','dispatching','dispatched','failed')),
  attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0 AND attempts <= 4),
  last_attempt_at INTEGER,
  dispatched_at INTEGER,
  last_http_status INTEGER,
  last_error_code TEXT,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS mad_v1_media_wakes_retry
  ON mad_v1_media_wakes(state, last_attempt_at);
