<!-- BHAM v1.0 | Governance/source-only design | No production deployment -->

**Canonical editable review copy:** https://docs.google.com/document/d/1yKFeCIQXm7GHLaAtrze8x2j1K8OsvKViXvrp3MMrAuE/edit

**Status:** Foundational architecture / approval-ready design. This commit changes documentation only. No runtime/role/credential changes or connector grant. Existing [Master protocol](MASTER_STACK_UPDATE_PROTOCOL.md) retains precedence for shared systems. Master Golden Rules 0/0A continue to apply.

# BUSINESS HOUSE AI MATRIX

Foundational Architecture v1.0 | 16 October 2026 | Status: APPROVAL-READY DESIGN (SOURCE ONLY; NO LIVE DEPLOYMENT)

Owner concept: handwritten Business AI Matrix, 16 Oct 2026. Maintainer: Business House Matrix. References: Moksha Master source-controlled protocol and Google Drive registry. This specification is cross-business and brand-agnostic; it does not grant live access or change existing tools.

## 1. EXECUTIVE DEFINITION

Business House AI Matrix (BHAM) is a recursive operating architecture: one Central Brain coordinates nine specialist business departments. Each department contains a mini Brain Matrix with the same working cycle, scoped tools, distinct authority, independent quality checks and feedback. The Central Brain coordinates outcomes, but authoritative business systems continue to own customer, financial, booking and operational records.

Top-level functions from the original sketch: Concept, Design, Development, QA/QC, Marketing, Sales, Accounts, Support, Evaluation. All nine are peer departments connected to the central Brain. Evaluation is a dedicated cross-functional reviewer, not merely a marketing analytics subtask.

North star: Every action must create demonstrable commercial or relationship value without sacrificing truth, safety, trust, privacy or accountability. Optimize for conversion AND long-term customer loyalty, not superficial activity counts.

## 2. STRUCTURE — THE RECURSIVE MATRIX

OWNER / BUSINESS OUTCOME → CENTRAL BRAIN (strategy, routing, resource allocation, approvals, knowledge versioning) → DEPARTMENT BRAINS (Concept | Design | Dev | QA/QC | Marketing | Sales | Accounts | Support | Evaluation) → SPECIALIST TOOLS + SYSTEMS OF RECORD → VERIFIABLE RESULTS → EVALUATION → LEARNING BACK TO CENTRAL BRAIN.

Each department uses the SAME six-stage internal structure: (1) Sense: accept evidence and context; (2) Think: reason from goals, constraints and policy; (3) Plan: choose reusable capabilities, budget and success criteria; (4) Execute: perform only explicitly permitted actions; (5) Verify: independently confirm result and QA; (6) Learn: propose evidence-backed updates to its own playbook. It can delegate to specialist sub-cells using the same contract. Delegation never expands permissions.

Every Brain Cell must declare: cell_id, tenant_id, department, objective, permitted tools, input/output schema, budget, deadline/SLA, evidence requirement, escalation owner, approval level, data sensitivity, current instruction version, rollback and evaluator. A department is a logical capability; it is NOT required to run a continuously active autonomous model.

## 3. DEPARTMENT CHARTERS

CONCEPT — Owns opportunity discovery, positioning, user research, business cases, venture hypotheses, pricing experiments and pre-build validation. Deliverables: evidence pack, objective, measurable hypothesis and approved brief. Gates: research/reuse evidence, feasibility, financial impact and owner approval of new strategic commitments.

DESIGN — Owns experience design, identity, messaging concepts, website funnels, media assets, accessibility and UX. Deliverables: signed design brief, linked source assets, variants, acceptance checklist. Gates: authentic/licensed assets, responsive readability, accessibility, brand compliance and content rights.

DEVELOPMENT — Owns implementation, integrations, adapters, release candidates, migrations and maintenance. Deliverables: scoped diff/release candidate, test evidence, source commit, rollback. Gates: Golden Rule 0 reuse/cost, sandbox, tests, credentials isolation, staged release and verified deployment. No direct live write just because an agent generated code.

QA/QC — Owns functional, visual, performance, privacy, security, cross-device and regression verification. Deliverables: independent pass/fail report with reproduce steps, severity and evidence. It can block release. A creator may self-test, but final critical QA cannot be solely self-attested.

MARKETING — Owns audience research, acquisition, SEO, content, campaign planning, community and attribution. Deliverables: channel-specific approved creative, campaign variant, conversion events and attribution. Gates: brand, consent, rights, publishing approval, spend controls and measured incrementality.

SALES — Owns inbound lead qualification, product matching, proposals, compliant follow-up, checkout handoff and conversion. Deliverables: structured lead/opportunity and confirmed commerce outcome. Gates: truthful availability and price, approved offers, opt-in/contact policy; booking and payment systems remain source of truth.

