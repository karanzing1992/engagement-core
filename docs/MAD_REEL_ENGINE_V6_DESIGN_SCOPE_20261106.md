# MAD Reel Engine V6 — Approved Architecture and FilmCraft Integration Scope

**Documented:** 2026-11-06 (Asia/Kolkata)  
**Status:** **OWNER-APPROVED TARGET DESIGN / DOCUMENTATION ONLY — NOT IMPLEMENTED, DEPLOYED, OR CERTIFIED.**  
**Scope:** Moksha-first, reusable across registered ventures with separate brand/rights configuration.  
**Owner directive:** Restore the earlier **Gemini Business + Groq multi-model combination**; **FilmCraft is the only video editor, effects engine, audio mixer and exporter**; preserve open-licensed music discovery, private storage, project history and event-driven Cloudflare → GitHub orchestration. No FFmpeg/FFprobe fallback.  
**Change control:** This Git commit is planning/documentation only. Do not enable V6, edit V5 production settings, invoke AI models, render, upload media, deploy, publish, change credentials or incur charges merely by reading this document.

## 1. Source-of-truth and current V5 audit

This document supersedes V5 **as the intended next architecture**, but **does not change the deployed V5 runtime or its existing technical beta**. Historic V4/V4.1/V4.2/V5 receipts remain immutable.

| Layer | Current verified state (pre-V6) | V6 design decision |
| --- | --- | --- |
| Owner mobile/desktop PWA | Cloudflare Pages `delulutech-ai-reel-engine-v1` at https://reel.delulutech.in, source private `aarondash5-star/delulutech`, production branch `feature/ai-reel-engine-v1-nextchat-20261104`; beta commit `fb70bf19b6b6f4362e3af943dbcdee90b8ca30dd` | Retain the standalone Projects / Studio / Renders / Settings PWA; extend only as needed |
| Frontend identity and projects | Cloudflare Workers `delulutech-ai-reel-api-v1` and `delulutech-ai-reel-projects-v1`, hashed owner-code secret, D1 project/message/version records | Preserve authenticated owner access, audit history, project/tenant isolation; don't fabricate positive-auth owner QA |
| Job queue and dispatch | D1 + encrypted `MAD_GITHUB_ACTIONS_DISPATCH_TOKEN`; Cloudflare workflow dispatch HTTP 204 and signed OIDC GitHub claim certified; scheduled recovery watchdog | Keep immediate event-driven wake and bounded recovery, idempotency, lease and retry safeguards |
| Real-media renderer | GitHub Actions `karanzing1992/engagement-core` `main` production workflow `.github/workflows/mad-v5-cloudflare-bridge.yml`, currently **FFmpeg / FFprobe** | Replace execution end-to-end with verified FilmCraft CLI/MCP, no hidden FFmpeg transcode, fallback or audio mix |
| Production models | `experiments/reel-engine-v5/v5_config.json` locks to **Groq only** | Restore Gemini-led analysis/researched scope followed by Groq 120B creative direction and Groq 20B constrained execution review |
| FilmCraft | Separate V6 predecessor adapter on branch `feature/mad-v5-filmcraft-only-editor-20261105`; Dell actual-footage private export; GitHub synthetic-only workflow #42023769206 PASS | Reuse and harden adapter; integrate into GitHub signed private queue; do not claim that prior narrow demo proves all effects |
| Music | `experiments/reel-engine-v5/music_provider.py` searches Openverse/licensing; current production runner bypasses it, uses source audio | License research/selection, source verification and filmcraft-native soundtrack timing/mix; never synthesize substitute music |
| Storage | Cloudflare `MEDIA_KV` private source/output chunks; Vercel Blob store `moksha-reel-v5-media` (Mumbai `bom1`, private) exists but has **0 objects**; Google Drive holds original footage only | Preserve authenticated previews/status, add verified private output delivery and retention with signed access; do not treat store existence as upload |
| Review and release | Technical decode checks passed in prior workflow; unexecuted creative effects and unverified end-user positive-auth UI remain gaps | Explicit per-effect receipt, independent artistic/audio/rights review, owner approval; no auto publication |

