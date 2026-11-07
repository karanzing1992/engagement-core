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