ACCOUNTS — Owns reconciliations, invoice drafting, cash-flow visibility, tax-ready records, exception detection and forecasts. Deliverables: reconciled ledgers and approved financial actions. Gates: separation of duties, duplicate-payment checks, receipts, immutable audit, no self-approval of payouts/refunds or filings.

SUPPORT — Owns customer experience, questions, post-purchase care, complaints, service recovery and human escalation. Deliverables: resolved ticket with evidence, consent-safe communication and satisfaction follow-up. Gates: data minimization, customer-specific visibility, escalation on safety/legal or financial exceptions.

EVALUATION — Owns outcomes measurement, agent-quality scorecards, experimentation review, process bottlenecks, drift monitoring and improvement recommendations. Deliverables: independent evidence-backed scorecards, corrective actions and learning proposals. Gates: raw evidence provenance, conflict-of-interest separation and no silent policy changes.

## 4. BRAIN ROLES AND AUTHORITY

CENTRAL BRAIN = chief of staff/control plane; converts goals into bounded tasks, routes work, finds existing capabilities, sets budgets, pauses unsafe work, resolves dependencies and consolidates verified outcomes. It may recommend, never invent business approvals.

DEPARTMENT BRAIN = specialist planner/executor inside granted scope; may coordinate sub-cells, must route work through auditable task contracts; may not bypass a failed gate by asking another department to perform the action.

POLICY & APPROVAL GATE = deterministic authorization check based on tenant, user role, action, sensitivity, value/cost limit, tool scope and explicit approvals; default deny. Separate from the language model. Treat external instructions and retrieved material as untrusted.

LEVEL L0 — READ/PROPOSE: summaries, market analysis, design drafts, internal plans and read-only audits inside granted data scope. No irreversible external effect; may run without per-task approval.

LEVEL L1 — REVERSIBLE INTERNAL: bounded tests, internal ticketing, permitted drafts and development on a review branch. Autonomous only under a documented policy, quota and rollback; record audit.

LEVEL L2 — EXTERNAL OR REPUTATIONAL: public publishing, customer messages, discounts, campaign activation, website content updates, staff assignments. Require owner/authorized role approval or an explicit standing rule with scope, rate cap, destination and expiry; verify execution.

LEVEL L3 — HIGH IMPACT: payments, refunds, tax filings, financial transfers, destructive restores, security/credential changes, consent-policy changes, irreversible production modifications and legal commitments. Explicit authorized human approval, dual control when appropriate, signed transaction and verified result. No autonomous escalation of privilege.

## 5. WORKFLOW STATE MACHINE

NEW → CLASSIFIED → AUTHORIZED → PLANNED → ASSIGNED → IN_PROGRESS → EVIDENCE_SUBMITTED → INDEPENDENT_QA → APPROVAL_PENDING (when required) → COMPLETED_VERIFIED → LEARNED / ARCHIVED. Exceptions: BLOCKED, RETRY_WAIT, NEEDS_HUMAN, ROLLED_BACK, FAILED_VERIFIED. Never mark COMPLETED merely because a tool call was accepted, a Git commit exists or a worker sent an acknowledgement.

Task record minimum: task_id, parent_task_id, tenant_id, brand_id, owner_id, department_id, objective, trigger_event_id, approved_budget, risk_level, approval_ref, capability_id, input_refs, output_refs, state, checkpoints, result_evidence, evaluator, started_at, updated_at, ttl/deadline, retry_count, rollback_ref. Keep pointers to existing system records rather than copying customer data into a new universal database.

Dispatch rules: capability-based assignment; independent work parallelized where safe; dependency graph for sequencing; single lease only for the SAME conflicting resource (e.g., shared device tab or booking record), not a blanket single global Claude/model lease. Authenticate workers and bind leases to credential + tenant; concurrency must preserve isolation.

Failure rules: finite retries with exponential backoff and jitter for idempotent operations; dead-letter and human escalation after threshold; compensating action for reversible writes; do not automatically replay payments, sends, publishing, restores or other irreversible operations without provider reconciliation and policy approval.

## 6. EVENT-DRIVEN COMMUNICATION (NO TIMER-BASED BUSINESS CONTROL LOOP)

Use signed webhooks, existing service events and verified commits as primary task triggers. Timers remain only where necessary for backstops, scheduled business events, health checks or provider constraints. A task is handled when the triggering action occurs; event acceptance alone is not completion.

