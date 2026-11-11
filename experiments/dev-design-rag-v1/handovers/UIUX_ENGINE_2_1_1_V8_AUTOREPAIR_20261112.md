# Generic Design RAG 2.1.0 × UI/UX Engine 2.1.1: Andaz V8 autonomous QA repair

Date: 2026-11-12. Isolated engineering candidate, **no website production release**.

## Root causes verified on real Andaz V8 autonomous output

- Writer `engine/agent.py` previously sent only first 1,800 chars of the multi-layer RAG packet. The authoritative Andaz phone was beyond that limit. First model generated a dummy WhatsApp number and unsupported room attributes.
- Browser QA found serious contrast failures at 320/390/768/1440. Engine stopped without evidence-based correction. The UI exhibited ~0.592 mobile cumulative layout shift; Lighthouse mobile performance 74, below required 90.
- Lazy images were inconsistently treated as broken by Chromium QA because some were not loaded at inspection time.

## V2.1.1 changes

- `brand_guard.py`: 1,800-char concise project-first, source-hash-bound writer context with canonical Andaz phone, logo and real image. HTML semantic, source-image, WhatsApp, unsupported-claim and internal-link checks reject noncompliant AI outputs **before implementation PASS**. Rejects generic contamination; use project scope.
- `qa-site.cjs`: include actual axe offending selectors and summaries; settle lazy images before checking them.
- `qa_repair.py`: limited and reversible color-contrast CSS correction only from genuine matching-source, full 4-viewport axe evidence. Preserves pre-repair source and raw QA receipt; max two attempts, no relaxation of QA threshold.
- `performance_repair.py`: bounded source-hash-bound layout-shift correction only after genuinely failed Lighthouse performance and numeric CLS evidence. Adds original width and height attributes to verified local image assets. Preserves old HTML and raw Lighthouse receipt. Browser QA and Lighthouse rerun.
- `orchestrator.py`: opt-in `--auto-repair`, bounded repair with provenance and replay protection. Unsupported defects fail closed.
- `core.py`: 2.1.1 understands existing 2.0.0/2.1.0 workspaces and checks repair provenance chain for 2.1.1 before preview gates. Independent reviewer, 95/100 and owner release gates unchanged.

## Test receipts

- Fresh isolated source regression suite **84/84 PASS**: 34 knowledge, 9 certification, 13 security, 4 orchestration, 14 Gemini-bridge, and 10 new auto-repair tests.
- Real Chrome/axe experiment: one contrast patch converted all four V8 viewport results from FAIL to PASS, zero axe violations (320/390/768/1440).
- Real Lighthouse after image-dimension repair and lazy-image QA settlement: mobile performance **98/100**, desktop **100/100**, accessibility **100/100**, best practices **96/100**, CLS **0**. SEO **58/100**, isolated noindex preview (not a production SEO certificate).
- Technical QA and Lighthouse of **one fixture page only**; this is not an independently assessed full five-route V8 website or artistic certificate.
- Original V2.1.0 release on Dell remains a rollback point. No Gemini credential moved onto Dell, no PR merge, no website deployment.

## Remaining gates

Production-grade source review, one fresh true end-to-end V8 writer iteration under 2.1.1, all five public route redesigns + technical smoke where applicable, genuine private Gemini review and separate independent signed ≥95/100 artistic certification, preview approval and owner production authorization.
