# Engagement Core CRM — Mobile-First Wireframes, Build Contract & Dell Dev Tool Yard Intake

**Spec version:** 1.0 · **Date:** 2026-10-26 · **Status:** OWNER-REQUESTED DISPATCH, PLANNING/WIREFRAME GATE ACTIVE · **Production:** NO-GO  
**Project ID:** `engagement_core_crm` · **Owner/source:** `karanzing1992/engagement-core`  
**Current source:** Draft [PR #74](https://github.com/karanzing1992/engagement-core/pull/74) on `feat/eccrm-tabler-ux-20261025`, v0.2.0-dev; Draft [PR #73](https://github.com/karanzing1992/engagement-core/pull/73) on `feat/eccrm-wp-native-foundation-20261025`. Both unmerged.  
**Earlier architecture:** [WordPress CRM source-of-truth](ENGAGEMENT_CORE_CRM_SOURCE_OF_TRUTH_20261025.md).  
**Real browser QA:** [v0.2.0 mobile QA and receipts](https://github.com/karanzing1992/engagement-core/blob/feat/eccrm-tabler-ux-20261025/docs/ENGAGEMENT_CORE_CRM_TABLER_MOBILE_UX_QA_20261025.md).  
**Dispatch control:** Owner instructs the Dell Dev Tool Yard to proceed. **Gate 0 project/lane onboarding and Gate 1 complete editable wireframes are in scope immediately.** Gate 2+ feature implementation requires the owner to accept the frozen wireframe package and approved implementation scope; owner approval of this dispatch does not override that distinct design gate.

## 0. Non-negotiable outcome and scope protection

Deliver a **commercially redistributable, independent, self-sufficient WordPress CRM** with a real mobile-first user experience, unifying customer relationships, inbox, sales, tasks and future integrations while **retaining all authoritative CRM data and operational state in the customer WordPress installation**. External AI is optional, least-privileged and provider-neutral; never a required datastore or dependency. Reuse first-party code and proven FOSS interfaces rather than build an entirely new CRM core or recreate an offsite CRM SaaS.

The owner rejected v0.1's generic WordPress admin form as visually inadequate. Preserve v0.2's **working Tabler 1.7.0 UI**, contact APIs, genuine counts/history, navigation, form validation, identity and events tables. Do NOT downgrade UI, substitute mock buttons, or present a wireframe as a working product. Do NOT silently broaden to live sites, sending messages, real customer imports, purchases, subscriptions or OAuth account linking. Separate Ashwakaal — Support Channels as a different workstream (credentials, permissions, accounts, customer data and reporting).

Stages are `PROPOSED → BRIEF_FROZEN → TOOL_FIT_VERIFIED → WIREFRAME_REVIEW → OWNER_DESIGN_ACCEPTED → DEVELOPMENT_VERIFIED → INDEPENDENT_QA_PASSED → USER_TEST_ACCEPTED → RELEASE_AUTHORIZED → PRODUCTION_VERIFIED`. Never skip or relabel.

## 1. Frozen information architecture

Five primary navigation destinations; everything else is a nested workflow, not fifteen fixed bottom tabs.

| Mobile bottom nav | Contents | Key quick action |
|---|---|---|
| **Home** | Dashboard, recent activity, assigned work | New contact/task |
| **Inbox** | Unified queue, conversations, message drafts, notes | Respond / assign |
| **Contacts** | Directory, 360° profile, identity, history | Find/create contact |
| **Deals** | Stage pipeline, deal details, follow-ups | New opportunity |
| **More** | Tasks, Calendar, Channels, AI, Automation, Campaigns, Reports, Team, Integrations, System | Contextual |

Desktop: left collapsible sidebar and resizable working area. Inbox uses queue (~28%) + conversation (flex) + customer context (~25%). On phone, queue → conversation → customer profile are separate full-width screens, preserving scroll, filter, message draft and last-open context.

### Wireframe WF-01 — Phone inbox (390×844)

```text
┌──────────────────────────────┐
│  Inbox          [filter] [⋯] │
│ [ Search messages…         ] │
│ [All] [Mine] [Unassigned]    │
├──────────────────────────────┤
│ ● Guest enquiry · WhatsApp   │
│   Booking question...  18:40 │
│ ○ Group enquiry · Website    │
│   Looking for availability   │
│ ● Follow-up · Email          │
│   Please confirm details     │
│                              │
│ [load more / next cursor]    │
├──────────────────────────────┤
│ Home Inbox Contacts Deals More│
└──────────────────────────────┘
```

Conversation list items: identity, source channel, snippet, unread, date, owner and status; list is real server data, not decorative samples.

### WF-02 — Phone conversation

```text
┌──────────────────────────────┐
│ ‹ Guest enquiry  [profile] ⋯ │
│ WhatsApp · Assigned to staff │
├──────────────────────────────┤
│ Received message            │
│               Agent response│
│ Internal note [staff-only]  │
│ Delivery failed [retry info]│
│                              │
├──────────────────────────────┤
│ [ Reply | Internal note ]    │
│ [ Write message or note… ]   │
│ [attach] [AI draft]    [send]│
├──────────────────────────────┤
│ Home Inbox Contacts Deals More│
└──────────────────────────────┘
```

Distinguish outgoing reply from internal note and user-authorized provider send; do not enable send without channel policy/consent/permissions and real delivery adapter. Attachment limits/validation, delivery states, anti-double-send and persisted drafts required.

### WF-03 — Customer 360°

```text
┌──────────────────────────────┐
│ ‹ Customer profile       [⋯] │
│          (avatar)            │
│        Sample Guest          │
│     verified identity        │
│ [ Message ]   [ Add Task ]   │
│ Overview Timeline Deals More │
├──────────────────────────────┤
│ Contact / consent / tags     │
│ Linked StayCore references   │
│ Linked Booking Core refs     │
│ Recent conversation events   │
│ Notes / owner / source       │
├──────────────────────────────┤
│ Home Inbox Contacts Deals More│
└──────────────────────────────┘
```

Contacts are CRM-owned; external bookings are linked and authority-labeled, not silently edited in CRM.

### WF-04 — Mobile pipeline

```text
┌──────────────────────────────┐
│  Opportunities      [+ Deal] │
│ [search] [filter]            │
│ [New] [Qualified] [Proposal] │
│ New stage · monetary total   │
├──────────────────────────────┤
│ ┌──────────────────────────┐ │
│ │ Wellness package lead    │ │
│ │ value / owner / deadline │ │
│ │ [Open] [Move stage ▼]    │ │
│ └──────────────────────────┘ │
│ ┌──────────────────────────┐ │
│ │ Group booking lead       │ │
│ │ ...                      │ │
│ └──────────────────────────┘ │
├──────────────────────────────┤
│ Home Inbox Contacts Deals More│
└──────────────────────────────┘
```

Mobile stage changes have tap/keyboard actions; desktop drag-and-drop is a progressive enhancement, never sole path.

## 2. Complete 15-module screen plan and acceptance flows

| ID | Priority | Screen | Required genuine user flow and state |
|---|---|---|---|
| S01 | P0 | **Unified Inbox** | channel/source filters; unread/assigned/unassigned tabs; search; status changes; empty and permission denied states; real queue pagination |
| S02 | P0 | **Conversation Workspace** | receive/read, reply vs internal note, draft, attach with validation, owner assignment, customer drawer, send authorization/delivery receipt/error |
| S03 | P0 | **Customer 360°** | authoritative contact detail, identities, tags, consent, notes, historical events, linked StayCore/Booking Core context with provenance |
| S04 | P0 | **Sales Pipeline** | stage totals, accessible Kanban on desktop, tap stage change on phone, filters, real updates and conflict handling |
| S05 | P0 | **Deal Detail** | opportunity value, currency, owner, stage/history, linked contact, tasks, activity, notes and audit |
| S06 | P0 | **Tasks & Follow-ups** | create/assign/complete, priority, due date, overdue, references to contact/conversation/deal; notification evidence |
| S07 | P0 | **Channel Connections** | provider availability, credential health, scoped onboarding, test/connection/revoke, consent and provider status; no simulated provider success |
| S08 | P1 | **AI Assistant** | BYO provider, minimized context, explain source, suggest actions, require approval for changes/sends, AI-off normal CRM behavior |
| S09 | P1 | **Automation Builder** | triggers/conditions/actions, draft, validate, dry-run, version history, failure queue, approval to activate |
| S10 | P1 | **Campaigns & Templates** | audience segmentation, templates, preview, consent/quiet hours/rate gates, schedule, actual receipts and errors |
| S11 | P1 | **Calendar & Bookings** | day/week tasks and authorized StayCore/Booking Core references, read-only default, explicit remote edit policy |
| S12 | P1 | **Reports & Analytics** | real channel/team/deal conversion measures, date-range, drilldown, sources, export, zero-data state |
| S13 | P1 | **Team & Permissions** | invite staff, granular roles/capabilities, assignment, separate access, revoke, audit/negative tests |
| S14 | P1 | **Integration Management** | versioned Engagement Core, StayCore and Booking Core contracts; webhooks, receipts, health, sync/conflict/error history |
| S15 | P2 | **System & Data** | export/erase/retention, privacy, backup/restore, audit logs, migration/version, upgrade rollback, licensing |

The P2 UI priority does **not** defer mandatory privacy, backup or tenant security controls required before any real customer-facing rollout.

For every S01–S15, wireframe the **normal, empty, loading, error/offline, permission-denied and destructive-confirmation** states plus at least one meaningful mobile task path. Record keyboard/touch behavior, backend owner, data persistence and screen-to-screen links.

## 3. Design system and UX constraints

Current approved design baseline is Tabler `@tabler/core@1.7.0`, locally bundled, MIT; don't copy external dashboards wholesale. Use consistent shell, spacing, typography, form controls, panels, icons, action hierarchy, alerts, badges, data tables/cards, dialog, bottom sheet, skeleton/loading, errors and toasts. No generic WordPress admin screen substitution.

- **Mobile first:** 320, 360, 375, 390, 414 CSS px; tablet 768/800; desktop 1024/1440. Each relevant view and dialog must be independently exercised at all widths.
- Zero document-level horizontal overflow; no clipped buttons, offscreen controls, minuscule icons or permanently occluded fixed footers.
- Touch targets ideally >=44×44 CSS px; forms at least 16px input font on mobile; account for virtual keyboard, focus return, notches/safe area, dynamic text, orientation and zoom.
- WCAG 2.2 AA-oriented keyboard flow, visible focus, label-association, color contrast and error identification. Provide touch/keyboard alternatives to drag gestures.
- Preserve draft and navigation state through back/forward and errors; distinguish send/unsent/read/delivery-failed; no unsaved changes silently discarded.
- Desktop conversation tri-pane, mobile progressive two/three-screen flow; tablet intentional adaptive layout, not scaled desktop.

**P0 design acceptance:** A reviewer can navigate Inbox → Conversation → Customer 360° and Deals → Deal Detail → Task end-to-end in clickable wireframes. Owner must approve appearance/UX BEFORE Gate 2 implementation.

## 4. Reuse decision / license / cost gate

| Resource | Version and license | Reuse decision |
|---|---|---|
| First-party CRM + Tabler | Current CRM v0.2.0-dev; Tabler 1.7.0 MIT | **Primary foundation**; preserve all working code and test suites |
| [Chatwoot](https://github.com/chatwoot/chatwoot) | community files MIT; `enterprise/` and bundled third parties excluded | Use as interaction reference; selectively reuse permissive components only after file-level review, not entire Rails backend |
| [Twenty](https://github.com/twentyhq/twenty) | core AGPL-3.0 + proprietary marked enterprise, some individual MIT packages (including `twenty-ui`) | Customer-profile/pipeline design reference; **do not copy AGPL or enterprise code blindly**; pin/verify any standalone MIT component |
| [Penpot](https://github.com/penpot/penpot) | verify deployment/runtime and version/license at intake | Optional editable wireframe/prototype tool; prefer existing installed/approved designer |
| [dnd-kit](https://github.com/clauderic/dnd-kit) | MIT; verify maintained release | Consider for desktop pipeline only if actual interaction needs it |
| [React Flow/xyflow](https://github.com/xyflow/xyflow) | MIT core | Candidate for later visual automation editor; no need before Gate 5 |
| Native WordPress REST / Abilities API | WordPress-native APIs | Mandatory for auth/capabilities/typed data actions; CRM SQL on customer site only |
| [Action Scheduler](https://github.com/woocommerce/action-scheduler) | validate exact pinned license/version and existing worker overlap | Candidate bounded job/outbox, not installed by this document |
| Playwright + browser | Existing Dell QA capability | Required actual mobile UI tests/screenshots/traces |

Golden Rule 0: inspect and reuse existing internal tools before new installations; paid APIs/subscriptions prohibited without explicit independent approval. `₹0 new authorized spend`; existing hardware/hosting/compute costs are distinct. Produce pinned dependency manifest, SPDX identifiers, attribution, SBOM and rollback plan before first code merge. Don't include ApexCharts v5+ or other non-permissive bundled chart assets in commercially redistributed plugin without separate legal approval.

## 5. Proposed WordPress architecture, authority and API families

**System of record:** customer WordPress site tables (WP-prefixed); plugin-deactivation retention. Do not migrate authoritative records to Supabase, Chatwoot, Twenty, CRM SaaS or external AI.

**Current implementation:** `eccrm_contacts`, `eccrm_identities`, `eccrm_events`; REST contacts/overview/activity; `manage_eccrm` capability. All proposed additional tables/paths are **NOT BUILT**.

**Planned tables** after schema review: `conversations`, `messages`, `drafts`, `opportunities`, `tasks`, `assignments`, `consent`, `outbox`, `delivery_receipts`, `integration_accounts`, `workflow_definitions`, `workflow_runs`, `audit`. Per-site isolation, retention/export/erase, forward/backward migration and rollback must be reviewed before mutations.

**Proposed HTTP endpoints (not implemented):**
- `GET /eccrm/v1/conversations`, `GET /eccrm/v1/conversations/{id}`
- `POST /eccrm/v1/conversations/{id}/drafts`, `POST .../notes`, `POST .../send` — protected, dry-run/deny by default until channel cleared.
- `GET /eccrm/v1/contacts/{id}/timeline`, `GET/POST/PATCH /eccrm/v1/opportunities`
- `GET/POST/PATCH /eccrm/v1/tasks`, `GET /eccrm/v1/integrations/status`.

Every mutation: nonce/capability or scoped auth, server validation, audit, idempotency where required, correlation ID, 4xx/5xx semantics and CSRF/replay safeguards. Inbound channel adapters: authenticated webhook → validated schema → dedupe → local store → delivery ACK. Outbound: consent → authorization/human approval → durable outbox → provider send → receipt/retry/dead-letter/reconciliation. No fake "connected" or "sent" status.

**Authority:** Engagement Core controls its campaign and engagement transport; StayCore controls stays/guest transactions; Booking Core controls appointments/availability; CRM owns profile/history/opportunities/tasks. External source provenance and permissions are explicit. WACRM Meta/Business App Coexistence remains production NO-GO until separately cleared. Ashwakaal is independently segregated.

## 6. Actual Dell Dev Tool Yard — governance-aware execution contract

**Do not infer that a Tool Yard library is an enrolled worker.** Verify current governed controller schema and project registry, its approval ledger, actual live SSH lanes, model/compiler/browser tools and security negative tests before scheduling build actions. The Dell controller's 25 Oct governance documentation says its stronger semantic/fidelity gates are **proposed, not certified globally**. Model-facing prompt text cannot grant bypasses or owner approvals.

Owner-directed project ID: `engagement_core_crm` under existing `karanzing1992/engagement-core` owner and isolated worktree. Do not route through `shaadi_aunty_dodge`, `delulu_tech`, `matrix_dev_manager` or other projects' manifests/workspaces, credentials or billing identities. Where full `dev_project_build` has no registered project/quality contract, **run only the existing read-only/proposal intake**; return a specifically reviewable enrollment diff/manifest, without rewriting allowlists or asserting execution capability.

Task managers, only if verified: **BMAD** for product stories and interaction requirements; **Spec Kit** for frozen spec and RTM; **LangGraph** as a governed orchestrator only if exact deployed controller and scoped agents are actually enabled. Prefer existing controller/QA and owner-held model subscriptions; no fresh metered API or new cron.

**Functional roles:** product brief owner / UX design / WordPress backend / frontend integrator / licensed reuse evaluator / independent functional+visual QA / release governor / owner approver. Independent QA cannot self-approve.

## 7. Milestone plan and explicit gates

**G0 — Registry and quality intake (authorized by user now).**
- Read source and PRs, record exact SHAs, license and dependencies, existing test evidence, clean new worktree, ownership/tenant limits.
- Verify whether `engagement_core_crm` is enrolled for builds. If not, produce guarded registration/approval proposal and identify precise blockers; no unsafe self-enrollment or write access to unrelated repos.
- Create RTM: for every 15-screen requirement, unique ID, source owner intent, status, validator, acceptance evidence and owner approval.
- Evidence: source fingerprints, tool versions, gate decision, branch/worktree plan, negative access-check results.

**G1 — Complete editable wireframes (owner requests this work now).**
- Every 15 screens and state variant; component/tokens spec; mobile-first at 390/360 plus tablet and desktop; clickable journeys and UX QA.
- Existing Tabler styling as baseline; produce realistic screen composition with action behavior mapped to backend, NOT fake working API states.
- Independent design review with source-labeled visual artifacts/screenshots. Deliver clickable preview and designer-friendly editable source. **STOP for owner design approval.**

**G2 — Inbox + Conversation + Customer 360°** *(blocked until G1 acceptance)*.
- Real self-hosted data persistence, synthetic webhook fixtures, outbox disabled/controlled, complete responsive interaction tests; no live providers.

**G3 — Deals + pipeline + tasks/calendar** *(next review gate)*.
- Real CRUD, stage history, assignments, concurrency, accessible drag alternatives and true contact links.

**G4 — Connections**.
- Versioned adapters/health for Engagement Core, StayCore, Booking Core/WACRM. External calls/test channels only after scoped separately approved access.

**G5 — Optional AI, visual workflow automation, campaigns**.
- Provider-neutral BYO, no-AI functionality, minimized context, approval gates, synthetic dry-run and outbox receipts.

**G6 — Commercial release qualification**.
- Granular staff rights, GDPR-style export/erase/retention, data backup/restore, migration/rollback, real staging-to-user test, licensing/SBOM, performance, accessibility and WordPress plugin install/upgrade smoke. Production requires exact target/time-bound owner release approval.

## 8. Mandatory quality bar ("no half-baked output")

For every accepted milestone provide: exact SHA, traceability mapping, real screenshot/trace per intended viewport (not only technical checklist), bound functional/negative tests, keyboard/touch/form and error-state interaction, audit and persistence readback, distinct independent QA verdict, version/license/SBOM, reproducible installable ZIP and rollback. No screens that are grey WP placeholders, no inert buttons, no invented data, no visual design substitutions as "equivalent." Any P0/P1 product/visual defect is **REWORK**, not waived by passing smoke tests.

Maintain prior verified `27/27 Chrome UI E2E` and `16/16 synthetic contact contract tests` (replace only with objectively more comprehensive, verified suites), plus new route/integration tests and role/tenant denial canaries. Existing screenshots on Dell are test evidence, **not owner acceptance**.

## 9. Deliverables returned to owner

1. GitHub issue/manifest and exact governed Yard receipt: project, action, id, status, runner and timestamp.
2. Frozen requirement matrix and complete G0 tool/source enrollment report.
3. Editable 15-screen wireframes, phone/tablet/desktop views and clickable two-path UX prototype.
4. Design tokens and reusable component inventory; mapped backend API/table contracts.
5. Reuse/license/cost dossier and architecture decision log; risk/security blocklist.
6. Genuine mobile QA screenshots/video/Playwright traces with critical defects recorded.
7. A Gate 1 owner-acceptance package with **no premature implementation, merge or publish**. Later phases require distinct approvals.

## 10. Stop, rollback, communication and reporting

Owner has authorized **submission and work on G0/G1**. No explicit authorization to merge PR #73/#74, provision paid services, change Dell sudo/root policy, connect real customer channels, touch live Moksha/Andaz WordPress or share account credentials. Preserve old functional builds and rollback refs. Dev Tool Yard can autonomously do bounded planning/research within its verified proposal capability; it cannot claim unattended build execution without registered scope, a verified job and terminal receipt.

Report verified platform/support-channel integrations only through existing authorized Supabase Master event inbox. This doc/dispatch alone is NOT a verified integration or production deployment and should not be reported as such.

**Owner review needed next:** approve/reject the complete G1 wireframes and user journeys; only then activate G2.
