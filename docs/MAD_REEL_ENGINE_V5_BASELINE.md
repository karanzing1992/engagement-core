# MAD Reel Engine V5 — Open Creative Engine and Licensed Music Baseline

**Baseline date:** 02 November 2026, Asia/Kolkata  
**Version:** V5.0.0  
**Baseline status:** **CURRENT DEVELOPMENT / CONFIGURATION BASELINE**. Release certification is strictly scoped to what the actual tests proved; **V4.1 remains the last verified private real-footage preview renderer** until a new V5 real-footage QA pass.  
**Owner directive:** Full creative freedom and modular tool/model extensibility; use existing freely licensed music from the web, **never compose substitute music**.

## 1. What changed relative to V4/V4.1/V4.2

- An **open creative brief** replaces a rigid format requiring exactly three versions, 5–15 clips and a 14–40-second timeline.
- The owner controls treatment count, source-derived duration, editing rhythm, output format and creative constraints per job. No creative *style* or *story* limit is hard-coded; a specific job must still fit its API/provider and compute budgets.
- A model registry supports Groq GPT-OSS 120B director, GPT-OSS 20B alternate director, Gemini 3.8 / 3.6 Flash vision, 20B technical planner and optional critic, with roles and priorities expressed in JSON.
- Tool registry is **extensible**: FilmCraft MCP, FFmpeg, licensed-music discovery, optional ArtCraft and future adapters can be registered. A newly imagined effect or unsupported capability is **recorded as deferred** until the relevant plugin/tool is installed and proven. Models cannot invent successful tool outcomes, execute arbitrary shell snippets or bypass source/rights checks.
- **Real recordings only** for music. The prior procedural soundtracks are preserved as historical V4.1 previews, *not the V5 standard*. V5 refuses to fabricate/computer-compose replacement music. Third-party recordings may be cut, fitted, faded, volume-balanced and mixed within their actual licenses.

## 2. Confirmed underlying baselines

**V4:** Groq 20B → FilmCraft MCP (17 enumerated tools) → FFmpeg technical 2s synthetic video PASS; only a narrow subset was used, not all command features proven.  
**V4.1:** Groq 20B creative planning, three 24s real-source 720×1280 private FFmpeg clips PASS for codec/decode/hash; soundtrack was synthetic and is now deprecated for V5 new production. Real footage rights and publishing were **not** certified.  
**V4.2:** LIVE Gemini 3.6 Flash analyzed five *generated synthetic* images; Groq 120B produced three storyboards; Groq 20B selected bounded edit parameters; FFmpeg generated three synthetic 360×640 H.264 files with full QA. Run https://github.com/karanzing1992/engagement-core/actions/runs/41364125827 PASS. Gemini 3.8 Flash model metadata was accessible, but inference suffered 503/timeout; fallback 3.6 succeeded. Never infer real footage creative quality from this synthetic test.  
**V5:** Contract/protocol tests and live creative plan tests are separate from a completed video render. V5 baseline approval means architecture and safe source-grounded creative planning; not owner publication authorization.

## 3. V5 model orchestration

- **Vision:** Gemini 3.8 Flash preferred if responsive; Gemini 3.6 Flash confirmed fallback. Cost/usage terms and media upload consent must be verified before sending non-synthetic frames. No guest photos or unlicensed third-party source input in public CI.
- **Primary creative director:** Groq GPT-OSS 120B at configured temperature **0.85**. This is a tested strong-creative preset, not the model's maximum. Creative direction may explore narrative, visual emphasis, pacing, multiple genres, audio direction, animation treatments, typography and reframing.
- **Execution planner / backup director:** Groq GPT-OSS 20B, constrain source timestamps and file operations; imaginative plans must be translated into a tool-specific verified EDL, never free-form shell.
- **Independent critic:** 120B candidate role; not certified as a separate live video/artistic critic. Human owner approval remains mandatory for final marketing release.
- **New providers:** add entries in `v5_config.json` and test their adapters. The engine does **not** claim arbitrary new APIs can execute automatically simply because names are entered into JSON.

## 4. Source accuracy, licensing, quality

Source manifest must include human-reviewed real shot timecodes, source/usage provenance and consent evidence. Creative models may rearrange, speed-ramp, layer, stylize or composite **actual cleared footage**, but must not fabricate scenes, people, location or benefits or misrepresent venue ownership.  
Moksha brand tokens are **immutable** for brand content: Deep Forest `#18382F`, Brass Gold `#C5A15A`, Warm Sand `#E8DCC7`, Soft Ivory `#F9F5EA`; editorial serif, real nature, understated premium voice, source truth and no invented logo. A richer creative effect must serve the visual story, not become a template.  
Preserve authentic ambience when rights allow. Reuse of recognizable people, commercial usage and published music must have proof. Before final approved distribution: human artistic/rights review, output listening, audio loudness, clipping, mobile previews, captions, logo, factual checks, video dimensions, export/decoding and owner release authorization.

## 5. External free/open-licensed music provider — ACTIVE CODE PATH

