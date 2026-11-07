# MAD Reel Engine V7 — audio selection, soundtrack provenance and A/V synchronization certification

Date: **2026-11-07 IST**. Owner request: certify automatic soundtrack selection, sound/video sync and the complete one-submit private render route. This is a bounded acceptance report, **not** a claim of a production owner-video job successfully completed from the browser.

## Release and source references
- Owner UI: `aarondash5-star/delulutech` PR #55 merged to `feature/mad-reel-v7-owner-20261107`, commit `989ec3ad6049cad4b4e011d8eb74453852e3a440` and live Cloudflare Pages production deployment `dd3f0a42-a465-46ac-8cc4-b6446e01ec67` (DEPLOY SUCCESS).
- Private beta: https://mad-v7-owner-private-beta.pages.dev/ (owner-code gate remains). Gateway: https://mad-v7-kv-private-beta.karanbizweb360.workers.dev/health — HTTP 200, `ready=true`, `dispatch_connected=true`, `published=false`.
- Audio runner: `services/reel-engine/v6-kv-gateway/runner.py`; soundtrack selection `v7_auto_music.py`, discovery `v7_music_discovery.py`, Commons original-file validator `v7_verified_source.py`; FFmpeg baseline `ffmpeg_v6_adapter.py`, final mastering `../v7-cinema/ffmpeg_v7_cinema.py`.
- Music admission in signed workflow: `MAD_V7_AUTO_SOURCE_MUSIC_ENABLED=true`. Source-host validation remains strict: automatic original Commons file CC0/PDM/CC BY only, including when indexed in Openverse. Non-Commons Openverse hosts remain discovery-only until independent source checks are implemented. This is a machine evidence check, not a guarantee against mislicensed original compositions or platform Content ID claims.

## Findings and corrective release
A live V5 Openverse + Wikimedia metadata discovery on Dell (`karan-Inspiron-5379`) returned 13 candidate records and 5 Commons-originated candidates in the eight-entry shortlist. The first four Commons file checks failed (media path, ineligible license, oversized file, ineligible license); the **fifth** passed original Commons imageinfo metadata validation (CC BY, attribution and media size). The previous runner tried only `pool[:4]`, so it incorrectly lost the fifth eligible candidate and selected source ambience.

Fixed by allowing all **eight bounded allowlisted candidates** to reach the strict original-host validator in source PR **#214**: https://github.com/karanzing1992/engagement-core/pull/214 , merged main SHA `e1e845cbbd9a3bf518eadf1c0880b518de61a56b`. Added regression asserting the fifth lead remains eligible to be attempted, with eight max. No automatic license acceptance rule changed; download, length, SHA, ffprobe and attribution checks remain mandatory. The source fix is in default branch; the private gateway Worker did not require modification.

## Reproducible test evidence — Dell local SSH, source pinned
- Tested `engagement-core` source `f94473c64da4176901844e3eae4363b82de5ec33` before fix and PR #214 head `895c49f1a8528c318e26abe8688c90374412829d` after fix.
- Python: `python3 -m unittest -v test_v7_verified_source test_v7_music_discovery test_v7_auto_music test_ffmpeg_v6_smoke`, run in `services/reel-engine/v6-kv-gateway`: **27/27 before**, **28/28 after**. Includes Commons MediaWiki mocked imageinfo original file verification and actual temporary synthetic-source audiovisual FFmpeg render/decode; rejects NC/SA/mismatched creator/license, redirects, tampered sizes, short recordings and unreviewed music.
- Gateway: `node --test test_kv_gateway.mjs`: **5/5 passed**, including owner auth / signed OIDC receipt / private upload and download response / expiry and tampering rejection contract. Signed gateway tests are simulated, NOT a live owner browser authentication.
- GitHub PR #214: **5/5 CI workflows success** (Reel Engine CI, generic source freeze, V6 KV Security & Models, V6 FFmpeg isolated gateway, V6 KV FFmpeg Owner Runner) for PR head SHA `895c49f...`.
- Dell FFmpeg `6.1.1`. Synthetic A/V alignment measurement with two 1.8s cuts and owned test-tone soundtrack: video 3.583333s, AAC audio 3.600s, **16.7 ms** duration difference, **0 ms** stream-start offset, valid audio RMS at opening, boundary and tail, audible fade and full stream decode.
- Dell longer 30s regression with three 10s cuts and human-approved *test-only synthesized sine* audio (not used in a public Reel): video **30.000s**, AAC audio **29.946s**, **54 ms** duration difference, **0 ms** start offset, nonzero RMS at 1s, 9.8s, 10.1s, 19.8s, 20.1s, 28s and 29.25s, full decode, verified receipt, `published=false`. This specifically rechecks against the historical short-audio/long-video failure. Fixture tones are for tests only; live music never synthesized as filler.
- Live gateway negative checks: `GET /health` 200; anonymous `POST /v6/media/uploads`, `GET /v1/projects`, `GET /v6/catalog` all 401; invalid owner token `GET /v1/projects` 401; allowed beta-origin OPTIONS preflight 204 and correct `Access-Control-Allow-Origin`. No owner videos, code or credentials were stored in these tests.

