# MAD V6 — FFmpeg editor and private licensed-audio source migration (2026-11-07)

**State:** SOURCE ONLY, draft PR #197, NOT merged/deployed. The existing Cloudflare V6 Worker and owner-private V5 service have not been replaced. This is a non-publication, non-production code proposal until the owner approves a controlled coordinated release.

## User requirement

Embed first-party FFmpeg/FFprobe as V6's video/effects/audio/export backend while retaining Gemini visual research, Groq GPT-OSS 120B direction, Groq 20B reviewer, screened Openverse/Wikimedia existing recordings, Cloudflare KV private chunk transport, GitHub-signed OIDC claims, owner PWA, and 30-minute finished-output expiry. Retired FilmCraft/MLT/GStreamer effect and decode paths must not be invoked in new V6 jobs. V5 remains unchanged.

## Implemented on the isolated branch

- `services/reel-engine/v6-kv-gateway/ffmpeg_v6_adapter.py`: safe curated templates, verified cuts and effect vocabulary (color_grade/title/caption), H.264/AAC exports, source and soundtrack SHA256, FFprobe both streams, full-file FFmpeg decode and three JPEG output checks. Source ambience preserved when there is no approved music. Outputs are technical-QA only; not an independent cinematic/artistic acceptance.
- `ffmpeg_frame_samples.py`: consent-gated, bounded three-frame JPEG extraction for Gemini research (replaces the GStreamer frame sampler on the active runner).
- `runner.py`: uses existing multimodel V6 Gemini/Groq planning and reviewed EDL compiler, first-party FFmpeg, V6 audio-library `admit` evidence validation, private source and audio SHA256 revalidation, encrypted/signed Cloudflare transport, secret-redacted stage diagnostics, and job-scoped temporary cleanup. No generated-music fallback.
- `worker.mjs`: owner-authenticated preparation and audio upload in existing private KV, signed OIDC runner GET, FFmpeg-only video/audio/full-decode receipt verification, music SHA match and fail-closed behavior for unapproved/missing music. Existing state/lease/expiry guards retained. The workflow filename is intentionally unchanged for the signed `workflow_ref` claim.
- `synthetic_qa.py`, `test_ffmpeg_v6_smoke.py`, `test_kv_gateway.mjs`: synthetic video/audio testing, negative license evidence, hash mismatch, premature dispatch, forged/incomplete mix receipt, private download expiry and storage cleanup.
- `.github/workflows/mad-v6-kv-filmcraft.yml`: historical file name preserved; workflow now installs/uses FFmpeg rather than MLT/GStreamer for real signed jobs.
- `experiments/reel-engine-v6/multimodel_filmcraft_bridge.py` remains a *historically named* module but now emits FFmpeg editor contract; model logic retained. Refactoring historical identifiers is non-critical and must not break serialized/OIDC contracts.

## Manual owner-private upload order (after future atomic deployment)

1. Obtain source video with documented people/usage consent, verified file SHA256, reviewed visible-shot description and Gemini-frame consent. Use existing authenticated owner PWA and `POST /v6/media/uploads`, `PUT /v6/media/uploads/{job}/chunks/{i}`, `POST /v6/media/uploads/{job}/complete`.
2. Discover the *existing human-created recording* with the V5/V6 Openverse provider. Independently review the **actual creator/source page**, composition and recording rights, license proof and attribution. Openverse metadata alone is not sufficient.
3. When music is wanted, owner POSTs `/v6/media/uploads/{job}/music` with `{mime,bytes,sha256,track,evidence}`; `track` is a V5 Openverse candidate, `evidence` the independently signed V6 reviewer record. Then PUT the original audio bytes to the **same path** with `X-Chunk-SHA256`. Max 4 MiB per track; no arbitrary URL fetch or public asset caching. Re-encode an authorized original recording as MP3 before upload when needed, retaining source provenance.
4. Render through existing owner-authenticated `POST /v6/jobs/{job}/render`. The existing Cloudflare dispatch sends an authorized private `job_id`; GitHub Actions uses its ephemeral signed OIDC identity. Runner pulls source, approved audio and Gemini frames privately, runs Groq reviewed EDL through FFmpeg, uploads verified MP4 chunks into private KV. No public GitHub artifacts.
5. Owner reviews only via existing `/v6/jobs/{job}/status` and `/preview`; 30-minute review/expiry window after completion. Distribution and social posting require separate owner authorization.

## Constraints / non-claims

- Existing V6 PWA does NOT yet expose a user-facing music picker/upload form. The authenticated API contract exists as proposed source; a manual authenticated client can submit music after rollout. Track access from a separate connected media provider is **not automatically materialized**.
- **No live V6 production migration or owner real-footage signed private full E2E has been certified yet.** CI synthetic MP4 and mocked signed transport are not proof of external AI model calls, rights clearance or a published social Reel.
- The FFmpeg renderer currently certifies 3 decoded visual frames, stream metadata and accepted effects, not human artistic parity per effect. Full cinematic QA remains an owner approval gate.
- Limits: input video 80 MiB; private soundtrack 4 MiB (single SHA-verified upload); finished MP4 80 MiB and 30-minute retrieval after completion, plus separate initial render window.
- Owner media and API keys never enter GitHub code/artifacts or public previews. Only verified free/open-source components used; Cloudflare/GitHub free quotas still apply.
- If coordinated runner/worker deployment fails, rollback both as a pair to previously signed compatible revisions, retaining OIDC filename. Never deploy just one side of a changed receipt protocol.

## Release gate

A. GitHub FFmpeg V6 synthetic smoke, Python diagnostics, Node signed KV/music tests, backend policy checks and all existing broad tests pass at **exact final commit SHA**.
B. Controlled deployment of both the FFmpeg runner (default GitHub branch) and Worker contract, maintaining OIDC workflow identity.
C. Separate owner-private actual footage + rights-cleared original recording + Gemini/Groq model chain end-to-end test, independent visual/audio review, correct playable preview, real expiry and deletion readback.
D. Owner accepts; only then deprecate legacy execution routing, mark live, and post verified Master Registry change. Do not auto-publish.

**Open Source / Reuse / Cost Gate:** FFmpeg/FFprobe (existing open-source), internal V5/V6 source and tests, GitHub Actions/Cloudflare existing private service, Openverse/Wikimedia first-party discovery and user-reviewed copyright evidence. No new paid services, no generated substitute tracks, historical rollback retained.
