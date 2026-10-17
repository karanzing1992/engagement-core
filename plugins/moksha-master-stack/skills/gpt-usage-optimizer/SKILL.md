---
name: gpt-usage-optimizer
description: Route tasks to the appropriate GPT reasoning effort, control chat/context bloat, and create reliable source-linked handoffs for long project workflows. Use for large projects, sluggish chats, expensive/repetitive agent work, model-choice questions, and new-chat resumes; do not claim to change the ChatGPT model, selected thinking level, or context window automatically.
---

# GPT Usage Optimizer — model guidance and chat lifecycle

**Scope:** Shared *guidance* for projects using the Moksha Master Stack. Project ownership and instructions take precedence; Golden Rules 0/0A, free-first, source reuse, approvals, privacy, branch/security controls, QA and rollback remain mandatory. This skill does **not** install an autonomous router, alter ChatGPT settings, run in the background, or extend tool permissions.

## 1. Model-effort decision at task entry

Use the lightest **available** reasoning level that satisfies *risk, ambiguity, complexity and acceptance criteria*, not the longest context or highest model by default:

| Lane | Example task | GPT-6 selector guidance | Process |
| --- | --- | --- | --- |
| QUICK | Direct factual answer, caption, simple read-only state | Instant | Answer from grounded current facts; no broad context reload |
| STANDARD | Synthesis, research, 2–3-way comparison, bounded plan | Medium | Targeted official/repo sources, concise decisions |
| BUILD | Multi-file code changes, root-cause debugging, deployment QA, dense synthesis | High | Existing ticket + relevant source + tests + checkpoint |
| CRITICAL | Unresolved high-stakes design, deep debugging, cross-system incident | Extra High **only if available and worthwhile** | Explicit assumptions, alternatives, risk review, verification |

**Escalate only on evidence**: incorrect first pass, unresolved contradictory evidence, failed bounded retry, significant irreversible risk, complex reasoning requirement, or repeated rework. A task can be long but mechanically simple; use STANDARD/QUICK plus automation/workflow tooling instead of raising effort. Downgrade after the hard subproblem is resolved. Never assume that typing “think harder” switches the actual model.

**ChatGPT UI truth (OpenAI Help, checked 17 Oct 2026):** GPT-6 on Plus/Pro does not automatically escalate Instant to Medium/High merely because a request is complex. A skill or connector cannot programmatically move the user's model picker; recommend a choice for the user to make. Available levels and quota depend on plan/workspace. UI safety/fallback routing is platform-owned. See https://help.openai.com/en/articles/20001354-gpt-6-and-other-models-in-chatgpt .

**API-based, owner-controlled workers:** A router *can* select an allowlisted model and supported reasoning-effort parameter on each new API request when the worker already has the required provider integration and owner approval. Before implementation, inspect the existing worker and the official API/model documentation; constrain per-task cost, latency, privacy, allowlists, rate limits, retries and non-API fallback. Do not invent an API key, paid tier, metered call, automatic ChatGPT UI switching, or separate scheduling daemon. Keep GPT Chat model UI and external API worker routing distinct.

## 2. Minimum viable task context

Use only: (a) active Project identity/lane, (b) current ticket/PR/checkpoint, (c) relevant files and relevant Master paragraphs, (d) latest authoritative runtime proof when needed. **Never dump the entire Master Registry or replay full prior chats by default.** Confirm source version/branch, action authorization and evidence freshness. Distinguish verified live, source-only, queued, untested, blocked, failed and proposed.

Use targeted file/connector searches, batch independent reads, deduplicate repeated outputs and favor fixed-format acceptance evidence over broad status chatter. Do not add a tool call when its answer is already verified and fresh enough. Parallel reads are fine; serialize writes to shared state, browsers/devices, production deployments and scarce worker quota. Reuse existing repositories, queues and skill owners rather than creating a monitoring agent to optimize chats.