## Live original-media limitation (do not certify)
The **fifth** Commons track's source metadata passed, but an unmodified full-file GET to `upload.wikimedia.org` returned **HTTP 429 Too Many Requests**. A standard byte-range probe returned HTTP 206, but **neither this response nor a valid metadata record establishes actual bytes loaded and mixed using the production downloader**. The real `source_music.admit(...)` call raised `SOURCE_UNAVAILABLE`; it did not deliver the track. We do not bypass the CDN's rate limit, forge a licence proof or substitute arbitrary Openverse music. If the original host is unavailable, V7 tries remaining allowable candidates then source ambience.

## What “synchronized” means today
- FFmpeg converts/crops real video clips and source audio, builds a concat timeline, aligns the private recording from 0 seconds, trims its duration to the final timeline, fades it in/out, ducks source ambience to 25% and music level to 70%, mixes to AAC 48kHz stereo, then applies V7 loudnorm/master fades. Stream duration and full decoding are checked. The 30s measured test confirms no missing 20s soundtrack.
- **Not currently demonstrated:** AI detecting musical beats/transients and deliberately snapping video cut points to the soundtrack beats. Neither waveform onset detection nor BPM beat-grid edit planning is a certified capability. Also no human listening/artistic acceptance was performed on a real guest clip; sample fixtures alone cannot certify subjective quality.

## Owner workflow / status and remaining gates
Expected owner actions: sign in; choose video; give human prompt; press **Submit for render**. UI automatically creates project, hashes/uploads source chunks, invokes private V7 job, and polls private preview. Runtime selects eligible private reviewed track first, otherwise ranks Commons originals and performs independent live validation; no user soundtrack attachment or reviewer forms, no automatic publishing.

**Current classification:**
- `PASS`: source-level candidate selection ordering after fix, rights/admission negative cases, signed gateway contract, synthetic end-to-end FFmpeg A/V sync, 30s continuity regression, live auth rejection/CORS, private Cloudflare Pages frontend and gateway health.
- `NOT CERTIFIED`: genuine external Commons recording downloaded and FFmpeg-mixed by the deployed production runner after HTTP 429; real owner-authenticated browser upload → job → private MP4, actual owner clip artistic review; beat-synchronized cut choreography.
- Release lane remains **PRIVATE BETA / FAIL CLOSED**, public publishing disabled. Do not represent partial certification as full production release.

## Rollback / retention
For audio selection regression revert PR #214 merge SHA `e1e845cbbd9a3bf518eadf1c0880b518de61a56b`; disable `MAD_V7_AUTO_SOURCE_MUSIC_ENABLED` if original-host issue becomes widespread. Frontend prior owner beta source `e71a78b4d67ac8049affffd20db5f02c7e00298b`. No change to D1 schema, owner auth, encrypted secrets, GitHub OIDC, publication policy or existing 30-minute download deadline.
