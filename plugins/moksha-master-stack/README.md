# Moksha Master Stack — portable Skill/Plugin

Reusable instructions for **all participating ChatGPT Projects**, packaged as a **skills-only** portable Agent Plugin. It does not contain credentials, service-role keys, scheduled jobs, production commands or data transfers.

The central verified protocol is https://github.com/karanzing1992/engagement-core/blob/main/docs/MASTER_STACK_UPDATE_PROTOCOL.md . The canonical Google Doc is https://docs.google.com/document/d/1-dSumLKkhmpzqGF2P-4x5_ZNUh9JamH3ApfXv4y4EeM/edit .

## Install

- **ChatGPT:** open **Plugins → Plugin Creator** and request creation/import of the plugin from the reviewed local ZIP or this GitHub source. Use the plugin in chats where available. Plugin installation and Skills support vary by plan/workspace; connect GitHub, Supabase and Google Drive separately. Neither a ZIP nor a GitHub commit installs a plugin in the ChatGPT account automatically.
- **Eligible Skills page:** open **Plugins → Skills → Create → Upload from your computer** and upload a dedicated skills bundle if Skills upload is available to your plan. Standalone Skills in ChatGPT are generally eligible for Business, Enterprise, Healthcare and Edu.
- **Codex:** use an eligible plugin marketplace or skill directory with the same `SKILL.md`.

A plugin provides a **reusable workflow**, not organization-wide authorization. For always-on behavior in an existing ChatGPT Project, apply the short text in `skills/master-stack-sync/references/project-instructions.md` via Project settings. Underlying GitHub repository instructions already include the tested synchronization protocol.

## On-demand sync target (16 Oct 2026)

The canonical Master now prefers an explicit approved change event → verified Docs marker → owned Plugin release → subscriber acknowledgment. The existing source at `services/master-stack-worker/apps-script/Code.gs` adds a signed `doPost` entry point and `services/master-stack-worker/dispatch-on-change.py` signs per-change events; **neither is a verified deployed integration yet**. Do not disable the old timed publisher until both GitHub and platform-only event routes pass the cutover tests in `docs/MASTER_STACK_UPDATE_PROTOCOL.md`. A GitHub update alone never refreshes this installed plugin or an old chat.

## Validation

Test in a fresh project chat with "Use the master-stack-sync skill to check which capabilities from this project must be reported". Confirm it uses *this project's* identity and existing connected apps, and accurately labels source-only changes. Do not generate canary commits to production or use real guest data. The external Google worker's independent source-to-Doc canaries have already passed.

## First-party FFmpeg Reel Studio

- `skills/ffmpeg-reel-studio/SKILL.md` registers the owned FFmpeg/Reel Engine v0.5 workflow, real-media-first ingestion, audio/caption/logo QA, platform output, and rights/approval gates. Descript is disconnected; do not route through it.
- The in-depth canonical production checklist remains at `../moksha-reel-shorts/skills/reel-shorts-production/SKILL.md` and the live installed owner plugin `moksha-master-stack-reinforced` may have a later release than this portable source. Updating a GitHub skill does not automatically refresh that installed plugin.

## Structure

- `plugin.json` — portable Agent Plugins manifest with onboarding skill.
- `skills/master-stack-sync/SKILL.md` — active change-reporting workflow.
- `skills/master-stack-sync/references/project-instructions.md` — optional per-Project always-on settings.
- `skills/setup-master-stack/SKILL.md` — first-use connectivity and enrollment checklist.

This skills-only plugin does not bundle MCP servers; it uses previously authorized connected apps when present. Nothing in this repository grants those external permissions.
