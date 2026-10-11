# Optional always-on ChatGPT Project instruction

Paste into **Project settings → Instructions** for projects that must apply this protocol automatically, regardless of whether a Skill happens to be selected:

> Follow the Moksha Master shared technology-change protocol at https://github.com/karanzing1992/engagement-core/blob/main/docs/MASTER_STACK_UPDATE_PROTOCOL.md. After every verified, material engineering or platform capability change, use the installed `master-stack-sync` skill when available. For one of the nine monitored GitHub repositories, make a factual reviewed commit with `STACK CHANGE:` at the start of the final commit subject so independent Google Apps Script can publish source facts into the master registry. For platform-only changes with authoritative evidence, submit an idempotent event through the connected Supabase `public.submit_master_stack_change` RPC, if authorized. Do not duplicate existing Doc markers, share credentials or guest/customer data, invent live deployment status, or bypass backup/restore controls. Technology registry: https://docs.google.com/document/d/1-dSumLKkhmpzqGF2P-4x5_ZNUh9JamH3ApfXv4y4EeM/edit.

## Boundaries

- Installing a Skill or Plugin in ChatGPT does not directly edit existing ChatGPT Project settings.
- If the Skill is available across the user's ChatGPT chats, it can be selected within multiple Projects, but tools still require their own connections and authorization.
- GitHub agent instructions are repository-scoped; the Apps Script watcher covers only the nine explicitly allowlisted repositories.
- For a new project with a new repo, explicitly review and add the repository to the worker allowlist and check its permissions. Never silently enroll an unrelated repository.

For the **Ashwakaal — Support Channels** project, use the same shared Master Stack Skill, but do not infer any channel is connected or monitored. Its register is https://github.com/karanzing1992/engagement-core/blob/main/docs/ASHWAKAAL_SUPPORT_CHANNELS.md . Until a verified repository is explicitly enrolled, source-backed non-GitHub channel changes must use the authorized Supabase inbox route. Keep Ashwakaal account and audience data separate from the other projects.
