# Private Resumable Media Studio Upload / 30s Multi-Clip Render

This implements the missing **file-ingestion and orchestration** stages. The old Reel Engine only accepted one multipart `video` input and was only smoke-tested with generated media.

## Data flow

1. Administrator opens `Tools → Reel Uploads` at the existing WordPress installation.
2. Selects 1–8 MP4/MOV originals. The browser explicitly confirms footage was captured in India / Goa and rights are held. This is an attestation, **not automatic proof of the filmed location**.
3. JavaScript uploads each video in 4 MiB chunks, each with a SHA-256 checksum. The browser persists an upload session for connection-interruption recovery.
4. WordPress reconstructs and verifies all files by streaming, in `.moksha-private-media/<session>` **outside** `ABSPATH` / public_html, mode 0700, with file mode 0600. If the hosting provider cannot provide such a vault, it **fails closed**.
5. Existing WP Control deployer secret, HMAC-context `mrs-media-queue-v1`, authorizes the cloud worker's **private** queue and per-part download. The deployment secret is **not** exposed to the browser.
6. Worker verifies every downloaded clip SHA-256, creates a private vertical 30-second cut in ephemeral runner storage, applies the byte-identical Google Drive original Moksha logo, checks FFprobe audio/duration and SHA-256, then returns the final MP4 in private verified chunks to WordPress.
7. Admin uses `Tools → Reel Uploads` to download the final review clip. **No social publishing, public media URL, or GH Action video artifact**.

### Limits, access, recovery
- Per clip: 800 MiB; 1.5 GiB maximum per session; 1–8 clips.
- Client chunk: 4 MiB; `php.ini post_max_size` above 4 MiB.
- Browser upload authentication: WordPress administrator cookie and REST nonce.
- Worker authorization: different HMAC scope from the existing Git deploy hook.
- Large videos are streamed in 4 MiB increments. PHP and Python **do not load 231 MB into memory**.
- Duplicate identical chunks are accepted; altered chunks and final-size/hash mismatches are refused.
- Missing parts refuse finalization; same selected files + same browser can resume the prior session.
- Completed media stays in a private, audited vault. No auto purge before operational backup/retention policy is set. Storage capacity must be monitored.
- Workers retry transient WordPress errors and never expose unreviewed footage as GitHub artifacts.
- User-uploaded geographic attestation is not independent editorial verification: preview is private; final approval and publication require the existing region provenance and rights checks.

### Multi-clip API (if a permanent worker is later deployed)

`POST /v1/render-multi` with multipart `videos` (repeat field per input), `config_json` containing `target_seconds` / `clip_plan` / real per-input geography provenance, and header `X-Reel-Engine-Token`. Server must configure `REEL_ENGINE_API_TOKEN` (minimum 32 bytes). Unknown tokens and missing auth configuration fail closed; download route requires same token for private renders. Media publishing endpoint categorically refuses private jobs.

The low-cost Github Actions worker runs `services/reel-engine/render_ready_sessions.py` directly, reusing the signed WP queue and saving startup time compared with booting the full Docker image.

### Run tests

```sh
php tests/media-studio-ingest-smoke.php
php -d memory_limit=128M tests/media-studio-ingest-large-smoke.php
cd services/reel-engine
python -m unittest -v test_multi_renderer.py test_private_worker.py
```

The large test assembles **230,924,113 actual bytes** in 56 verified 4 MiB parts and asserts bounded PHP memory; it does not only accept a claimed size.

### Remaining runtime dependencies

This connector runtime cannot export an already-uploaded 231 MB ChatGPT file into Drive because the file-service upload limit is lower. The new first-party uploader bypasses that size ceiling by uploading from the user's browser directly into WordPress. Already attached ChatGPT bytes are not automatically transferable out of the chat service. A persistent hosted worker is optional: GitHub Actions CPU runner can process ready jobs in temporary storage with low idle costs.

This is a general-purpose engine module: only `MRS_SITE_URL`, brand registry, and WordPress installation are deployment-specific.
