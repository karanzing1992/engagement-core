# MAD Reel Engine V6 — GitHub Delivery Tracker and Developer Handover

**Initialized:** 2026-11-06 IST. **Current stage:** ARCHITECTURE DOCUMENTED, IMPLEMENTATION NOT STARTED.  
**Scope document:** [V6 Gemini Business + Groq / FilmCraft-only specification](MAD_REEL_ENGINE_V6_DESIGN_SCOPE_20261106.md).  
**Project repository:** `karanzing1992/engagement-core`. Frontend repository remains `aarondash5-star/delulutech`.  
**Instruction received:** "Document this and start V6 FilmCraft integration in Git and revert to Gemini Business and prior Gemini/Groq combination. Report after documenting; no executing."  
**Execution restriction:** This tracker and scope are documents, not implementation approval. No provider switch, workflow trigger, run, test, deployment, media upload or publication is authorized in this phase.

## 1. Frozen current checkpoints

- **Last verified owner-private technical beta:** Cloudflare Pages `reel.delulutech.in`, git `aarondash5-star/delulutech`, commit `fb70bf19b6b6f4362e3af943dbcdee90b8ca30dd`. Owner-code positive-auth full browser workflow not yet certified.
- **Live event path:** Cloudflare Workers + D1 + private KV -> GitHub Actions `.github/workflows/mad-v5-cloudflare-bridge.yml` -> signed source claim, Groq creative plan, FFmpeg render, private output; latest verified signed path [run 42000927850](https://github.com/karanzing1992/engagement-core/actions/runs/42000927850).
- **Current V5 model lock:** `experiments/reel-engine-v5/v5_config.json` has `provider_lock=groq_only`; `v5_orchestrator.py` validates the lock. V6 **must not overwrite V5 in place**.
- **Historical Gemini + Groq evidence:** `experiments/reel-engine-v4_2/gemini_adapter.py`, `creative_director.py`, `synthetic_multimodel.py`; V4.2 run [41364125827](https://github.com/karanzing1992/engagement-core/actions/runs/41364125827) (Gemini 3.6 synthetic vision, Groq 120B director, Groq 20B EDL review).
- **FilmCraft-only technical evidence:** branch `feature/mad-v5-filmcraft-only-editor-20261105`, adapter `services/reel-engine/filmcraft_v5_adapter.py`, [run 42023769206](https://github.com/karanzing1992/engagement-core/actions/runs/42023769206). No production bridge integration; human-style real-footage Dell draft had residual visual issues and no working Drive preview.
- **Open-source music provider:** `experiments/reel-engine-v5/music_provider.py` handles metadata and licensing, but its old mix path is FFmpeg-dependent. V6 must use FilmCraft native audio after license admission.
- **Private delivery gap:** Current private Vercel Blob store `moksha-reel-v5-media` in `bom1` exists and was empty at last audit. No working edited-reel Drive upload link; Cloudflare KV signed private preview works for V5 queue outputs only.

## 2. Work packages (NOT YET EXECUTED)

| ID | Priority | Planned work | Evidence required before accepted | Status |
| --- | --- | --- | --- | --- |
| V6-01 | P0 | Define immutable V6 configuration contract `gemini_plus_groq`; keep deployed V5 unchanged | Versioned config, tests for provider-role enforcement | **NOT STARTED** |
| V6-02 | P0 | Restore Gemini Business research/vision to pre-plan stage using V4.2 adapter | Authorized Gemini API/Workspace capability + privacy/cost consent preflight; timestamped grounded manifest | **NOT STARTED** |
| V6-03 | P0 | Groq 120B director and separate Groq 20B editor-plan feasibility reviewer | Separate inference receipts, JSON schemas, source/timecode checks, rejection tests | **NOT STARTED** |
| V6-04 | P0 | Turn FilmCraft branch adapter into GitHub isolated real-video queue editor with pinned binary/checksum | Zero FFmpeg/FFprobe calls, native FilmCraft edit and audio output, verified source hash | **NOT STARTED** |
| V6-05 | P0 | Per-effect compiler and actual output parity; no silent skipped effects | Every requested op -> applied/failed/deferred, output visual QA, honest UI status | **NOT STARTED** |
| V6-06 | P1 | Openverse discovery, source license evidence, FilmCraft-only music mixing | Original creator license URL, allowed commercial reuse, track/credits hash, audio output proof | **NOT STARTED** |
| V6-07 | P1 | Reuse Cloudflare event dispatch, signed OIDC, queue and private output contract | End-to-end signed job with synthetic media and failure / idempotency / retention tests | **NOT STARTED** |
| V6-08 | P1 | Authenticated private video preview and history; resolve Vercel/Drive delivery issues | Complete private upload, checksum readback, 206 range playback, access/expiry tests | **NOT STARTED** |
| V6-09 | P1 | Independent sound/picture/artistic QA with native FilmCraft frame inspection | Real rendered keyframes, title safe areas, source truth, soundtrack rights, quality report | **NOT STARTED** |
| V6-10 | P1 | Owner-private V6 beta security, accessibility, deployment and rollback certification | 320/390px positive-auth mobile UI, invalid permissions 401, version rollback, no lost D1 history | **NOT STARTED** |
| V6-11 | P2 | Optional multiuser/public beta governance | Tenant isolation, quotas, retention/erasure, commercial licenses, owner approval | **NOT STARTED** |

## 3. Planned implementation order / boundaries

- **Sprint A — contracts and authenticated provider checks:** V6-01 -> 02 -> 03. Do not send actual guest frames until rights/consent verified and the Gemini privacy/usage terms are approved. Check actual business-account API rights and quotas; Workspace subscription != developer API billing entitlement.
- **Sprint B — FilmCraft-only renderer:** V6-04 -> 05. Tests must prove a native FilmCraft operation affected the actual output. Avoid the previously observed missing 21 creative operations, clipped title, grey strip and sidebars. Retain original source audio when authorized.
- **Sprint C — licensed music and previews:** V6-06 -> 07 -> 08. No public media in GitHub artifacts, no public link to guest video without user authorization, and no unlicensed music.
- **Sprint D — release:** V6-09 -> 10. A public release requires V6-11 and separate owner authorization; do not bundle it into owner beta.

**Future developer handoff:** create an isolated V6 implementation branch **only after explicit execution authorization** and bring in V4.2 Gemini adapter and FilmCraft-only V5 experimental adapter by reviewed changes, never wholesale overwrite of production V5. Preserve the actual FilmCraft v0.16.0 binary pin/known SHA with its licensing and supply-chain review. Add cloud worker integration behind a V6-specific opt-in version flag. No paid credits. Keep an immediately reversible V5 route.

## 4. Acceptance gate matrix

| Gate | Required proof | Status |
| --- | --- | --- |
| G0 documentation / stakeholder intent | V6 scope + tracker linked from canonical engine latest | **DOCUMENTED** |
| G1 model roles | Gemini findings, Groq 120B creative, Groq 20B validator each recorded separately | **OPEN** |
| G2 source admission | Consent, source hash, private handling, actual timestamps and fact/source attribution | **OPEN** |
| G3 editor | FilmCraft-only video/audio/effects and independent output probe; no FFmpeg/FFprobe fallback | **OPEN** |
| G4 music | Verified original licensed track and FilmCraft-only mixing, or clear soundtrack block | **OPEN** |
| G5 technical | Signed event dispatch; private output with byte count/SHA-256, failure-recovery proof | **OPEN** |
| G6 artistic | No silent effect omissions; captions/graphics/grade/sound and independent human QA | **OPEN** |
| G7 owner beta | Positive-auth 320px mobile upload to private watchable preview, accepted by owner | **OPEN** |
| G8 public beta/publish | Security/tenant segregation, explicit destination/rights owner approval | **OPEN — OUT OF SCOPE** |

## 5. No-execution handover receipt

- **Repository documents only:** `docs/MAD_REEL_ENGINE_V6_DESIGN_SCOPE_20261106.md`, this tracker, and a design pointer in `docs/MAD_REEL_ENGINE_LATEST.md`.
- **No V6 implementation source exists in production.**
- **No Gemini/Groq API requests performed**, no model settings changed, no FilMcraft conversion in GitHub runner, no workflow trigger, no FFmpeg changes, no new media/job/project, no deployment, no publication.
- Status to tell owner: **“V6 documented/initialized in Git; implementation not started; V5 still running Groq-only and FFmpeg; previous Gemini+Groq combination reinstated in the V6 target architecture only.”**

## 6. V6 implementation kickoff — 2026-11-06, revised owner instruction

The owner subsequently instructed: **"Start with reel engine v6 and gemini is pro account api key."** This supersedes the earlier **no execution** restriction for isolated V6 development, NOT for changing V5 production, using chargeable inference, real guest footage, automatic publishing, or declaring certification.

**Account clarification:** Use the owner's existing Gemini Pro API key route `GEMINI_API_KEY`, not a presumption that Workspace/Business subscriptions convey API access. Model selection is from the key's live `models.list` response, Pro `generateContent` candidate first, never silently substitute Flash. API billing/privacy entitlement remains unverified until separately evidenced. Keep server-side secrets out of source/logs; no inference without the free/approved-cost gate.

**Implementation branch:** `feature/reel-engine-v6-gemini-pro-filmcraft-20261106` (not merged; not deployed).
- V6-01 **SOURCE_ONLY IMPLEMENTED, CI pending:** `experiments/reel-engine-v6/v6_config.json`, `v6_contract.py`, offline contract regression tests. Explicit `gemini_plus_groq` routing roles: Gemini Pro research, Groq 120B director, Groq 20B editor reviewer. V5 remains production default.
- V6-02 **SOURCE_ONLY PARTIAL:** `gemini_pro_preflight.py` reuses existing V4.2 Gemini key-from-environment and allowlisted HTTPS REST, offers opt-in READ-ONLY Pro model discovery with no inference/media. No claim that Pro quota or billing status is verified.
- V6-03 **CONTRACT ONLY:** distinct Groq model identities validated; live director/reviewer execution and evidence receipts not yet integrated.
- V6-04 **SOURCE_ONLY PARTIAL:** existing FilmCraft experimental adapter ported to `services/reel-engine/filmcraft_v6_adapter.py`; source SHA/consent and audio rights are checked before editor admission. Native command-accepted receipts remain visibly `output_unverified`, not `creative_complete`. GitHub signed private V6 queue/export still NOT INTEGRATED.
- V6-05 **SOURCE_ONLY PARTIAL:** immutable effect IDs and 1:1 command receipt requirements; independent output verification pending.
- V6-06–11 **OPEN:** FilmCraft music approval/mixing actual audio output, private queue, artistic and mobile positive-owner acceptance, and release remain blocked.
- `.github/workflows/mad-v6-gemini-pro-contracts.yml` introduced as isolated offline CI; optional authenticated model LISTING requires explicit manual opt-in. No keys, billed inference, real media, production workflow or customer data in these files.

**Certification status:** source implementation only pending CI readback; not a V6 render or an owner's accepted reel. **Rollback:** close branch/draft PR, leave V5 runtime unchanged. Master Registry final sync and consumer acknowledgements are pending a verified eligible default-branch change and required publication readback.

## 7. Verified V6 branch-only kickoff readback (2026-11-06 IST)

**Developed:** isolated source branch `feature/reel-engine-v6-gemini-pro-filmcraft-20261106`; [draft PR #165](https://github.com/karanzing1992/engagement-core/pull/165). Source commit at offline Dell certification: `9812d0709d7c0f7da19e186c7191eb115a6cf375`.

**Dell independently executed tests:** 13/13 offline unit tests PASS and V6 Python modules compile, job receipt ID `b397d004151e4a198e05285a900e6d8a` on online `dell-linux`; isolated temporary checkout removed. Tests cover Gemini Pro general-purpose selector, Groq model-role constraints, strict FilmCraft-only config, effect IDs, omitted-effect rejection, source rights, SHA-256 and audio license admission. No real editor process or inference attempted.

**GitHub Actions verification:** [V6 run 42104046740](https://github.com/karanzing1992/engagement-core/actions/runs/42104046740) finished **success**: source-contracts and `gemini-pro-key-metadata-probe`. Probe authenticated existing `GEMINI_API_KEY` with a GET-only models.list call, returned **7** eligible Pro generation model IDs, and selected generic-purpose `gemini-3.1-pro-preview` (not the specialized `-customtools` variant). This proves an API key can list supported models, NOT that Gemini Pro generation/vision requests are certified, billed API quota is free or subscription tier guarantees API entitlements. No media was transmitted and no inference performed. No key bytes were exposed.

**Scope/release classification:** `SOURCE_ONLY_BRANCH_TESTED`; LIVE V5 unmodified. **Do not merge or promote V6 from a metadata preflight.** Next technical gate: implement independent full-model invocation and source-grounded observation on fully synthetic approved inputs with cost/privacy checks, then signed GitHub FilmCraft export with meaningful independently inspected output effects. Follow with licensed audio and user-private preview; real guest footage only after rights/consent.

**Master Stack delivery:** branch-only change tracked in PR #165. Route A registry publication requires a verified eligible default-branch change and actual Google Doc readback; separate consumers NOT ACKNOWLEDGED. Do not assert `FULLY_SYNCED` for this draft PR.
