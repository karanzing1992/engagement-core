-- Owner-only Phase 1 guard: at most one active browser job at a time.
-- Existing GitHub synthetic issue jobs remain independent.
CREATE UNIQUE INDEX IF NOT EXISTS mad_v1_owner_active_one ON mad_v5_jobs(project_id) WHERE job_id LIKE 'madapp-%' AND state IN ('queued','claimed');
