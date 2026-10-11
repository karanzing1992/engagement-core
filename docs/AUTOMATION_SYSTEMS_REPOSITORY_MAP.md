# AUTOMATION & SYSTEMS — Source Repository Map
Effective: 11 October 2026
Status: **Verified multi-repository workstream mapping**, not a new single repository or a ChatGPT Project Settings binding.

## Decision
The **Automation & Systems** workstream is coordinated under MOKSHA MASTER. Its codebase deliberately spans multiple existing repositories, so a single "designated source repo" is the wrong audit criterion. Use the verified component-to-repository map below. The operating audit and the installed GitHub watcher both identify these repositories.

| Source repository | Component ownership | Evidence and important boundary |
|---|---|---|
| [karanzing1992/moksha_wordpress](https://github.com/karanzing1992/moksha_wordpress) | Mac Opera native messaging and browser agent; WordPress-side automation, WP Control and integration adapters | [Automation/local-browser-agent branch](https://github.com/karanzing1992/moksha_wordpress/tree/automation/local-browser-agent/tools/local-browser-agent), distinct from default branch monitored for ordinary releases |
| [karanzing1992/android_gpt_bridge](https://github.com/karanzing1992/android_gpt_bridge) | Android/Termux/Shizuku native control and command bridging | [Android bridge](https://github.com/karanzing1992/android_gpt_bridge), private access required; no claim the device is currently online |
| [karanzing1992/engagement-core](https://github.com/karanzing1992/engagement-core) | Shared workflows/orchestration, media production, social-channel adapters, documentation and automation registry | [Shared components and source](https://github.com/karanzing1992/engagement-core) |

Associated live systems (not GitHub source repositories): [Supabase project saczglesalubroyaucqe](https://supabase.com/dashboard/project/saczglesalubroyaucqe), WordPress sites and device-local bridges. Their runtime configuration and deployment evidence must be verified separately.

## Exact reporting route
- Material *committed changes* in those three repositories: **Route A**. Ensure a final default-branch source commit uses `STACK CHANGE:` at the start when material; the existing Google Apps Script already monitors all three by default branch.
- **Important branch caveat:** changes that exist *only* on `automation/local-browser-agent` or any other non-default branch are **not yet watched by the independent Google Apps Script**. Promote through a reviewed merge to the monitored default branch, or submit a verified event through Route B when appropriate. Never claim GitHub monitoring of an unmerged branch.
- Runtime-only WordPress/Edge Functions/Opera/Nokia/Android changes without a monitored default-branch commit: **Route B**, the private `public.submit_master_stack_change` inbox and the verified separate publisher. Supply authoritative evidence, test state and correct project identity.
- Reporting writes to the Google Doc do not modify production configuration and must never advance source cursors unless documentation is committed and verified.
- An automation request spanning more than one component must identify *every* impacted repository. Do not invent a single repository mapping for the whole ChatGPT Project.

## Audit treatment
**Automation & Systems repository mapping: PASS (verified multi-repository map).**
This is an explicit source governance mapping, not proof that this ChatGPT Project's inaccessible Settings have an attached or designated repo. It is sufficient for routing workstream changes across the monitored three repos and private non-repository event path.

**Source evidence:** [Automation & Systems consolidated technical audit](https://docs.google.com/document/d/1ybmMCLX_9gy2SUAL9_h-8HpTWBVWt_ksbTShHn1FF5w/edit), 11 October 2026.
**Canonical reporting policy:** https://github.com/karanzing1992/engagement-core/blob/main/docs/MASTER_STACK_UPDATE_PROTOCOL.md
**Master registry:** https://docs.google.com/document/d/1-dSumLKkhmpzqGF2P-4x5_ZNUh9JamH3ApfXv4y4EeM/edit
