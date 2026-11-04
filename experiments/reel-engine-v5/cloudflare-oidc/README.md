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
- **Master:** Register staging capability and verify central registry readback; production feature claims require live OIDC/negative cross-tenant tests and D1 receipt verification.
- **Limitations:** Existing GitHub-release media vault MCP is separate and remains fail-closed. Real guest processing and direct ChatGPT MCP OAuth are NOT implemented here.
