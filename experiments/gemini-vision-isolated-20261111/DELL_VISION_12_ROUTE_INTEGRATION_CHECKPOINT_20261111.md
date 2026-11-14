# Shared Art Director × Generic Design RAG V2 — isolated Dell checkpoint
Date: 2026-11-11 IST
Status: ENGINEERING PASS; INDEPENDENT ARTISTIC CERTIFICATION BLOCKED; NO RELEASE.

## Source and provenance
- Parent source: `karanzing1992/engagement-core` draft PR #268, retained unmerged.
- Prior genuine public-site probe: GitHub Actions #42891765472; `gemini-3.5-flash-lite` independently responded to one real mobile and one real desktop homepage screenshot using **one-image-at-a-time** requests. This is TWO public homepage captures, NOT 12 isolated route reviews or a 95 score.
- New isolated Dell adapter: `vision_single_dell_adapter.py` in this PR, identical to local `shared-art-director-v0-20261111/vision_single.py` (SHA-256: `check recorded local receipt for exact source hash`); uses model metadata allowlist, a single image per generateContent request, tight prompt/size bounds, 503 retry, verified fixture screenshot bytes, and no signing or self-approval.
- Dell-only negative tests: `test_vision_single_dell.py`. The fixture paths are intentionally Dell-local; never run this file as an unqualified public CI test without providing the isolated fixture. No private screenshots/brand assets are committed here.

## Fresh Dell execution
- Adapter + prior Shared Art Director tests: **34/34 PASS**, including 12 new single-image and boundary checks.
- Existing Generic Design RAG V2 worktree commit `2de2b388d3291f850c6de23ce68a6f45c4ee2f2f`: **60/60 PASS** (34 RAG/knowledge; 9 certification; 13 Ed25519/security; 4 orchestration/recovery).
- Six fixture pages × 390px/1440px = **12/12 real screenshot files hash-checked**, against original browser-QA receipt. Routes: `index.html`, `rooms.html`, `experiences.html`, `explore.html`, `contact.html`, `engine-smoke.html`. The last route is a technical test page, NOT a sixth public-facing marketing page.
- Original Nov 10 genuine Chromium Lighthouse audits: **12/12 raw report SHA-256 and reported category scores revalidated** on Nov 11. Each meets established floors: performance ≥90, accessibility ≥95, best-practices ≥90. This is report verification, NOT fresh audits at new build revision; the isolated site SHA is unchanged.
- Local checkpoint: `evidence/SHARED_ART_DIRECTOR_V1_CHECKPOINT.json` SHA-256 `c241351453973e0e7992ce58451373ddc00ae8070c34ef93745f3aeb9b21f6c1`.

## Hard stops — fail closed
1. **Live Gemini on 12 Dell-local captures:** BLOCKED `GEMINI_KEY_NOT_IN_DELL_BOUNDARY`. The existing secret is GitHub Actions-owned; do not copy it into an interactive shell, logs, code, PR artifact, or chat. Unit mocks do NOT count as true model inference.
2. **Independent signing:** BLOCKED; root-owned `/etc/moksha-uiux-v2/trusted-reviewers.json` absent. Existing cryptographic tests use synthetic signer fixtures only. No separate privileged reviewer service was established.
3. **Artistic ≥95/100:** NOT MEASURED or SIGNED. `artistic_score=null`, `artistic_95_certified=false`, `release_authorized=false`. No arbitrary score, release bypass, or model self-approval.
4. **Autonomous design revisions / actual preview / production:** not executed. Existing original engine/production unaffected.

## Next controlled step
Provide an authorized ephemeral reviewer execution boundary that can access the exact Dell build and existing GitHub-held Gemini secret without artifact or persistent secret disclosure; independently score calibrated full-page per-route visual evidence and sign using an owner-provisioned separate Ed25519 review identity. Verify project/job/build/RAG/screenshot/QC hashes, raw model outputs, tamper/replay/score-calibration negatives, and a 12/12 genuine ≥95 threshold. If ANY gate fails, revise the design and rerun; do not approve the preview or production.

## Open-source / reuse / cost gate
Reused in-place Python stdlib, Pillow, Playwright screenshots, Chromium Lighthouse, the existing RAG V2 governance/Ed25519 attestation implementation and the existing authorized free-tier Gemini Actions probe. No new paid model, package, worker, runner subscription, deployment or production change; no private imagery or credentials in this PR.
