# MAD Reel Engine V6 — GStreamer GES Production Certification

**Date:** 2026-11-06 (Asia/Kolkata)  
**Repository:** `karanzing1992/engagement-core`  
**Release class:** **VERIFIED LIVE for synthetic private workflows**, **PENDING actual guest-footage and mobile artistic acceptance**  
**Live owner beta:** https://mad-v6-owner-private-beta.pages.dev/  
**Cloudflare gateway:** `mad-v6-kv-private-beta`  
**GitHub current approved main:** `95e97b23489b0ee97746333f63fdd07c03e7741e`

## Incident and change

The initial FilmCraft V6 guest output contained audible sound but no meaningful video, despite an MP4/H.264/size-and-checksum receipt. That earlier classification was insufficient; structural video metadata did not establish that meaningful source frames survived the timeline export. Do **not** cite Master event #297 as visual or artistic acceptance.

**Migration:** Replace V6 native FilmCraft with GStreamer Editing Services (GES) on GitHub ubuntu-24.04. Preserve Gemini creative research, Groq GPT-OSS 120B director and GPT-OSS 20B independent reviewer, signed GitHub OIDC, Cloudflare KV private media, D1 job ledger, Projects auth, owner consent, Cloudflare dispatch service, original CC0 generated soundtrack and 30-minute private download. V5 unaffected. **No FFmpeg CLI renderer.**

## Approved commits

| PR | SHA | Change |
|---|---|---|
| [#184](https://github.com/karanzing1992/engagement-core/pull/184) | `b25c66873240a4f1e901874a15a5e9a836dd99f9` | New GES render adapter, private JPEG/Gemini sampler, source/receipt gate, source-only review and test |
| [#186](https://github.com/karanzing1992/engagement-core/pull/186) | `8c5391857446ce0f4c8b6e6fc53134dfb825abfe` | Overlapping title/caption/hook text each placed on independent GES layers |
| [#188](https://github.com/karanzing1992/engagement-core/pull/188) | `9a0240b2017fc10c1a7f6a3a0f77210ea82afd1c` | Private `PRIVATE_GSTREAMER_FAILED` diagnostic and truthful synthetic source description |
| [#190](https://github.com/karanzing1992/engagement-core/pull/190) | `95e97b23489b0ee97746333f63fdd07c03e7741e` | 1s+ exported reels admitted while minimum source-duration admission remains 2.5s |

## Cloudflare live gateway

- Script: `mad-v6-kv-private-beta` in account `3409ce0fa4794fb024c570d141ef0521`.
- Current Cloudflare Worker version: `a980afc6-27a5-4d15-8b86-5f91160b65e1` **100% traffic**.
- Deployment: `f185d1fd-deb8-4b0d-831c-0bef5df121b0` verified by deployment readback.
- Preserved bindings: `DB` (D1), `MEDIA_KV` (private KV), `PROJECT_AUTH` (service auth), `DISPATCH_API` (signed GitHub dispatch service).
- `/health`: HTTP 200, ready=true, dispatch_connected=true, published=false.
- PWA HTTPS: HTTP 200.
- New private completion gate: reject non-GES receipt, missing video frame-decode proof, fewer than 3 checked samples, missing verified audio, SHA mismatch, nonprivate publication, or FFmpeg CLI claims.
- **Workflow filename** `.github/workflows/mad-v6-kv-filmcraft.yml` intentionally remains for pinned OIDC `workflow_ref` compatibility; workflow *execution* uses **GES only**, no FilmCraft. Rename only in an independently tested auth migration.

## Independent certification evidence

1. **Synthetic 1080x1920 video/audio with overlapping titles, captions and hook**: native GES CI PASS, [run #42221266544](https://github.com/karanzing1992/engagement-core/actions/runs/42221266544).
2. **Full live Gemini/Groq/CC0/GES private signed job:** [GitHub run #42221416402](https://github.com/karanzing1992/engagement-core/actions/runs/42221416402) SUCCESS at source SHA `8c539185`. D1 job `v6job-cd3df4b89a244a3d934d2df9eb3c4231` state=review_ready, signed private MP4: 165449 bytes; SHA-256 `9e49d2ee13a8545d8c41e390b8d8d7327f61115ec336e102118a0b158e75c333`; 1080x1920, 30fps, 4s, 3 decoded visible frames, output variance peak 188.66, audio present and original CC0 mixed, FFmpeg invocations 0, published false.
3. **Short output regression:** source-mode GES smoke on [run #42222393722](https://github.com/karanzing1992/engagement-core/actions/runs/42222393722) passed visible video and audio for a 2s output in addition to standard and vertical profiles.
4. **Final post-deployment private signed fixture:** [GitHub run #42222568409](https://github.com/karanzing1992/engagement-core/actions/runs/42222568409) SUCCESS at final main `95e97b2` against Worker version `a980afc6`. D1 `v6job-1f8ec26a9bc64ea2a57c1d3e20f436b9` state=review_ready, 59512 bytes, SHA-256 `131a7fe3203ad1b93f11d555179f753fd7e65051b90a43e40635db1425746fb5`; 1080x1920 2s, 3 decoded visible frames, verified audio, published false, no error code.

All confirmed stage checks were run with **synthetic footage**. The original private guest-video job `v6job-7b2afca305fc4559962d8807c341173b` has expired; no raw guest upload can be reused or inferred from an expired private job.

## Beta status and remaining gates

**Technically live and synthetic end-to-end certified:** genuine GStreamer native H.264/MP4, audible sound, frame content, private signed worker delivery, correct security isolation and bounded expiry.

**NOT certified on actual guest source; NOT cinema-quality certified; NOT authorized for publication.** Owner must provide fresh consenting guest footage through the private beta, render, visually inspect actual cuts/effects/type/brightness and independently play the finished video on Android. Do not claim effect appearance merely because a GES command was accepted; preserve artistic QA.

## Rollback and incident response

- Immediate safe response to a new blank-video issue is **halt new V6 dispatch / fail closed** and preserve/expire private jobs according to policy; no V5 or public media fallback.
- Current compatible GES gateway rollback version `ec2e93ee-83e2-4364-abd3-0a1046abaebc` has the same new strict visual/audio receipt contract. Pair any worker version rollback with compatible owner workflow source and verify bindings, OIDC and D1.
- **Do not silently revert to the old FilmCraft version** `fc981566-98eb-497d-83cb-3a374e016c89`; it accepted video-stream metadata without meaningful visual frames, the defect that triggered the migration.
- Source/finished private videos have time-limited Cloudflare KV retention, and no original or rendered media is uploaded to GitHub artifacts. V5 unaffected.

## Authoritative release references

- [PR #184](https://github.com/karanzing1992/engagement-core/pull/184), [PR #186](https://github.com/karanzing1992/engagement-core/pull/186), [PR #188](https://github.com/karanzing1992/engagement-core/pull/188), [PR #190](https://github.com/karanzing1992/engagement-core/pull/190)
- [Signed Gemini/Groq/GES pass #42221416402](https://github.com/karanzing1992/engagement-core/actions/runs/42221416402)
- [Final signed private GES smoke #42222568409](https://github.com/karanzing1992/engagement-core/actions/runs/42222568409)
- [Master Registry](https://docs.google.com/document/d/1-dSumLKkhmpzqGF2P-4x5_ZNUh9JamH3ApfXv4y4EeM/edit) event #298 was SOURCE_ONLY; a new live certification event supersedes it.
