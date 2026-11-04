-- AI Reel Engine V1: serialized rendering, unbounded persistence of queued entries.
-- The original constant-key UNIQUE index on queued+claimed turned any queued
-- orphan (including jobs created outside Projects) into a global input lock.
-- This migration preserves all rows and retains exactly one claimed worker.
-- Nonterminal 'queued' rows may now wait independently until claimed by the
-- existing owner-only GitHub OIDC worker. Does not grant more concurrency.
CREATE UNIQUE INDEX IF NOT EXISTS mad_v1_one_claimed_media_job
  ON mad_v1_media_jobs((1))
  WHERE state='claimed';

DROP INDEX IF EXISTS mad_v1_one_active_media_job;
