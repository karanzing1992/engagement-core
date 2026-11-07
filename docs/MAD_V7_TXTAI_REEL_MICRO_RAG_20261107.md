# MAD Reel Engine V7 — txtai Reel Best-Practices Micro-RAG (2026-11-07)

**Status: source implementation under CI, NOT live until the exact branch SHA passes CI and signed private E2E receipt verifies RAG source IDs.** Preserve V5 and V6 production, V7 private gateway and owner release gates.

## Objective and narrow scope

The owner requested a ready-to-use open-source Micro-RAG around **Gemini → Groq 120B → Groq 20B → FFmpeg V7**, containing **only Reel filmmaking craft and production best practices**. It is not the main company memory or brand RAG, cannot retrieve customer/guest data and cannot edit footage or trigger publishing. Reuse the actual maintained NeuML txtai package, not a home-grown vector store or new Cloudflare service.

## Selected upstream

- Engine: [NeuML txtai](https://github.com/neuml/txtai) (Apache-2.0), packaged [txtai-minimal 9.11.0](https://pypi.org/project/txtai-minimal/9.11.0/) with CPU-only dependencies. **No custom BM25 code.**
- Retrieval mode: built-in txtai `keyword=True, content=True, defaults=False` (BM25 sparse keyword search plus bundled SQLite text/metadata storage). [Official config](https://neuml.github.io/txtai/embeddings/configuration/general/), [SQLite docs](https://neuml.github.io/txtai/embeddings/configuration/database/).
- **Explicit limitation:** this first micro release uses real packaged BM25 retrieval, NOT neural dense/semantic embeddings. This is deliberate for a tiny trusted corpus, low cold-start and zero remote embedding APIs. Optional semantic upgrade must be separately tested and approved.
- No local/remote generative model, Hugging Face model download, database daemon, external API key or paid cloud subscription is added.

## Curated Reel-making knowledge

43 concise original advisory chunks in `services/reel-engine/v7-micro-rag/reel_practices.json`, `version=2026-11-07.1`, with stable IDs, topic, role, source title and exact HTTPS citation.

Covered: narrative/hook, genuine footage, continuity, 9:16 composition/safe zones, cinematic pacing, transitions, color, text/accessible captions, recorded rights-cleared music, sound mixing, FFmpeg/ffprobe output QA and platform-specific portrait requirements. Sources include approved internal FFmpeg Reel skill, current V7 capability baseline, FFmpeg official references, W3C caption/contrast guidance, official YouTube Shorts documentation, and Meta-provided platform sizing guidance.

All records are static, reviewed and bounded. Source URL host allowlist, distinct citation ID, text length and role validation reject untrusted ingestion. Raw owner prompts, private video, music bytes, guest identities or model output are **never indexed**.

## Implementation

- `services/reel-engine/v7-micro-rag/txtai_reel_guidance.py`: import upstream txtai, validate fixed JSON, index 43 chunks with its real BM25/SQLite engine in the GitHub job's existing owner-private tmp dir, save, reopen in read-only query usage, retrieve at most 3 role-relevant passages under 1,750 characters each; store only source IDs and corpus SHA-256 in cloud receipt.
- `services/reel-engine/v6-kv-gateway/runner.py`: new `micro_rag` stage before model planning; enable only via `MAD_V7_TXTAI_MICRO_RAG_ENABLED=true`. Degraded retrieval returns an explicit `unavailable` provenance and existing V7 prompts, no secret/error leakage.
- `experiments/reel-engine-v6/multimodel_filmcraft_bridge.py`: each role gets its own cited advice:
  - Gemini = observed visuals, credible framing and source authenticity hints;
  - Groq 120B = cinematic narrative, hook, rhythm, typography and editing;
  - Groq 20B = strict independent creative/technical/audio/consent checks.
- Advice is explicitly lower priority than true source observations, owner instructions, consent, allowed FFmpeg operations, genuine license proof and safety checks. Retrieved text cannot add new permitted editor effects, new media sources, billing mode or publishing permission.
- Receipt field `reel_best_practices_rag` includes status, engine, retrieval method, corpus digest, version and role source IDs. No project or user information included.
- GitHub Actions private runner uses `python3` from the pinned setup-python 3.12 environment for the micro-RAG package and original V7 renderer; keeps OIDC workflow filename/identity unchanged.

## Tests and release gates

- CPU-only package install and actual native txtai build/save/load/search, not a mocked search engine.
- 32 representative role-grounded retrieval intents across core Reel topics, corpus content and source URL validation, private query exclusion, size limits, dependency-unavailable behavior, stable digest, no public artifacts.
- Existing V6+V7 private KV, signed FFmpeg renderer, audio/music licenses, model gates and QA regression remain mandatory.
- Accept beta only after signed synthetic V7 job shows `MAD_V7_REEL_MICRO_RAG_STATUS ready` and D1 private receipt with real stable source IDs, `published=false`, passing full audiovisual decode.
- Live Gemini Free tier remains **owner-attested only**; its independent API and frame consent guards remain. No social publishing.
- Fail and revert on unexpected multimodel outputs, other private data in RAG index, unexpected paid requests, missing private output or regressions. Quick rollback: set `MAD_V7_TXTAI_MICRO_RAG_ENABLED=false`, or revert release PR; V7's original creative chain runs unchanged.

## Open Source / Reuse / Cost Gate

NeuML txtai-minimal (Apache-2.0), Python stdlib, bundled SQLite, existing owner-auth GitHub Actions and Cloudflare KV, existing V7 FFmpeg; no new server or subscription. Operational cost is existing GitHub CPU time for per-job index build and Python dependency installation; test cold-start cost under real runner. Downstream OSS license notice required if packaging application; no OSS libraries shipped to user here. Dense embeddings would increase package/model footprint and are not presented as already implemented.

## Decision record

The existing Dell LiteRAG is intentionally **not** a runtime dependency: V7 must work if Dell is offline and should not ingest broader private MAD/CRM context. A separate general knowledge graph would be excessive for 43 fixed Reel practices. No third-party creative product or custom RAG platform required.

## 2026-11-07.2 — Official Meta creative guidance and AI music search (V7 private)

**Source changes in review; this section describes intended behavior, not evidence of a finished live rendering.**

- Corpus expanded from 43 to **62** original cited, bounded chunks; adds official Meta Instagram Best Practices, Meta Blueprint Reels training, Meta-maintained Instagram API Postman documentation, Instagram creation, retention and Trial Reels announcements.
- Music search workflow now has role-grounded, dedicated **txtai BM25 retrieval** for Openverse search, broad-query fallback, Wikimedia Commons metadata fallback, license/original recording evidence, AI source-ID selection, pre-cleared SHA-only use, sound mix and full-length verification. Corpus version: `2026-11-07.2`.
- Independent source refs: https://about.fb.com/news/2024/10/best-practices-education-hub-creators-instagram/ ; https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api ; https://about.fb.com/news/2023/11/new-ways-to-create-content-on-instagram/ ; https://about.fb.com/news/2020/08/introducing-instagram-reels/ ; https://metaspark.facebookblueprint.com/student/path/219746-fb-ig-reels-course ; https://about.fb.com/news/2024/12/trial-reels-try-content-non-followers-first-see-what-perfoms-best .
- `v7_music_discovery.py` calls the **existing** V5 Openverse/Commons search implementation (two concise live Openverse search terms, one official Commons fallback on empty response), filters CC0/PDM/CC BY candidates, and asks the existing Groq 120B director to select a precise allowlisted **candidate ID** as an *unverified recommendation*. No discovered bytes are fetched and no rights are self-approved.
- On the real V7 owner-private runner, reviewer-approved existing V6 private music SHA candidates remain first priority and can be mixed automatically. When the library is empty or all candidates are rejected, the runner records a metadata-only selected discovery candidate with `rights_status=DISCOVERY_ONLY_UNVERIFIED`, `used_in_render=false`, and uses source ambience. A reviewed source recording with rights evidence must still be added via V6 before actual soundtracking.
- `reel_best_practices_rag.music_search_ids` records targeted txtai source IDs; no private brief/video is stored in RAG or exposed in this receipt. Off/on switches, signed OIDC, private Cloudflare KV, existing FFmpeg post-processing, 30-minute output expiry and owner publishing gate are unchanged.
- CI contract requires real pinned txtai index build/reload and grounded retrieval, source discovery with an offline stub, poison candidate and approval bypass rejection, and **real synthetic test audio** processed through SHA approval, V6 rights admission, licensed FFmpeg mix, V7 mastering and full A/V ffprobe/decode. The disposable synthetic tone is only a test fixture, never owner music.
- Meta's documented API limits are not guarantees of publishing eligibility or improved reach. Keep mobile-safe text, actual footage and separate real listening/artistic acceptance gates.
- **Rollback:** revert this PR; retains previous 43-item corpus and original V7 approved-soundtrack selector. Public publishing stays disabled.


## 2026-11-07.3 — Owner default: automatic source-verified open-license music

**Owner instruction:** new music discovered through Openverse or Wikimedia Commons should normally be usable without manual per-track approval, unless the specific work's source, license or restrictions say otherwise.

**Implementation boundary:** Openverse aggregates third-party metadata and expressly disclaims independent license verification. Wikimedia Commons asks reusers to verify the individual file; this release honors the owner's preferred *automatic workflow*, while substituting live machine verification for manual reviewer attestation. "Automatic verification" is not a guarantee of copyright ownership. Refer to:
- https://docs.openverse.org/terms_of_service
- https://commons.wikimedia.org/wiki/Commons:Reusing_content_outside_Wikimedia/en
- https://creativecommons.org/licenses/by/4.0/deed.en

**New automatic use flow:**
1. Existing Groq V7 music curator selects candidates from existing V5 Openverse and Wikimedia Commons official search APIs; dedicated NeuML txtai BM25 music retrieval now describes the new source verification policy (corpus 2026-11-07.3).
2. Previously owner-cleared SHA256 music in private KV retains first priority.
3. If empty, the owner-private GitHub runner searches both sources. Auto-admission currently covers **original Commons audio files** with original Commons URLs, whether discovered through Wikimedia search or indexed in Openverse. Other Openverse third-party hosts (Jamendo/Freesound/etc.) remain discovery-only until host-specific original-rights verification is certified; being listed by Openverse alone is not sufficient.
4. Live MediaWiki `action=query&prop=imageinfo` independently rechecks the original file title, audio media type, current license and license URL, named creator, any explicit restrictions, canonical direct upload URL and byte length. Allow CC0 / Public Domain Mark / CC BY only; reject BY-SA, NC, ND, unsupported licenses, mismatches, warnings, missing creator or other explicit limitations. Only read `upload.wikimedia.org/wikipedia/commons/` over HTTPS; no off-host redirect, unsafe media host or arbitrary model URL.
5. Download a **max 16 MiB** recording exclusively into the job's private ephemeral directory. Validate byte count, codec, minimum edited duration and SHA256; use the existing FFmpeg renderer and V7 master. No persistent catalog promotion or generated music is needed.
6. Keep **automatic-source** evidence distinct from `human_verified` in FFmpeg, model receipt and the private Cloudflare Worker; new signed receipt gate binds SHA, checked original Commons file URL, official media URL, license, creator and Title/Author/Source/License (TASL) attribution. CC BY caption credit is carried for later owner-approved publication. Runner receives no publishing authority.
7. Preserve reviewed per-job audio override, owner auth, OIDC lease, sensitive media separation, private 30-minute preview and existing shutdown/expiry. `MAD_V7_AUTO_SOURCE_MUSIC_ENABLED=true` enables this in the signed V7 runner, and `false` reverts to the previously certified reviewed-private-library-only behavior.

**QA:** PR checks must run actual Python admission-negative tests, simulated Commons API evidence, malicious URL/redirect/licensing restrictions tests, exact media hash and verified duration tests, signed Worker receipt allow/deny tests and the synthetic-source FFmpeg/V7 real audio-video decode. Production source deployment and live licensed-music artistic listening are **separate** gates. Do not label all discovered Openverse audio legally verified.

