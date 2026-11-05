-- Cloudflare Reel Engine 2026-11-05: prevent repeated active renders for one source upload.
-- Non-destructive, idempotent. Run only after confirming no duplicate active upload rows.
-- Terminal review_ready / failed jobs are preserved; a subsequent render is allowed.
CREATE UNIQUE INDEX IF NOT EXISTS mad_v1_unique_active_upload
ON mad_v1_media_jobs(upload_id)
WHERE state IN ('queued','claimed');
