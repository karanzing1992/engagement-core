# MAD V7 — music licensing, originals and synchronized-FFmpeg certification

**Date:** 2026-11-07 IST. **Scope:** V7 music source and private QA only. **Publishing:** forbidden absent owner approval. The runtime's legacy `mad-v6-*` filenames/endpoint IDs are protected V7 OIDC compatibility and must not be renamed in this change.

## Why this was necessary

Last V7 signed private canary (GitHub Actions `42363358638`, main `dc0078a`) completed FFmpeg but fell back to source ambience because no independently rights-eligible original musical recording was selected. Earlier real recording `Terminus Void - Inception` was explicitly in Commons `Category:License review needed (audio)`; that recording must **not** be treated as automatically cleared. A catalog's CC label is not certification of its composition and recording.

## New V7 fail-closed admissions

1. Keep existing V5 Openverse and Wikimedia Commons discovery, including bounded model-assisted shortlist, but **always add** a targeted Commons query of self-published original recordings tailored to the creative brief (`lofi ambient`, `piano music`, or `instrumental music`). A random Commons link indexed by Openverse does not displace the first-party search. Max two Openverse and one Commons query; source discovery still confers no rights approval.
2. Preserve an eight-candidate independent source-validation limit, and constrain Groq's choice to the eight displayed allowlisted IDs rather than any seen-but-excluded result. A failed/invalid inference falls back to deterministic ordered candidates; no AI-created or arbitrary-host audio.
3. Accept a Commons original only when the **same live Commons MediaWiki imageinfo + complete categories response** verifies exact original file/title, allowable CC BY/CC0/PDM license URL and metadata, creator, `Category:Self-published work` (claimed first-party composition/recording authorship), no pending-license or copyright dispute categories, bounded format/size, original URL and SHA-1. Missing review or authorship evidence: fail closed. Require immutable original-media digest and actual bytes SHA1+SHA256 from serial HTTP ranged download, FFprobe duration and audio, and FFmpeg final-media full decode.
4. For CC BY, preserve a publish-ready attribution record with title, creator, file source URL, license URL and **change notice**: 'Adaptation: excerpted, synchronized to video, mixed and audio-level adjusted.' Creative Commons officially says synchronization of music to moving images counts as an adaptation. This credit must be supplied with any owner-approved future platform post; metadata-only proof is not a substitute for public attribution.
5. Signed V7 receipt now distinguishes AI's metadata `discovery.selected` from the **actually downloaded/admitted** `discovery.actual_selected` with file URL, title, license and original SHA256; `ai_first_choice_admitted` indicates whether the first model choice passed safety validation.
6. Identify original Commons metadata reads with a contact-identifiable, non-secret User-Agent. Preserve upstream 429/503 Retry-After, no redirect/proxy/rate-limit bypass, private temporary media and 30-minute post-render retrieval policy.

## Independently verified real track

