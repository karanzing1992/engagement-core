# MAD Reel Engine V5 — GitHub-render private beta technical certification
Date: 2026-11-05 (Asia/Kolkata)
Project: Moksha MAD / DeluluTech Reel Engine
Classification: **OWNER-ONLY PRIVATE TECHNICAL BETA: PASS** / **GENERAL MULTI-USER BETA: NOT CERTIFIED**

## Architecture verified
- Frontend PWA remains at https://reel.delulutech.in on Cloudflare Pages; live API and Projects Workers, persistent D1 state and private media KV remain Cloudflare.
- Heavy FFmpeg rendering and Groq inference **stay on GitHub Actions** via the existing pinned signed GitHub OIDC bridge. No new Cloudflare paid containers, R2 provisioning, or social publishing.
- Render workflow: `.github/workflows/mad-v5-cloudflare-bridge.yml`, owner-only `[MAD-V5-WAKE]` issue route, scheduled queue recovery on GitHub at `16,46 * * * *`.
- Direct automatic dispatch remains unconfigured because `MAD_GITHUB_ACTIONS_DISPATCH_TOKEN` is absent from both Cloudflare Workers. The Cloudflare `*/5` cron cannot dispatch without that secret. User submissions therefore rely on existing GitHub scheduled pickup (or an owner-initiated GitHub issue), with no guaranteed immediate start.

## GitHub runner repair and CI evidence
- PR https://github.com/karanzing1992/engagement-core/pull/161 merged to main as `ffaeefde19d8c4ae241fb7ac27af75a8a13929da`.
- Removed unbounded Ubuntu `apt-get update/install` in the GitHub private-media runner and generic Reel Engine CI. Check preinstalled FFmpeg/FFprobe first; if absent, install only pinned npm FFmpeg/FFprobe with a 120-second timeout. Validate DejaVu font, H.264 encoder `libx264`, `drawtext`, and pinned Python dependencies.
- Added `test_beta_readiness.py` regression contracts for duplicate active upload prevention (D1 migration 012), preserved terminal history, retry cap 4 matching the event-wake D1 CHECK constraint, fail-closed owner authentication and readable Projects API CORS 401.
- Six PR GitHub Actions checks **PASS** at head `b483d0c6876ad612fb9c0806a437e384ef4fa574`:
  - Reel Engine CI: 41984532001
  - AI Reel Engine V1 owner PWA API contract: 41984531950
  - MAD Reel Workspace: 41984531914
  - MAD V1 real-media owner-only security: 41984532059
  - MAD V5 Cloudflare OIDC Bridge Contracts: 41984531835
  - Generic SSH production source freeze: 41984531840

## Fresh production synthetic private-media acceptance
- Fixture: previously verified, original **synthetic-blue-test.mp4**, 3,269 bytes, one private KV chunk. No guest media, personal content or user-uploaded footage was used in this acceptance.
- Queued one new isolated synthetic-source job in production D1: `madmedia-e6280631-1585-4e36-beba-f83dcb826d6a`. Confirmed no preexisting queued/claimed jobs.
- Owner GitHub issue https://github.com/karanzing1992/engagement-core/issues/162 launched signed workflow https://github.com/karanzing1992/engagement-core/actions/runs/41984759753. **SUCCESS**, one job claim, one render, one completion callback. Real-media source was retrieved privately via OIDC; GitHub workflow run has **zero public uploaded artifacts**.
- D1 state: `queued` -> `claimed` -> `review_ready`; attempts=1; no error. Queue after test: five review_ready total, one historical failed, zero queued/claimed.
- Output: 1080 × 1920, 30fps, H.264/AAC, full_decode=true; 45,617 bytes, one output KV chunk.
- Independent Cloudflare KV binary digest/readback matches the job and output-chunk D1 records exactly:
  `fc5a6ebd11a5edd90ca3a0380c1c16e2f8c19f6f6929ebc4ceec74d11a751e95`; MP4 `ftyp` header detected.
- Groq creative report: attempts=2, `creative_plan_applied=true`, `creative_fallback_reason=null`; source frames sampled=3, vision captions=2, vision failures=1; proposed operations not executed=5. Creative plan application proves the cuts/heading path ran, **not** execution of all proposed effects or artistic quality.
- FFmpeg runner passed full decode and authored an owner-only technical review draft; no music-rights, manual artistic or guest release certification.

## Mobile and authorization smoke
- Browser against the live Cloudflare PWA at widths 320px and 390px: no horizontal overflow; owner access-code input and Projects/Studio/Renders/Settings controls present. PWA manifest fetched HTTP 200.
- Browser-origin unauthenticated requests to owner API `/v1/media/jobs` and Projects API `/v1/projects` return readable HTTP **401** with CORS. Unsupported origins return 403. These are negative auth checks only.
- A **valid** owner access-code positive browser flow (log in -> select project -> upload video -> select directions -> submit render -> poll status -> play/download review -> reload to verify persistence) was **not** independently exercised in this run. Do not claim complete client E2E.

## Beta release verdict
1. **PASS:** owner-private technical backend, signed GitHub execution, isolated original synthetic media, Groq-directed plan, FFmpeg render, full decode, private output integrity, duplicate queue/schema tests, basic mobile layout and negative auth.
2. **CONDITIONAL:** owner-only invited private technical beta at https://reel.delulutech.in, with expected scheduled GitHub pickup rather than instant dispatch, no render-time SLA, existing file and storage TTL/size limits.
3. **NO-GO:** multi-user public beta; user signup/tenant-isolation/limits not certified. Do not share a single owner code with unrelated testers.
4. **NO-GO:** marketing-quality creative and guest footage release; Groq's five proposed effects were not executed, vision captioning partially failed, music rights and artistic review not certified. Private drafts only.
5. **PENDING:** configure a narrowly scoped GitHub Actions write credential in both Cloudflare Workers **directly via secret manager** (never in source/chat) and demonstrate automatic event wake and recovery; test valid owner login + real upload/preview on mobile and desktop; test zero/duplicate network errors, expired media, restart/timeout and cleanup; then certify invited user beta.

## Rollback
- Previous safe GitHub runner baseline: `9246726e95c1dbec92854716dddba8a6e8b35f64`. Revert only PR #161 if media jobs regress; preserve signed OIDC/rights checks and D1/KV. No Cloudflare deployment or DNS changes were made by this PR. Keep existing PWA and owner API protections intact.
- Master Stack source: this monitored repository uses a `STACK CHANGE:` commit, subject to independent registry synchronization. Do not infer registry publication from this document.