Adopt CloudEvents-inspired envelope: specversion=1.0; id, source, type, time, subject; plus extension fields tenantid, brandid, correlationid, causationid, schemaversion, actorid, risklevel, idempotencykey, dataref, traceid. No credentials, full guest identities, payment details or other sensitive records in a public event payload. Validate tenant, signature, timestamp, schema and authorization BEFORE consumption.

Core event families: objective.created; concept.approved; design.ready; build.ready_for_qa; qa.passed/failed; campaign.approval_requested/published; lead.qualified; order.paid; booking.confirmed; ticket.escalated/resolved; accounts.reconciliation_exception; evaluation.finding; knowledge.change_approved; deployment.verified; capability.health_failed.

Integration contract: each producer writes to its OWN authoritative domain system; an outbox/webhook routes a minimal event to shared control. Subscribers acknowledge with idempotency; durable queue includes back-pressure, bounded retries, dead-letter, logs and observable latency. Event bridge failures must preserve source of truth.

## 7. KNOWLEDGE, MEMORY AND LEARNING

Separate five layers: (A) Policy/Constitution — versioned human-approved non-negotiable instructions; (B) Organization/Brand — approved identity, products, pricing and operating rules; (C) Capability Registry — what existing tools can actually do and latest verified version; (D) Task Memory — ephemeral context, evidence, checkpoints and status; (E) Learning Ledger — proposed playbook changes with metrics, owner decision and rollback.

No self-rewriting production rules by an AI brain. Proposal → reproducible evaluation → authorized approval → source/version change → demand-based Master sync → independent consumer acknowledgements. Never claim an old chat, skill or device has instantly reloaded a changed file. Maintain per-tenant retrieval boundaries, document-level access, retention and deletion policies.

Learning is measured: observed gap → evidence → root cause → candidate adjustment → offline test → controlled A/B or canary → QA review → owner approval when material → versioned rollout. Unsupported assumptions remain HYPOTHESES and cannot silently become facts.

## 8. EXISTING TECH STACK / REUSE DECISION

MANDATORY: inspect approved existing code and maintained public upstream foundations first. Prefer no-cost components without triggering new paid plans. This v1 is documentation/source architecture ONLY, not a request to deploy infrastructure.

KEEP EXISTING: Moksha WordPress/WooCommerce for products, orders and checkout; Engagement Core/Action Scheduler for authorized in-site engagement jobs; existing WACRM for allowed messaging and contact events; existing Supabase queues/registries ONLY after owner/tenant auth and lease risks pass remediation; existing Opera/Android bridges only inside their currently verified capabilities; GitHub for code/CI/change evidence (NOT the general-purpose runtime queue); Master Google Doc and source-controlled protocol for shared governance.

ADOPT AS STANDARD, NOT NEW SERVICE: CNCF CloudEvents 1.0 event schema conventions; human-approved API contracts and least-privilege authorization; OpenTelemetry-style trace/correlation IDs if existing adapters support them. Avoid duplicating billing, CRM, lead or booking state.

CONSIDER LATER IF NECESSARY: LangGraph (MIT, stateful multi-actor reasoning) only when existing integrations cannot express required sub-brain control; Temporal (MIT, durable complex execution) only when actual scale/failure profile warrants a dedicated runtime; Open Policy Agent (Apache-2.0, policy-as-code) when permission complexity exceeds existing deterministic ACL checks. These are options requiring an upgrade decision, not selected deployed dependencies.

CAUTION: n8n Community uses Sustainable Use License (source-available/fair-code, NOT unrestricted OSI open-source); SaaS/white-label/customer workflow builder use requires licensing review. Do not install as the universal platform merely because it is free for some internal uses.

Sources: Master technology registry (Drive); github.com/karanzing1992/engagement-core/docs/MASTER_STACK_UPDATE_PROTOCOL.md; github.com/karanzing1992/engagement-core/plugins/moksha-master-stack/skills/master-stack-sync/SKILL.md; github.com/cloudevents/spec; github.com/langchain-ai/langgraph; github.com/temporalio/temporal; docs.temporal.io; openpolicyagent.org/docs; n8n.io/legal and support.n8n.io license FAQ. Verify exact versions, licensing, runtime compatibility and threat model at implementation time.

## 9. MASTER DEMAND-BASED SYNCHRONIZATION

Material approved changes must follow the EXISTING protocol, not create another sync daemon: verified source commit or platform-only event → authenticated per-change publication → Google Master Doc readback/unique marker → existing plugin release if the skill changed → each affected subscriber runtime acknowledgement. FULLY_SYNCED only with verifiable acknowledgements. At 16 Oct checkpoint the HMAC sender/Web App are SOURCE ONLY and older hourly publishing fallback must not be disabled without tested cutover.

