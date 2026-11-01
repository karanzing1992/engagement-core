# Reel Engine V4.2 — Gemini-first provider setup (candidate)

**State:** Gemini adapter implemented. **Live Gemini authentication and visual analysis BLOCKED until owner adds a Google AI Studio key and explicitly accepts free-tier data terms.** Reel Engine V4.1 remains latest usable.

## Model roles
- Gemini `gemini-3.8-flash`: timecoded visual shot logging from up to eight small JPEG frames; only with explicit media rights, person consent and external-input approval.
- Groq GPT-OSS 120B: creative director for 3 divergent source-grounded storyboards; live synthetic fixture test passed on 02 Nov 2026, with JSON edit decision lists.
- Groq GPT-OSS 20B: optional small execution-model role, **not yet wired into V4.2**; current validated EDL compiler is deterministic and bounded. Retain V4.1 FFmpeg and V4 FilmCraft synthetic cloud pilot unchanged.

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

## Creative director (tested on safe synthetic shot descriptions)
```sh
# Safe, offline shape check:
python3 creative_director.py --shots fixture_verified_shots.json --brand README.md --brief 'Nature in motion' --output /tmp/reel-v42-offline.json

# On a private trusted machine with a secure GROQ_API_KEY environment variable:
python3 creative_director.py --shots /private/human_reviewed_shots.json \
  --brand /private/brand.txt --brief 'Three creative versions' \
  --output /private/creative-directions.json \
  --live-groq --authorize-external-shot-metadata
```
`creative_director.py` requires a structured shot manifest with `provenance=human_reviewed` or `gemini_human_reviewed` and actual source timecodes. It never executes model-generated shell commands or renders or publishes media. Live tested against synthetic fixture via existing Groq secret on the Mac; generated three original concepts. Source descriptions, not raw footage, were sent.

## Verified versus pending
- Adapter implementation: committed; offline tests in GitHub Actions.
- Gemini key and model availability: **not yet verified**.
- Visual analysis of consented source: **not run**.
- Groq 120B creative director: **live synthetic fixture PASS**, Mac local; Gemini not involved. Groq 20B / FilmCraft full integration remains pending.
- Gemini → Groq 120B director → 20B executor → FilmCraft integrated pipeline: **not yet certified**.
- No production WordPress/social change, Mac tunnel/thermal bypass, duplicate scheduler or paid-tier enrollment.

Sources: https://ai.google.dev/gemini-api/docs/get-started ; https://ai.google.dev/gemini-api/docs/pricing ; https://ai.google.dev/gemini-api/docs/video-understanding .
