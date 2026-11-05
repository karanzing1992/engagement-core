# MAD V5 — Activate Cloudflare → GitHub Actions event dispatch (owner runbook)

**Status on 2026-11-05:** `media_event_wake.mjs` and GitHub `mad-v5-cloudflare-bridge.yml` already implement authenticated dispatch. **Not activated:** neither production Worker has a `MAD_GITHUB_ACTIONS_DISPATCH_TOKEN` secret. No credential was generated or transferred by ChatGPT. The connected GitHub App token must never be extracted/reused.

## Minimal owner action (beta)
1. Use GitHub's official **fine-grained** token creation form, signed into the owner of private `karanzing1992/engagement-core`:
   https://github.com/settings/personal-access-tokens/new?name=MAD-V5-Render-Dispatch&description=Cloudflare-to-GitHub-Actions-workflow-dispatch-only&target_name=karanzing1992&expires_in=30&actions=write
2. **Repository access: Only select repositories → `engagement-core`**. Required repository permission: **Actions: Read and write** (GitHub REST POST workflow dispatch). Do not grant Issues, Contents, Administration, Secrets or Workflows. Metadata read is automatically included. Verify the repository selection, then generate. For longer-lived operation replace PAT with a dedicated GitHub App installation token minted server-side (never a static reusable installation token).
3. In Cloudflare account `3409ce0fa4794fb024c570d141ef0521`, Workers & Pages → select `delulutech-ai-reel-api-v1` → Settings → Variables and Secrets → Add → **Secret**, name `MAD_GITHUB_ACTIONS_DISPATCH_TOKEN`, paste the token in the Cloudflare dashboard (NOT into source code, GitHub PR, ChatGPT or messages) → Deploy.
4. Repeat **with the same token** on `delulutech-ai-reel-projects-v1` because `project_render.mjs` invokes `wakeMediaJob(env, job)` using the Projects Worker environment. Never add a placeholder: once a name exists with an invalid value, real queued jobs would consume up to four failed dispatch attempts.
5. After deploying both, perform a new owner-only **synthetic** private-media render from the live UI. A valid dispatch is HTTP **204** at GitHub; this only confirms acceptance. Verify the GitHub `workflow_dispatch` run started, signed OIDC claims a queued D1 job, private H264/AAC full-decode output is written to KV, SHA-256 matches D1, job state is `review_ready`, and history/status/preview work. `mad_v1_media_wakes` should show `dispatched`, last_http_status=204. **Do not use private guest footage to test authentication**.
6. Fail-safe: GitHub Actions schedule `16,46 * * * *` and Cloudflare `*/5 * * * *` cron remain recovery paths; Cloudflare retries are bounded to 4, transient backoff 90s, in-flight 120s, dispatched 480s. Do not remove these recovery mechanisms without first certifying auto-event wake.

### Endpoint and policy
- Cloudflare source: `services/reel-engine/ai-reel-api-v1/media_event_wake.mjs`
- GitHub workflow: `.github/workflows/mad-v5-cloudflare-bridge.yml`
- Dispatch endpoint: `POST https://api.github.com/repos/karanzing1992/engagement-core/actions/workflows/mad-v5-cloudflare-bridge.yml/dispatches`
- Body: `{"ref":"main","inputs":{"media_job_id":"madmedia-<uuid4>"}}` (never source bytes or prompts).
- Tokens remain in Cloudflare encrypted Worker secrets only, GitHub API never supplied to client.
- If unauthorized HTTP 401/403: verify token resource owner/repository/Actions:write permission; if 404 verify workflow path/ref; if 422 verify UUID/ref. **Never log or copy the credential**.
- Owners should rotate/revoke the 30-day token when migrating to a GitHub App. Production beta remains owner-only, with no social publication.

### Certification state
- GitHub private FFmpeg technical beta independently passed via signed owner issue event, GitHub run `41984759753`, D1 job `madmedia-e6280631-1585-4e36-beba-f83dcb826d6a`.
- That **does not** prove the Cloudflare-to-GitHub `workflow_dispatch` credential is configured. Mark `dispatch_auth=NOT_CONFIGURED` and `automatic_event_wake=NOT_CERTIFIED` until the above live evidence exists.
