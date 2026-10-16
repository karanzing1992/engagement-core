---
name: reel-shorts-production
description: Make, inspect, repair and safely distribute short-form Reels, Shorts, Stories and Spotlights using user-owned or properly licensed clips, clean continuous nature audio, an approved brand logo, safe-area typography, and authorized platform-specific publishing. Trigger for reel creation, editing, caption placement, audio repair, covers, distribution, or multi-channel publishing. Never claim a post is live from a pending schedule.
---

# Reel & Shorts Production — FFmpeg-first production checklist v1.1.0

**Editor policy (16 October 2026):** Descript has been disconnected at the owner's request. The first-party FFmpeg renderer, existing Reel Engine v0.5, local attachments, official brand assets and previously approved footage/edit timeline are the DEFAULT. Never direct a reel job to Descript or a generic editor out of habit, or treat an editor's description/storyboard as a finished cut. Do not install any replacement SaaS by default. Keep an approved timeline, change only required music/scene/closing layers, then prove the rendered result exists. For launch films, consult the approved retreat brief and verify all guest footage and licensed aerial/music inputs before using them. The dedicated Master skill is [ffmpeg-reel-studio](../../../moksha-master-stack/skills/ffmpeg-reel-studio/SKILL.md).

**Goal:** deliver a real, playable, reviewed MP4—not a storyboard, placeholder download, unverified render, or a claim that a tool did something. This Skill is guidance, not direct access to a render host or social accounts. Reuse established tools and first-party source code.

## 1. Intake and rights

- Resolve duration (default 30 seconds for an everyday wellness Reel), aspect 9:16, mood, one concept, intended platforms, and the account/brand. Choose creative defaults; ask only for critical unresolved permissions.
- Use genuine user-provided files already mounted in the current execution runtime **before** routing through third-party editing connectors. Probe exact file paths with `ffprobe`; locate an actual mounted path or properly materialized file before asserting existence. Never guess a sandbox path or assume ChatGPT attachment IDs are accepted by Canva/Descript.
- For Moksha: **Goa first, India second** unless the user explicitly requests another region. Every visual clip must have accurate source, geography and rights evidence. Distinguish user-supplied-but-not-geolocated from independently human-verified. No mislabeled international scenery, fabricated filming claims, or stock without checked reuse terms. Record attribution when the license requires it.
- Use the **authentic** approved Moksha logo; never fabricate, redraw or approximate it. Pinned source sha256: `76e89b83667827da4b5d89143fb267f4000a9392eff685129c838c3d0b24748c`; reject mismatch. Prefer the verified official brand resolver. Brand identification should appear **once near the end**, not repeatedly on every scene.
- Separate per-brand assets, accounts, customer data and publication permissions. Andaz public name: **Andaz Vibe Stay - Arambol, Goa**. Other brands must supply their own approved logo and geo rules; do not reuse Moksha's credentials.

## 2. Composition and audio — fail closed on contamination

- Pick clean natural visuals with a calm story arc. For 30 seconds, about 4–6 scenic beats; do not add scenes just to increase cuts. Keep footage relevant to the brief, and visual transitions unobtrusive.
- Normalize input video to consistent **1080×1920**, square pixels (`setsar=1`), `yuv420p`, **30fps**, H.264; limit stretches and avoid cropping faces/landmarks/text. Handle footage with mixed frame rates, source sound and/or no audio.
- If the brief asks for **nature sounds only**, drop **every original audio track** using `-an` before assembly. Never use an old final MP4 as a new audio source. Add only a separately verified, appropriately licensed natural recording (ocean/waves/rain/birds) with no speech or music. Do not describe music as nature ambience.
- **Critical historical defect:** a previous output was 30 seconds but the replacement audio stopped at **10.6 seconds**. Do not rely on `-stream_loop` alone: explicitly prepare a continuous 30-second bed using seamless looping or overlap-and-`acrossfade`, then trim to exact program duration, add a gentle beginning/end fade, and map only the new bed.
- Probe **independently** the encoded audio and video stream durations and ensure the audio spans the full program with no discontinuity around splice points. Inspect waveform/RMS/short-time silence at 0, 10, 20 and 29 seconds; manually listen when possible. A technical silence scan is not proof that speech or music is absent; use direct listening/source isolation for that assurance.
- Keep natural ambience audible but comfortable; no sudden gain spikes, clicks or hard cutouts. Do not add narration/music unless requested.

## 3. Readable text and restrained brand placement

