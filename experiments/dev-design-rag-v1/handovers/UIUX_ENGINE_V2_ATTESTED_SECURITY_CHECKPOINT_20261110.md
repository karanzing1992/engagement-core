# Generic UI/UX RAG V2 — independent attestation and autonomous-engine security checkpoint
Date: 2026-11-10 IST. Source basis: local 8f450830c216de84b4b55188c24cec0229928544; Master Registry #351.

## Scope and status
Owner-authorized isolated Dell development only. The local V2 branch and other workers' untracked directories were preserved. Hardening is in an independent review worktree/branch. **Release status remains BLOCKED.** Nothing here authorizes production, OTA, billing, guest-data access, or public deployment.

## Implementation
- `engine/attestation.py`: Ed25519 signature validation against *owner-provisioned root-owned* `/etc/moksha-uiux-v2/trusted-reviewers.json`. Trusted keys specify reviewer identity, allowed models and enabled status. No signing/private key exists in writer repo.
- Reviewer receipt validates distinct job ID, exact site and QA hashes, every screenshot hash, the complete 390px/1440px set on every page, independently observed per-page raw JSON model results, derived minimum score, and strict >=95 APPROVE.
- `engine/reviewer.py`: screenshot provenance and raw Ollama responses are recorded; output is explicitly **unattested evidence**, not auto-approved. Per-page checkpoint/resume supports long inference. It cannot sign itself.
- `engine/lighthouse.py` + `cli.py`: per-route mobile and desktop Lighthouse reports, raw hashes and resumable multi-page summary; old one-page smoke scores cannot certify a site.
- `engine/orchestrator.py`: job lock, stage ledger, model retry classification, bounded attempts, idempotent reuse, checkpoint/status and fail-closed stop on missing attestation.
- `engine/preview_deploy.py`: same policy gate before Vercel preview only, free-preview flag, immutable source copy and remote build-hash manifest verification. No production subcommand or owner release claim. Independent deploy surfaces outside this adapter still require governance enforcement.
- `engine/security_tests.py`: isolated synthetic cryptographic/negative tests. `engine/certification_tests.py` was copied **without overwriting** the original worker-owned untracked test; the Lighthouse error name was updated for new policy.

## Real evidence so far
- Existing source-grounded RAG policy and knowledge suite: **34/34 PASS**.
- Engine/security suite: **20/20 PASS** (legacy eight plus 12 Ed25519/negative tests).
- Original isolated six-page responsive Playwright/axe: **24/24 PASS** from previous source receipt; not rerun as a new claim.
- Previous single agent-generated smoke-page Lighthouse: mobile perf 100, desktop perf 98, axe/accessibility 100; **not all routes**.
- Preview wrapper on preexisting fixture: **BLOCKED** for missing independent artistic attestation and full-route Lighthouse.
- Vision failure traced to Ollama HTTP 400: 2,239 image-plus-prompt tokens for 2,048 context. Increased to 4,096; a subsequent *real screenshot pair* still timed out after 100 seconds on CPU. No score, no successful vision receipt, and no >=95 claim.
- Machine: 7.5 GiB RAM Dell, Ollama 0.40.6, local Qwen3-VL 2B instruct; CPU inference remains a throughput blocker.

## Trust/security limitations
- The trusted reviewer OS identity and root-owned public-key registry have **not been provisioned**. A test-only Ed25519 key proves validator behavior, not an operational organizational trust boundary. Only a distinct reviewer service identity may sign, with controlled model-call receipts and immutable evidence. A writer must not have access to that signing key.
- A signed receipt binds evidence and model responses, but a dishonest authorized signer or weak model can still score inaccurately; human review and evaluation calibration remain mandatory for production-critical aesthetics.
- Test-generated 96-point receipts are **synthetic fixtures only** and are never an artistic evaluation.
- Original V1 remote Git history diverges from this local V2 lineage; do not force-push, overwrite main, merge unrelated history blindly or call local commits remotely published.
- Per-route Lighthouse needs actual execution on all 6 pages; any score below enforced thresholds must stay BLOCKED and be fixed, not weakened.

## Open Source / Reuse / Cost Gate
Existing local Python, Playwright/axe, Lighthouse, Ollama Qwen3-VL and Matrix free-plan GPT-OSS/OpenCode were reused, with no new paid APIs, subscriptions, model purchases or cloud deployments. cryptography Ed25519 was already installed locally. Confirm model weights, dependency versions and redistribution licenses before packaging a new install; live production licensing has not been newly certified. For local vision, test smaller existing open-weight models as a diagnostic fallback but do not replace the competent independent artistic jury with a weaker fake score.

## Next certification gates
1. Obtain genuine full-screen all-route mobile+desktop artistic evidence; use a viable authorized zero-cost reviewer with sufficient resources; truthfully report sub-95 results.
2. Deploy distinct protected reviewer principal/trust registry with secret separation; rerun forged, replay, data-tamper, per-page evidence and concurrent-job tests against actual service boundary.
3. Run all-route real Lighthouse, fix actual failed pages, and certify V2 orchestrator crash recovery, throttling and restart on isolated brand-neutral and Andaz fixtures.
4. Validate preview adapter against actual free preview only after all gates pass; add policy controls to every authorized deployment route. Keep production owner approval external.
5. Reconcile remote source without force, open a review PR and publish/acknowledge Master Stack event. Preserve default branch/production until explicit approval.

## Latest additional verified receipt
- New per-route Lighthouse on actual `engine-smoke.html`: mobile performance 94 / accessibility 100 / best practices 96; desktop performance 100 / accessibility 100 / best practices 96, on 2026-11-10. This is **1 of 6 routes** covered. Score variance from previous run is real and must not be masked.
- New secured reviewer + existing certification unit suites: **20/20 PASS**; unchanged core/RAG suites **34/34 PASS**, total **54/54**. These are **test cases**, not visual judgment.
- CLI reviewer with real screenshots: original actual HTTP 400 was `2239 tokens exceeds available context size (2048)`; after raising to 4096, the actual model call timed out at 100 seconds. No raw artistic result or externally attested score exists.
- GitHub source is a *shallow, unrelated/divergent local lineage* from fetched remote `main` at `8c074046815b238299eb0982ee0fa6ab149582aa`, no common ancestor resolved; therefore this snapshot must remain review-only until safe GitHub reconciliation. Dell `gh auth` was not logged in.
- No deploy command has succeeded; preview and release stay blocked. No production changes.