**Original source:** [Purrple Cat - Just Relax.ogg](https://commons.wikimedia.org/wiki/File:Purrple_Cat_-_Just_Relax.ogg).

- Creator: `Purrplecat` (Commons original `Artist` metadata); original uploader classifies it as `Self-published work` / `Own work`.
- Commons original license: **CC BY 4.0**, `https://creativecommons.org/licenses/by/4.0`. It permits commercial reuse/adaptations with appropriate attribution, license link and change indication.
- MediaWiki original SHA-1 `48fefb880e306d06117426545126f39d3a0d7c89`; verified full original **7,517,345 bytes**, independently downloaded original SHA-256 `6dad02b3386d856803189a686616ae809514b6fd179a6f211502d38491129c19`; FFprobe original **212.762494 s**.
- Private real-recording FFmpeg mix on Dell using synthetic video: H.264 video + AAC audio, `music_mixed:true`, `full_decode_passed:true`, `published:false`, output SHA-256 `d09e355cb2751c4541cb7b9dbc509c268e1b995cd5c69a388ea6a82179589077`, duration video **3.166667 s**, audio **3.187 s** (~20.3 ms difference), output **254,858 bytes**. Ephemeral temporary workdir deleted at task completion; no published content or original guest media.
- Strict active branch Dell tests: `test_v7_verified_source.py` **18 passed**; `test_v7_music_discovery.py` **11 passed**; `test_v7_auto_music.py` **5 passed**; `test_runner_stage_diagnostics.py` **9 passed**; 43/43 tests. Negative cases cover pending source review, absent authorship, conflicting license, invalid origin, missing SHA1, length mismatch, malicious Groq choice, redirect, 429 Retry-After, and corrupt media.

## Legal and operational distinction

This is **technical evidence for the specific claimed original recording under the original license**, not a copyright-law judgment or indemnity. Wikimedia metadata and a self-published claim cannot independently prove that a melody does not contain an unauthorized sample, nor guarantee Instagram/Meta Content ID will not flag it. Respect later deletion, dispute or rights-holder claims and fail closed. A human-reviewed private music library remains separately permitted with its own reviewer proof. **Do not publish without owner permission or without carrying the required CC BY attribution to the public post.**

## Still gated until separately verified

- Live Commons-indexed V7 discovery of multiple eligible sources is being tested after implementation.
- Final signed **GitHub OIDC → Cloudflare private KV → Gemini/Groq/txtai → AI-picked original audio → private full FFmpeg render → output checksum and rights receipt** must succeed on this commit before declaring end-to-end V7 music operationally certified.
- Owner browser footage upload, status/preview/download and visual quality are **owner-beta UAT**, not included here. Owner approval to publish remains mandatory.

Rollback: revert this PR, preserve previous V7 gateway/Pages deployments, owner-scoped service bindings, KV/D1, auth, external music-review flags and signed OIDC workflow path.

## FINAL SIGNED V7 MUSIC ACCEPTANCE — PASS (2026-11-07 IST)

**Scope:** signed GitHub owner synthetic fixture through final private Cloudflare KV, not real customer footage or owner browser UAT. Signed GitHub Actions [run 42368642711](https://github.com/karanzing1992/engagement-core/actions/runs/42368642711), owner-authorized [issue #229](https://github.com/karanzing1992/engagement-core/issues/229), exact code SHA `9392378be8dc50428abfc846be596b438672c999`, workflow completed **success**. All five original PR CI workflows passed. A test-pattern only source was used; no real guest footage uploaded, nothing published.

Cloudflare D1 job `v6job-9392378be8dc50428abfc846be596b43`: `state=review_ready`, `error_code=null`, output `1,173,379` bytes, SHA256 `4441c82cec36f684f06c2f957e5960bcc4a5d90764ee3c5dc201f732450da6e1`. 1080×1920, 30 fps, 4.033333 seconds, H264/AAC signed private FFmpeg, `full_decode_passed=true`, `music_mixed=true`, `audio_rights_verified=true`, `published=false`, `owner_approval=false`, txtai BM25 ready. Independent Cloudflare **KV management read** fetched raw `private/mad-v6/output/<job>/0` MP4 `1,173,379` bytes, independently SHA256 hashed to **same D1 value**, found MP4 `ftyp`, `avc1`, `mp4a` structures. Audio/video full decode was verified by runner; private KV is ephemeral with 30-minute output expiry. No media shared publicly.

**Actual automatic source selected & mixed, from final D1 receipt:**
- `Purrple Cat - Beach Resort.ogg` by `Purrplecat`; Commons original: https://commons.wikimedia.org/wiki/File:Purrple_Cat_-_Beach_Resort.ogg
- Original reported CC BY 4.0 https://creativecommons.org/licenses/by/4.0 and Commons first-party self-published file categories, no pending license review category.
- Original Commons SHA-1 `6e58fd18ec9e759c148ddb9449f3f6bf57f785b6`; verified downloaded original audio SHA256 `d086e63b684ec18404c25231c2aafa7060eb653e67538c9eee7173c1b76ae3af`. Both signed audio SHA and precise origin are in private receipt.
- Attribution in receipt: `Purrple Cat - Beach Resort.ogg — Purrplecat | CC BY | https://creativecommons.org/licenses/by/4.0 | https://commons.wikimedia.org/wiki/File:Purrple_Cat_-_Beach_Resort.ogg | Adaptation: excerpted, synchronized to video, mixed and audio-level adjusted.`
- Candidate search performed `openverse:cinematic`, `openverse:ambient`, `wikimedia:self_published_original`, 18 total provider entries, 8 candidate admission cap; final `discovery.actual_selected` matched the original metadata candidate SHA. **Selection mode was deterministic_fallback**, not a verified Groq model selection; it operated automatically without user music selection, while AI models generated/reviewed the video plan. Do not claim the LLM itself chose the soundtrack for this acceptance.
- AI planning/model receipt: Gemini 3.6 Flash, Groq 120B director and Groq 20B reviewer; txtai guidance ready. (Signed source receipt asserts roles, not independent proof of every inference payload.)

**Rights decision:** `PASS — V7 technically rights-gated automatic Commons music selection, verified-original media import, CC BY adaptation notice, source+output hashes and private FFmpeg audiovisual render`. Legal rights are conditional on accuracy of Commons uploader's self-published composition and recording claim. The engine cannot rule out undisclosed samples/Content-ID claims or guarantee platform immunity. For public posting, require owner approval and ensure complete CC BY title, author, source, license URL and modification notice accompanies the distributed video. The private D1 receipt currently contains the complete credit, but the owner-facing UI presently only exposes simple audio_mode via status; **presenting/copying the full public caption credit in owner beta** is a separate UI acceptance requirement.

**Owner beta remains a separate step:** authenticated real source video+prompt submission, Cloudflare login, private preview/download and artistic listening/visual QA, display/copy credit and independent posting approval. No owner beta launch/publication performed by this technical certification.