**Primary provider:** [Openverse](https://openverse.org/) (open-source discovery engine) and [official free anonymous audio-search API](https://api.openverse.org/v1/), filtered to **CC0, public-domain mark, or CC BY**. Openverse itself warns source license metadata is not guaranteed correct; opening the original creator/source page and verifying the full license is mandatory before use. **CC BY needs attribution**. NC and ND restrictions are excluded; SA excluded by default until a compatible license-specific review.  
**Music code:** `experiments/reel-engine-v5/music_provider.py`. Supports live audio search metadata with no extra keys, attribution/source/creator/license normalization, separate rights-review evidence gate, ingestion of a pre-downloaded original recording, SHA256 proof, FFprobe duration checks, credits manifest, and FFmpeg normalized AAC music mix. **There is no procedural-music fallback**, no blind bulk downloading, no auto-publication.  
**Additional sources:** Wikimedia Commons, Free Music Archive and Freesound can be used after provider-specific commercial license and API terms verification. Freesound's developer API is free for noncommercial API applications only without a separate commercial-use arrangement; do not silently route business marketing through an unsuitable free API. <https://freesound.org/help/developers/>

Workflow:
1. Query existing music through Openverse with concept mood/instrument/timing keywords.
2. Compare tracks aesthetically, listen, and check original creator's license page and any commercial/derivative requirements.
3. Store reviewer evidence separately (track ID, original source, exact license URL, verification URL/date, reviewer, credit).
4. Download the verified track from its original legitimate provider to private local storage, then run `music_provider.py ingest` to hash and register the original file.
5. Use `music_provider.py mix` with a private video and approved recording. Finalize loudness, crossfade and ambience, human audio/artistic review, attribution in caption or credits.
6. If no permitted sound recording can be verified, **report soundtrack pending**—do not compose an artificial substitute or publish a music-dependent cut.

Commands:
```bash
python3 music_provider.py search --query "cinematic ambient instrumental nature" --limit 6 --output /private/music_candidates.json
python3 music_provider.py ingest --track /private/selected_track.json --evidence /private/license_evidence.json --audio /private/licensed_recording.ogg --output-dir /private/approved_music
python3 music_provider.py mix --video /private/reel_no_music.mp4 --music-dir /private/approved_music --output /private/reel_with_licensed_music.mp4
```

## 6. Execution tools and capability truth

`capability_registry.json` is data-driven: operations and adapters distinguish **verified, candidate and blocked**. `capability_probe.py` is a local read-only FFmpeg and FilmCraft CLI inspector; it reports actual installed FFmpeg filters, encoders, FilmCraft command IDs and their counts. A FilmCraft command being listed is not evidence that it works for every creative treatment. Model suggestions for transitions, motion typography, mask, speed ramp, sound design, ArtCraft video or cinematic color look are preserved as pending if no executor adapter has been tested.  
A full ArtCraft API or Studio bridge is **optional and not yet certified**. Hosted ArtCraft generation is credit-based; do not make it mandatory when the owner requires free/open-source only. Use local/open engines where genuinely installed and budget-approved.

## 7. What the V5 tests mean

- `test_v5_orchestrator.py`: multi-treatment counts including six, 50-segment planning, 100-second timeline, model fallback, plugin registration, source offsets, rights and shell safety, unverified effects deferred.
- `test_music_provider.py`: Openverse metadata, CC0/CC BY/public domain filter, NC/ND exclusions, attribution/rights evidence and bad-audio fail closed.
- `reel-engine-v5-cert.yml`: no-video offline tests; anonymous Openverse metadata search; FFmpeg read-only capability probe; Groq 120B real inference on **synthetic shot descriptions only**. Artifacts contain only synthetic storyboards/receipts. None of these tests certifies cinematic owner footage, real audio mixing, FilmCraft full feature set, ArtCraft or live publishing.
- Passes must be verified from workflow receipts before changing any status to certified.

## 8. Baseline and release semantics

**V5.0.0 is the new master development/configuration baseline** once merged and master-registry signed.  
**V4.1 remains the last confirmed private real-footage renderer** until V5 actually ingests licensed music and real consented footage and passes end-to-end output and independent quality gates.  
V4.2 remains the synthetic multimodel technical pass.  
Moksha M3/M4 and any social publishing remain independently owner-approved gates. Do not turn the public repository into a host for private video, API keys or third-party recordings. No bypass of Mac thermal controls, Firefox or existing MAD Manager host safeguards.

## 9. Handover

Open `docs/MAD_REEL_ENGINE_LATEST.md` for the version pointer, this document for V5 architecture, `experiments/reel-engine-v5/v5_config.json` for provider settings, `capability_registry.json` for editor adapters, `v5_orchestrator.py` for planning, `music_provider.py` for existing-licensed-music workflow, `capability_probe.py` for tool inspection.  
The next certification milestone is a source-rights-cleared 1080×1920 15–30-second Reel with a genuine CC0/CC BY recording, correct credits, art/tech/audio QA, and a reviewer-signed acceptance receipt. Respect free-tier quotas and do not silently use paid APIs.
