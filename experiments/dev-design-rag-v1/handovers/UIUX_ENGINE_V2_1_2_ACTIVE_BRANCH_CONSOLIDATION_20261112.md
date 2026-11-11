# Engine 2.1.2: additive Lighthouse CLS recovery over active RAG/Engine 2.1.1

Source base: 327e346c9fd3fa3d3762881279bb39deed7a0ef4 (Dell active at inspection; owner-fact RAG and QA repair already promoted). The competing draft PR #294 is NOT merged into this source. No production website changes.

Safely carried forward 2.1.1 features: deterministic source-grounded Andaz design contract, guarded free OpenCode writer, bounded corrective new-page generation and contrast-specific immutable variant, replay control, existing signer and production release gates.

Added in 2.1.2:
1. Chromium/axe checks wait for real lazy-image completion before marking otherwise valid photos broken.
2. Failed real Lighthouse audit is bound to exact source tree SHA, QA receipt SHA, page, failed mobile/desktop mode and raw report hash; no stale or fabricated report is accepted.
3. High CLS and performance below 90 trigger one bounded intrinsic-width/height patch from genuine local image files only. Saves original HTML and raw Lighthouse, records provenance and requires brand policy validation.
4. Automatically reruns four-width Chromium/axe plus both mobile/desktop Lighthouse. Any remaining low score blocks release; no score is imputed or threshold relaxed.
5. Existing 2.0.0/2.1.0/2.1.1 workspaces remain readable. RAG version stays 2.1.1; only engine bumps to 2.1.2.

Verified fixture (isolated and not marketing-ready): Lighthouse failed at mobile performance 74, CLS 0.6068. Evidence-bound repair added dimensions for two real local images; re-ran browser QA 4/4 PASS at 320/390/768/1440 and Lighthouse mobile 96 / desktop 100, accessibility 100, best practices 96, CLS removed. SEO 58 due isolated noindex and incomplete page; not a production SEO score. The fixture was synthetically constructed from prior generated V8 with owner facts corrected, not a genuine full five-route autonomous V8 production build.

Production and preview release, genuine private screenshot Gemini independent review and signed artistic >=95 remain separately BLOCKED.
