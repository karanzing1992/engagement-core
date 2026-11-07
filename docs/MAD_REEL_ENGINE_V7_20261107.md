# MAD Reel Engine V7 — Cinematic FFmpeg + licensed-media baseline (2026-11-07)

**Release state: SOURCE-ONLY V7 foundation, stacked atop unmerged V6 FFmpeg draft PR #197. NOT deployed, NOT a finished user Reel or complete V7 beta.** Development branch: `feature/mad-reel-v7-cinematic-audio-20261107`. V5 production unchanged.

## Source of truth and creative goal

Owner direction: move to **V7** after V6 FFmpeg migration. User-supplied private real footage, human-written creative prompt, no invented guest testimony or trademark reconstruction. Goal: move from mechanically correct edited clips to coherent, recognizably premium 30-second vertical films for Moksha and authorized other brands. Reuse owned model chains, FFmpeg and libraries; open-source, free-first. No secret copying or unreviewed publication.

## V7 capabilities implemented in this branch

| Capability | Implementation | Verification |
|---|---|---|
| Reuse V6 for source hash, reviewed cuts, subtitles/titles, rights-admitted existing music, owner-private output | `services/reel-engine/v7-cinema/ffmpeg_v7_cinema.py` calls `ffmpeg_v6_adapter.render` directly | V7 code path + synthetic CI |
| Preset-based cinematic finishing | `elemental-sanctuary`, `sauna-cinema`, `guest-reflections`, `earth-rejuvenation`, `clean-editorial` | Deterministic presets, no model-defined filter strings |
| Second video finishing pass | Controlled EQ contrast/saturation/brightness, vignette, very light grain, in/out fades | H.264/yuv420p, 3 decoded frames, full decode, duration/size checks |
| Sound mastering | One-pass FFmpeg `loudnorm` to -16 LUFS integrated with fade-in/fade-out; retains baseline soundtrack exactly as licensed/mixed by V6 | AAC stereo output required; artistic listening remains pending |
| Safe ownership boundaries | No custom filter strings, shell commands, arbitrary media URL, unapproved publication or invalid presets | Unit negative tests |
| Isolated tests | `services/reel-engine/v7-cinema/test_v7_cinema.py`; additional CI V7 step in inherited `mad-v6-ffmpeg-bridge-ci.yml` | FFmpeg generates synthetic source, renders actual final MP4 and fully decodes |

## V7 production architecture to complete

1. **Input / media vault:** retain V6 Cloudflare owner credentials, verified private source hashes, signed GitHub workflow and job leases, timed download/deletion. Add client-side source preview and audio asset picker to the existing owner PWA. Never publish raw guest content to public GitHub.
2. **Perception / research:** Gemini analyzes at most consented source frames with text observations and factual verification. Groq 120B proposes creative EDL, Groq 20B independently checks exact times/effect validity and computes digest binding. Fail closed on absent paid/free-tier authorization or unknown model outputs. Feature cannot be claimed live until actually exercised.
3. **Creative EDL:** evolve from V6 fixed vocabulary to **bounded per-shot** motion/zoom, ramps, pacing, semantic transitions, subtitle treatments, overlays and beat-aware shot selection. All operations implemented with actual FFmpeg filters, validated visually; no free-form shell, remote template code or invented footage. Current V7 implementation only adds a **global finishing layer**, not these per-shot effects.
4. **Real open-licensed recordings:** reuse V5 `music_provider.py`, V6 `audio_library_v6.py`, approved media assets and `services/reel-engine/audio_sync.py` for beat metadata. Require original-license/composition/recording proof and hashes. V6 proposed private music upload supports a single 4 MiB audio transfer; V7 needs chunked larger recordings and a V7 PWA picker. No procedural or synthesized soundtrack. Keep track/source/license/attribution metadata in the private render manifest.
5. **Audio polish:** source voice protection/ducking against selected human-created soundtrack, environmental foley only from approved real recordings, loudness measurement and speech intelligibility checks. V7 currently performs mastering over V6 audio, **not** independent voice ducking.
6. **A/V/brand QA:** measure H.264/AAC stream durations independently, full decode, three+ sampled frames, source logo identity, title safe areas, shot boundaries, output hash and privacy. Human audio/visual signoff is distinct from technical PASS.
7. **Manual owner workflow:** upload video/rights, choose `v7_preset` and licensed track (or source ambience), enter creative brief, verify generated plan, launch signed V7 job, review result, download within configured private window. Only subsequent explicit publishing consent allows scheduling.

## Manual isolated V7 smoke (developer sandbox, synthetic media)

```bash
python3 services/reel-engine/v7-cinema/test_v7_cinema.py
python3 services/reel-engine/v6-kv-gateway/test_ffmpeg_v6_smoke.py
node --test services/reel-engine/v6-kv-gateway/test_kv_gateway.mjs
```

For an existing rights-cleared local source, a private job manifest can run:
```bash
python3 services/reel-engine/v7-cinema/ffmpeg_v7_cinema.py \
  --spec /private/job/v7-spec.json --receipt /private/job/v7-receipt.json
```
Manifest must include all V6 inputs (`source`, `source_sha256`, `workdir`, `output`, `width`, `height`, `fps`, `cuts`, `operations`, optional `music`, `music_sha256`, `music_rights`) plus `v7_preset`; source/output/approved music must be in a single isolated work directory. Music with unverified rights is rejected.

## Release gates

- **G0 Source / isolated CI:** V7 and inherited V6 synthetic tests green on the exact final V7 branch SHA. No test ever includes real guest footage.
- **G1 Functional integration:** V7 renderer selected from an authorized signed GitHub run, not merely a CLI-only module. Cloudflare receipt, OIDC workflow, PWA UI, music file delivery and expiry all match. Existing V6 and V5 preserved until successful canary.
- **G2 Creative feature parity:** demonstrate actual motion, transitions, captions, brand/logo, beat mapping, licensed-audio reuse and repeatable full-frame QA. No effect is marked verified based merely on a successful command.
- **G3 Real private Reel:** a representative Moksha 30s sauna/ritual film rendered through *all* live Gemini/Groq/FFmpeg stages, with valid consents, source facts, rights-cleared original recording, independent artistic review, phone playback and downloadable output.
- **G4 Owner release:** explicit approval, main merge, co-deployment/rollback evidence and Master Registry LIVE acknowledgement. **Never mark V7 production LIVE from a draft PR or synthetic-only CI.**

## Open Source / Reuse / Cost Gate

- Core: already owned FFmpeg / FFprobe, Python standard library, V5+V6 private transport & audio metadata, GitHub Actions/Cloudflare within existing quotas, Groq/Gemini only when owner/free-tier authorization verified.
- FFmpeg upstream: https://ffmpeg.org/ ; reuse under corresponding configured binary licenses; music CC0/CC BY/public-domain only with separately proven recording/composition rights.
- Additional custom glue: V7 safe finishing preset module and tests only. No new paid APIs, proprietary editors or model subscriptions added.
- Rollback: leave source-only V7 branch inactive, preserve V6 draft and V5 live routes; if deployed later, coordinated rollback of runner/worker/PWA and retain OIDC workflow identity.

## Certification caveat

CI is authoritative only after the final exact SHA has completed; this document and module presence alone are not acceptance. No private production job dispatched, no music uploaded, and no Reel published by this V7 source change.
