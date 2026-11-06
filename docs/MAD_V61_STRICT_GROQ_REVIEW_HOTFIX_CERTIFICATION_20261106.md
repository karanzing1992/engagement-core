# MAD Reel Engine V6.1 — Strict Groq Review Hotfix Certification

**Date:** 2026-11-06 (Asia/Kolkata)  
**Status:** **VERIFIED LIVE in GitHub runner + synthetic signed end-to-end**, guest source **RETRY ARMED / NOT RENDERED**.  
**Repository:** `karanzing1992/engagement-core`  
**Main hotfix commit:** `4b045af0e27ca7992445106b7139b4e75d052bef`  
**PR:** [#193](https://github.com/karanzing1992/engagement-core/pull/193)  
**Evidence:** [Signed V6.1 real-model synthetic run #42229927461](https://github.com/karanzing1992/engagement-core/actions/runs/42229927461)

## Incident

- Real private owner job `v6job-d8349449dac043269fc641a62559fd5c`, source `1000081480.mp4`, failed in [GitHub run #42227079129](https://github.com/karanzing1992/engagement-core/actions/runs/42227079129), at `edl_compile` before GStreamer execution.
- Diagnostic: `REVIEW_DIGEST_OR_APPROVAL_MISMATCH`. Previous reviewer was instructed to reproduce the cryptographic digest and exact ordered segment indices. This conflated actual creative disapproval with formatting/digest mismatch, generating wasted retries. Reviewer approval was **not assumed**.

## V6.1 correction

- Verified Groq documentation for `openai/gpt-oss-20b` and `openai/gpt-oss-120b` supports `response_format.type=json_schema` and `json_schema.strict=true`, with required properties and `additionalProperties=false` for all objects. Docs: https://console.groq.com/docs/structured-outputs .
- Reviewer now returns **only** a strict JSON schema: a global boolean `approved` and a `decisions` object containing an exact required key for each proposal segment (`s0`, `s1`, etc), each with required boolean `approved` and allowlisted reason code.
- **No model-generated SHA or segment indices.** Application alone computes `director_plan_sha256`, maps ordered segment IDs and validates exact response structure, consent, source bounds, and renderer-supported effects.
- Independent reviewer still evaluates creative feasibility and rights, without bypassing rejection. Any explicit global or segment disapproval terminates the render; malformed or contradictory responses fail closed. No blind retries or fallback auto-approval.
- Both Gemini+Groq and Groq-only fallback paths use the same strict reviewer function.
- Director limited to native GES effects `color_grade`, `title`, `caption`; unsupported effects and malformed title text fail before rendering.
- User-provided media and provider responses remain out of CI artifacts. V5, Cloudflare gateway bindings, private consent gates, 30-minute output lifetime, and publication permissions unchanged.

## Certification

1. [PR #193](https://github.com/karanzing1992/engagement-core/pull/193) merged at `4b045af0e27ca7992445106b7139b4e75d052bef`.
2. Five pull-request CI workflows green (Reel Engine CI, V6 consolidated KV/security/models, Gemini Flash preflight, legacy isolated FilmCraft smoke, generic SSH freeze). V6 consolidated regression: **20 + 38 tests**, all green.
3. Real-model, owner-signed synthetic job `v6job-4b66c78e0d20476b982fe0f3453a492d` executed [GitHub Actions #42229927461](https://github.com/karanzing1992/engagement-core/actions/runs/42229927461), completed **success** at exact `4b045af0` SHA.
4. Cloudflare D1 job `review_ready`, no error, one output chunk, **120,880 bytes**, SHA-256 `96a5629ea5b2e3f6d7c5c9e3f6fe0dbc23b2d6a675f7f8364aa8ee57b67b61e7`. Native GStreamer 1080×1920/30fps/4 seconds, 3 decoded visible frames, verified audio mix, `openai/gpt-oss-20b` reviewer, `published=false`, private KV output. This certifies **synthetic technical rendering**, not artistic approval or playback of real guest media.
5. Original real owner job `v6job-d8349449dac043269fc641a62559fd5c` was *not* silently rerun. Guarded Cloudflare D1 state reset only after verifying 7 private KV source chunks present and D1 part count complete, source SHA-256 `bae18d8e1f7950fce79474059f1b685c273adf0334289f7ce1f491f05e671dc5`, attempts=1, no output chunks, no prior ready receipt, source still unexpired. Job now `uploaded`, `error_code=V61_STRICT_REVIEW_RETRY_ARMED`.

## Remaining gated owner action

Open existing private V6 project via https://mad-v6-owner-private-beta.pages.dev/ , press **Refresh status** and then **Render with V6 once**, retaining the approved creative direction already stored with the job. **Do not upload again, do not create a new project/job.** This enforces the original owner-authenticated dispatch, GitHub OIDC and KV claim. Do not submit an alternative GitHub Issue for real guest media: Cloudflare's current signed `issues` pathway is intentionally restricted to synthetic QA, and should not be bypassed.

After that authentic request: inspect actual job GitHub run, D1/receipt, visible frames and soundtrack, Android preview and owner's artistic acceptance. Only then report the real guest reel as successful. No social post without explicit owner approval.

## Rollback

- Revert code changes only if a strict schema incompatibility is observed on real content; preserve original sensitive media and fail closed rather than letting the independent reviewer be bypassed.
- Cloudflare production Worker remains unchanged; no worker rollback required for this Groq-only runner hotfix.
- Maintain V5 isolation, no media artifacts in GitHub.
