# MAD V7 — Wikimedia sequential/resumable audio import certification
Date: 2026-11-07
Scope: user-authorized original-licensed audio source download; no public publishing.

## Baseline and problem
- Original admission: `services/reel-engine/v6-kv-gateway/v7_verified_source.py`. Full-file GET to `upload.wikimedia.org` yielded Wikimedia Varnish HTTP **429** with `Retry-After: 10`, while single byte-range requests yielded **206**. Wikimedia’s published 2026 rate-limit policy requires contact-identifiable User-Agent, bounded concurrency and respecting Retry-After. The older V7 User-Agent lacked contact.
- Previous PR #214 already expanded independently checked music candidates from 4 to 8; source-independent rights checks remain fail closed.

## Change
- Single serialized HTTP Range stream, max 4 MiB per requested segment, max 16 MiB per original track. No parallel downloader, proxy, alternate host or rate-limit bypass.
- One fixed identifying User-Agent with the owner’s public repository contact URL; Wikimedia can identify the requesting client.
- Require response HTTP 206, exact requested byte ranges and matching Content-Range and Content-Length; HTTP 200 accepted only for the **first** request returning the **entire** validated file. Never concatenate an unexpected 200 after a partial transfer.
- Preserve source-host and redirect checks, original Commons file page and CC BY/CC0/PDM license audit. Fetch `imageinfo.sha1` from Commons original-source API, require a valid source checksum, reassemble bytes under the private job workdir and match SHA1 against Wikimedia’s original, then calculate SHA256. Any mismatch or incomplete transfer deletes the local partial file before FFmpeg can touch it.
- On upstream 429/503, obey Retry-After (delta seconds or HTTP date), use bounded fallback backoff if absent, at most two retries per segment, and **fail closed instead of ignoring Retry-After above 30 s**. Other upstream errors fail closed; source ambience remains fallback.
- No change to Gemini/Groq, uploader, FFmpeg mixing, private delivery, rights approval, owner authentication or publishing gate.

## Verified tests
- Physical Dell isolated test checkout `dac922698e084eef7eb1419be79818cbf97b7269`, synthetic importer, rights and FFmpeg tests: **35/35 passed**. Signed gateway/owner claim tests **5/5 passed**. Dell worker receipt `254410767d7b4cacb0d37240124d65db` exit 0.
- GitHub PR #216 check runs all five successful: Reel Engine CI, MAD V6 KV FFmpeg Owner Runner, consolidated KV security and models, signed gateway and media QA, Generic SSH freeze.
- **Real original Wikimedia import** on Dell worker receipt `eb450b87ccc64d99ae48b04264b471e0` exit 0. One metadata discovery returned 5 Commons tracks, first 4 failed original license/media/size gate, fifth passed CC BY. Original track `https://commons.wikimedia.org/wiki/File:Terminus_Void_-_Inception_(Dystopian_Cyberpunk_Space_Ambient_Music_similar_to_Blade_Runner_soundtrack_music).opus`, original size 9,288,803 bytes.
- Three accepted **HTTP 206** ranges: `0–4194303`, `4194304–8388607`, `8388608–9288802`. Complete assembled file **9,288,803 bytes**; original Wikimedia SHA1 `2f2ef57616ce283df05f742d162aeaa0f27fda86` matched, final SHA256 `7b8cacfca4571e75687a58eb3dd5382621d8b6d3bb5bd434776dcdd37de2e075` verified.
- The real CC BY recording was mixed with synthetic source video by existing `ffmpeg_v7_cinema.finish`. Output H.264 video + AAC audio, **78 ms audio/video duration difference**, full decode, audio present, rights attribution in private manifest. `published=false`, `owner_approval=false`. No media uploaded to public storage and temporary test workdir cleaned.
- Tests deliberately use temporary WAV tones (non-release assets) for synthetic audio; real Commons test uses a specific external recording only for private technical certification. CC BY attribution remains required for any approved public use.

## Release boundaries
- This validates real music **retrieval + checksum + FFmpeg**, not genuine owner footage through browser login and complete Gemini/Groq render dispatch, which remains a separate UAT gate.
- Audio start/duration synchronization and end fades are verified; **beat-accurate music-to-edit sync and human sonic quality acceptance are not established**.
- A successful single test does not guarantee Wikimedia will never return 429. Rate limits remain enforced and fallback to source ambience is mandatory.
- Existing owner-vault reviewed-music catalog is **not automatically overwritten or populated by new external downloads**. Cross-job caching would require a distinct bounded license revalidation / expiry and media-retention design, so the importer stays ephemeral and safe.
- Owner code, API secrets, personal footage and platform publishing are unchanged.

## Rollback
- Revert PR #216 in `engagement-core` main to restore the old full-file downloader and previous safe fail-closed behaviour. GitHub private job artifacts and Cloudflare private gateway are separate; no direct Cloudflare deploy is needed because signed GitHub runner consumes repository source.
