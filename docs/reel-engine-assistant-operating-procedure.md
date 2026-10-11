# Reel Engine — assistant operating procedure (2026-10-11)

## Default: finish the user's video before extending infrastructure

When the user attaches videos in ChatGPT and asks for a final cut, **use the attached original bytes directly in the available container runtime**, rather than redirecting the user to Canva, Descript, GitHub Actions or Drive. The 231 MB source of 11 October was already automatically mountable in `/mnt/data`; the failure was caused by choosing a Python runner that returned `ClientError` and then trying connector egress that returned `BLOCKED_FILE_REFERENCE`.

1. Call container-backed runtime to inspect `/mnt/data`, then `ffprobe` the exact original file paths. If an attachment is not automatically mounted, use `files.list` to locate its exact `file_id`, then `files.materialize` it. Never invent or infer a filename/path from a file card.
2. Normalize mixed-video frame rates and pixel aspect ratios before concatenating. The FFmpeg concat filter requires `setsar=1` for every input; the two real uploaded vertical clips had different FPS and source audio availability. Preserve source audio and use silent padding or a user-approved source bed only when needed.
3. Keep footage Goa/India-relevant; do not substitute unrelated foreign stock. Respect the verified original logo SHA-256 `76e89b83667827da4b5d89143fb267f4000a9392eff685129c838c3d0b24748c` before using the Drive-origin original. Do not fabricate a logo.
4. Render a **private** finished MP4 immediately. Verify duration, audio stream, 9:16 aspect ratio, actual on-screen text readability and logo. Return only sandbox paths verified as existing by the container, together with optional smaller social-sharing export.
5. Publishing/scheduling requires a separate explicit user request; generating a finished Reel is not authorization to post.
6. When the container environment cannot process the attachment, use the **first-party WordPress admin Tools → Reel Uploads** (currently hosted in `src/class-grec-media-ingest.php`) and its 4 MiB resumable chunk uploader. Private video input and rendered output stay outside public webroot and the GitHub OIDC worker checks the queue every 30 minutes. Do not tell the user to split or re-upload manually without first trying the native file mount.
7. The new Reel Engine 0.5 endpoints in `upload_api.py`/`multi_api.py` are another authenticated 8 MiB streaming route for **a separately deployed persistent engine**. Their GHCR container image is not proof of a public server or GPT-to-worker egress. Use a private HTTPS worker configured with a secure `REEL_ENGINE_TOKEN` before offering them as live endpoints.
8. Capture workflow errors precisely: local runtime `ClientError`, connector `BLOCKED_FILE_REFERENCE`, WordPress deployment HTTP 401, geometry mismatch (SAR), transcoding failure, or actual engine error are different failure classes. Never call one the other or claim the final exists until `ffprobe` verifies the exact output.

## Successful 11 October proof

- Original chat clips: `1000042280.mp4` (16.07 s, 1080×1920, 30 FPS, silent), and `1000038892.mp4` (22.64 s, 1080×1920, variable nominal ~24.83 FPS, with source audio).
- Completed real-source 30-second vertical MP4 with original media and approved Drive logo, with a 12 MB smaller share copy.
- Authenticated multi-clip pipeline PR #39 passed source tests and separately reconstructed all 230,924,113 bytes of the large video in 28 SHA-verified 8 MiB chunks.
- Never say WordPress uploads, permanent cloud rendering or scheduled publishing are working merely because the GHCR container is tested.
