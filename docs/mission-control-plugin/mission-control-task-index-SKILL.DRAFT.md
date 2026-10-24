---
name: mission-control-task-index
description: Use when the owner wants to classify, consolidate, update, search or hand off tasks from ChatGPT projects and chats into the private Mission Control dashboard.
---

# Mission Control — current-chat task index workflow (proposed Master plugin v1.4.2)

This is a **source-only proposed Skill** for the existing private `moksha-master-stack-reinforced` plugin. Adding this file to Git does NOT install a ChatGPT Skill, MCP tool, or ChatGPT history permission.

## Source and authority

- Index only chats/messages actually available in the present conversation/project context, explicitly supplied ChatGPT exports, or authorized tool results. Do not imply account-wide access from a Skill or GitHub connector.
- Preserve the original private `https://chatgpt.com/c/<conversation-id>` link when known. Do not create or accept public `/share/` links or invent missing links.
- Never send full transcripts, OTP codes, passwords, contact details, bot credentials, or guest/payment data into public Git, third-party analytics or Telegram groups.
- Scope decisions to the owner's project and active ChatGPT connection. If an MCP task-index function is not actually present in tool discovery, do NOT call it or claim a backend write.

## Workflow

1. For each accessible chat, extract stable chat title/ID, verified project (else Unfiled Chats), last update, bounded metadata-only summary, next action and blocker.
2. Classify status using exactly **Working / Done / On Ice / Deprecated**. **All** is a view/filter, never a stored status. Lack of an explicit end phrase is a *signal to review*, not proof work is still running.
3. Interpret user-only standalone markers: `TASK DONE` → Done, `TASK PAUSED` → On Ice, `TASK DEPRECATED` → Deprecated, `TASK REOPEN` → Working; `TASK BLOCKED` → Working plus blocker. Owner's later manual override wins over inferred status.
4. Deduplicate by conversation ID; do not merge distinct chats merely because their titles match. Record evidence/provenance and uncertainty privately.
5. If the genuine owner-scoped `task_index_*` MCP tools are discovered and authorized, use their documented schemas and verify readback. If unavailable, prepare a metadata-only import payload for the private dashboard, or guide owner import of their own `conversations.json`.
6. Mark sync status `SOURCE_ONLY / IMPORT_READY / VERIFIED_BACKEND` accurately. Do not label an index LIVE based solely on creating a GitHub file or writing a skill.
7. After task metadata changes, offer the owner a concise list of Working and On Ice items with source chat links and a dated completion receipt.

## Dashboard contract

Single-page Projects → Chats → Task detail, five tabs All / Working / Done / On Ice / Deprecated, global text search, original-chat deep links. Default authentication is one-time code to the existing owner-private Engagement Core Telegram DM; offline PIN remains a separate local fallback. The frontend implementation is [android_gpt_bridge PR #16](https://github.com/karanzing1992/android_gpt_bridge/pull/16). Backend is [Engagement Core PR #70](https://github.com/karanzing1992/engagement-core/pull/70), with WPCode #13375 pending owner activation. No auto-enumeration API for all ChatGPT conversations has been verified.

## Security release requirement

Publish this as an **update to the SAME existing plugin ID**, preserving v1.4.1 skills, scope, defaultPrompt, manifests and existing MCP configuration. A real task-index MCP capability requires a separately deployed authenticated server and actual post-release tool discovery. Do not create a duplicate plugin or append an unauthenticated server URL.
