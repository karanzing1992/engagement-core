# MAD V5 Cloudflare to GitHub Actions OIDC Bridge — synthetic pilot

- **Endpoint:** https://mad-reel-v5-oidc-bridge.karanbizweb360.workers.dev/health
- **Worker:** mad-reel-v5-oidc-bridge, D1 database mad-v5-bridge-queue in owner Cloudflare account
- **Source:** worker.mjs, 001_queue.sql, wrangler.toml
- **Runner:** services/reel-engine/cloudflare_bridge_runner.py and .github/workflows/mad-v5-cloudflare-bridge.yml
- **Model credentials:** Existing GROQ_API_KEY and GEMINI_API_KEY stay in first-party engagement-core GitHub Actions secrets.
- **Authentication:** GitHub Actions short-lived OIDC JWT signed RS256, validated by Cloudflare against GitHub fixed JWKS URL. Requires audience mad-v5-cloudflare-bridge/v1, repository ID 1403281267, owner ID 30191163, main ref, exact workflow_ref, GitHub-hosted runner, signed exp/iat/nbf, and owner actor for issue enqueue. No GitHub PAT.
- **Queue:** An owner-authored GitHub issue titled [MAD-V5-CF] with exact JSON schema submits prompt. The issues workflow signs an OIDC request to Cloudflare; the same workflow can lease one synthetic job; schedule/manual runs poll and recover a 45-minute abandoned lease up to 3 attempts.
- **Scope:** Synthetic-only text/fixtures. No raw customer video, external source URLs, preview streaming, social publishing, production OAuth MCP registration, or real guest consent processing.
- **Output:** Owned V5 Groq/Gemini/FFmpeg synthetic runner; 7-day GitHub technical Actions artifact, D1 result SHA256 and GH run reference.
- **Reuse:** Official GitHub OIDC issuer and Cloudflare Workers+D1, existing owned MAD V5 runner. No custom identity provider or duplicate model keys. https://docs.github.com/en/actions/reference/security/oidc ; https://developers.cloudflare.com/d1/worker-api/d1-database/
- **Open Source / Reuse / Cost Gate:** Existing source and free-tier Workers+D1+GitHub Actions were reused. No paid assets, subscriptions or media storage introduced. Observe quotas and provider free-tier use before scaling.
- **Rollback:** Disable this Worker subdomain, then disable this dedicated GH workflow; delete D1 only after reviewing/purging pending jobs. Existing V5 engine, WordPress ingest and GitHub media vault must remain unchanged.
- **Master:** Register the *verified synthetic-only* OIDC bridge capability and independently verify central Registry publication. This does not certify ChatGPT OAuth MCP, real guest-media intake or cross-client/tenant isolation.
- **Limitations:** Existing GitHub-release media vault MCP is separate and remains fail-closed. Real guest processing and direct ChatGPT MCP OAuth are NOT implemented here.

## 4 November 2026 — live synthetic end-to-end acceptance

- **Root cause fixed:** Cloudflare Workers rejects `fetch(url,{redirect:'error'})`; switching to supported `redirect:'manual'` while requiring exact HTTP 200 for the GitHub JWKS resolved GitHub Actions OIDC 401 failures.
- **Fix:** PR #127 merged as `2098b0c6c3cd39c4b50057acceb3cb7fee0e5ef9`, removing temporary debugging headers/claims logs; CI suites passed including guard against regression.
- **Live admission and model rendering:** GitHub workflow run https://github.com/karanzing1992/engagement-core/actions/runs/41798627740. Owner-authored issue #123 signed with OIDC and enqueued `madcf-123`; Cloudflare D1 job claimed, existing Groq 120B V5 creative director processed synthetic brief; guarded FFmpeg output decoded; stored receipt returned from GitHub to Cloudflare. Job state `passed`, `attempts=1`, SHA-256 `7ae8670b7dbad5ab8e9087ec4e0afc62a7437791465b8becc6774bb13b9f7ed5`; MP4 and technical receipt in GitHub Actions synthetic-only artifact with seven-day retention.
- **Idempotency:** Issue #123 replay https://github.com/karanzing1992/engagement-core/actions/runs/41798911385 returned `CLOUDFLARE_SYNTHETIC_ENQUEUE_ACK madcf-123 False` followed by `CLOUDFLARE_BRIDGE_QUEUE_IDLE`; no second render.
- **Deny tests:** Unauthenticated claim returns HTTP 401, forged JWT status returns HTTP 401, both after the fix. No staging authentication diagnostic headers remain. Disposable Cloudflare JWKS egress probe deleted and verified absent.
- **Private media and user-facing ChatGPT:** **NOT certified**. The separate draft-release media bridge still requires secure binary-source intake, rights/consent checks, audio/music and artistic certification, automated expiry tests and full MCP OAuth authorization. Do not publish real guest footage or declare live ChatGPT bookable/usable from the synthetic receipt.
- **Provider credentials:** `GROQ_API_KEY` and `GEMINI_API_KEY` remain in the existing `engagement-core` GitHub Actions; no new provider secrets or GitHub PAT were generated or moved. Gemini model invocation was not part of the successful Groq-only acceptance run (prior Gemini synthetic connection was validated separately).
- **Cost/OSS:** GitHub Actions, Cloudflare Workers+D1 and FFmpeg with free-tier budget checks; no paid tier provisioned. The synthetic pilot has no raw-media downloads or public user footage.
