# MAD V5 — Cloudflare → GitHub Event Dispatch: Production Certification

**Date:** 2026-11-05 UTC. **Status: OWNER-PRIVATE TECHNICAL EVENT-DISPATCH PATH CERTIFIED.** No guest footage, no release/publication approval.

## Root cause and permanent source correction

- Prior production code in `media_event_wake.mjs` set `redirect: 'error'` in the outgoing `fetch()` to GitHub workflow-dispatch REST API. Cloudflare Workers rejects this redirect setting with a local TypeError *before the HTTP request*, causing NULL HTTP status, `GITHUB_DISPATCH_NETWORK_ERROR` and consuming bounded retries.
- Replaced with Workers-supported `redirect: 'manual'`, explicitly rejects HTTP 3xx, distinguishes timeout / fetch TypeError / network errors, never logs token values or exception messages.
- Regression tests updated: manual redirect must be sent; a 302 is rejected and a TypeError is sanitized. CI on PR **#164**: 5/5 workflow checks passed.
- Source: [PR #164](https://github.com/karanzing1992/engagement-core/pull/164), merged main commit `72c8953843643f24779a5f2150d6a96f3b24e68b`.

## Verified live deployment

Direct Cloudflare module upload with strict **binding inheritance** (no credential values copied). Production Worker modules read back with the corrected redirect setting:
- `delulutech-ai-reel-api-v1`: shared dispatcher updated; `DB` D1, `MEDIA_KV` private KV, `MAD_OWNER_CODE_SHA256` encrypted secret and `MAD_GITHUB_ACTIONS_DISPATCH_TOKEN` encrypted secret preserved.
- `delulutech-ai-reel-projects-v1`: shared dispatcher updated; `DB` D1, `MAD_OWNER_CODE_SHA256` and `MAD_GITHUB_ACTIONS_DISPATCH_TOKEN` both encrypted secrets preserved.
- Original compatibility date `2026-11-04` retained. Owner API's `*/5 * * * *` recovery watchdog schedule retained. No CDN/site UI or public rollout changes.

## Fresh signed production synthetic acceptance

The earlier test job `madmedia-09e720eb-4027-4922-b99c-7c2f26f63628` exhausted four attempts while the unsupported code was deployed. It was explicitly finalized as failed; wake history retained without bypassing retry constraints.

New fixture: `synthetic-blue-test.mp4` (3269 bytes), private upload `upload-5c409a5c-998b-4ae6-9e68-d79848af1fe4`. Rights/people/provider consent flags valid **for the synthetic fixture only**. One fresh job:
- D1 job: `madmedia-e21959e8-a375-4083-a7c5-0edaf22d2cef`.
- Cloudflare scheduled reconciliation delivered automatic `workflow_dispatch` to GitHub: **HTTP 204**, `mad_v1_media_wakes.state=dispatched`, `attempts=1`.
- GitHub workflow-dispatch run [#42000927850](https://github.com/karanzing1992/engagement-core/actions/runs/42000927850), job `127155633094`: **success**, signed OIDC private-media claim and full private FFmpeg render/complete callback.
- Live source verification, Groq creative report `attempts 1 plan_applied 1 reason none`, `vision_captioned 2`, `vision_sampled 3`, `vision_failures 1`, `unapplied_effects 9`; technical draft only, **not** full artistic-effects certification.
- Production D1 result: `state=review_ready`, render `attempts=1`, `result_bytes=45756`, `result_chunks=1`, `error_code=NULL`, SHA-256 `644075f0addd4737e797debcbe691b3f2ea400d4db3e154167e8604b1ca28c1d`.
- Independently read Cloudflare private KV `private/mad-v1/output/<job>/0` and recalculated SHA-256 **exactly matching** D1 (45756 bytes, valid MP4 `ftyp` signature). Media bytes were not returned in chat.
- No queued or claimed jobs after completion; historical failed jobs retained. No video publication.

## Boundaries, next gates, rollback

- **PASS:** owner-private event wake from Cloudflare, scoped GitHub dispatch HTTP 204, signed claim, Groq/FFmpeg completion, private-storage checksum and isolation.
- **Still not certified:** valid owner-code interactive mobile UI upload → render → history/status/preview; multiuser tenancy and permissions; guest footage consent/music licensing; independent cinematic/artistic review; public beta and publication.
- GitHub schedule `16,46 * * * *` and Cloudflare five-minute cron remain recovery only; normal user Render calls `wakeMediaJob()` immediately via `ctx.waitUntil`.
- Rollback: previous Cloudflare deployment/version for either Worker or restore only the former `media_event_wake.mjs` and redeploy with `bindings_inherit=strict`. Note the former version has the confirmed redirect defect; do not roll back unless operationally necessary. Revoke/rotate compromised credentials via Cloudflare Dashboard; never log them.