## 3. Chat-length lifecycle (heuristics, not fake token measurements)

**Healthy:** single objective, manageable source set, no repeated questions; continue the current chat.

**Checkpoint trigger:** any milestone, >2 unrelated goals in a chat, repeated re-fetches/contradictions, large tool dumps, complex multi-stage branch, uncertainty about last verified state, or user reports that responses are sluggish. If platform token-use is not exposed, **do not claim a measured context percentage**. After ~25–40 substantive turns *consider* a checkpoint, but do not hard-stop based on turn count alone.

**Fresh-chat recommendation:** checkpoint is saved in the existing issue/doc; chat becomes confused, repetitive, slow, or near user-visible limits; or a logically independent workstream begins. **Never start or move to another chat autonomously**, claim the new chat inherits all active context, or abandon an in-flight write. User opens a fresh project chat with the verified checkpoint URL and bounded resume instruction. Memory is helpful context, not a substitute for authoritative project state.

**Recovery:** if a new chat lacks the file, connector or permission, retrieve only the relevant source again; state missing access instead of guessing. Recheck the source SHA and live state, then continue from the first incomplete acceptance criterion. Do not conflate a git commit with production deployment.

## 4. Durable handoff packet

Write to the **existing** approved GitHub issue/PR, project file or durable tracking record at significant transitions. Aim for 250–500 words of *actionable* prose; extend for required security or rollback facts. Use this exact structure:

```
TASK: <one measurable objective>
PROJECT / LANE: <specific approved project and repository>
STATUS: <VERIFIED_LIVE | SOURCE_ONLY | TESTED | QUEUED | BLOCKED | FAILED>
LAST PROOF: <source URL / full commit SHA / deployment or run ID + UTC time>
DONE: <verified outcomes and passed tests>
NOT DONE / RISKS: <remaining checks, failed tests, uncertainty>
REUSE / COST: <existing foundation, official/upstream source, license/₹ status>
ACCESS / APPROVAL: <authorized operations; anything requiring human approval>
ROLLBACK: <known safe restoration path>
NEXT SINGLE ACTION: <one executable next step + acceptance criterion>
```

Never paste credentials, private transcripts, customer/guest data, or unrelated project information into the handoff. A checkpoint is authoritative only for what its evidence actually proves. Existing issue/checkpoint IDs are preferable to a new spreadsheet, copy of the Master Doc or duplicate queue.

## 5. Response and workflow quality checks

- Respond outcome-first: answer QUICK asks briefly; execute BUILD asks in bounded stages with genuine readback and clear acceptance evidence.
- Do not repeatedly ask for already-provided facts. When an ambiguity is non-blocking, state the safe assumption and progress.
- Do not inflate effort because a chat is long; split context from reasoning. Do not lower effort when risk or factual correctness demands investigation.
- Recommend a model/effort change **only when it materially helps**. User must operate the ChatGPT model picker.
- Reuse the existing Master demand-based event flow for significant verified technology changes. Do not use old hourly publication as the primary sync mechanism or claim full propagation from a GitHub commit.
- Log the source version, plugin release, and consumer acknowledgement independently; an installed skill update does not hot-reload existing chats or Project Instructions.

## 6. Tiny resume message (for use in a new Project chat)

`Resume [PROJECT] task from [CHECKPOINT URL]. Confirm repository/permission/source SHA and live status, load only files needed for NEXT SINGLE ACTION, preserve Golden Rules 0/0A and safety gates, execute and verify. Report only evidence-backed changes.`

## Reuse / source decision

Internal reuse: existing Master `FAST EXECUTION DEFAULT`, `master-stack-sync`, active GitHub issues/checkpoints and the owner-approved demand-based event protocol; no new agent, paid dependency, API key or backend service. Official reference: OpenAI GPT-6 help and applicable official API model/reasoning documentation. New material is a narrow reusable policy/Skill that combines model-effort guidance with bounded chat context and verified handoffs; zero additional service procurement.
