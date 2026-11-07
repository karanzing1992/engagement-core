# MAD Reel Engine V7 — owner-verified Gemini free-tier activation

**Date:** 2026-11-07 (IST)  
**State:** Owner billing-tier attestation recorded; activation pending CI/live signed test at time of creation.

## Evidence and scope

The owner explicitly stated **"I checked mark as verified"** after being asked to confirm that the **Google AI Studio Gemini API project used for Reel Engine V7** displays the **Free** billing tier. This is **owner attestation**, not independently verified access to the billing console. No API key value, Google account identity, billing profile, project name or payment details are written to source.

Independent evidence from GitHub Actions Gemini model metadata probe #42337225827:
- Existing `GEMINI_API_KEY` authenticated successfully.
- Six available candidate models; a Flash candidate identified.
- **Authenticated metadata does not prove billing-tier status**, which is why the separate owner attestation is recorded.

The connected third-party browser was unavailable due to zero wallet balance; no paid browser, chargeable model, plan switch, new API key or billing method was purchased.

## Bounded implementation

In `.github/workflows/mad-v6-kv-filmcraft.yml`, `GEMINI_PROJECT_FREE_TIER_VERIFIED` is enabled **only for the owner-private signed Reel Engine job**, annotated with the 2026-11-07 attestation. `GEMINI_INFERENCE_OWNER_APPROVED` is separately true by explicit owner approval. The Python runner and Gemini bridge **both** require both flags to equal `true`. They retain per-footage consent, three-frame cap, model discovery, free Flash candidate allowlist, source-grounded research, Groq independent direction/review, FFmpeg V7 cinematic finishing, signed Cloudflare private transport, and no-publication controls.

No changes to Google AI Studio project billing or key were made. Changing the workflow flag back to `"false"` immediately returns future signed jobs to the certified Groq-only fallback. Running jobs cannot be retroactively cancelled by a flag change.

## Live acceptance requirements

1. GitHub FFmpeg and V7 model/rights/security tests pass on the **exact PR head SHA**.
2. Merge as `STACK CHANGE:` on main after passing checks.
3. Trigger **synthetic-only** owner-issue `[MAD-V6-LIVE-MULTIMODAL-AUDIO-QA]` through the real signed GitHub workflow.
4. Confirm job log contains the `gemini_research`, `groq_director`, `groq_reviewer`, `cinematic_finish`, `output_upload`, `private_complete` stages.
5. Independently read the Cloudflare D1 owner-private job receipt: `model_roles.gemini` names the actual Gemini Flash model; director/reviewer are correct; `full_decode_passed=true`; `published=false`; no real guest media or commercial music claim.
6. Do not mark full creative/audio/artistic V7 production certification based solely on synthetic footage. No public social publishing is authorized.

## Open Source / Reuse / Cost / Rollback

- Reuses the existing V7 FFmpeg renderer, Gemini free-model REST adapter, Groq review pipeline, private GitHub OIDC/Cloudflare gateway, and test suites. No new providers or subscriptions.
- The owner reports the configured project is on Free. Service quota, tier and model eligibility may change; repeated errors or billing concerns require revalidation. This configuration is not a promise of perpetual zero charges.
- Rollback the flag to `false`, or revert the recorded main merge; preserve V5 and V6 deployments.
