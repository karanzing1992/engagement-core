---
name: setup-master-stack
description: Onboard a ChatGPT project to the existing Moksha Master capability-reporting system, check installed tool access, identify its source repository, and provide the reusable project instruction. Use when enabling a project or installing the Moksha Master plugin.
---

# Moksha Master setup

## Mandatory Golden Rule 0 — research and reuse before every action

For every linked project, look first in the Master Registry/approved code and research maintained public open-source Git repositories and other lawful reusable foundations before design, development, automation, integrations, tools or technical changes. Evaluate license, security, maturity, feature fit, compatibility, cost and QA; adapt rather than recreate. Document candidate sources, reuse choice, version/license, tests and rollback for nontrivial work. Never approve a from-scratch build without documented absence of suitable options AND the user's explicit exception approval. Include this rule in the project's actual instructions; updating central Docs alone does not edit those settings. Canonical policy: https://github.com/karanzing1992/engagement-core/blob/main/docs/MASTER_STACK_UPDATE_PROTOCOL.md .

Confirm the project identity and whether it is one of the nine allowlisted GitHub repositories. Check the existing user-authorized GitHub, Supabase and Google Drive connections before claiming direct write ability. Read the live protocol at https://github.com/karanzing1992/engagement-core/blob/main/docs/MASTER_STACK_UPDATE_PROTOCOL.md and the working registry at https://docs.google.com/document/d/1-dSumLKkhmpzqGF2P-4x5_ZNUh9JamH3ApfXv4y4EeM/edit when those tools are accessible.

Explain the two routes: GitHub source commit → independent Apps Script → master Doc; verified service-only event → private Supabase inbox → separate inbox publisher → master Doc. Never install duplicate schedulers or request private tokens in chat.

Review `../master-stack-sync/references/project-instructions.md` and provide its one-paragraph Project settings instruction if persistent always-on activation is desired. The plugin Skill can be reused across eligible chats after user installation; it does NOT automatically modify Project settings, connect apps, or grant cross-business access. If no appropriate repository exists, keep reporting manual through a verified service event until enrollment is authorized. Report configured, available and blocked components precisely.

Ashwakaal support channels is a separate registered workstream without a verified monitored repository. For Ashwakaal requests, read https://github.com/karanzing1992/engagement-core/blob/main/docs/ASHWAKAAL_SUPPORT_CHANNELS.md, first verify each official support/community channel and its authorization, and use the existing private event inbox for validated platform-only changes. Never claim that its channels are already connected or publish messages as part of onboarding.

## Automation & Systems / Ashwakaal verification rules
For the Automation & Systems ChatGPT Project, **do not ask for a single source repository**. The verified governance map is `moksha_wordpress` (Mac Opera/browser/WP), `android_gpt_bridge` (Android bridge), and `engagement-core` (shared orchestration and channels). Check the relevant component and branch; Google Apps Script watches default branches, not non-default feature branches. Source: https://github.com/karanzing1992/engagement-core/blob/main/docs/AUTOMATION_SYSTEMS_REPOSITORY_MAP.md

Ashwakaal Support Channels' current channel-coverage state is **NO_VERIFIED_CHANNELS** (zero ownership-backed channels, not a claim none exist). Do not upgrade to active/verified without an official channel URL and authorized operator evidence. Refer to https://github.com/karanzing1992/engagement-core/blob/main/docs/ASHWAKAAL_SUPPORT_CHANNELS.md and use Supabase Route B for any future verified platform-only changes.

Check the [Master Health Runbook](https://github.com/karanzing1992/engagement-core/blob/main/docs/MASTER_STACK_HEALTH_RUNBOOK.md) and explicitly verify the Route B hourly automation is enabled, that Supabase pending/verified review lag is acceptable, and that real Google Doc markers exist. Apps Script trigger status requires its own Executions evidence. Cron success is not Docs success. Never claim installed Skill parity with GitHub if the loaded Skill is an older release.
