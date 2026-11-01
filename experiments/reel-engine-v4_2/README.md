# Reel Engine V4.2 — Gemini-first provider setup (candidate)

**State:** Gemini adapter implemented. **Live Gemini authentication and visual analysis BLOCKED until owner adds a Google AI Studio key and explicitly accepts free-tier data terms.** Reel Engine V4.1 remains latest usable.

## Model roles
- Gemini `gemini-3.8-flash`: timecoded visual shot logging from up to eight small JPEG frames; only with explicit media rights, person consent and external-input approval.
- Groq GPT-OSS 120B: creative director, divergent stories, independent creative critique (existing Groq access, orchestration pending).
- Groq GPT-OSS 20B: constrained technical execution planner. Retain V4.1 FFmpeg and V4 FilmCraft synthetic cloud pilot unchanged.

Google AI Studio key: https://aistudio.google.com/api-keys . Create a **free-tier key with no billing enabled**. Google Drive/Gmail connection does NOT authenticate this API. Keep the key outside the public repo and chat.

## Setup on private terminal
```sh
bash configure_gemini.sh
export GEMINI_API_KEY_FILE="$HOME/.config/mad-yard/secrets/gemini-api-key"
python3 gemini_adapter.py preflight
python3 gemini_adapter.py preflight --verify-connection --accept-free-tier-terms
```
Offline preflight makes **no** API calls. Verify-connection lists available models using an authenticated read-only API call, **never sends media**. It does not guarantee the account has billing disabled: inspect the account in AI Studio.

## Explicit-only vision operation
```sh
python3 gemini_adapter.py vision --source "/private/cleared-video.mp4" \
 --brand-file "/private/moksha-brand.md" --timestamps "2,8,14,20" \
 --allow-external-frames --rights-and-consent-cleared --accept-free-tier-terms
```
This is **blocked by default**, sending at most 8 downsized JPEG frames—not entire footage. No original private video or guest photos may enter public GitHub. In particular, the previously shared third-party Arambol vlog is **not cleared** for free-tier Gemini upload.

## Verified versus pending
- Adapter implementation: committed; offline tests in GitHub Actions.
- Gemini key and model availability: **not yet verified**.
- Visual analysis of consented source: **not run**.
- Gemini → Groq 120B director → 20B executor → FilmCraft integrated pipeline: **not yet certified**.
- No production WordPress/social change, Mac tunnel/thermal bypass, duplicate scheduler or paid-tier enrollment.

Sources: https://ai.google.dev/gemini-api/docs/get-started ; https://ai.google.dev/gemini-api/docs/pricing ; https://ai.google.dev/gemini-api/docs/video-understanding .
