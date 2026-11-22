# Shared Art Director — Dell isolated V1.1 hardened evidence
**Date:** 2026-11-11 IST  
**State:** Engineering VERIFIED; full Gemini 12-image visual inference and independent ≥95/100 artistic attestation BLOCKED; no release.

## Code and evidence
- Draft PR #268, existing `feat/gemini-vision-art-cert-isolated-20261111`, head source after hardening `fd367f2c8f5d408a38ab1deb298298a78dba791d`. Branch unmerged; this checkpoint is documentary, not a promotion.
- `vision_single_dell_adapter.py`, mirrored from isolated Dell `vision_single.py`: SHA-256 `11e367b04b8a03d9d21560c62e4583092f9c07a7296426b169f318bb5c0a6201`. Source-tree hash, exact browser QA receipt and twelve SHA-verified screenshots required; reject cross-project packet, symlink site/input/packet, unsafe output destination, non-allowlisted API endpoint/model, unverified provider response. One compressed image per request; no model approval/scoring.
- `test_vision_single_dell.py`, mirrored Dell test SHA-256 `cc08235c1f1a5ca35a712ed875cb589d21141f48bbd9832659725c7e8fc9f663`; **37/37 local advisory suite tests PASS**, **15 new**. Tests require the existing Dell-local fixture and must not be described as GitHub CI tests. All 60/60 original Generic Design RAG V2 tests separately re-ran PASS (34 RAG, 9 certification, 13 security, 4 recovery). Original engine source untouched.
- Exactly **12/12 actual Dell isolated fixture screenshot hashes** (six HTML pages × 390/1440) verified: index, rooms, experiences, explore, contact, technical engine-smoke. These are not the same public homepage screenshot used for the live API probe.
- **12/12 existing Nov 10 genuine Chromium Lighthouse reports** per-route/mobile/desktop: underlying report SHA256 and categories revalidated Nov 11; performance ≥90, accessibility ≥95, best practices ≥90. These are *revalidations* of prior full audits on an unchanged site, not fresh audit runs.
- Isolated Dell latest checkpoint `evidence/SHARED_ART_DIRECTOR_V1_1_CHECKPOINT.json` SHA-256 `b6bbe8f1912e73a2eb82b0476c1b4d9b9ee4fe9fed657cf395bcbaa74dfc02fc`. Does not contain credentials or image files.

## Real Gemini probe and hard gate
- Original evidence: [Actions #42891765472](https://github.com/karanzing1992/engagement-core/actions/runs/42891765472). At latest source head, [Actions #42897655761](https://github.com/karanzing1992/engagement-core/actions/runs/42897655761) also passed authenticated model discovery `gemini-3.5-flash-lite` and **two distinct real public homepage** mobile/desktop reviews (model text 1712/1556 characters). The latest run is further evidence of working secret-safe GitHub Actions live vision transport, not 12-route scoring.
- The Dell 12-image *genuine Gemini* attempt produced `GEMINI_KEY_NOT_IN_DELL_BOUNDARY`; GitHub Actions secret was NOT extracted, copied or logged. A mocked 12-call unit test proves request format and hash contracts only.
- Owner-controlled root-level reviewer trusted Ed25519 key registry absent; no independent signing identity or real signed verdict. `artistic_score=null`, `artistic_95_certified=false`, `release_authorized=false`.
- Existing security/recovery/Lighthouse gates verified to the scope above. Do NOT equate a model's advisory opinion, passing CI or simulated cryptographic negative tests with independent artistic approval.
- No GitHub merge, production deployment, website update, preview release, OTA/booking/credential modifications, or billed service. Open-source/free-first reuse of existing Python/Pillow/Playwright/Chromium/Lighthouse and existing Gemini free-capability route.

## Master registry
[MASTER-STACK-EVENT:361] was independently submitted as verified platform event, published and read back **once** in canonical Google Master Registry. This event recorded the V1 initial 34/34 checkpoint; this V1.1 document records the subsequent 37/37 hardening. Consumer ACK remains pending; not FULLY_SYNCED. 
