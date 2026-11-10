# Shared Art Director × Design RAG V2 — Gemini Vision Handover
**Date:** 2026-11-11 IST  
**Status:** Isolated Gemini vision review proven on real public Andaz mobile + desktop screenshots; full artistic certification NOT granted.  
**Authoritative source:** `karanzing1992/engagement-core` draft [PR #268](https://github.com/karanzing1992/engagement-core/pull/268), branch `feat/gemini-vision-art-cert-isolated-20261111`.  
**Latest successful reviewed source commit:** `3406909c10ba407682bb71b498ec0a8eb293dce2`.  

## Goals and non-negotiable controls
- Reuse free/authorized AI model infrastructure and existing Git Art Director/creative-direction patterns under Generic Design RAG V2's project-scoped brand/reference governance.
- Use actual browser screenshot evidence; keep project, page, viewport, job, screenshot, source and RAG hashes bound to reviews.
- Prevent self-approval and fabricated scores; independent artistic certification requires independently trusted reviewer/signer, genuine visual evaluation and min **≥95/100 across all required routes/viewports**. Do not release if any component fails.
- No public publishing, production mutation, paid-tier change, GitHub merge, cross-project credential exposure, or bypass of existing game/Design RAG tests without explicit owner approval.

## Cross-repository source findings
1. `KaranZi/shaadi-aunty-dodge`, Git M7/M8 agent: bounded AI task selection, model-backed planning, replay/idempotency and engineering gates; this is **not** already a certified screenshot Art Director. Isolated Git worktree was deployed and 68/68 Python tests passed; full gameplay suite did not complete. Game PR #451, `feat/m71-artistic-foundation-20261111`, contains visual foundation work, not independent ≥95 approval.
2. `karanzing1992/engagement-core`, `experiments/reel-engine-v4_2/creative_director.py`: structured Groq GPT-OSS creative-direction pattern; media-domain specific, not direct screenshot evaluation.
3. `aarondash5-star/business-house-matrix`, visual-first-yard V2: deterministic screenshot pixel/geometry comparison and art-quality governance contracts. Pixel similarity must not be presented as artistic merit.
4. Generic Design RAG V2 isolated Dell engine: evidence binding, browser/Lighthouse coverage and Ed25519 attestation validation. Previous status 60/60 engineering tests; 12/12 historical Lighthouse checks. Genuine reviewer inference and trusted signing registry remained blocked. Preserve these tests and original engine; no production modification.

## Dell shared interface
Isolated local folder:
`/var/lib/generic-linux-automator-exec/.local/share/isolated-cert/shared-art-director-v0-20261111/`

Contents:
- `creative_contract.py`: project-scoped RAG packet SHA256, screenshot SHA256 and route/mobile-desktop pair admission; structured advisory findings; no scores or release approvals.
- `vendor/visual_yard_metrics.py`: reused deterministic visual metrics only, not artistic scoring.
- `gemini_vision_advisory.py`: standalone Gemini vision adapter and response validation.
- `tests/test_contract.py`, `tests/test_gemini.py`: 22/22 isolated contract and mocked API tests PASS at last recorded execution.
- `evidence/actual-screenshot-binding.json`: SHA256-verified 12 real fixture screenshots across 6 routes × mobile/desktop; these are **not** the same as the later successful GitHub two-viewport public-site Gemini critique.
- `evidence/GEMINI_38_ARTISTIC_CERT_GATE_20261111.json`: earlier blocked gate evidence, before credential route repair.
- No independent reviewer trusted registry at `/etc/moksha-uiux-v2/trusted-reviewers.json`; not certified or deployed.

## Credential discovery and safe reuse
Dell and Mac interactive environments did not expose `GEMINI_API_KEY`. Root-level Dell searches did not find the expected MAD local secret file. Do not copy or expose secrets.
Existing `karanzing1992/engagement-core` GitHub Actions V7 workflow `.github/workflows/mad-v6-kv-filmcraft.yml` already references `secrets.GEMINI_API_KEY`, and historical V7 material records owner free-tier attestation (not an independent billing verification).
Instead of copying the key to Dell, **isolated same-repository owner-only PR GitHub Actions** securely references `secrets.GEMINI_API_KEY` with `contents: read`, no deployment grants, no private media artifacts, fixed public URL `https://andazgoa.com/`. This is an authenticated GitHub Actions secret, not a Dell-local secret.

## Draft PR #268: technical debug timeline
PR: https://github.com/karanzing1992/engagement-core/pull/268

- Run [#42888365999](https://github.com/karanzing1992/engagement-core/actions/runs/42888365999): live Gemini request, HTTP 503.
- Run [#42888712441](https://github.com/karanzing1992/engagement-core/actions/runs/42888712441): HTTP/read timeout.
- Run [#42889091609](https://github.com/karanzing1992/engagement-core/actions/runs/42889091609): authenticated model discovery; `gemini-2.5-flash` inference 404.
- Run [#42889427679](https://github.com/karanzing1992/engagement-core/actions/runs/42889427679): `gemini-3.6-flash` 503 followed by unusable output.
- Run [#42889726286](https://github.com/karanzing1992/engagement-core/actions/runs/42889726286): `gemini-3.6-flash` 503 and `gemini-3.8-flash` timeout.
- Run [#42890827804](https://github.com/karanzing1992/engagement-core/actions/runs/42890827804): **PASS** with `gemini-3.5-flash-lite`; authenticated discovery, genuine text response, synthetic image recognized correctly. No artistic approval.
- Run [#42891089509](https://github.com/karanzing1992/engagement-core/actions/runs/42891089509): original dual-image structured-JSON review still returns 503 on Flash-Lite.
- Run [#42891410543](https://github.com/karanzing1992/engagement-core/actions/runs/42891410543): **PASS** on one real public Andaz screenshot with short plain-text prompt; real screenshot vision confirmed.
- Run [#42891765472](https://github.com/karanzing1992/engagement-core/actions/runs/42891765472): **PASS**. Two separate short plain-text Gemini Flash-Lite calls on actual public Andaz 390px mobile and 1440px desktop captures. Mobile response **1,664 chars**, desktop **1,520 chars**; both genuine, with viewport screenshot hashes and response hashes. This was a standalone public-homepage review, **not** all six routes nor an attested 95/100 score.

**Observed failure mode:** combined two-image + forced JSON/output request proved unreliable on this provider/model route. Splitting individual compressed screenshots with bounded plain-text critique succeeded. This does **not** prove which single parameter caused the earlier 503. Do not claim free quota/availability guaranteed.

## Verified real image critique findings (model opinion only)
- Mobile: competing CTA priorities, awkward feature-list line breaks, tight paragraph leading.
- Desktop: muted body-text contrast, cramped secondary features, overlay labels insufficiently separated from illustration.
Treat these as unvalidated design recommendations for RAG-guided iterative improvement, not objective artistic measurements.

## GitHub evidence
- Latest passing source: `3406909c10ba407682bb71b498ec0a8eb293dce2`.
- Run #42891765472 uploaded non-image JSON artifact `andaz-gemini-public-vision-42891765472`, artifact ID `13797688940`, with a one-day retention (downloaded into this conversation as `andaz-gemini-vision-evidence-20261111.zip`).
- Detailed checkpoint comments exist on PR #268 (one for fail-closed attempts and one for subsequent successful split-review fix).
- Files on PR include `.github/workflows/andaz-gemini-vision-isolated-20261111.yml`, `experiments/gemini-vision-isolated-20261111/review_public_site.py`, `diagnose_gemini.py`.
- No GitHub merge, deployment, key extraction, private screenshot publication or production change. PR remains draft.

## Certification distinction
**PASS:** Existing GitHub secret binding; API authentication; model discovery; proven text and synthetic-image inference; genuine single public screenshot vision; genuine two-viewport public homepage critique, hashes and safe receipt; isolated tests.

**NOT CERTIFIED:** Six-route/12-viewport production-grade visual review, robust structured critique schema, calibrated artistic rubric ≥95/100, independent reviewer/signer with root-trusted Ed25519 registry, tamper/replay tests of real signed output, complete autonomous iterative improve→review→recover lifecycle, full current Lighthouse/accessibility/functional/security QA, fail-closed release integration. Owner must separately approve any production release.

**Important:** A Gemini Art Director's own subjective model score or positive critique may not independently certify the artwork it helps generate.

## Required next sprint
1. Validate artifact readback, screenshot hashes and actual review quality. Preserve raw model responses in access-controlled evidence, not public PR artifacts.
2. Port the proven `gemini-3.5-flash-lite` one-image-at-a-time pattern into the isolated Dell Shared Art Director, using the existing authorized GitHub Actions credential boundary. Keep public-site screenshot tests separate from Dell's isolated six-route fixture.
3. Expand to all six routes × mobile/desktop, with per-image fallback and bounded concurrency; record exact build/route/RAG/source hashes and failure receipts.
4. Establish calibrated rubric, independent reviewer identity and root-controlled signer registry. Distinguish advisory generation from independent scoring/attestation. Validate reviewer independence, signature, replay, tamper and calibration negative cases.
5. Run genuine improvement loops and certify every gate; preserve original passing engineering tests, backout plan and source provenance.
6. Open/review a source PR for actual reusable engine integration, then submit verified material source changes to Moksha Master Stack through the authorized registry protocol. Do not claim registry published until verified readback and consumer ACK.

## One-line continuation prompt
Continue Shared Art Director × Generic Design RAG V2 from engagement-core draft PR #268 and the handover `experiments/gemini-vision-isolated-20261111/SHARED_ART_DIRECTOR_GEMINI_VISION_HANDOVER_20261111.md`: preserve successful Gemini 3.5 Flash-Lite split-screen review (Actions #42891765472), securely reuse existing GitHub Actions key, integrate into isolated Dell RAG, verify all six routes × mobile/desktop, independently attest genuine ≥95/100 artistic scoring, run security/recovery/Lighthouse gates, fail closed on deficiencies, and document verified source and Master Registry results without touching production or revealing secrets.
