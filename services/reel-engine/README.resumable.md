# Private large-file ingest and multi-clip render (v0.5)

This fixes the ChatGPT 231 MB video failure in the **renderer API**. It does not bypass ChatGPT connector egress restrictions. The user can upload source videos to an authenticated long-running Reel Engine via 8 MiB chunks, or an assistant runtime with mounted attachments can call the same API when HTTPS egress is available.

## Security and deployment prerequisites

- Use a **private HTTPS** service with persistent `/data` storage (minimum 5 GB free for large projects), Linux file locks, FFmpeg, and a single Uvicorn worker. Do **not** expose the Docker container publicly without an HTTPS proxy, rate limiting and the configured secret.
- Provision `REEL_ENGINE_TOKEN` as a random secret **at least 32 characters** via host secret manager. Never paste the token in chat or include it in frontend JavaScript, logs, CLI commands or source control.
- The engine does not publish or schedule any video. The existing WordPress approval gate remains in control. All clips require properly reviewed Goa/India source evidence to render branded content. Uploading alone does not approve footage.
- The Docker image is CI-tested and released to GHCR. GHCR is **not** hosting a long-running service; deploy the released image to an appropriate CPU/FFmpeg-capable private host with persistent storage separately.

## Resumable upload API

All routes require `Authorization: Bearer $REEL_ENGINE_TOKEN` (the server fails closed if no token is configured).

1. `POST /v1/uploads` with JSON `{"name":"video.mp4","size":230924113,"sha256":"<64 hex chars>","mime_type":"video/mp4"}` returns a random `id`, `chunk_bytes` (8 MiB), `total_chunks` and `received_chunks`.
2. `PUT /v1/uploads/{id}/chunks/{index}` with a raw chunk of at most 8 MiB and an `X-Chunk-SHA256` header. Chunks are independently checked and committed atomically. Re-sending exactly the same chunk is safe; a conflicting retry is rejected.
3. `GET /v1/uploads/{id}` supports interrupted-transfer resume by returning which chunk indexes are already available.
4. `POST /v1/uploads/{id}/complete` reassembles once and checks the **whole-file SHA-256** and exact byte count before returning an `asset_id`. Incomplete or modified files are rejected.

All file writes are private, paths use server-generated random IDs and uploads expire after 48 hours; startup cleanup can remove expired sessions. Maximum file size defaults to 1 GiB and no more than 24 incomplete sessions are permitted. For a client that owns the video bytes, use `private_upload_client.py --url https://private-engine.example path/to/video.mp4` with `REEL_ENGINE_TOKEN` set through its environment. This CLI streams each 8 MiB block, retries transient HTTP failures and resumes from the last confirmed chunk. It never sends raw video via a GPT connector.

## Multi-clip background render API

`POST /v1/render/multi` with:

```json
{
  "asset_ids": ["<uploaded asset 1>", "<uploaded asset 2>"],
  "cuts": [
    {"source_index": 0, "start": 0, "end": 13},
    {"source_index": 1, "start": 0, "end": 17}
  ],
  "duration_seconds": 30,
  "width": 1080, "height": 1920, "fps": 30,
  "audio_source_index": 1,
  "config": {
    "brand": "moksha", "placement": "reel", "editorial_region": "Goa",
    "source_provenance": [
      {"origin":"owned", "capture_country":"India", "capture_region":"Goa",
       "source_url":"https://YOUR_VERIFIED_SOURCE_PAGE_1",
       "location_evidence_url":"https://YOUR_LOCATION_EVIDENCE_1",
       "verification_status":"human_verified", "verified_by":"YOUR_REAL_EDITOR"},
      {"origin":"owned", "capture_country":"India", "capture_region":"Goa",
       "source_url":"https://YOUR_VERIFIED_SOURCE_PAGE_2",
       "location_evidence_url":"https://YOUR_LOCATION_EVIDENCE_2",
       "verification_status":"human_verified", "verified_by":"YOUR_REAL_EDITOR"}
    ]
  }
}
```

Replace all placeholders with real, independently confirmed facts. Do not fabricate reviewer identity. Returns immediately with `202` and a private job ID. `GET /v1/render/multi/{job_id}` reports `queued/running/completed/failed`; `GET /v1/render/multi/{job_id}/video` returns an authenticated MP4 after completion. The queue keeps job metadata on disk and retries up to three times after a worker restart. Files are normalized to vertical output and concatenated precisely, with the selected user-provided audio track looped gently. Moksha-brand outputs automatically use the approved Google Drive original logo via checksum-verified fallback. The result remains a **private preview**, not a published social asset.

## Limits and remaining integration

- Browser-to-engine ingestion requires the private engine hostname and secret-managed upload authorization. A file attached in ChatGPT cannot automatically be sent to an arbitrary connector unless that connector is allowed to handle its bytes. The previous ChatGPT/Canva/Descript `BLOCKED_FILE_REFERENCE` errors are platform transfer restrictions, not FFmpeg failures.
- The 231 MB original was locally assembled successfully in 28 chunks and validated against SHA-256. The 30-second final cut from both actual originals is already available as a separate conversation MP4.
- For continuous production, deploy the image to a persistent CPU worker with a private volume; preferably create a WordPress Media Studio signed session endpoint that issues short-lived upload tokens, so raw long-term bearer credentials never reach browsers.