**Historic multimodel evidence:** [V4.2 synthetic multimodel certification](MAD_REEL_ENGINE_V4_2_STAGING.md), GitHub Actions [run 41364125827](https://github.com/karanzing1992/engagement-core/actions/runs/41364125827). This established Gemini 3.6 Flash synthetic visual analysis → Groq GPT-OSS 120B storyboard → Groq GPT-OSS 20B bounded EDL planning. Gemini 3.8 metadata preflight passed but generation timed out / 503: **do not claim Gemini 3.8 inference was proven.** V4.2 ended with FFmpeg synthetic output; the V6 owner decision deliberately changes the editor.

**FilmCraft evidence:** [Synthetic GitHub FilmCraft-only run 42023769206](https://github.com/karanzing1992/engagement-core/actions/runs/42023769206); independent Dell FilmCraft v0.16.0 real-source 20-second private draft, 720×1280, original audio, no FFmpeg calls. Manual output checksum `7920ae180bf7e727884197ddeb164a05a10ec22e615442b31604cfdcc7f224d1`; last file location `/home/karan/Videos/Moksha-FilmCraft-Edited-20sec.mp4`. Initial render had clipping/pillarboxing; subsequent QA still found visual defects. **Do not call this visually certified or Drive-uploaded.**

## 2. V6 intended orchestration — one canonical job

```text
Mobile/Desktop owner: human prompt, project, uploaded source and permissions
    |
Cloudflare Pages PWA -> signed authenticated Owner/Projects API
    | Cloudflare D1: immutable project / source manifest / job state
    | Cloudflare private source, media access and signed dispatch
    v
GitHub Actions: signed OIDC isolated per-job runner (no public source artifact)
    |
    1. Ingest/probe consented source; restricted working directory, metadata and safe source manifest
    2. Gemini Business-backed research / vision / source understanding
       -> timestamped OBSERVATIONS, NOT invented footage, visual shot log, candidate story scope
    3. Groq GPT-OSS 120B creative director
       -> hooks, emotional arc, storyboards, shot order, typography, audio mood
    4. Groq GPT-OSS 20B technical reviewer / smaller-model validator
       -> validate timestamps, feasible FilmCraft command IDs, parameters and rights constraints
    5. Openverse + primary creator provenance checks
       -> licensed source track + credit and legal-rights evidence (or explicit music hold)
    6. Deterministic EDL -> FilmCraft-only MCP/CLI (pinned and checksum verified)
       -> actual timeline/effects/keyframes/titles/transitions/audio mixing
    7. FilmCraft native export + native probe + independent technical/artistic/rights checks
       -> strict per-operation APPLIED / FAILED / DEFERRED receipt and private MP4
    |
Authenticated private Blob/KV (whichever is actually integrated and certified)
    -> D1 state + persistent preview/history + owner approval
    -> authorized destination-specific publishing only after a separate approval
```

**Non-negotiable boundary:** Gemini and Groq **propose and validate**; neither receives arbitrary shell access nor directly executes editing. Only the deterministic FilmCraft adapter may alter the timeline. Any unsupported creative instruction is reported and either fails the creative-completeness gate or returns a clearly marked incomplete draft. A technically successful video does not imply 100% effects applied.

## 3. Roles / Gemini Business restoration

1. **Gemini — research and source intelligence first.** Restore Gemini to the initial researched-scope/vision role using the existing authorized user's **Gemini Business / Workspace context** where available. Inputs: owner brief, trusted public/local research within permissions, actual sampled frames after consent and privacy admission. Outputs: source-grounded shot observations with timestamps/confidence and a researched creative scope; no claim that the service performed research unless its tool calls are evidenced. Keep the original source and user account private.
2. **Groq GPT-OSS 120B — lead creative director.** Use Gemini's *validated* findings, brand system and natural-language brief to propose narrative, cinematic treatment, hook, shot selection, rhythm, motion typography and suitable real-recorded audio mood. Do not overconstrain artistic scope beyond factual, safety, rights and actual compute limitations.
3. **Groq GPT-OSS 20B — separate editor preflight / feasibility critic.** Review proposed operations against the discovered, pinned FilmCraft command schema, EDL source bounds, transitions, text positions, color settings and audio instructions. Reject model-created commands or unrecognized effects; do not silently omit 21 proposed operations as prior V5 did.
4. **Independent review:** compare expected and actual effects, inspect keyframes / preview frames / soundtrack / subtitles, check claims and permissions; owner is final artistic and publishing gate.

**Important Gemini Business/API entitlement distinction:** A Workspace or Google AI subscription is NOT proof of Gemini developer API capacity or cost. The previous V4.2 `GEMINI_API_KEY` GitHub secret and genuine API ability were historical, **not checked in this V6 documentation task**. Before execution, verify current owner-authorized account/credential, permitted model IDs, API usage caps, commercial data terms and privacy; fail closed if there is no approved API route. Do not create paid credentials, link billing or use unapproved paid inference. The provider policy to **plan** is `gemini_plus_groq`, replacing V5's Groq-only policy **only in a future separately approved and tested V6 change**.

**Model policy:** exact model versions must be dynamically checked against current authorized account listings rather than hard-coded from stale documentation. Historical verified roles are Gemini 3.6 Flash visual synthesis, Groq GPT-OSS 120B director and 20B editor reviewer. Gemini 3.8 was not verified to generate in V4.2. No substitution that silently changes authorized provider, terms or cost.

**Minimal research contract (to implement):**
- `research_scope`: brand/context/source facts with origin URL, retrieval date and rights terms when web research is used.
- `visual_manifest`: source SHA, source timebase, clip ID, start/end, confidence, actual-frame evidence and permitted external processing.
- `creative_plan`: narrative, cut list, FilmCraft effects as structured operations, soundtrack intent, captions and exact brand attribution.
- `edl_validation`: accepted/rejected operations, model-review reason, FilmCraft command mapping, parameter bounds, source/timebase checks.
- `execution_receipt`: FilmCraft binary version/checksum, command transcript **without secrets**, timeline/export SHA, each operation requested/applied/failure code and QA verdict.
- `license_receipt`: audio source, original creator URL, explicit reusable commercial license, permission/attribution, track hash, checker/time.
- `owner_approval`: authenticated user, preview hash, exact approved version and channels; never inferred from technical QA.

## 4. FilmCraft ONLY editing and audio policy

- FilmCraft (pinned CLI/MCP; historic verified v0.16.0) owns ALL trim, crop, fit, layers, effects, transitions, grades, text, motion, speed changes, music, fades, mixing, encoding and media probe.
- **Do not invoke FFmpeg, FFprobe, moviepy, alternative render/transcode tools, or a hidden fallback in any V6 production or QA step.** Retain historical FFmpeg files for rollback provenance only; they must not be selected by V6.
- Start from existing branch adapter `services/reel-engine/filmcraft_v5_adapter.py`; audit it before integration and validate effect parameter units. The earlier 20-second manual cut did not run full Gemini/Groq/Openverse workflow.
- FilmCraft CLI enumerating 716 commands does NOT mean all effects are certified. Implement allowlisted operations with real output assertions. Detect title clipping, missing audio, empty frames, incorrect aspect fit, omitted planned effects and incomplete stream. Permit failure / honest incomplete-draft labeling.
- No generated music. Use actual source ambience or existing music with independently verified license. If soundtrack is requested but unavailable, produce a clear blocked/awaiting-license state (never silently replace with synthetic audio).
- Maintain private source retention and redaction, sealed signed access, job TTL and signed output hash; don't put guest footage in source repos or public Actions artifacts.

## 5. Hosting allocation for V6 (reuse, not migration)

| Component | Keep / target location | Change permitted in future V6 only |
| --- | --- | --- |
| UI / project management | Existing Cloudflare Pages `reel.delulutech.in`; private frontend repo | Add truthful effect/music progress, preview and owner review, no NextChat legacy UI |
| API, identity and job scheduling | Existing two Cloudflare Workers + D1 + KV | V6 type/version fields, signed queue, model-role receipts and anti-duplicate controls |
| Multi-model API calls | GitHub Actions isolated runner, keys server-side in GitHub/authorized secret store | Gemini research adapter preflight + Groq director + Groq 20B checker; each with separately evidenced calls |
| Video editor / renderer | **FilmCraft only**, initially pinned in GitHub Actions, Dell optional non-production development/QA | Native CLI install/checksum + OIDC source claim + native MP4 export; Mac not a required runtime dependency |
| Third-party audio | Existing Openverse discovery and source-license verification code in `engagement-core` | Replace any old FFmpeg mixing path with FilmCraft-native audio; no production audio without proof |
| Final files / preview | Existing Cloudflare authenticated private KV; optionally connected Vercel private Blob `moksha-reel-v5-media` Mumbai | Integrate actual authenticated upload, readback hash, range streaming and short-lived preview URL; store existence != upload success |
| Owner delivery | Owner-specific project Studio, preview/history, optional owner-authorized private Drive | Do not claim Drive preview without verified upload + ID |
| Central registry | `engagement-core` GitHub + Moksha Master Registry | Report V6 **design kickoff only**, never 'deployed' before certification |

## 6. Required execution workstreams, dependencies and acceptance criteria (NO execution in this change)

**V6-D0 — Lock scope and governance.** Baseline this document, preserve V5 source and successful deployment receipts, map all existing credentials only by names and scopes, plan a rollback. Owner approval must precede release-changing actions.

**V6-D1 — Gemini Business / Groq re-orchestration.** Document and later verify Gemini account/API usage and privacy entitlement. Restore V4.2-style Gemini → Groq 120B → Groq 20B chain with grounded research and strict source-manifest contracts. Test each role on synthetic/owner-authorized material, failures, timeouts, quota and no paid fallback.

**V6-D2 — FilmCraft integration.** Pin binary/checksum; turn creative EDL into a real FilmCraft project; implement and validate actual shot selection, 1080×1920 framing, color, motion, transitions, typography, audio, fades and export. Regenerate render receipts from *actual executed* commands. No FFmpeg/FFprobe.

**V6-D3 — Open music flow.** Discover records, independently verify copyright/commercial use and credits, ingest private source and mix in FilmCraft. Soundtrack selection must respect editorial mood and owner rights.

**V6-D4 — GitHub event-based production bridge.** Update runner while preserving Cloudflare OIDC claim/auth, D1 queue leases, tenant isolation, retries and secret handling. Run one synthetic test and then explicitly cleared guest footage with privacy controls. Verify completed outputs and SHA in private storage.

**V6-D5 — Visual/audio QA + preview.** Automatic effect count parity (100% applied or explicit incomplete status), title safe-area, video/audio quality, correct orientation, valid soundtrack rights, 320px mobile authenticated owner status/preview, private download. Perform independent artistic review; owner sign-off.

**V6-D6 — Beta release.** Promote only with: passing CI, certified real-source end-to-end FilmCraft render, positive-auth mobile upload/render/preview, rights/consent record, rollback exercise, private-media isolation and owner approval. No public/multiuser beta until dedicated security gate passes.

**Completion is NOT declared** when a module compiles, a synthetic clip exports, Gemini/Groq returns JSON, an API token exists or a preview store is empty.

## 7. Open-source / reuse / cost gate

Reuse FilmCraft pinned CLI and project files; existing Groq integration, Gemini V4.2 adapter, Openverse provider, Cloudflare/D1/KV, GitHub Actions, Vercel private Blob only if actual authorized storage access is verified. Verify upstream FilmCraft redistributable license and compatible dependencies at integration time; maintain pin and SHA. Use free/owner-entitled quotas; separately gate actual Gemini API usage, data retention and commercial terms. **No subscriptions, paid account upgrades, billed model calls or new storage products are approved by this design document.**

## 8. QA and rollback

- **No-work / read-only design baseline now:** source documentation is the sole change; no video rendering, no API inference, no credential rotation, no workflow dispatch, no deployment, no media transfer, no publication.
- Future fail-closed regression tests: no FFmpeg/FFprobe executable calls, valid Gemini and Groq role completion, Gemini denied/timeout, unapproved external-frame consent, invalid source timecodes, absent FilmCraft effect, nonexistent/expired music license, missing output, media hash mismatch, unauthorized preview, duplicate job, stuck render, oversize file, clipping/safe-area violation.
- Keep current V5 owner-private beta intact until V6 passes and owner approves promotion. Rollback will use existing Cloudflare Pages/Worker version and GitHub commit; D1 schema migrations must be reversible and never orphan existing render history. Don't auto-deploy from planning commits.

## 9. Evidence links / successor documents

- [Current V5 status](MAD_REEL_ENGINE_LATEST.md)
- [V4.2 original Gemini / Groq multimodel chain](MAD_REEL_ENGINE_V4_2_STAGING.md)
- [V5 baseline and license gates](MAD_REEL_ENGINE_V5_BASELINE.md)
- [FilmCraft-only adapter on isolated development branch](https://github.com/karanzing1992/engagement-core/blob/feature/mad-v5-filmcraft-only-editor-20261105/services/reel-engine/filmcraft_v5_adapter.py)
- [FilmCraft-only synthetic Actions evidence](https://github.com/karanzing1992/engagement-core/actions/runs/42023769206)
- [Current owner-private beta / public release boundary](mad/MAD_V5_OWNER_PRIVATE_BETA_RELEASE_CERT_20261105.md)
- [V6 workstream tracker](MAD_REEL_ENGINE_V6_DELIVERY_TRACKER_20261106.md)
- [Official Google AI Studio access](https://ai.google.dev/gemini-api/docs/workspace), [Gemini API key setup](https://aistudio.google.com/docs/get-started), [Gemini API billing](https://ai.google.dev/gemini-api/docs/billing/)

**Authority:** Owner V6 kickoff, 2026-11-06. **No runtime change approved in this commit.**
