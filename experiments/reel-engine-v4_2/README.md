# Reel Engine V4.2 — Gemini-first provider setup (candidate)

**State:** Authenticated Gemini model metadata PASS, live Gemini 3.6 vision + Groq 120B/20B + three synthetic FFmpeg exports PASS. **Real-media video workflow NOT CERTIFIED**. Reel Engine V4.1 remains latest usable private footage-preview release. [Read canonical V4.2 evidence](../../docs/MAD_REEL_ENGINE_V4_2_STAGING.md).

## Model roles
- Gemini `gemini-3.8-flash` is authenticated for model metadata but generation returned 503/timeout. Live `gemini-3.6-flash` fallback successfully analyzed five generated synthetic JPEGs. Real-media ingestion still requires explicit rights/consent and data-term approvals.
- Groq GPT-OSS 120B: creative director for 3 divergent source-grounded storyboards; live synthetic fixture test passed on 02 Nov 2026, with JSON edit decision lists.
- Groq GPT-OSS 20B: **live synthetic** constrained edit-style selection passed; deterministically applied via a guarded EDL with three FFmpeg H.264 exports. No untrusted shell commands or customer footage. Retain V4.1 FFmpeg and V4 FilmCraft synthetic cloud pilot unchanged.

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
- Gemini key and model access: **authenticated and verified**, https://github.com/karanzing1992/engagement-core/actions/runs/41363494905.
- Visual analysis: **live Gemini 3.6 on five generated synthetic drawings PASS**, https://github.com/karanzing1992/engagement-core/actions/runs/41364125827. Real consented source not tested.
- Groq 120B creative director: **live synthetic fixture PASS**, Mac local; Gemini not involved. Groq 20B / FilmCraft full integration remains pending.
- Gemini 3.6 → Groq 120B director → 20B constrained editor → FFmpeg three synthetic MP4s: **E2E SYNTHETIC PASS**. FilmCraft integration with actual media remains **NOT CERTIFIED**.
- No production WordPress/social change, Mac tunnel/thermal bypass, duplicate scheduler or paid-tier enrollment.

Sources: https://ai.google.dev/gemini-api/docs/get-started ; https://ai.google.dev/gemini-api/docs/pricing ; https://ai.google.dev/gemini-api/docs/video-understanding .
