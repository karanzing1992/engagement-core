# MAD Reel Engine — exclusive FFmpeg backend decision
**Owner decision:** 2026-11-06 | **State:** SOURCE_ONLY migration proposal on isolated branch, not deployed.

## Official new-job routing
- FFmpeg + FFprobe are the single supported video/effects/audio/export engine, with existing in-house `services/reel-engine` renderer and the ChatGPT-local Direct Studio reference reused.
- **DEPRECATED for all new render jobs:** FilmCraft MCP, GStreamer Editing Services/GES as an editor, MLT and frei0r editing adapters. Archive historical tests, branches, workflow IDs and rollback receipts; do not delete code or terminate already-running jobs.
- Retain Gemini research/frame understanding, Groq 120B director, Groq 20B strict reviewer, Openverse or vetted recorded music/ambience/SFX and captions, official verified logo, Cloudflare owner auth/queue/storage, GitHub signed job admission and media deletion policy. AI is for planning, **never a substitute for FFmpeg output or QA**.
- Visual output: actual effect verification, H.264/AAC MP4, safe-area text, 1080x1920 at 30 fps by default, full source/video/audio FFprobe, full decode, A/V sync, soundtrack rights, private owner preview and manual artistic acceptance. Never classify an audio-only file as a video.
- No synthetic replacement soundtrack for production, no automatic social posting, and no paid API or model upgrade.

## What already works
- **V5 remains active owner-private FFmpeg** (Groq + FFmpeg in GitHub Actions via Cloudflare). This code change does not modify Cloudflare production or V5.
- The ChatGPT local FFmpeg Direct Studio V1 rendered a synthetic 360x640 audiovisual QA clip and passed seven local regression tests on FFmpeg 7.1.5. Its owner-held ZIP lives in Drive (asset, **not** production deployment).
- The FFmpeg-only `backend_selection.py` and `backend_policy.json` reject FilmCraft, GStreamer, MLT/frei0r, fail incomplete video/audio verification, and deny publication. Unit tests pass locally.

## Migration / deprecation gates
1. Wire the reviewed FFmpeg render adapter into the **existing** V6 Cloudflare OIDC KV runner and its exact workflow filename (OIDC audience/workflow_ref are pinned); stop MLT, frei0r and GES editor/tool installation only when replacement E2E is certified.
2. Migrate consented source frame samples to FFmpeg; keep Gemini/Groq tasks and private source rules. Only use real owner-approved/licensed music and SFX with a recorded license manifest.
3. Gate output success on verified encoded video and audio, actual visually applied edits, signed output SHA, authenticated byte-range preview, 30-minute data expiration, mobile owner acceptance and private rollback.
4. Once deployed and private end-to-end certified, stop issuing new jobs to deprecated workflows. Retain historical source for rollback; never mass delete branches, GitHub Actions, secrets or source history.
5. Record each verified transition in the Moksha Master Registry and obtain runtime/consumer acknowledgements. A PR, source commit or local test **does not** equal deployed cutover.

## Source control and rollback
Authoritative repo: `karanzing1992/engagement-core`, frontend: `aarondash5-star/delulutech`. This is an additive isolated PR against main. V6 MLT currently remains in the GitHub runner until replaced; do not represent it as already disabled. V5 owner-private FFmpeg remains available. Reverse the policy only by a reviewed source change; preserve consent, job history and private media.
