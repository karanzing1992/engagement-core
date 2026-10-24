---
name: mission-control-workflow
description: Use when the owner asks to record, find, update, or review tasks for the private Mission Control dashboard from a ChatGPT conversation.
---

# Mission Control workflow

1. Call mission_control_connection to verify the connected owner Supabase account. If disconnected, use the plugin's supported OAuth connection flow. Never request or reveal credentials, PINs, Telegram codes, service-role keys or session tokens in chat.
2. For new ChatGPT task intake, ask for only genuinely missing project/title details. Extract explicit work descriptions and user-verified status from the current conversation. Call mission_control_capture_task. Do not copy whole conversation transcripts, personal contact details or unrelated project content. ChatGPT does not grant programmatic account-wide conversation enumeration, and this plugin cannot list every ChatGPT chat.
3. Only pass chat_url when it is a verified link supplied by the user; do not invent conversation IDs. Leave it empty otherwise. Store only a concise summary, next action and blocker. Default status to Working when no completion evidence is present.
4. Use mission_control_list_staged to review the private Supabase staging inbox. For updates, use mission_control_update_staged with the exact returned task ID. Do not mark Done without evidence or explicit owner instruction. For paused tasks choose On Ice; for deliberately retired work choose Deprecated.
5. Use mission_control_open_dashboard to send the owner to https://mokshagoa.com/mission-control/ and its existing private Telegram OTP sign-in.
6. Scope distinction: Supabase MCP inbox records are staged; the WordPress owner-vault and its encrypted Supabase replica are a separate, currently one-way workflow. Do not claim a task was saved into the WordPress dashboard until a future ingestion action is implemented and a matching receipt verifies it. Do not conflate the owner-approved backup canary with MCP inbox ingestion.
7. Handle errors explicitly. Do not bypass OAuth, row-level security, site login, or pre-existing plugin scopes. Do not publish or change unrelated assets or devices.
8. If asked to auto-discover all ChatGPT history, explain that a manual ChatGPT export can bootstrap the existing dashboard; supported current-chat capture can proceed immediately. No default history-scraping claim.

The app is private and uses the existing owner's Supabase project, its OAuth issuer, and the MIT-licensed MCP SDK/Zod/Supabase JS dependencies. No new paid service is required beyond existing service plan limits.
