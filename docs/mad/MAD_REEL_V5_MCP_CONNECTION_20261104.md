# MAD Reel Engine V5 — Remote MCP Connection Registration and Isolation Record

**Recorded:** 4 November 2026 (Asia/Kolkata).
**Acceptance:** PENDING_AUTH_QA / SOURCE_INTEGRATED_ONLY. Not a deployed or available ChatGPT MCP connector.
**Canonical policy:** [MCP OAuth registration and isolation SOP](../MCP_OAUTH_REGISTRATION_SOP.md); [registration checklist template](../templates/MCP_CONNECTION_REGISTRATION_CHECKLIST.md); [Master Stack](../MASTER_STACK_UPDATE_PROTOCOL.md).

## A. Ownership, scope and reuse

- Project: MAD Reel Engine V5, initial Moksha Wellness tenant, no blanket rights to other brand content.
- Source: public owner repository karanzing1992/engagement-core, main commits c1f9394cacb04f44a982b4770189d0ccf4ad1d41 and efa2d7a14550f9d199c515d62613d92f731a95b8.
- Temporary private vault **PILOT ONLY**: karanzing1992/Matrix-House, draft PR #1. Never mix unrelated files or publish original guest videos.
- New MCP source: experiments/reel-engine-v5/github-ephemeral/worker.mjs.
- Renderer reuse: existing first-party V5 Groq planner, guarded source manifest validator and FFmpeg multi_renderer.
- Cloudflare Worker role: stateless HTTPS/MCP API front end only; GitHub temporary Release assets and Actions runners hold media, not Cloudflare KV/R2.
- Existing ChatGPT MCP identity: NONE confirmed for V5; do not duplicate, hijack or replace WordPress, Generic Linux or any other MCP plugin ID.
- Free/open-source gate: no paid storage and no upgraded account approved; GitHub and Cloudflare free quotas apply, model rate/cost gates require independent verification.

## B. Connection and OAuth topology decision

**Decision: NOT SELECTED until an issuer and client ID are independently verified and accepted.**
- Shared issuer vs distinct issuer: OPEN. Preserve existing WordPress/Generic Linux clients, authorizations and pairings.
- Canonical resource URI and protected resource metadata: NOT CONFIGURED.
- Authorization server discovery and verified issuer: NOT RUN.
- PKCE S256, state, redirect URI allowlist, explicit consent UI and denial: NOT RUN.
- Signed token / JWKS, audience, expiry, client_id and owner/tenant authorization: NOT RUN.
- Six cross-plugin/tenant authorization denial tests: NOT RUN.
- ChatGPT connector compatibility test: NOT RUN.
- Existing prototype single bearer-token mechanism is NOT OAuth and cannot be called production connected, even if /health works.
- Separate owner-scoped GitHub App/PAT for the private vault is not configured. ChatGPT's connected GitHub token must NOT be extracted or reused in the Worker.
- Endpoint, Cloudflare deployment SHA, ChatGPT plugin ID and OAuth issuer: NONE verified.

## C. Actual certification evidence

1. Public engine source integration PR #116 merged, commit c1f9394cacb04f44a982b4770189d0ccf4ad1d41. GitHub synthetic contract/FFmpeg CI: https://github.com/karanzing1992/engagement-core/actions/runs/41778436834
2. Private vault synthetic upload -> source readback -> first-party renderer -> output readback -> delete: PASS, https://github.com/karanzing1992/Matrix-House/actions/runs/41778115689 . This verifies an explicitly deleted draft release, NOT the scheduled expiry or real guest footage.
3. Draft-release absent-tag acknowledgement fix PR #117 merged, commit efa2d7a14550f9d199c515d62613d92f731a95b8. CI https://github.com/karanzing1992/engagement-core/actions/runs/41778847259
4. Private vault workflow PR #1 remains DRAFT. Scheduled TTL cleanup has an identified draft-release tag-ref error; remediation not certified. No owner-private media source has been uploaded.
5. Master Registry Google Doc marker corresponding to these source commits was not found during the 4 Nov readback. Source event routing queued/eligible through existing STACK CHANGE commits, but DOC_VERIFIED status cannot be claimed.

## D. Hard blockers before LIVE_CERTIFIED

- Owner-restricted GitHub App install/credential provisioning to this private vault only; private GitHub Actions GROQ_API_KEY scoped appropriately.
- Verified Cloudflare Worker deployment version only after OAuth resource/client/tenant isolation, consent, security checks and rollback.
- Actual authenticated binary transfer bridge from ChatGPT attachment source to private Release assets. File names or a tool prompt do NOT imply media transfer.
- User-owned/consented real footage, human-reviewed source shot manifest and branded facts; any external Gemini/Groq processing must be specifically approved.
- End-to-end GitHub Action actual Groq creative plan, full supported edit operation fidelity, 1080x1920 video, legitimate verified music licence/audio mix, independent artistic QA, private readback and owner release approval.
- Acknowledgement deletion and scheduled 24-hour expiry live verification, with separate explicit deletion of assets as appropriate; GitHub backups/CDN physical erase cannot be guaranteed.
- Token replay, wrong-client, cross-project, file MIME/size/sha, malicious source, upload retries, concurrent uploads, owner-only access, inactive job, revoked credential and rollback negative tests.
- Signed receipt tying source hash, prompt, actual model, output artifact hash, time, rights evidence and exact main commit.

## E. Safe rollout and rollback

Until all gates pass: mark SOURCE_ONLY; do not register a remote MCP production connector, claim an active direct prompt interface, or publish or send real guest media to public GitHub.
For rollback: revoke scoped GitHub App/PAT and Worker secret; remove only new MAD V5 ephemeral workflows and job-specific temporary release assets after independent review; revert isolated engine commits. Do not disturb existing V5 defaults, signed WordPress Media Studio queue, MAD Manager, Mac/Dell machines or their browser sessions.
