# MAD Reel Engine V5 — Groq-only high-capability model routing
Date: 2026-11-04
Owner scope: private Reel Engine V5 GitHub worker and synthetic QA. Older V4.2 Gemini pilot remains archived; do not modify.
Source baseline: `67c8d1a1b3a6c802ba76ab8d6e469164660b1f04`

## Golden Rule 0: reuse, licensing and cost
- Reuse existing official Groq OpenAI-compatible APIs, already installed `groq==0.37.1` Python SDK, Pillow, FFmpeg and GitHub Actions. No new paid service, new model platform, vendor key, or cloud account.
- Groq official docs: https://console.groq.com/docs/models ; https://console.groq.com/docs/vision ; https://console.groq.com/docs/deprecations . Qwen 3.6 and Llama 4 no longer usable on free/developer plans (2026-09/07 deprecations).
- Model IDs are Groq-hosted open-weight inference models, NOT a license statement about GroqCloud infrastructure. Existing owner free-tier only. This configuration does **not** authorize pay-as-you-go usage. Check quota and permission before model calls.

## Task-to-model policy
| Task | Primary | Same-provider fallback | Implemented |
|---|---|---|---|
| Cinematic direction / storyboard | Groq `openai/gpt-oss-120b` high reasoning | Groq `openai/gpt-oss-20b` | Used in real and synthetic V5 |
| Visual frame analysis | Groq `qwen/qwen3.8-27b` image-to-text | None (fail visibly) | Real frame and synthetic fixture adapters |
| Complex editing decisions | Groq `openai/gpt-oss-120b` medium reasoning | None | Configured role; not an actual FFmpeg effect executor |
| Fast deterministic edit validation | Groq `openai/gpt-oss-20b` low reasoning | None | Configured role; separate execution integration pending |
| Cinematic quality critique | Groq `openai/gpt-oss-120b` high reasoning | None | Configured role; independent artistic review still pending |

## Security, scope and functionality
- `v5_config.json` explicitly rejects any non-Groq model/provider; config maps only `GROQ_API_KEY`. GitHub production worker no longer exposes `GEMINI_API_KEY`.
- The real private pipeline uses a shared Groq vision adapter on source frames only after rights/people consent/external AI approval; images are base64 in process memory and never logged.
- Synthetic V5 multimodal QA creates five existing-style drawings and sends these exact frames to Groq Qwen3.8 before reusing the same frames in FFmpeg render. No customer media or model-generated images.
- Missing Groq account permissions, previews or rate limits do NOT authorize Gemini/paid model fallback. A missing vision result is recorded as unknown rather than fabricated frame content; source-only technical fallbacks remain marked as unapproved.
- Technical validity is not artistic/musical/full V5 certification. Third-party music must remain rights-cleared; output remains owner-only preview, no automated publication.

## 04 November 2026 — official Groq free-plan verification and operational routing

Provider references: https://console.groq.com/docs/rate-limits, https://console.groq.com/docs/models, https://console.groq.com/docs/vision, https://console.groq.com/docs/model-permissions.

Free-plan documented **per-model** limits for the three configured IDs: 30 RPM, 1,000 RPD, 8,000 TPM, and 200,000 TPD, subject to the actual organization's limits. The API account is **not** verified: previous signed GitHub preflight `GET /openai/v1/models` returned HTTP 403. No paid usage, billing or plan upgrades are permitted. Local tests and the public Groq catalog do not prove project/account authorization.

Free-tier model selection:
- **Creative / complex decisions / critique:** `openai/gpt-oss-120b` (production, high reasoning for primary director).
- **Fallback creative direction / quick validation:** `openai/gpt-oss-20b` (production). Avoid loading preview Qwen's image-token quota during fallback creative planning.
- **Actual frame captioning:** `qwen/qwen3.8-27b` (preview image model). Six authorized source frames processed at most three per quota batch with 63s before the second batch. Qwen charges 2,048 input tokens per image; three frames consume about 6,144 image tokens before prompt/output tokens. Other organization workloads or different account limits may still cause HTTP 429.
- Deprecated Llama 3.1 8B, Llama 3.3 70B, Qwen 3.6, Compound, and retired Llama 4 Scout are not part of V5 routing. Enterprise-only/limited-preview models such as Muse Spark are excluded.
- `whisper-large-v3-turbo` is listed with free-plan audio limits but is **not integrated into the current private rendering workflow**. Do not imply audio transcription is executed.

**Release gates:** Genuine model availability requires owner GitHub secret/account permission restoration and read-only preflight HTTP 200; never disable the gate to process private guest media. The production preview remains private and full artistic/music certifications are separately required.

## Validation and release gates
1. Synthetic-only Python tests: `test_v5_orchestrator.py`, `test_git_cloud_runner.py`, `test_creative_audit.py`; GitHub workflow contracts and source security checks.
2. Read-only model availability script `groq_models_preflight.py` uses `GET https://api.groq.com/openai/v1/models` with existing masked owner secret and logs only IDs/availability. It does not perform inference or certify paid/free limits.
3. Only merge after tests pass or explicitly document/resolve failure. Check account model permissions; if preview Qwen3.8 unavailable, block vision and report, never silently revert to Gemini.
4. Post-merge signed owner real-media run and fully traced receipt are separate acceptance; protect existing projects and private footage. No automatic repeat of old guest upload or artistic certification by config change.
5. Rollback config/runners to prior signed main commit, preserving D1/KV and not restarting jobs. No publication rights affected.

## Implementation status
PR review and tests pending at document creation. Treat this as a change proposal until merged/tested. Preserve exact resulting commit SHA and Master Registry verified status separately.
