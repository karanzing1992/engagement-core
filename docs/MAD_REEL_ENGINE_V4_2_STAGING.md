# MAD Reel Engine V4.2 — Multimodel Synthetic Technical Certification

**Date:** 02 Nov 2026 (Asia/Kolkata)  
**Status:** **Synthetic multimodel chain PASS**; **real-source creative production NOT CERTIFIED**.  
**Latest usable real-footage private preview:** [V4.1](MAD_REEL_ENGINE_V4_1_LATEST.md).

## Verified chain

A dedicated ephemeral GitHub Actions job executed:

1. **Google Gemini 3.6 Flash (live vision)** — interpreted **five generated synthetic JPEG drawings**. Authenticated model-metadata preflight for **Gemini 3.8 Flash** also succeeded, but 3.8 generation returned **503/timeout**. The fallback to 3.6 worked.
2. **Groq GPT-OSS 120B (live)** — used these visual observations plus verified synthetic-frame facts and Moksha brand style constraints to produce three different storyboards.
3. **Groq GPT-OSS 20B (live)** — returned allowlisted pace/transition selections. The compiler retains fixed source timecodes, cannot use shell code from the model, and only permits cut transitions.
4. **FFmpeg** — exported **three synthetic 360×640 H.264 videos**, passed FFprobe and full FFmpeg decode checks.

**PASS evidence:** [GitHub Actions run #3](https://github.com/karanzing1992/engagement-core/actions/runs/41364125827) — [test videos and receipts](https://github.com/karanzing1992/engagement-core/actions/runs/41364125827/artifacts/13106073378).  
**PR #96:** https://github.com/karanzing1992/engagement-core/pull/96 (merged).  
**Credentials:** `GEMINI_API_KEY` and `GROQ_API_KEY` in GitHub Actions Secrets, never committed.  
**Actual Gemini model used:** `gemini-3.6-flash`; do **not** state that 3.8 vision generation passed.

### Synthetic MP4 checksums

- A: `bb83dc00b6dd346f0b2f869dc10714c0a3e483ad72d15900ccbc12b0c0006b63`
- B: `336209cf599936c64b709a77b6bbce022d2df317f3c75fef08b8c86c27f48dc6`
- C: `b24944c25296a9f0539db700bd9f78af8433911ed5582d2985de5dd8b2aa8ea9`

## What remains a hard HOLD

**No real Moksha, Arambol vlog or third-party footage was sent to Gemini or posted.** All API input frames were self-generated synthetic test drawings. The synthetic films are *not* attractive finished marketing Reels and cannot prove authentic artistic quality. No FilmCraft MCP rendering occurred for these V4.2 outputs; the established V4 FilmCraft synthetic pilot is a separate receipt.

Not yet certified: real-footage privacy/consent/rights, automated video timecoding at scale, realistic source motion editing, production-grade 1080×1920 Reel quality, soundtrack and captions, creative independent review, owner sign-off, single MAD Manager orchestration/queue, private artifact storage, social publishing, repeatability/cost safeguards. Google AI Studio account billing status not inspected; check it remains free. Google's free tier can use submitted content for product improvement.

**Version policy:** V4.2 is a **synthetic technical milestone**, not an owner-approved public or creative-production release. Retain Reel Engine V4.1 as latest usable private Reel preview for source footage. Preserve historic V4/Groq/FilmCraft tests. Never supersede Moksha M3 or M4 publication gates through this technical test alone.

## Implementation

- [Gemini adapter](../experiments/reel-engine-v4_2/gemini_adapter.py): explicit permission gates for externally uploaded frames.
- [Groq creative director](../experiments/reel-engine-v4_2/creative_director.py): verified source-manifest contract and allowlisted EDL.
- [Synthetic-only E2E test](../experiments/reel-engine-v4_2/synthetic_multimodel.py): generates its own five scenes; will not read your media.
- [Certification workflow](../.github/workflows/reel-engine-v42-multimodel-cert.yml): manual runs on `main` and synthetic test output artifact.
- [Gemini metadata authentication workflow](../.github/workflows/reel-engine-v42-gemini-connection.yml).

Next stage: use **approved rights-cleared source footage**, validate the timecoded shot manifest against actual frames, implement private intake and FilmCraft/FFmpeg edit execution, review three realistic 1080×1920 drafts and run independent visual/rights/audio QA. Production publication requires separate authorization.

**Rollback:** Disable the scoped V4.2 certification workflow/adapter. Do not change V4.1, MAD Manager, WordPress, Mac thermal/Firefox controls, or user secrets.