- Use **one caption track only**: at most 1–2 short lines on screen, readable within ~1 second, centered or optically aligned, generous line spacing, legible large type for a mobile 1080-wide video.
- For Instagram/Snapchat safe viewing, avoid top and bottom interface regions and screen-right interactions. Default working text area: roughly **x=120–960 px, y=300–1420 px** on 1080×1920, adjusted by inspecting actual frames. Put crucial words toward the middle, not the footer.
- Favor high-contrast ivory/white on a **subtle localized dark translucent band/shadow** over bright sand, sea foam, skin or foliage. Maintain consistent position between scenes, avoid overlapping moving subjects, and use restrained fades.
- Keep copy non-repetitive. For a calm 30-second Reel, example beats: “A moment to slow down” → “Breathe in” → “Breathe out” → “Release the rush” → “Stay with the tide.” The official brand mark appears on the final card only.
- Review contact sheets at the start, every cut, around the scene after each cut, last text event, and final logo hold. Check that title fragments or source-embedded text are not exposed/truncated at ~25 seconds.

## 4. Encode, verify, deliver

- Export the master as H.264/AAC MP4, 1080×1920 at 30fps, `-movflags +faststart`; optionally a lighter share copy, preserving the same content. Exact target **30 seconds** unless instructed otherwise.
- Validate by `ffprobe`: width, height, fps, video duration, **audio stream duration**, pixel aspect, expected streams, file size and nonzero bytes. Check coverage and sync across the full timeline, not just the first ten seconds.
- Review extracted first/middle/end frames for typography, verified branding, transitions and source visual artifacts. Check audio independently for unintended music, voiceover and dropouts.
- Only link downloads that were generated or verified at the exact output path in the active runtime. Do not invent links from filenames or a prior session.
- Deliver the final video, optional mobile copy and cover. Treat **asset completed**, **scheduled**, **platform accepted**, and **publicly published** as different statuses.

## 5. English and other-language publishing

- Never publish simply because a render succeeded. Obtain/retain explicit user authority to publish **and** verified location/source rights. If rights or provenance remain unresolved, prepare drafts or a nonpublic preview and disclose the blocker.
- Discover exact connected brand accounts and supported posting formats from the publisher. Reuse the existing Metricool and first-party WordPress Engagement Core when authorized; do not unnecessarily deploy a new integration. Check the day's schedule first to avoid duplicate posts.
- For English-only or “exclude Russian channels” instructions, enforce a **destination allowlist** for this campaign; exclude Telegram Russian groups, VK, OK, Russian Instagram and any other Russian-targeted accounts regardless of language used in the caption. Do not infer language preference for future campaigns.
- Prepare **platform-specific copy** instead of a single generic dump: hooks and save/comment CTA for Instagram, shorter X/Bluesky/Threads, substantive wellbeing angle for LinkedIn, searchable title/description and declared audience for YouTube Shorts, video Pin with **verified numeric Pinterest board ID**, and Google Business Profile **video gallery/photo type** where applicable. Stories have no standard post caption.
- Do not silently omit Pinterest, LinkedIn, Google Business Profile, Snapchat or WhatsApp from an “all channels” request. Give each a verified result (queued, accepted, unsupported, requires manual action, blocked), not a fabricated success. Snapchat profile read access does not prove publish access: prior Spotlight attempt returned HTTP 403.
- For any scheduler, query/read back the job IDs, per-network statuses, exact scheduled local times and destination; distinguish `PENDING` from `PUBLISHED`. Monitor until actual platform completion when tools and user request allow. Never claim that “queued everywhere” means successfully live everywhere.

## 6. Platform architecture, cost, and escalation

- **Fastest completed route:** local mounted ChatGPT media → FFmpeg direct render → verified artifacts → optional approved platform scheduling.
- **Other usable route:** WordPress **Tools → Reel Uploads** accepts authenticated 4 MiB chunks and an existing short-lived GitHub OIDC private rendering worker; verify its current live state and user authorization, never assume setup from repo existence.
- **Released but not permanent cloud hosting:** `engagement-core` Reel Engine v0.5 GHCR image with authenticated 8 MiB resumable 1 GiB uploads, queued multi-clip API and official-logo verifier. The CI-built container is not itself a running long-lived upload endpoint.
- Preserve privacy, avoid downloading private media into public repositories or GitHub artifacts, and avoid wasteful repeat renders when a small audio mux or caption-layer fix is sufficient.
- If the task creates a new **technical capability**, report the verified source change through the existing Master Stack Sync Skill and monitored repository route; routine social posts and daily captions do **not** create Registry events.

See [provenance-and-operations.md](references/provenance-and-operations.md) for grounded engineering evidence and known problems.
