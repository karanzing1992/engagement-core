# MAD Reel Engine V6 — GitHub-native MLT + frei0r Production Cutover

**Date:** 2026-11-06 (Asia/Kolkata)  
**Status:** **VERIFIED LIVE on synthetic private media**, owner guest video and artistic acceptance pending.  
**Source:** `karanzing1992/engagement-core`, PR [#195](https://github.com/karanzing1992/engagement-core/pull/195), squash commit `bfed2dc6bb336d0af415175978f2fbff307d5018`.  
**Signed production render:** [GitHub Actions #42236237689](https://github.com/karanzing1992/engagement-core/actions/runs/42236237689).  
**Production gateway:** `mad-v6-kv-private-beta`, deployed Cloudflare Worker version `d09cfa57-634e-411e-a690-14089d9e5729`, deployment `70367fa0-0ef6-4c32-b0da-fa3b420f60f1`, **100% traffic**.

## Owner instruction and architecture

Owner authorized replacing the existing GStreamer Editing Services V6 video editor with the open-source **MLT Framework / frei0r** editor, **hosted on GitHub Actions, not Cloudflare Containers**. This decision followed a Cloudflare Containers API response of HTTP 401 (connector lacks permission) and preference to keep rendering on the existing GitHub backend. Cloudflare Workers/D1/KV continue as the private media gateway; no Cloudflare container is used.

Flow: existing private V6 Studio → Project Auth → signed Cloudflare dispatch → existing protected GitHub Action (workflow filename retained for pinned OIDC claims) → Gemini still-frame intelligence → Groq GPT-OSS 120B source-grounded director → GPT-OSS 20B independent strict-schema reviewer → application-validated source-bound EDL → **MLT XML timeline + frei0r MLT effects + six approved preset families** → independently decoded GStreamer visual frames / audio inspection → signed private Cloudflare KV chunk storage → 30-minute owner preview. No guest or output footage in GitHub artifacts; publishing remains disabled. V5 untouched.

MLT uses the **libavcodec/FFmpeg libraries internally** via MLT's `avformat` consumer for H.264/AAC MP4. The application does not invoke the `ffmpeg` CLI for editing or QA; avoid claiming there is zero FFmpeg-family dependency. GStreamer remains a **read-only metadata/frame decoder for independent QA**, not an editor.

## Implementation details

- Added `services/reel-engine/v6-kv-gateway/mlt_v6_adapter.py`: validates private file paths, checksums, allowed profiles, source bounds, effects and templates. Builds isolated MLT XML from approved EDL and audio and renders through `melt`. Requires installed `frei0r.contrast0r`, `dynamictext`, `brightness`, `avformat`.
- Six starter allowlisted preset recipes: `wellness-cinema`, `earth-editorial`, `guest-story`, `social-kinetic`, `nature-minimal`, `recovery-reset`. Every preset is composed from existing installed MLT/frei0r filters; the broader Kdenlive/frei0r effect catalog is **not yet certified** or exposed wholesale. Text and color effects are source-bound. Deterministic owner prompt keyword-to-preset mapping; no untrusted package or effect name injection.
- `services/reel-engine/v6-kv-gateway/runner.py`: switched signed rendering to MLT, while retaining immutable source SHA, owner identity, Groq/Gemini roles, original CC0 soundtrack, GStreamer-only read-only probe, strict visual/audio QA, chunked private upload and fail-closed receipts.
- `.github/workflows/mad-v6-kv-filmcraft.yml`: **filename retained solely for pinned GitHub OIDC `workflow_ref` compatibility**; live workflow is labelled **MAD V6 KV MLT frei0r Owner Runner** and installs native MLT/frei0r on Ubuntu 24.04.
- `services/reel-engine/v6-kv-gateway/worker.mjs`: owner UI and status renderer now MLT; the Cloudflare completion endpoint only accepts `engine=MLT Framework + frei0r`, `mlt_only=true`, `frei0r_verified=true`, `gstreamer_only=false`, signed checksum, decoded visible frames (at least 3 samples) and verified audio. Legacy GStreamer receipts are rejected for newly completed jobs. Existing ready footage remains retrievable within its expiry.
- Updated isolated gateway, signed workflow, model source contract and legacy regression expectations to accurately refer to MLT. No changes to V5. Legacy GES editor adapter remains in source history for controlled rollback rather than silently replacing a running job.

## Verification and evidence

- Native MLT/frei0r synthetic render CI: [GitHub run #42234878622](https://github.com/karanzing1992/engagement-core/actions/runs/42234878622) PASSED, producing 480×270 and actual 1080×1920 moving-image video with text and CC0 audio. GStreamer independently decoded 3 visible frames and confirmed audio.
- Final branch tests before merge (source head `0c1dee443dfcd536b2160313aeb86f219b5a8cfb`) passed **all six workflows**: SSH source freeze, Reel Engine CI, consolidated KV security/models, Gemini Flash preflight, legacy FilmCraft isolated regression and new MLT/frei0r visual/audio CI.
- Isolated Cloudflare Worker version `d09cfa57-634e-411e-a690-14089d9e5729` uploaded and verified with unchanged bindings `DB`, `DISPATCH_API`, `MEDIA_KV`, `PROJECT_AUTH`. Main merge and 100% compatible Cloudflare deployment followed, with deployment readback `70367fa0-0ef6-4c32-b0da-fa3b420f60f1`.
- After deployment, signed owner synthetic real-model job `v6job-aee691a030bd4feb934bbfe905b418b2` ran from GitHub `bfed2dc6` via [Actions #42236237689](https://github.com/karanzing1992/engagement-core/actions/runs/42236237689). Run conclusion: **SUCCESS**. Cloudflare D1: state=`review_ready`, attempt count=1, 1 private output chunk, 117659 bytes, SHA-256 `903a24e7678f5681e207bb43334e43c0e49416d614e45ab573c1a5e43bd40f58`, 1080×1920, 30 FPS, 4.011 seconds, 3 decoded visible frames (variance peak=268.59), output audio verified=true, original audio mixed=true, licensed CC0 generated soundtrack, template=`wellness-cinema`, published=false, libav backend=true.
- Private output expires 30 minutes after ready; do not publish direct KV output addresses or tokens.

## Acceptance boundaries and next tests

**Certified:** signed synthetic GitHub-to-Cloudflare technical V6 MLT rendering, visible-video presence and mixed audio, private delivery, isolated owner auth/claims.

**Not yet certified:** artistic/typography fidelity of edited real guest footage, exact effect appearance, mobile playback, broad Kdenlive/frei0r template catalog licensing and individual QA, or general public beta. All real guest media remains private and there was no automated reprocessing of previous failed uploads.

**Follow-up:** new authenticated V6 owner render of fresh/retained consented guest video, manual Android preview and independent artistic review; then consider expanding template registry to independently tested MLT/Kdenlive/frei0r effects, transitions, LUTs and presets with per-effect provenance and licensing. Do not require owner to change V5 or choose paid Cloudflare Containers.

## Rollback

- Restore synchronized compatible GitHub GES runner source (`a07737bf1ad27618c148697d5e5eea8328bf6d9b` pre-MLT merge) **and** Cloudflare Worker version `a980afc6-27a5-4d15-8b86-5f91160b65e1`, only after ensuring no live job is in `sent`, `dispatching` or `rendering`.
- Never roll back only one side of the signed receipt contract; both components must agree on the editor, source hash, visible-frame gate and audio gate.
- Old FilmCraft version must not be treated as a verified video-content fallback.
