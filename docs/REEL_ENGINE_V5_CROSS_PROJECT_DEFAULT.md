# Reel Engine V5 — Default for New Video/Reel Jobs Across Projects

**Effective:** 02 Nov 2026. **Owner rule:** route *new* social/video creative tasks to Reel Engine **V5.0.0**, never silently back to V4.1.

## Inheritance

This is a cross-project **production selection rule**, not a claim that all creative tools are live or every output is commercially ready. Each project supplies **its own brand**. Moksha's Forest/Gold palette and creative voice are **not inherited** by Andaz, DeluluTech, the game, recruitment or community projects.

In scope: Instagram Reels, Facebook Reels, YouTube Shorts and longer video marketing, Snapchat promos, events, product demonstrations, social trailers, website promos, guest-approved footage edits. The game project's core Three.js runtime, code, animation, character and level generation remain outside Reel Engine.

Default roles: **Groq GPT-OSS 120B creative direction**, **Gemini 3.8 Flash / tested 3.6 Flash fallback** for vision, **Groq 20B** for bounded execution, **FFmpeg and FilmCraft MCP** through individually verified adapters. A model may propose novel effects; unknown commands remain deferred, not executed.

**Music:** reuse actual **CC0, public-domain or verified CC BY** existing recordings. Openverse discovery with Wikimedia Commons fallback. Composer/source identity, recording license, legitimate use, attribution and audio SHA must be retained. Never compose a synthetic replacement soundtrack or treat metadata search as license verification.

## Project routes

- Moksha Wellness: all new wellness/ritual Reels and videos; retain Moksha Golden Rules, brand handbook and M3/M4 sign-off.
- Andaz Vibe Stay: promotional travel/hospitality Reels, with *Andaz* branding.
- DeluluTech / WP Manager / CRM: product demonstration and marketing, no private customer data.
- Goa Commune / Community: event and community videos, participant permission.
- Synergistica Staffing: employer brand, vacancy/recruitment claims verified.
- Shaadi Aunty's Dodge: trailer/short-form video only; no changes to core game rendering or rigged animations.
- Future owner projects: video jobs inherit V5 unless a project-approved override is explicitly specified.

## Enforcement contract

A new work packet must identify `project_id`, `job_type`, `reel_engine_version=5.0.0`, project brand reference, media rights, operation and model eligibility, owner release gate. The canonical routing map is [ops/media/reel-engine-routing.json](../ops/media/reel-engine-routing.json); V5 provider config is [v5_config.json](../experiments/reel-engine-v5/v5_config.json).

This rule must be respected by MAD Manager and AI agent handovers. An existing queue/job is *not* migrated or replayed. V5 is the **selected version for new briefs**; **V4.1 is the last technically verified real-footage preview pipeline**. V5 still lacks full rights-cleared real-video/audio release certification. If an operation is unavailable, emit a blocked/deferred receipt and request implementation, not secret use of the old engine. Publishing never happens without owner approval. Free-tier budget, source truth, license/consent and Mac thermal safeguards stay active.

## Evidence / rollbacks

V5 merged baseline PR #97: https://github.com/karanzing1992/engagement-core/pull/97
V5 code and master document: https://github.com/karanzing1992/engagement-core/blob/main/docs/MAD_REEL_ENGINE_V5_BASELINE.md
Google canonical V5: https://docs.google.com/document/d/1gn1oAGwG55_CYKGnYIoWM2tCDMEpEDcXI_t50Kvg1nU/edit
Moksha Technology Master: https://docs.google.com/document/d/1-dSumLKkhmpzqGF2P-4x5_ZNUh9JamH3ApfXv4y4EeM/edit

Rollback the routing rule by a reviewed source change; do not revert previous real-media technical receipts or remove manager/Mac safeguards.
