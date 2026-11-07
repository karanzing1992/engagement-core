# MAD Reel Engine V8 — Creative Intelligence Beta

**Status: isolated source/test beta; NOT the currently live owner UI.**
**Owner source:** `karanzing1992/engagement-core`, branch `feat/mad-v8-creative-intelligence-20261108`.
**Preserve V7:** its Cloudflare private beta, original GitHub OIDC workflow path, D1/KV, legal music admission, existing GitHub dispatch, and approval gates remain unchanged.

## Root cause addressed

V7 could produce a valid playable MP4 even when its limited editing vocabulary buried spoken audio, omitted meaningful transitions or failed its artistic brief. A successful FFmpeg decode or model approval of an *edit plan* is not evidence of a successful *finished film*. V8 introduces an auditable evidence → direction → deterministic editing compiler → decoded-output critic → independent multimodal artistic review → owner UAT pipeline.

## Module map

- `intelligence.py`: owner-intent precedence, ffprobe + source SHA, FFmpeg factual scene cuts and quiet intervals. No invented dialogue, transcript, faces or visual claims. Existing consented Gemini still-frame path can augment observations.
- `director.py`: four competing treatments with story arcs and ranked evidence, a grounded multimodal-director prompt, strict JSON schema, source-bound segments, allowlisted grades/transitions, protected full-duration source and original dialogue, separated universal/brand/feedback RAG inputs. The source-led deterministic fallback is labelled **non-AI** and never represented as creative certification.
- `models.py`: wraps the existing Groq 120B director and free Gemini Flash source analysis; bounded approved free-tier use only. The separate Gemini actual-media critic receives up to three real output frames plus three matched original/output audio excerpt pairs, **never** private public URLs. AI cannot be invoked without explicit owner-approved free-tier flags and external-media consent.
- `editor.py`: validated FFmpeg finite editing DSL. Real source-grounded grading, titles, cuts, dip-to-black, conditional dissolves, continuous original audio when required and **speech-keyed sidechain music ducking**, licensed source preflight reused from V7, decoded output SHA and duration receipts. No LLM-supplied command strings.
- `critic.py`: independent inspection of the actual completed MP4; checks full decode/hash, preserved duration, audio peaks, actual frame values at interior transitions. Marks intelligibility **unverified until actual audio review**. Reviewer output must bind to the exact MP4 SHA; no plan-only pass.
- `pipeline.py`: one private, bounded operation with optional txtai V7 retrieval, separate tenant-scoped brand directives and feedback, explicit Gemini/Groq hooks, up to two revisions, preview-only output, permanent publishing gate.
- `test_v8*.py`: actual FFmpeg AV tests plus negative consent/schema/cross-brand/rights/output-review contracts.

## Owner instruction priority

1. Explicit rights, safety and publishing constraints.
2. Preservation of owner-requested original speech and full duration.
3. Source facts/visual and audio evidence.
4. Creative direction and coherent, appropriate narrative.
5. Licensed music, effects, transitions and aesthetic experimentation.

A sound-carrying timeline may be visually subdivided, but original audio remains continuous. In the absence of speech timestamps and human review, the editor must never silently trim a sentence or claim full speech intelligibility. Silence detection is **not** speech-to-text or voice separation.

## Proposed release and certification gates

1. **Dev:** 17 synthetic tests + V7 regression tests pass locally and in independent GitHub CI.
2. **Creative E2E:** externally authenticated Gemini/Groq with existing owner-managed free keys, txtai required, rights-approved music, source video supplied with consent; sample frames and paired original/rendered audio assessed.
3. **Real-footage owner beta:** fresh copy of the original owner file; source vs delivered spoken-word checks, multiple transitions, readability and sound, 30–60 s cases; user accepts private preview.
4. **Production promotion:** explicit owner approval, isolated V8 worker/UI binding with secure login, OIDC, signed upload/download receipts, time-limited private KV outputs, rollback to unchanged V7. No automatic publishing.

## Known limits (do not claim these are complete)

- No V8 owner UI, Cloudflare worker route or new signed GitHub dispatch deployed. V7 remains the only live owner browser.
- No live owner-video artistic acceptance, licensed-music V8 production render or Gemini/Groq V8 provider call was executed by the synthetic tests. A signal in three frames or short audio excerpts does **not** prove subjective full-video artistry.
- Clip support is currently 1.2–120 s. Mixed transition styles containing dissolves and protected source audio cannot be safely processed without time-preserving retime; fail closed, not emulate success.
- Speech-aware music ducking is implemented in FFmpeg, but independent intelligibility evaluation must still sample/listen to the actual dialogue. Production speech-timing (optional Silero VAD and transcription via WhisperX) and multi-model auto-revision remain integration work.
- Brand rules/feedback are isolated input layers but long-lived encrypted owner-feedback storage and tenant authorization still need integration with existing Engagement Core identity infrastructure. No separate credential system may be introduced.
- Free and open-source reuse: owned FFmpeg V7 source/hash/rights code; existing Gemini/Groq owner-approved free-tier adapters; txtai; FFmpeg/ffprobe. No new SaaS or paid model. Optional upstream Silero VAD / WhisperX require separate dependency/license review before use.

## Reproduction (private synthetic media only)

```sh
PYTHONPATH=services/reel-engine/v8-creative:services/reel-engine/v6-kv-gateway \
python3 -m unittest discover -s services/reel-engine/v8-creative -p 'test_v8*.py' -v
```

**Rollback:** leave V8 integration disabled and keep V7 current. To abandon the candidate simply close its V8 PR/remove the separate V8 source directory/workflow on a reviewed revert; do not alter or retire V7 compatibility endpoints.

**Source vs runtime:** a PR/merge or green tests prove versioned code only; do not say V8 is public/live/creatively accepted until independent source/media/worker/beta receipts exist.
