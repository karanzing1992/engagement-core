# Engagement Core CRM — G1 Mobile-First Interactive Wireframes

**Status:** DESIGN DRAFT / BROWSER QA PASSED / INDEPENDENT ART REVIEW PENDING / OWNER VISUAL ACCEPTANCE PENDING  
**Branch:** `feat/eccrm-mobile-wireframes-g1-20261026`  
**Workstream:** Engagement Core CRM only · **No WordPress, customer data, messaging, AI or production code changed.**

## What this is

A locally runnable, editable HTML/CSS/JavaScript **wireframe prototype** for the 15 unbuilt CRM modules. It is a design/interaction reference, **not** the installed WordPress CRM UI or a live integration.

- `index.html` — accessible responsive navigation shell
- `wireframes.css` — custom Tabler-inspired, mobile-first design tokens and layouts
- `wireframes.js` — 15 screen definitions, two navigable user journeys, synthetic fixtures, five UI states per screen
- No CDN, paid components, dynamic imports, external assets or network requests.
- Open `index.html` in a browser. The hash URL selects a screen (`#inbox`, `#conversation`, `#profile`, `#pipeline`, etc.).

**Design inventory:** S01 Inbox; S02 Conversation; S03 Customer 360°; S04 Pipeline; S05 Deal Detail; S06 Tasks; S07 Channels; S08 AI Assistant; S09 Automation; S10 Campaigns; S11 Calendar; S12 Reports; S13 Team; S14 Integrations; S15 System & Data.

**Interaction journeys:** Inbox → Conversation → Customer 360° and Pipeline → Deal Detail → Task.

**Interaction state simulator:** normal, empty, loading, error and permission-denied on every screen. All illustrations and fixtures use synthetic values, with explicit "wireframe / no CRM updates" notices. Even the reply composer **does not send**.

## Actual Dell G1 QA results (26 Oct 2026)

Source checked out into isolated detached worktree `/var/lib/generic-linux-automator-exec/eccrm-g1-wireframes-20261026`, unchanged original CRM development worktree.

- Playwright + Chrome exercised 15 distinct routes, normal/empty/loading/error/denied states, both journeys, mobile drawer, keyboard Escape, navigation, and browser errors.
- **253 / 253 checks passed** after correcting the test to dismiss the modal navigation drawer with Escape rather than clicking an obscured menu button.
- Tested widths: **320, 360, 375, 390, 414, 768, 800, 1024, 1440 CSS pixels**; no document-level overflow.
- **18 actual screenshot files** and full machine-readable report retained in dedicated Dell QA directory:
  `/var/lib/generic-linux-automator-exec/eccrm-g1-wireframes-20261026-qa/`
- JavaScript source SHA-256: `a9fa3bcaaa7b0708b21b42c566521e6cc5fa5fa0e4ddf9f6c3bfa1693438c92a`.
- Assertions do **not** prove accessibility WCAG conformance, professional visual excellence, usability with real users, or actual CRM backend behavior.

## Visual / art-director quality gate

Require independent review of:
1. Typography scale, tap targets, contrast and legibility in 320/360/390px screenshots.
2. Navigation comprehension, perceived density and avoidance of dead-end flows.
3. Three-pane desktop conversation vs mobile single-pane journey.
4. Safe handling of the synthetic badge, live/unavailable status and outbound messaging.
5. Customer data provenance, channel-status distinctions and error-state clarity.
6. Focus management, touch keyboard, safe areas, screen zoom and dark-mode behavior.

The installed **Shaadi AI Art Director is project-specific**, operates on a 30-minute timer, and last reported `waiting_for_local_vision_model`; **do not copy its data or claim it reviewed CRM**. Manager V3 observes statuses continuously, not creative iteration. A CRM-specific art-direction receipt must be source-bound and human-reviewed or use a separately verified image-capable local model **for advisory critique only**. No automated release approval.

## Current next gate

**Owner reviews editable prototype source and the actual screenshot pack.** The separate governed Tool Yard `engagement_core_crm / crm_wireframe_g1_v1` admission contract is pinned and scoped; exact owner-controlled cryptographic intake approval remains required before executing additional controller `dev_project_build` jobs. Do not self-create an owner approval ledger entry.

For the full requirements, reference `docs/ENGAGEMENT_CORE_CRM_V1_MOBILE_WIREFRAME_DEVYARD_BRIEF_20261026.md` on main.

**No G2+ functional development, live CRM integration, PR merge or production deployment without a separate owner approval.**
