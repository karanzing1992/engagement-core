# Reel Engine Cloudflare reliability patch — 2026-11-05

Scope: **Cloudflare live API reliability only**. Not migration of FFmpeg/Groq creative execution from GitHub Actions. No user-upload/guest-media publication.

## Verified live deployment
- Account ID: `3409ce0fa4794fb024c570d141ef0521`.
- Existing PWA: `https://reel.delulutech.in`, Cloudflare Pages `delulutech-ai-reel-engine-v1`; production deployment `c068a51a-8eca-4ac2-b567-47b455b73dbd` remains unchanged.
- Updated Cloudflare Worker scripts directly with `PUT /content`: `delulutech-ai-reel-api-v1` and `delulutech-ai-reel-projects-v1`. Their D1, KV, SHA256 owner-code secret and origin allowlist bindings were independently read back and preserved.
- Wake retrier now caps at **4** attempts, matching `011_event_wake.sql` deployed D1 CHECK constraint (previous code attempted 6).
- Submission reuses existing active queued/claimed job for the same source upload, returning HTTP 202 and `existing:true`; race prevented atomically by migration `012_one_active_job_per_upload.sql` (applied live; unique index readback confirmed). No data deletion or render retries.
- Previously misleading generic 'another render active' on any DB error replaced by HTTP 503 with explicit queue error. Projects API missing-credential 401 response now includes exact allowed-Origin CORS headers, so browser sees meaningful rejection instead of 'Failed to fetch'.

## Acceptance and evidence
- Before index creation: D1 active queued/claimed jobs: **0**; duplicate active uploads: **0**. After: unique partial index present; existing 4 review-ready and 1 failed media jobs preserved.
- Both dedicated temporary QA Cloudflare Workers compiled successfully with patched modules and no production secrets. Source hashes of the four patched production modules match these GitHub files exactly (FNV-1a compatibility hash lengths from runtime readback: owner worker 17626/df9ca984; wake 5484/4f9a325a; Projects render 3076/2cbae77b; Projects entry 2113/30c8028d).
- Live `https://reel-api.delulutech.in/health` and `https://reel-projects.delulutech.in/health` return ready:true. PWA and manifest respond normally. Unapproved origins rejected with 403. Browser-origin missing-credential tests of both protected API paths now return readable HTTP 401 (previous Projects path failed CORS). PWA manifest browser fetch HTTP 200.
- The original owner-only private-media render `madmedia-ede1549f-049a-4efe-b198-a73473a9e6a2` previously completed via manual GitHub wake with 22,430,716-byte private review output, **NOT** a fresh postpatch render receipt. No new authenticated render executed here.

## Remaining blockers and scope boundary
- Cloudflare Workers handle frontend, D1, private KV, API and event wake logic; **actual FFmpeg execution remains on GitHub Actions**. Full Cloudflare-only runtime is not deployed. Cloudflare free Worker CPU/runtime cannot be treated as a generic video render host; R2 is not enabled in this account. Do not enable paid Cloudflare Containers without owner cost approval.
- `MAD_GITHUB_ACTIONS_DISPATCH_TOKEN` absent in both production Workers; automatic direct GitHub workflow_dispatch remains unavailable. Cloudflare 5-minute recovery cron is present but inactive without dispatch key. Existing GitHub schedule/manual owner wake is a fallback.
- Owner code not available to this QA: browser file-picker > authenticated video upload > model-directed FFmpeg render > private playback / cleanup remains **not certified**. Groq 120B creative structured plan had failed validation; historical renders used source-only FFmpeg fallback. No rights/consent/music/artistic acceptance and no public publishing.

Rollback: deploy prior Cloudflare Worker version(s) or revert only the four changed source modules and drop the new partial index **only after** no in-flight jobs and explicit review. Preserve all D1 media/history, KV and owner secrets; do not roll back unrelated Cloudflare Workers.

This report is a **post-deployment source-sync**: GitHub does NOT run the frontend/API at request time, and the GitHub PR must not be misrepresented as full renderer migration or video certification.
