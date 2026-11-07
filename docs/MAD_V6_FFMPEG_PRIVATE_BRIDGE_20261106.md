# MAD Reel Engine V6 — FFmpeg Private Pipeline Implementation — 6 November 2026

**Status: SOURCE-ONLY MIGRATION / OWNER-PRIVATE MANUAL PREVIEW. NOT DEPLOYED TO V6 LIVE.**

## Source and review
- Repository: `karanzing1992/engagement-core`
- Migration branch: `feature/mad-ffmpeg-only-backend-20261106`
- Draft review: https://github.com/karanzing1992/engagement-core/pull/197
- Existing V5 production is not modified; live V6 Cloudflare Worker and default-branch OIDC runner are not updated by this branch.
- The .github/workflows/mad-v6-kv-filmcraft.yml **filename is deliberately preserved** because the production OIDC identity is pinned to its path and `refs/heads/main`. Its *content* changes to FFmpeg only upon approved merge.

## Implemented on the branch
1. First-party `ffmpeg_v6_adapter.py`: deterministic reviewed-EDL cuts; wellness/nature/guest/recovery templates; color-grade/title/caption; safe `textfile` subtitles; source SHA; FFprobe duration/stream QA; full FFmpeg decode and three decoded frame checks; H.264/AAC output; `published:false`.
2. `ffmpeg_frame_samples.py`: bounds-checked consent-gated 3×640×360 JPEG still-frame extraction for existing Gemini visual research; no GStreamer.
3. `runner.py`: preserves owner-private signed OIDC, authenticated KV source byte chunks, source hashes and consent; routes original Gemini research / Groq 120B director / Groq 20B independent review EDL to the FFmpeg adapter, no procedural soundtrack.
4. `worker.mjs`: accepts **only** FFmpeg receipts with verified video/audio stream, full decode, 3 frames, original sound mode and unpublished state; explicitly refuses old MLT receipt payloads.
5. `multimodel_filmcraft_bridge.py`: reviewed creative EDL still uses the established Gemini/Groq constraints but advertises FFmpeg editor only. Historical filename retained for imports; no FilmCraft execution in active V6 runner.
6. `synthetic_qa.py`, `test_ffmpeg_v6_smoke.py`, `test_kv_gateway.mjs`, diagnostics, `mad-v6-kv-contracts.yml`, `mad-v6-ffmpeg-bridge-ci.yml`: synthetic-only automated checks of private-gateway signing/expiry/range, FFmpeg, planner fixtures and privacy.
7. Legacy `mad-v6-filmcraft-smoke.yml` made manual-only as archival rollback. Historical adapters preserved. V5 not altered.

## Manual ChatGPT local test
- Owner supplied original Moksha sauna clip in ChatGPT; local FFmpeg EDL applied 6 validated shots, branded text, warm look and original source ambience.
- Verified private output: 30.021 s H.264/AAC 720×1280 30fps, ~8.3MB. The original Moksha logo stays in source ending.
- Local evidence paths are **conversation-local** `/mnt/data/v6_ffmpeg_bridge/moksha_sauna_manual_edl.json`, `moksha_sauna_manual_receipt.json`, and `Moksha_Sauna_V6_FFmpeg_Manual_30s.mp4`; these are not GitHub files or deployed Cloudflare media.
- Models: **human manually crafted plan**; no claim of live external Gemini or Groq inference for this output.

## Manual CLI
```sh
# Source is a privately mounted, explicitly consented video in the workdir.
python3 services/reel-engine/v6-kv-gateway/ffmpeg_v6_adapter.py \
  --spec /private/workdir/reviewed_edl.json \
  --receipt /private/workdir/verification.json
```
The JSON spec requires `workdir`, `source`, `source_sha256`, `output`, `width`, `height`, `fps`, `template_id`, `hook`, `cuts:[{start,seconds}]`, `operations` aligned to cuts. Only `color_grade`, `title`, `caption` are currently supported; proposed other effects must fail/defer rather than be declared applied. Source and output must be direct children of a private workdir. Never place guest video in the public repository or CI artifacts.

## Open-source music / current blocker
- Existing providers: `experiments/reel-engine-v5/music_provider.py` (Openverse, Wikimedia) and `experiments/reel-engine-v6/audio_library_v6.py` (licensed asset + SHA and reviewer evidence). Catalogue metadata is discovery only, not a licence or audio bytes.
- FFmpeg adapter accepts a **pre-transferred local existing recording** with matching SHA and owner-supplied licence provenance via `music`, `music_sha256`, `music_rights`. Reviewer/primary-source licensing must be independently checked before platform reuse; adapter's field check alone is **not independent legal certification**.
- **V6 Cloudflare gateway is still restricted to `source_ambience_only`**. There is no certified owner-authenticated private music byte-upload/delivery contract to the GitHub runner. The signed runner intentionally blocks any other requested audio mode; it neither fabricates licensed music nor silently substitutes a generated track. Full automatic soundtrack integration remains NOT DONE.
- Separate owner-private Cloudflare music intake + evidence + SHA + expiry + job association + readback + independent source licence checking is required to complete this feature. No track from external creative asset services has been claimed as source-verified.

## Release gates
- Run PR automated V6 FFmpeg, gateway, security and model fixture suites; accept only green final HEAD.
- Apply and smoke-test D1/KV/Worker and main-branch signed workflow **in a coordinated owner-approved cutover**. Source PR alone does not update Cloudflare production.
- Verify a signed owner-private real-source job with explicit guest/AI processing consent and end-to-end SHA, valid audio/video, private byte-range and 30-minute expiry, then independent aesthetic/rights signoff.
- V5 production remains untouched. No autonomous publication, no paid service, no secrets in logs.
- Rollback: revert new GitHub runner/worker pair to the previous certified version together; do not restore legacy output receipts under a mismatched gateway.

**Open Source / Reuse / Cost Gate:** existing FFmpeg, FFprobe, V5 licensed music discovery, V6 planner and OIDC Cloudflare/GitHub private media route reused. Open-source, already owned/free-tier tools only; running CI/Cloudflare has usage quotas. Historical MLT/FilmCraft files retained for rollback, not new rendering.