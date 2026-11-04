# MAD Reel Engine V5 — Verified REEL_ENGINE_KEY + signed synthetic execution receipt
Date: 2026-11-04 UTC / 2026-11-05 IST
Classification: SYNTHETIC_TECHNICAL_CERTIFIED / GUEST_MEDIA_AND_PUBLICATION_NOT_CERTIFIED
Prior registry context: Moksha Master Registry event #272 (temporary diagnostic Cloudflare Worker removed).

## Source alignment
- PR #149: https://github.com/karanzing1992/engagement-core/pull/149
- Merged source commit: `dde65f8a549423eff3eb1b7045ba3ee61fde4dbb`
- Existing signed GitHub Actions workflow `.github/workflows/mad-v5-cloudflare-bridge.yml` now maps **all three runtime GROQ_API_KEY environment variables** (model preflight, synthetic render, private media render) to the pre-existing verified GitHub **REEL_ENGINE_KEY** secret.
- No secret values copied into source or Cloudflare. Groq credentials remain GitHub Actions secrets; Cloudflare retains signed GitHub OIDC and D1 access controls.
- Synthetic issue-triggered workflow runs skip `media_claim`; scheduled workflow processes private media only under existing owner/rights/consent restrictions.
- The temporary Cloudflare diagnostic endpoint was not restored.

## Independent isolated credential + inference + private synthetic render
- GitHub Actions successful run: https://github.com/karanzing1992/engagement-core/actions/runs/41888532132
- Account model preflight authenticated: GPT-OSS 20B, GPT-OSS 120B and Qwen 3.8 27B listed. **Listing does not certify image inference.**
- Actual Groq `openai/gpt-oss-20b` minimal text-completion smoke: PASS.
- Actual Groq `openai/gpt-oss-120b` synthetic-only cinematic director + FFmpeg `instagram_reel` profile: PASS.
- Local ephemeral artifact: generated test-only synthetic source, 1080x1920 H.264 / AAC, independent full decode, no guest media, no publication.
- Private test receipt SHA256: `38b078d5ccfac4a8e8c71a785b882a391738938417b798700dca5d93054ca0fe`.
- The isolated test intentionally did not upload its MP4 as a GitHub Actions artifact.

## Signed Cloudflare OIDC + GitHub synthetic end-to-end acceptance
- Owner-issued synthetic-only issue: https://github.com/karanzing1992/engagement-core/issues/154
- Successful signed pipeline: https://github.com/karanzing1992/engagement-core/actions/runs/41888905082
- Authenticated preflight, issue enqueue, signed GitHub OIDC lease, real Groq V5 synthetic direction, FFmpeg render, D1 completion and synthetic artifact archive: PASS.
- Verified Cloudflare D1 table `mad_v5_jobs`: `madcf-154`, mode `live`, profile `instagram_reel`, state `passed`, attempts `1`, error `null`, result SHA256 `009671c17d945da5af079b4b172de29f182a683eca8f2621e7b765d67b08816e`.
- Private real-media claim, install, download, render and completion steps: **SKIPPED** on this synthetic issue event; verified from the run step receipts.
- This existing public repository workflow archived **synthetic-only** output in a short-retention Actions artifact, not any real/guest media. The isolated private certification above archived no media artifact.

## Post-run production isolation
Read-only Cloudflare D1 `mad_v1_media_jobs` counts after run: `review_ready:2`, `failed:1`, `queued:0`, `claimed:0`. Historical private jobs untouched. Neither workflow published social content.

## Exact certification boundary / follow-on gates
**Certified now:** verified owner key usable for real Groq text inference, 120B synthetic directing, private synthetic FFmpeg render, and signed GitHub Cloudflare synthetic enqueue-to-D1-completion.

**Not certified:** actual guest footage rights/consent, browser upload-to-private-preview click-through on mobile, real footage visual interpretation by Qwen, guest-visible source fidelity, permitted soundtrack selection, artistic quality, full end-to-end real-media execution with this key, and any production publishing. Do not treat these as passed by synthetic acceptance.

**Next safe gate:** owner-authorized synthetic video through the **private-media** upload/KV transport (not only the separate synthetic queue), verify authenticated chunk ingestion, signed render, private preview download, SHA256, and no-publication; perform negative auth/expiry/concurrency tests. Only then, after explicit guest rights and consent checks, attempt an owner-approved private guest draft. Never enable paid provider fallbacks or public publishing without separate authorization.

## Rollback
Revert the narrowly scoped workflow secret binding/issue guard using the pre-PR baseline, preserving the Cloudflare D1 queues, existing private-media objects, other sites and unrelated workflows. Never reproduce diagnostic credential-forwarding endpoints.