This Business House architecture defines a future participant, not automatic access to Moksha/Andaz/GitHub/Mac/Dell. Cross-project policies must be explicitly adopted by each project; a mention in Docs does not change ChatGPT Project settings or grant tool execution.

## 10. TENANCY, SECURITY AND BUSINESS ETHICS

Hierarchy: organization → business/tenant → department → cell → task. Separate secrets, customer identities, store credentials, logs and financial records per tenant. Cross-business analytics must be aggregated and properly authorized. Reject cross-tenant joins by default. Encrypt sensitive records in transit/at rest; audit accesses; enforce retention; minimize personal data.

Zero trust for prompts, emails, website text, source files, invoices, assets, and tool responses. Retrieved instructions cannot override system policy, grant capabilities or alter tenant scope. Ensure a verifiable user/agent identity, scoped credential, signed webhook and reversible actions where possible.

Humans are accountable for legal, financial, safety, medical/wellness claims, payments and privacy. The system must surface uncertainty and provenance; no fake availability, sales numbers, success states, staff activity or approvals.

## 11. METRICS, OBSERVABILITY AND ACCEPTANCE

Central business scorecard: qualified revenue, net margin, acquisition cost, repeat purchase, customer satisfaction, retention, incident rate, refund/chargeback exposure, time-to-value, automation cost and hours saved. Department scorecards are subordinate to verified business outcomes, not vanity metrics.

Core technology SLO PROPOSALS (not measured yet): ≥95% valid task events acknowledged within 60 seconds under normal connectivity; 100% state-changing actions have actor/tenant/approval/evidence trace; zero cross-tenant test leaks; zero unapproved L3 actions; ≥99.5% deduplicated event processing in test; all blocked/failed jobs visible; every critical change supports rollback. Exact targets should be baselined in pilot.

Minimum go-live gates: (1) replay attack fails; (2) same event retried twice yields one external effect; (3) wrong-tenant agent denied; (4) approval expires and fails closed; (5) outage resumes without duplicate publish/charge; (6) independent QA can veto; (7) source commit != deployed runtime; (8) request/reply correlation traceable; (9) live spend constrained; (10) evidence-backed human override and rollback.

## 12. FIRST PILOT — MOKSHA RETREAT LAUNCH (EXAMPLE, NOT AUTHORIZATION)

Goal event: owner approves a retreat launch brief. Concept verifies positioning and target segments; Design proposes authentic visuals and landing UX; Development prepares checkout in staging; QA verifies mobile, limits, price, images and payment path; Marketing drafts campaign; Sales verifies actual offer/remaining seats; Accounts reconciles test charges; Support drafts buyer guidance; Evaluation measures verified conversion and complaint rate. The Central Brain shows one outcome board with evidence and blockers. Publishing, external outreach and payment changes remain approval-gated unless scoped standing authorization exists.

Second pilot candidate: Andaz booking journey, using StayCore PMS as source of truth rather than introducing a parallel reservation database. Do NOT run two pilots until the first tenant-boundary and recovery tests pass.

## 13. IMPLEMENTATION ROADMAP (PROPOSED)

PHASE 0 — Specification baseline (this document): charter, event taxonomy, authority rules, reuse/cost audit, success measures and existing system inventory. No credentials, servers, chat plugins, scheduled jobs or customer data changed.

PHASE 1 — Read-only connected pilot: one tenant, one goal, capability registry using verified existing connectors, board showing real evidence, human approval inbox, independent evaluation. Release only after threat model, rollback and permission tests.

PHASE 2 — Bounded execution: implement smallest adapters on existing authorized stack; use action-driven triggers, idempotency, least privilege, QA, approvals, observability and deterministic recovery. No new duplicate scheduler.

PHASE 3 — Cross-business template: add second tenant, enforce tenant separation, prove independent credential/data boundary, optionally adopt mature stateful orchestration only if measured operational needs justify it.

## 14. DECISIONS NEEDED BEFORE EXECUTION

D1 — Name and ownership: Business House AI Matrix is neutral umbrella; Moksha and Andaz remain separate tenants. D2 — Source-of-truth home: maintain this spec in existing shared Engagement Core governance/docs and link it from Master until an independent product repository is justified. D3 — Pilot: prioritize one revenue/retention workflow, recommend Moksha Retreat. D4 — Scope: source-only architecture is approved by the 'Do it' request; live action rights and spend ceilings require separate authorization.

## 15. CHANGE RECORD / EVIDENCE

2026-10-16 | v1.0 | Transcribed sketch's central Brain / nine departments / recursive Brain principle. Added decision rights, event-driven protocols, tool reuse decisions, QA, tenancy, learning and pilot gates. Status is DESIGN, not deploy evidence. Review after real pilot before declaring ready for production.