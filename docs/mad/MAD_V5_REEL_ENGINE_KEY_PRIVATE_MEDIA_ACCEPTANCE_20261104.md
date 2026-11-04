# MAD Reel Engine V5 — REEL_ENGINE_KEY signed-media certification gate
Date: 2026-11-04 (Asia/Kolkata)
Repository: karanzing1992/engagement-core
Branch: fix/mad-v5-reel-engine-key-signed-media-20261104
Pull request: https://github.com/karanzing1992/engagement-core/pull/148

## Verified baseline
- The existing Cloudflare OIDC bridge `mad-reel-v5-oidc-bridge` has D1 and private MEDIA_KV bindings. It uses pinned main-branch GitHub Actions OIDC identity for signed requests.
- An owner Groq model-list preflight uses `secrets.REEL_ENGINE_KEY`. Do not copy or print the secret value.
- Historic synthetic D1 results include passed jobs; they do not certify the current credential migration or owner-private real-media editing.
- The separate `mad-reel-v5-github-mcp` candidate has no required GitHub/MCP secrets and is not the certified remote-MCP production entrypoint.

## Narrow change
- Map `REEL_ENGINE_KEY` into the existing runner's `GROQ_API_KEY` process variable at three points in `.github/workflows/mad-v5-cloudflare-bridge.yml`: model preflight, signed synthetic V5 runner, private-media runner.
- Leave the Cloudflare identity verifier, OIDC claims, private KV, database, owner code, OAuth constraints and all consent checks unchanged.
- Add a separate bounded one-call `openai/gpt-oss-20b` inference test, plus a no-artifact synthetic V5 FFmpeg render smoke test on ephemeral CI.
- Keep Groq-only/free-tier provider routing. No paid provisioning, guest-file upload or public distribution.

## Live evidence
- New branch commit for mapping: `4a8c9f73b9ccf66f9e317419bf135e5de856aec6`.
- Smoke CI: https://github.com/karanzing1992/engagement-core/actions/runs/41885329002 .
- Minimal real Groq call: PASS in GitHub job step `Verify one real Groq text inference under authenticated owner key`.
- Synthetic fixture-only FFmpeg render: PASS in run 41887146855 (see live smoke certification below).
- Branch changes are staged for merge; full owner-real-media and release certification remains pending.

## Remaining release gates
1. Check smoke run conclusion and receipt, full decode and SHA-256; no synthetic MP4 is to be uploaded as an artifact.
2. Merge only after CI passes and confirm canonical pinned-main signed-bridge workflow now receives `REEL_ENGINE_KEY`.
3. Execute a fresh owner-issued synthetic-only OIDC job via existing Cloudflare D1 bridge, verify queue claim, Groq V5 plan, FFmpeg SHA-256 result, duplicate suppression, and unauthorized 401 rejection.
4. Verify private-media source transport, rights/consent, authenticated private preview, expiry/cleanup, and independent creative/music review before any guest footage is processed.
5. Never claim ChatGPT OAuth MCP production certification, public rollout, owner rights clearance, or publication based solely on synthetic tests.

## Rollback
Revert only the workflow credential reference if the verified key fails in pinned main after merge. Preserve old secrets, unrelated connections, D1/KV data, and owner gates. Never print provider credentials.

## Live smoke certification — 2026-11-04 23:56 IST
- Independent minimal authenticated Groq inference: **PASS**, model `openai/gpt-oss-20b`, `MAD_GROQ_INFERENCE_PASS`.
- Private fixture-only synthetic FFmpeg render: **PASS**, `MAD_V5_PRIVATE_SYNTHETIC_SMOKE_PASS`, full decode and SHA-256 `3120cb296b9dbbae3bc2d1d20909bb3841c52a0db4de80c93eb141f4210920ac`.
- Evidence: https://github.com/karanzing1992/engagement-core/actions/runs/41887146855
- Fixture ran only in ephemeral GitHub runner, using pinned npm-distributed FFmpeg/FFprobe binaries to bypass GitHub Ubuntu apt mirror hang. Test-only binaries are not introduced into the production private-media runner; no media artifact upload, no real guest footage and no publication.
- An earlier combined `--mode live` 120B creative-planning smoke **FAILED**: Groq returned `400 json_validate_failed`, max completion tokens exhausted before a valid JSON document (run https://github.com/karanzing1992/engagement-core/actions/runs/41886189737). This failure remains an explicit blocker to full model-directed media certification.
- The minimal Groq inference and private fixture render pass are **independent**; no claim of Groq creative plan being applied to synthetic footage.
