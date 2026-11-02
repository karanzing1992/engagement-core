# Reel Engine V5 — Creative Orchestration and Third-Party Music

**V5 is the architectural/configuration baseline** with source-grounded creative freedom and extensible model/tool registry. It is **not** proof of a rights-cleared, 1080x1920 production release; prior V4.1 remains the last technically verified real-video private preview until V5 real-footage QA. See [full V5 baseline](../../docs/MAD_REEL_ENGINE_V5_BASELINE.md).

## Quick start: model and tool inspection (no external media)

```sh
python3 -m unittest -v test_v5_orchestrator.py test_music_provider.py
python3 v5_orchestrator.py --shots synthetic_shots.json --brand fixture_brand.txt \
  --brief 'Plan six distinctive cinematic nature films' --versions 6 \
  --output /tmp/v5_planning_preflight.json
python3 capability_probe.py --output /tmp/v5_installed_tools.json
```

Creative model: Groq GPT-OSS 120B; execution: Groq 20B, existing source-timestamp guard and verified editor tools; visual model: Gemini 3.8 Flash preferred / 3.6 Flash synthetic-tested fallback. Other providers can be registered with real adapter support. User decides artistic style, shot count, treatment count and duration; per-job compute/API limits are still configurable. Proposed effects without an installed/verified executor are retained as **deferred**, not silently discarded or executed as shell commands.

## Existing licensed music only — no AI composition

**Primary open-source catalog gateway:** [Openverse](https://openverse.org/) / [Openverse API](https://api.openverse.org/v1/), publicly accessible without API keys at anonymous rate limits.

```sh
# One metadata search, never downloads music:
python3 music_provider.py search --query 'serene instrumental ambient music' \
  --limit 6 --output /private/music_search.json

# Independently inspect original source and exact recording's license.
# Select an item as /private/selected_track.json.
# Copy music_license_review_template.json to /private/music_license_review.json
# and fill evidence only after reviewer has confirmed the exact source rights.

# After legitimately downloading the verified original recording from source:
python3 music_provider.py ingest --track /private/selected_track.json \
  --evidence /private/music_license_review.json --audio /private/song.ogg \
  --output-dir /private/approved_music

# Mix the existing recording into a video; keep original ambience when available:
python3 music_provider.py mix --video /private/source.mp4 \
  --music-dir /private/approved_music --output /private/reel_with_music.mp4
```

Commercially usable license candidates: CC0, public-domain mark, CC BY (credit required). NC/ND excluded, SA deferred for legal compatibility review. **Openverse itself cautions that index license information is not always accurate**; independently confirm the specific work's creator and source license. Never automatically download or distribute a track based solely on catalog metadata. Keep proof/credits in every deliverable. Fall back to a visibly pending soundtrack, **never synthetic music**. Other optional sources: Wikimedia Commons, Free Music Archive and Freesound, subject to each API/content use terms. Freesound's API specifically requires commercial-use consideration; do not treat free API access as commercial permissions.

## Version and certification boundaries

- V5 config/models/source/creative choices: implemented and subject to offline + synthetic planning QA.
- V5 third-party catalog API: discoverable; separate live metadata certification receipt required.
- V5 original-source soundtrack ingestion, attribution, and FFmpeg mix: code implemented, individual tracks **must have verified provenance**, actual real-song mixing on rights-approved footage not yet certified.
- ArtCraft Studio: optional **candidate**, not automatically installed, subscribed or certified; its hosted generation is credit-based. FilmCraft advanced 716-command catalogue is also not an exhaustive execution certification.
- Real footage should remain private, with rights, consent, accurate brand claims and owner release gate. Production services, WordPress/Instagram and Mac thermal controls unchanged.
