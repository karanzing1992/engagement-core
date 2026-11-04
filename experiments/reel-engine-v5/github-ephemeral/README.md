# MAD Reel Engine V5 — GitHub-native ephemeral media + MCP candidate

## Evidence and certification status (2026-11-04)
- SOURCE INTEGRATED, feature branch only. Not deployed as a live ChatGPT plugin.
- Public synthetic V5 FFmpeg + MCP security contract CI PASS: https://github.com/karanzing1992/engagement-core/actions/runs/41777736844
- Private GitHub draft Release upload → download → render → return → release deletion PASS, synthetic only: https://github.com/karanzing1992/Matrix-House/actions/runs/41778115689
- The real guest clip 1000083489.mp4 is NOT uploaded or rendered through this flow. Issue #99 remains blocked.
- Live MCP OAuth, real-footage visual analysis, licensed audio, artistic review and deployment remain NOT CERTIFIED.

## Reference/reuse/open-source and cost decision
Reuse existing owner V5 config, v5_orchestrator.py, capability_registry.json, multi_renderer.py, Groq adapter and GitHub Actions. Reuse GitHub Releases API as private short-lived binary object storage and Cloudflare Workers as a stateless MCP gateway. No R2/Vercel Blob or paid media service. Only necessary transport/identity validation glue is new. The owner's GitHub Actions free-tier quotas and Cloudflare Workers limits still apply.

## Tenant and source boundaries
The media vault pilot is the existing PRIVATE karanzing1992/Matrix-House GitHub repo; only temporary job-specific draft GitHub Release assets belong to V5. The engine code is in PUBLIC karanzing1992/engagement-core. Never put guest videos, signed URLs, tokens or identifiable original footage into public issues/commits/Actions. An eventual dedicated private vault repo is preferable. Do not modify unrelated Matrix-House content.

The private workflow reconstructs uploaded source chunks, checks SHA256, checks consent and human-reviewed shot/source facts, calls Groq 120B only with approved source metadata, uses the actual V5 shot/EDL validator and the existing FFmpeg renderer, and writes a technically validated private review MP4 and JSON receipt. Unsupported creative effects are a BLOCK, not a falsely claimed successful effect. No automatic publishing.

## MCP control surface (candidate only)
- reel_create_job: prompt, project, chunk count, SHA256, source size, rights, optional verified shots/brand.
- authenticated POST /media/{job_id}/{chunk_index}: raw 80 MiB maximum stream chunks, GitHub release assets.
- reel_submit_prompt: private Actions dispatch after source inventory validation.
- reel_status: job state and output availability.
- reel_get_preview: HMAC-signed ten-minute preview link.
- reel_acknowledge_and_delete: remove temporary release assets after review.
- Fallback hourly expiry: remove only job-tagged V5 temporary releases older than 24 hours.

## Critical deployment blockers and separate ownership actions
1. Review and merge feature branch CI before using main code in private Actions.
2. Review/merge private Matrix-House workflows; pin trusted merged public engine SHA.
3. Cloudflare requires a **new owner-scoped fine-grained GitHub App installation or PAT** for that private vault, limited to releases/contents and Actions dispatch. The existing ChatGPT GitHub connector does not expose its token to a Cloudflare Worker. Never print or copy credentials into source, tools or chat.
4. MCP/OAuth must use the canonical docs/MCP_OAUTH_REGISTRATION_SOP.md with a per-client registration checklist: issuer, PKCE/state, resource audience, client ID, tenant isolation and cross-plugin denial tests. The present bearer auth is a source candidate, not ChatGPT remote MCP production certification. DO NOT register/deploy as production until verified.
5. Provide original source bytes through a real authenticated file-transfer adapter. ChatGPT uploaded file names do not automatically become GitHub release assets.
6. Configure private Actions GROQ_API_KEY and independently verify live model calls. Production also requires source rights/consent, human-reviewed shot manifest, verified brand context, licensed real soundtrack and artistic review. Real Gemini frame analysis and its consent are not yet implemented/certified.
7. Certify actual owner-footage prompt → source ingest → model → FFmpeg → private preview/download → acknowledgement purge, and scheduled TTL cleanup.

## Known limitations and truth
Source runner can do synthetic test and guarded real-media draft with reviewed source manifest; a prompt and media attachment alone do NOT complete a verified autonomous cinematic output. The draft is not commercially rights-cleared or owner approved. GitHub Release deletion removes application-accessible assets but cannot promise immediate physical deletion from vendor backups/CDNs.

## Rollback
Delete only the V5-specific Worker/workflows and temporary assets if deployed; revoke scoped credentials; revert isolated Git branch. Preserve existing public Engine V5 baseline, WordPress signed queue, MAD Manager, Mac/Dell operations and non-sensitive receipts. Do not disable existing protections.
