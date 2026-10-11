# Moksha Reel & Shorts Studio — reusable Skill source

**Status:** Skills-only portable plugin source, v1.0.0 (2026-10-11). Source packaging **does not automatically install the plugin**, enable any ChatGPT Project instruction, deploy a worker, or authorize publishing.

- Skill entrypoint: [skills/reel-shorts-production/SKILL.md](skills/reel-shorts-production/SKILL.md).
- Specific engine and platform evidence: [references/provenance-and-operations.md](skills/reel-shorts-production/references/provenance-and-operations.md).
- Built on existing `engagement-core` Reel Engine v0.5 and WordPress Engagement Core; do not copy proprietary or customer/guest data between brands.
- Invoke for making original Reels, YouTube Shorts, Snapchat Spotlights, nature-sound videos, and managing multilingual / multi-channel release controls.
- Brand configured per job: Moksha / Andaz or another explicitly authorized brand. Moksha's official logo and Goa-first visual policy must not be silently generalized to unrelated tenants.
- Provides instructions and quality gates only; rendering requires an accessible local FFmpeg/runtime or verified deployed worker, and scheduling requires a separately connected publisher.
- Manual review of source provenance/licensing is required before any public post. A file rendered to MP4 is **not** a permission to publish it.

**Rollback:** revert the source commit; no WordPress, Metricool, public channel, or engine runtime is changed by installing the Skill source.

**Master Registry:** report through Route A in [MASTER_STACK_UPDATE_PROTOCOL.md](../../docs/MASTER_STACK_UPDATE_PROTOCOL.md); a final monitored `STACK CHANGE:` commit is ingested by the existing independent Apps Script, never manually duplicated.
