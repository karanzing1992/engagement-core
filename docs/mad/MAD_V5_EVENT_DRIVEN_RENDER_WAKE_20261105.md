# MAD Reel V5 — Event-driven render wake handover (2026-11-05 IST)

## Problem confirmed

Owner private-media upload and Project render submitted jobs into Cloudflare D1 but the only normal GitHub Actions pickup was `on.schedule: 16,46 * * * *`. The owner submitted `madmedia-ede1549f-049a-4efe-b198-a73473a9e6a2`, a complete 9,749,020-byte upload (3 SHA-256 chunks). The row stayed `queued` with `attempts=0`, which is an orchestration pickup failure, not a render-model failure.

## Change scope / source

PR #156: https://github.com/karanzing1992/engagement-core/pull/156

Source changes:
- `services/reel-engine/ai-reel-api-v1/media_event_wake.mjs` calls GitHub's **pinned** `workflow_dispatch` endpoint (POST, main ref, bounded job ID only), from the server, after D1 accepts a private render job.
- Both legacy `/v1/media/jobs` and Project `.../render` submit paths call this helper. Existing owner authentication, authorization, upload SHA and D1 queue are preserved.
- `011_event_wake.sql` adds an idempotent D1 outbox with `pending`, `dispatching`, `dispatched`, `failed` states, at most four attempts, 30-second retry throttle, 90-second ambiguous-outcome lease.
- Owner API exposes job wake status and `POST /v1/media/jobs/{job_id}/wake` for explicit retries; jobs cannot be dispatched after claim or expiry.
- The signed GitHub workflow continues to claim **one** D1 media row through pinned OIDC and returns `PRIVATE_REAL_MEDIA_TECHNICAL_DRAFT`; 204 dispatch acceptance is **not** render completion.
- The workflow additionally allows a private queue wake from a GitHub issue starting `[MAD-V5-WAKE] `, **only** when both issue author and event actor are the repository owner; its existing GitHub OIDC bridge further pins the issue event actor ID. These issues contain no video, source URL or creative prompt, and skip synthetic enqueue.
- Scheduled GitHub workflow is retained **only as a recovery fallback during transition**, and must not be disabled before live-event certification.

## Tested

CI `AI Reel Engine V1 owner PWA API contract` passed offline with `test_media_event_wake.mjs`: valid 204 dispatch, exact bounded job ID payload, no duplicate wake, missing credential fail-closed, retry throttling, HTTP 401 classification/recovery, claimed/expired/invalid refusal, and SQLite wake-ledger migration. Other OIDC/workspace/real-media security checks passed too.

## Live enablement remaining

No GitHub Actions dispatch credential currently exists in either production Cloudflare Worker settings. **Do not claim automatic event-driven production wake enabled until done:**

1. Create a fine-grained GitHub access credential for *only* `karanzing1992/engagement-core` with **Actions: read/write** permission; use an expiration and rotation policy or a GitHub App that can mint ephemeral installation access tokens automatically.
2. Bind the credential as **Cloudflare secret** `MAD_GITHUB_ACTIONS_DISPATCH_TOKEN` to BOTH Workers `delulutech-ai-reel-api-v1` and `delulutech-ai-reel-projects-v1`, never to browser or GitHub source. Do not print or paste credentials into issues/docs.
3. Apply D1 migration `011_event_wake.sql` in isolated target and then production; independently verify schema.
4. Build/deploy both modular Cloudflare Workers (new local imported module), preserving the existing D1/KV, `MAD_OWNER_CODE_SHA256`, Origin constraints, and routing.
5. With a synthetic owner-approved video, verify a **new** event creates a GitHub `workflow_dispatch` run and the exact D1 job is signed-claimed, completed, checksum verified in private preview, no publishing. Negative: no secret => fail closed, invalid token => failed wake, duplicate button => one dispatch, network retry => no duplicate render.
6. After successful live receipt, remove/reduce schedule to an infrequent safety watchdog only if robust durable retry/alerting is in place. Do not silently remove the recovery path.

## Existing queued job recovery

Once workflow changes are on `main`, the owner may create exactly one GitHub issue with title `[MAD-V5-WAKE] Owner private queue request` and body containing no media/secret. The owner-only issue event runs signed `media_claim` for oldest queued job without a new upload or creator token. It is a **manual one-off recovery**, not a substitute for the automatic Cloudflare dispatch credential.

## Safety

- No source video or private render output in GitHub issues/artifacts or public URLs.
- No new external provider, fee, credential exposure, or public release.
- Preserve previous successful synthetic credential and model certificates (PR #149 and run #41888905082), and existing private-media data.
