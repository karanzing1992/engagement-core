---
name: ffmpeg-reel-studio
description: Use to render, revise, verify or hand off Reels, Shorts, Stories and Moksha launch films with first-party FFmpeg, existing footage, official logos and licensed music. Descript is disconnected; never use a third-party editor by default.
---

# Moksha Master — FFmpeg Reel Studio (16 October 2026)

**Scope:** reusable production Skill guidance, not a new cloud renderer or publishing credential. This is an addition to the existing source-based Master plugin; the owner-maintained *installed* `moksha-master-stack-reinforced` plugin has an independently versioned skill package. Authoritative implementation: [Reel Engine v0.5](https://github.com/karanzing1992/engagement-core/tree/main/services/reel-engine), [Full Reel & Shorts Skill](https://github.com/karanzing1992/engagement-core/blob/main/plugins/moksha-reel-shorts/skills/reel-shorts-production/SKILL.md), [Media Studio runbook](https://github.com/karanzing1992/engagement-core/blob/main/docs/reel-engine-assistant-operating-procedure.md), [Moksha Social Golden Rules](https://docs.google.com/document/d/1BgCQcK6k4byjGI3x8V01iXWPL5yFKNIEmJ4WxiklEbk/edit).

## Default execution path — own FFmpeg, not Descript

1. Descript was explicitly disconnected by the owner on 16 October. **Do not call, install, re-connect, require or automatically fall back to Descript** for any existing Moksha or approved brand video. No storyboards, descriptions or fake links in place of actual finished MP4s. Do not rely on Canva or other proprietary video editors as the primary cut pipeline.
2. Inspect already mounted original attachments, authenticated Google Drive media, approved Master asset Library, verified render archives and ongoing edits. Before redownloading or rerendering, identify exact local paths, hashes, licensed usage, clip durations and the last approved timeline; use `ffprobe`. Prefer untouched source assets to recompressed exports. Do not invent private paths.
3. Use the **existing** `services/reel-engine/` FFmpeg renderer / multi_renderer / audio_sync / captions / verified_logo / quality modules, not a new film-making platform. Primary route: local/mounted media → existing FFmpeg edit → tested MP4. Only if native bytes are unavailable, verify WordPress Tools → Reel Uploads (4 MiB resumable workflow) or the private Reel Engine v0.5 endpoint (8 MiB chunks, authenticated HTTPS, persistent storage). A released GHCR image is not proof that any server is running.
4. For targeted revisions (new soundtrack, more live people, grand Goa beach aerial opening, strong closing shot) **preserve the approved cut** and replace only selected layers/shots. In a launch video, match actual approved retreat itinerary and participant footage. Never assert a person endorsed a product or appeared in a clip that has not been verified.

## Brand, source and sound gates

- Moksha authentic official logo only: original SHA-256 `76e89b83667827da4b5d89143fb267f4000a9392eff685129c838c3d0b24748c`. Use verified original artwork or a true-alpha derivation from the real artwork; never AI-redraw or place a black JPEG rectangle over a shot. Keep correct proportions and inspect alpha.
- Goa-first, India-second real footage. For Moksha Reset, use genuine Goa/Arambol coastal scenes, nature, people, actual Moksha venue, verified approved Jyotsana Chandola Singh clips. Stock aerials must be genuinely from claimed geography with confirmed commercial-license scope; note footage ownership vs stock and maintain source URLs and attribution.
- Each new episode gets fresh footage/music where possible. Do not reuse yesterday's video, music or scene sequence as an undocumented shortcut. Daily knowledge Reels are informative and non-sales; do not mix full animation and live real-people material in the same wellness guide unless the owner authorizes it. Use the current brand handbook and Social Golden Rules.
- Music: **real, already-composed, licensed/open-source human-made tracks**, NOT synthetic, MIDI or improvised filler music. Verify recording/composition commercial and platform rights, creator credit and attribution. Nature-only briefs remove all original audio and mix independently verified clean ambience, checking total audio coverage.
- Caption track is singular and mobile-readable, preferably FFmpeg/libass, 1–2 short lines and safe margins. Never allow overlapping source text, giant illegible keyword blocks, missing glyphs or title text that survives into unrelated shots. Use normal editorial spacing and the verified official logo.

## Export and quality gate

- Default 9:16 1080×1920, 30fps, square pixels, yuv420p H.264 video/AAC audio MP4 with `-movflags +faststart`; produce 4:5 or platform-native variants only when justified by the platform rules.
- Verify actual video **and audio stream durations separately** with `ffprobe`; check volume clipping, unwanted narration, fades, encoding, file size, timecoded captions, transitions, faces, contrast and closing frame. Guard against the historical 30-second-video/10.6-second-audio defect. Inspect sampled frames from opening, cuts, center and closing, and listen when available. A nonpublic draft or storyboard is never a completed render.
- Store a project manifest: original asset ID/path/hash, date, geography, source URL, rights, approval, track license/credit, chosen trims, scene order, caption timecodes, official logo hash, render settings, QC summary and output artifact paths. Keep private files/guests off public GitHub.
- Rendering and publishing are separate actions. Publish only with owner consent and verified rights, using existing authorized Engagement Core/Metricoool/other approved channels. For 'all channels', examine Russian-language Telegram as appropriate plus Pinterest, LinkedIn, WhatsApp, YouTube, Facebook, Instagram, GBP and others. Report each destination as rendered, approved, queued, accepted, confirmed published or blocked; never invent success.

## Reuse / cost / rollback / central registry

**Golden Rule 0:** inspect already-owned Reel Engine v0.5 and its pinned MIT-licensed `ffmpeg-mcp-video-editor` upstream as documented in its README; prefer free FFmpeg/libass and legitimate owner-held source assets. Verify licenses, maintenance, security, operational storage/compute cost and rights before adding new dependencies. Paid editors are not needed by default, and spending requires the separate criticality/approval gate.

A source-only Skill update cannot prove live engine access, new media asset availability, runtime deployment, or a rendered file. Roll back the Skill commit/edit layer if necessary; preserve previous approved sources and private projects. Report meaningful verified changes through the existing [Master Stack protocol](https://github.com/karanzing1992/engagement-core/blob/main/docs/MASTER_STACK_UPDATE_PROTOCOL.md), GitHub Route A; never make a second sync worker or duplicate registry entry.
