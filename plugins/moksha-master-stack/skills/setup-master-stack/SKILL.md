---
name: setup-master-stack
description: Onboard a ChatGPT project to the existing Moksha Master capability-reporting system, check installed tool access, identify its source repository, and provide the reusable project instruction. Use when enabling a project or installing the Moksha Master plugin.
---

# Moksha Master setup

Confirm the project identity and whether it is one of the nine allowlisted GitHub repositories. Check the existing user-authorized GitHub, Supabase and Google Drive connections before claiming direct write ability. Read the live protocol at https://github.com/karanzing1992/engagement-core/blob/main/docs/MASTER_STACK_UPDATE_PROTOCOL.md and the working registry at https://docs.google.com/document/d/1-dSumLKkhmpzqGF2P-4x5_ZNUh9JamH3ApfXv4y4EeM/edit when those tools are accessible.

Explain the two routes: GitHub source commit → independent Apps Script → master Doc; verified service-only event → private Supabase inbox → separate inbox publisher → master Doc. Never install duplicate schedulers or request private tokens in chat.

Review `../master-stack-sync/references/project-instructions.md` and provide its one-paragraph Project settings instruction if persistent always-on activation is desired. The plugin Skill can be reused across eligible chats after user installation; it does NOT automatically modify Project settings, connect apps, or grant cross-business access. If no appropriate repository exists, keep reporting manual through a verified service event until enrollment is authorized. Report configured, available and blocked components precisely.

Ashwakaal support channels is a separate registered workstream without a verified monitored repository. For Ashwakaal requests, read https://github.com/karanzing1992/engagement-core/blob/main/docs/ASHWAKAAL_SUPPORT_CHANNELS.md, first verify each official support/community channel and its authorization, and use the existing private event inbox for validated platform-only changes. Never claim that its channels are already connected or publish messages as part of onboarding.
