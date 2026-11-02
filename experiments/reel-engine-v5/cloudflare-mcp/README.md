# V5 Cloudflare MCP gateway (candidate)

Cloudflare Worker provides authenticated MCP tools: `v5_submit_render`, `v5_list_runs`, `v5_get_results`. GitHub Actions performs rendering and stores private artifacts. Worker does not render, store source media, or publish.

## Required deployment

1. Merge the render workflow and gateway into `main`.
2. In this folder: `npm install && npm run check && npm run deploy`.
3. Set Worker secrets with `npx wrangler secret put GITHUB_TOKEN` (fine-grained Actions read/write for this repository) and `npx wrangler secret put MCP_ACCESS_TOKEN` (long random bearer token). Never commit secrets.
4. Connect an MCP client to `https://<worker>.workers.dev/mcp` using the bearer token.
5. Upload original source MP4 as private artifact named `v5-source` in a source-intake GitHub Actions run. The gateway does **not** currently implement binary upload. Call `v5_submit_render` with the intake run ID, source artifact name and unique job ID. Poll `v5_list_runs`, then `v5_get_results`.
6. Retrieve private artifacts through authorized GitHub Actions API. Never claim successful render until artifact verified.

## Known limits

This is a first implementation, **not deployed or certified**. Token comparison is simple bearer auth, not user OAuth. GitHub Actions artifact retention is 30 days, not permanent object storage. The current render workflow uses a fixed technical treatment and is **not the full multimodal V5 orchestrator**. Source-ingestion, real model/tool routing, music and guest consent, end-to-end QA and signed artifact delivery must be certified separately. Do not publish without owner approval.
