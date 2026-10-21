# Moksha Master — Dell Autonomous Browser and Let’s Goa Handover

**Snapshot date:** 21 October 2026  
**Owning project:** Moksha Social Media  
**Purpose:** Resume the existing Dell autonomous-browser workflow and complete the Moksha Reset retreat listing on Let’s Goa.  
**Status:** Source handover only; all runtime states must be verified afresh in the next chat.

> This handover is stored in a public GitHub repository. It intentionally excludes credentials, cookies, tokens, passcodes, exact private endpoints, local session identifiers, and other sensitive access information. Obtain live state through the existing authenticated tools, not this document.

## 1. Current task and verification state

- **Machine:** Dell Inspiron 5379, known to the connected Generic SSH Linux app as **dell-linux**.
- **Task:** List **The Moksha Reset** retreat on the official Let’s Goa partner portal, using Moksha Wellness's existing provider account.
- **Original brain task:** Already exists in the Dell operator's persistent SQLite job store. It previously reached escalation after repeated navigation failures. **Find and recover the existing task; do not create a duplicate task or listing.**
- **Latest technical deployment:** Browser session-preservation v2, semantic navigation v1, scoped public knowledge retrieval v1, and remote-viewer latency improvements.
- **Dell services:** Most recently verified active and healthy on 21 October 2026, following the session-preservation release.
- **Let’s Goa session:** At the last read-only verification the partner server displayed **Unauthorized**, although the same persistent Chrome process and saved profile remained present. Owner reauthentication had not yet been reverified. **Do not assume authentication is still valid or that session recovery has been proven.**
- **Publication:** No verified new public Let’s Goa event listing or completed publication receipt as of this snapshot.

The secure login gateway, ChatGPT connector status, operator task receipts and site's current page must be checked live before acting.

## 2. Existing architecture — reuse, do not rebuild

The owner-operated Dell automation stack includes:

| Component | Purpose | Last verified state |
| --- | --- | --- |
| Generic SSH Linux | Authenticated remote command/receipt bridge to dell-linux | Functional at latest verified check; connectivity can fluctuate |
| Dell AI Operator | Local task planner, restricted executor and auditable persistent SQLite queue | Deployed; health check passed |
| Existing Ollama local model | Planner for bounded, permission-gated actions | Connected to operator; navigation planning needs real-world validation |
| Playwright and Chrome DevTools Protocol | Attach to the **same** visible Chrome window and inspect/navigate pages | Installed; localhost-only DevTools handoff |
| Persistent Chrome profile | Browser cookies, remembered website data and current user window | Present; profile persistence alone does not guarantee site-server authorization |
| Remote viewer | Owner manually enters credentials on the Dell browser and locks the remote view | Deployed; screen capture/input latency optimizations verified |
| Semantic navigation module | Discover live menus/links and follow verified, allowed navigation targets | Installed and locally smoke-tested |
| DDGS, Trafilatura and SQLite FTS5 | Scoped, open-source external research and evidence recall | Installed; limited to owner-approved public domains |
| Self-repair and task queue | Preserve task state, bound retries, pause on login/safety conditions | Installed and tested with known limitations |

**Golden Rule 0:** Reuse these proven components, inspect source and runtime evidence first, and avoid duplicate browser frameworks, extra paid APIs, new browser services or replacement automation systems without an explicit need.

## 3. Browser login and session-preservation incident

### Verified observations

1. Chrome was already running with the existing site-specific persistent browser profile.
2. The CDP bridge attached to the existing Chrome process rather than launching a fresh browser.
3. Browser-side Let’s Goa session data was still present when the site reported **Unauthorized**. A non-expired browser cookie does **not** establish a valid server-side login.
4. The original autonomous task could issue hard navigation to the login route, or reload the application's page while the owner was logged in.
5. Site-enforced expiry or revocation is distinct from accidental browser navigation. The exact cause of the server-side invalidation was **not proven**.

### Fixes actually deployed

- With a live CDP handoff, forced browser-open/reload requests are denied.
- Agent planning uses **browser_session_status → browser_snapshot → browser_inspect → browser_navigate**, rather than guessing URLs or opening the login route.
- The session-status tool returns authentication booleans and a short diagnostic, **not** cookies or tokens.
- When the portal rejects authentication, the brain pauses for owner intervention instead of retrying the login page repeatedly.
- Repeated secure-login start and handoff requests reuse the same running Chrome instance.
- On legitimate Chrome restart, the previously approved dashboard route may be restored, but the website still independently validates its login.
- Automatic retries of forced browser-open actions were removed.
- All changes have rollback copies on Dell; the original persistent profile must be preserved.

### Validation boundary

Local tests passed for refusing forced login/dashboard reloads, reusing the same Chrome session, reporting an authentication failure, preserving existing security gates, and restarting the Dell operator healthy.

**A fresh owner sign-in followed by long-duration authentication-retention testing has not yet been completed.** Do not promise permanent login or bypass the provider's expiration policy. Never copy live browser cookies or tokens into Git, ChatGPT messages or another machine.

## 4. Navigation capabilities and safety policy

The operator has two added Playwright actions:

- **browser_inspect:** Enumerates visible, permitted navigation choices from the current page with names and fresh references.
- **browser_navigate:** Clicks only a verified, current-page navigation reference. It validates names and domain restrictions, and rejects protected or stale targets.

Isolated smoke tests passed for an **Activity** route, navigation-menu toggle, rejection of a stale reference, rejection of off-domain links, and filtering of unsafe form/publish controls.

**Still pending:** Live end-to-end menu navigation while genuinely authenticated in the Let’s Goa provider dashboard. A login or Unauthorized screen has no useful dashboard menu targets.

The existing approval gates still apply to public submission, publication, payment, checkout, credential entry, sensitive fields, and other protected actions. Do not reinterpret a generic browser click as permission to publish.

## 5. Moksha Reset — confirmed listing brief

**Event title:** The Moksha Reset — A Morning Back to Yourself  
**Collaborator spelling:** Jyothsna Channdola Singh  
**Date:** Saturday, **24 October 2026**  
**Time:** **7:00 AM–1:00 PM IST**  
**Meeting point:** **Cafe Food Planet, Arambol Beach, Goa**  
**Venue sequence:** Arambol Beach, followed by the Moksha Wellness experience  
**Activities:** Gentle beachfront movement and breathwork, vegetarian breakfast, guided wood-fired sauna, optional cold plunge, mineral mud and aloe wellness care. Use the approved full itinerary rather than inventing inclusions or medical claims.

**Ticket structure:** ₹6,499 for the first 4 paid seats, then ₹7,499 for the next 6 seats; **10 guests is a hard total cap**. Verify current paid bookings and remaining inventory on the booking website before stating remaining seats. **All sales final** under the retreat-specific policy.

**Website checkout:** https://mokshagoa.com/moksha-reset-retreat-jyotsna/  
**Campaign booking link:** https://mokshagoa.com/moksha-reset-retreat-jyotsna/?utm_source=letsgoa&utm_medium=referral&utm_campaign=moksha_reset_20261024  
**Terms:** https://mokshagoa.com/moksha-reset-retreat-terms-24-oct-2026/

Use approved real Moksha and collaborator assets only, and follow the established brand identity. Reconfirm prices, live page availability, inventory, event information and final imagery before posting.

## 6. Exact continuation procedure for the next ChatGPT conversation

1. **Read this entire document from GitHub**, check the existing Moksha Master instructions, then connect to **dell-linux** via the already installed **Generic SSH Linux** app.
2. Read-only verify the host heartbeat and completed SSH receipt. Query the existing operator's health, services, task queue and browser-handoff status. A queued SSH command is **not** completion; wait for the terminal receipt.
3. Locate the saved Moksha Reset / Let’s Goa task in the existing Dell jobs database. Preserve its state and original ID privately. Do **not** start a duplicate task solely because the prior one is escalated.
4. Use **browser_session_status** first. If the site's server still rejects the session, ask the owner to sign in inside the existing Dell remote viewer; do not request passwords, passcodes or OTPs in chat. The owner may choose Remember Me if Let’s Goa offers it. The remote viewer's **Lock** operation must not close Chrome.
5. After owner sign-in, read-only verify **Welcome Moksha Wellness** and a real dashboard; distinguish page content from URL-only assumptions. Confirm no login form or Unauthorized message.
6. Test **browser_inspect**, then follow a verified, non-transactional navigation target with **browser_navigate**. Check that the exact live tab remains authenticated and that navigation did not launch a new Chrome/profile.
7. Inspect existing provider activities and any event listings for **Moksha Reset** to prevent duplicates.
8. Reuse the saved event brief and approved assets. Proceed through the authorized listing workflow, respecting protected submission and publication approvals.
9. Only declare the listing live after verifying the provider record, publication status and actual public URL. Verify booking CTA, copy, pricing, time zone, collaborator spelling, image and mobile readability.
10. Measure session retention after the live handoff and an idle/reopen cycle. If the website legitimately expires authorization, report that accurately rather than modifying cookies or attempting an unauthorized bypass.
11. Report changes and validation results to the **Moksha Master Registry**, including source/verification evidence, rollback and any consumer acknowledgements.

**Never perform speculative publication, payment, destructive resets, service redeployment or credential export.** Do not overwrite an active agent's concurrent work. Respect the owner-controlled escalation and approval gates.

## 7. Master Registry and verified milestones

Canonical Master technology registry:  
https://docs.google.com/document/d/1-dSumLKkhmpzqGF2P-4x5_ZNUh9JamH3ApfXv4y4EeM/edit

Relevant recorded event keys:

- DELL-CDP-HANDOFF-20261021-V1 — live Chrome process handoff.
- DELL-SCOPED-KNOWLEDGE-20261021-V1 — scoped open-source research.
- DELL-PLAYWRIGHT-NAV-V1-20261021 — semantic navigation integration.
- DELL-SESSION-PRESERVE-20261021-V2 — login persistence safeguards.

This GitHub handover is **documentation only**. It is not a machine software deployment, plugin release, proof of valid current authentication, or proof of listing publication. Resolve those states through live connected tools.

## 8. Open source / reuse / cost gate

Existing components were reused rather than introducing a replacement platform: **Playwright** (Apache-2.0), **Trafilatura** (Apache-2.0), **DDGS** (MIT), **SQLite** (public-domain SQLite core), and the owner-operated task/controller stack. No newly purchased service or paid API was required for these integrations. Their upstream documentation should be verified for version/license changes before any upgrades. Rollback means restoring the component-specific Dell backups and checking operator health; never reset the user's Chrome profile or erase provider data to troubleshoot login.

## 9. Recommended new-chat opening prompt

> Read the full handover at **https://github.com/karanzing1992/engagement-core/blob/docs/dell-letsgoa-handover-20261021/docs/handoffs/DELL_LETSGOA_MOKSHA_RESET_HANDOVER_2026-10-21.md** using the connected GitHub app, not memory alone. Follow the Moksha Master Stack Skill. Continue the existing Dell autonomous-browser + Let's Goa Moksha Reset listing workflow. Start with read-only Dell SSH, browser_session_status and the saved job; do not rebuild or create duplicates. Validate live authentication, then test browser_inspect/browser_navigate, finish the listing within approval gates, and report proof of publication and Master sync. If login is expired, request secure owner reauthentication without asking for credentials in chat.

**Final source status at this handover:** Dell navigation/persistence code locally verified; public GitHub document is the handover; authenticated Let’s Goa end-to-end navigation and public event listing verification remain pending.


## 10. Live recovery checkpoint — 21 October 2026

**Check window:** 15:02–15:12 UTC, 21 October 2026. **Status:** BLOCKED_ON_OWNER_REAUTH, not published; no Dell code, policy, service or Chrome profile changes were made.

- Connected GitHub handover and Master/Golden Rule 0 instructions read. Generic SSH `dell-linux` heartbeat online, owner pairing active, shell enabled. Authenticated identity probe finished successfully (exit code 0); additional read-only shell receipts completed.
- `dell-ai-operator.service`, `dell-private-login.service`, `dell-private-relay.service`, and `generic-linux-automator.service` active. `health.py` returned healthy, no pending/running operator tasks. Same original Let's Goa Chrome window/profile remained running through subsequent checks; no Chrome restart or browser-open action was made.
- Existing original brain job for *The Moksha Reset* was found in `jobs.sqlite3`, status `escalate`; its task brief and audit history remain intact. No replacement brain job or provider listing created. One read-only `browser_session_status` task completed in the existing queue.
- **Authoritative browser result:** `url=https://letsgoa.co.in/OTASP/UI/#/dash/home`, `authenticated=false`, `needs_login=true`, `reason=Session rejected`, `profile_persistent=true`, `chrome_attached=true`. This proves browser/profile continuity but **not** server-side authentication. Do not use `browser_inspect`/`browser_navigate` or resume the AI listing job until the owner has completed a fresh Let’s Goa login in the existing remote Dell browser and a new session-status check confirms true authentication.
- The existing secure owner remote access gateway `https://dell-private-login-ui.vercel.app/` was verified from Dell returning HTTP 200 HTML; private relay and desktop services are active. Owner must use trusted-device PIN to unlock, sign in to Let’s Goa inside Dell Chrome, then **Lock remote view without closing Chrome**. No credentials, passcodes, cookies, or session IDs are recorded here.
- One extra read-only SSH SQLite-result inspection command did not return a terminal receipt before its TTL and was marked `stale_running`; it was **not replayed**. Later independent read-only CLI receipt proved the queued browser status probe completed; a bounded SQLite read returned the exact result above. Avoid interpreting an unfinished bridge receipt as proof of mutation.
- Public Let’s Goa publication, activity duplicate check, authenticated Playwright navigation, pricing/CTA/image QA and idle-retention test are **NOT DONE**. The independent public search did not substantiate publication; absence from search is not definitive proof that no listing exists.
- **Next single action:** owner authenticates through the existing remote Dell gateway; then recheck `browser_session_status`. On `authenticated=true` and visible real dashboard, test `browser_inspect` and one permitted `browser_navigate`, check existing activities for duplicates, and resume the saved brain job within publication/approval controls. Require provider publication receipt plus public event URL before declaring live.
- **Open Source / Reuse / Cost Gate:** retained owned Dell operator, Playwright/Chrome, SQLite, Generic Linux SSH and secure remote relay; no new dependency or paid spend. No rollback necessary because no runtime changes were made.
- **Master registry:** no significant technical implementation change was deployed or proved during this recovery; no new platform capability event is warranted. Resume demand-based Master synchronization only for later verified material engineering changes.


## 11. Verified authenticated continuation — 21 October 2026

**Live verification:** 16:40–16:55 UTC, 21 October 2026. **Overall listing status:** NOT PUBLISHED / recovery requires owner-approved escalated-job rearm. The existing Dell Chrome PID `373686`, persistent profile and four previously deployed services were preserved (no process restart, new brain job, new browser profile or provider submission).

**Authentication and dashboard:** `browser_session_status` in the original Playwright/Chrome CDP queue reported `authenticated=true`, `needs_login=false`, `chrome_attached=true` at `https://letsgoa.co.in/OTASP/UI/#/dash/home`, after owner sign-in. `browser_snapshot` displayed the actual authenticated partner header `Welcome Moksha Wellness`, dashboard, and seven existing wellness activity titles, without a visible Moksha Reset entry in that dashboard card. This is not a comprehensive duplicate search or publication proof.

**Bounded Dell navigation compatibility fix — VERIFIED_LIVE:** The live Angular Material toolbar's hamburger button has text `menu`, but a generic aria label `Example icon-button with menu icon` and no `aria-expanded`/`aria-controls`. Existing `browser_inspect` returned no navigation candidates. Narrow extension made to the **existing** `browser_navigation.cjs`: recognize only a toolbar button containing the Material `menu` icon as a `Menu` navigation candidate; recognize Angular Material `mat-nav-list` containers; use the same normalized candidate name for stale-reference comparison in `browser_navigate`. No generic button, form, JavaScript URL, cross-domain, payment or publication bypass was introduced. Backups on Dell: `browser_navigation.cjs.bak-before-live-angular-menu-20261021`, `browser_navigation.cjs.bak-before-live-angular-menu-v2-20261021`, and `browser_navigation.cjs.bak-before-live-menu-name-consistency-20261021`.

**Tests/receipts:** Node syntax checks PASS; existing `nav-smoke-test.cjs` PASS (menu-toggle, Activity route, refusal of unsafe controls/stale refs). Live operator queue `browser_inspect` returned `nav-0 Menu`; subsequent `browser_navigate` on that fresh ref completed `status=ok`, `action=navigation`, `changedRoute=false` (toolbar toggle; deliberately not a page-route switch); closing it with the same verified menu method preserved `authenticated=true`. Chrome/profile did not restart. When the toolbar hides the sidebar, the current DOM heuristic may yield `authenticated=false, needs_login=false, reason=unknown` despite still rendering `Welcome Moksha Wellness` without login/Unauthorized; reopening the menu restored heuristic `authenticated=true`. Do not interpret that ambiguous state as a site login failure or a robust authorization proof.

**Existing job resume was attempted and safely refused:** `task_queue.py enqueue ai_resume 1b61f126-32c6-4681-a177-db164147c573` yielded an escalated receipt: `ValueError: Only paused jobs can be resumed`. The original brain job remains `escalate` in `jobs.sqlite3`, and contains its full task and steps. `self_repair.py` permits `resume_id` only when job status is `waiting_user_auth` or `paused_review`. Last historical errors were denied/invalid browser_open attempts; those predate the current navigation fix. **Do not silently rewrite `jobs.sqlite3`, discard steps, create a replacement job, or weaken the resume gate**. Require owner-approved, audited recovery of this escalated job using an explicit controlled transition, followed by read-only browser state verification and bounded resume. The current user requested resume, but the controller correctly blocked unsupported status; no override was made.

**Remaining:** Owner-reviewed rearm of escalated brain job, navigation to existing Activity records, comprehensive duplicate check, asset/availability/price confirmation, event draft, explicit protected publication approval, provider publication receipt and public URL with booking/mobile QA. No claimed public Let's Goa listing or booking receipts. Public search returned no relevant event results, which is not conclusive.

**Open Source / Reuse / Cost Gate:** Continued existing Chrome, Playwright, Generic SSH, SQLite queue, local source-backed semantic navigation. No replacement stack, paid API or additional dependency; code fix is a narrow local compatibility patch. **Rollback:** restore `browser_navigation.cjs.bak-before-live-angular-menu-20261021` only with owner approval, then run existing nav smoke tests and verify attached Chrome PID/session and policy gates. No service restart needed for Node's fresh per-action module imports.

**Master Registry:** Record this material independently verified Dell local navigation change through the existing Route B event and canonical Doc marker `[MASTER-STACK-EVENT:DELL-LETSGOA-ANGULAR-MENU-NAV-20261021-V1]`. This handover is a checkpoint on a documentation branch, not an operator binary release or default-branch source commit.


## 12. Audited owner-requested rearm and bounded model run — 21 October 2026

**Verification window:** 17:00–17:07 UTC, 21 October 2026. **Outcome:** Existing brain job resumed and exited `step_limit`, no public listing or publication verification.

- The user expressly requested resumption. Before any rearm, inspected the original `jobs.sqlite3` job `1b61f126-32c6-4681-a177-db164147c573`: state `escalate`, 9 historical steps, latest four errors were `browser_open` with `replan` outcome, not publication or payments. Confirmed no running AI queue tasks and successful authenticated partner dashboard state.
- Standard `ai_resume` was first attempted without any override and correctly refused an escalated job with `ValueError: Only paused jobs can be resumed`. There was no new brain job.
- Implemented narrow **resume-step-budget preservation** on the existing Dell `self_repair.py`: a resumed run gets at most one fresh `max_steps` budget (configured 12) added to the preserved historical step count rather than immediately exhausting on prior history. Syntax check passed; backup `self_repair.py.bak-before-owner-reviewed-resume-budget-20261021` retained. No autonomous action allowlist, Chrome, token, SSH or publication policy changed.
- Owner-reviewed manual rearm: used Python SQLite consistent backup `jobs.sqlite3.bak-before-owner-reviewed-rearm-20261021` (mode 0600) before an atomic conditional status transition from `escalate` to `paused_review` on that *same* job ID; appended a `owner_reviewed_rearm` audit step, preserving all nine original observations. Re-arm was allowed only after verifying no active task and reviewing the failed steps, not an automated generic escalation bypass. The standard existing controller then accepted `ai_resume` for the original job. No duplicate listing or job created.
- **Observed run:** bootstrap steps `browser_session_status authenticated=true`, `browser_snapshot`, and `browser_inspect` succeeded. Browser navigation `Menu` completed via Playwright with the original Chrome and persistent profile. However the small local model subsequently proposed malformed `browser_navigate` arguments (e.g., `ref:nav-0` without required JSON/name and URL strings), which existing executor rejected. With the sidebar hidden the DOM-only heuristic sometimes reported `authenticated=false, needs_login=false`, despite the visible Moksha partner header; this is NOT proof of revoked server login. The run reached its bounded `step_limit` with 22 steps and terminal queue state `escalate`; original brain status now `step_limit`. No form was submitted and no public listing URL exists in the observed receipts.
- **Do not blindly rearm a second time.** Next development step is a separately reviewed, minimal safe normalization of model-generated `browser_navigate` arguments using current-page inspected manifests (never guessed URLs), and improved auth heuristic with actual visible portal evidence. The live `Apply For Activity` form-entry button remains outside the current navigator's automatic navigation allowlist. Preserve its review gate and require concrete confirmation before submission/publication. The existing autonomous planner alone is not yet a reliable end-to-end listing agent.
- **QA / rollback:** Nav smoke test PASS, syntax tests PASS, Dell services/Chrome PID remained healthy, initial session authenticated and user controls preserved. To undo budget change restore `self_repair.py.bak-before-owner-reviewed-resume-budget-20261021` with owner approval; backup SQLite DB before any data restore and reconcile concurrent writes, never blindly overwrite job history. Machine status is VERIFIED_LIVE for audited original-job rearm and finite attempt; listing is NOT PUBLISHED and NOT VERIFIED.
- **Golden Rule 0:** reused local Dell queue, Playwright, SQLite, browser, owner SSH, no extra dependencies or paid services. Significant recovery capability to be recorded as independent platform-only Master event `[MASTER-STACK-EVENT:DELL-ORIGINAL-JOB-REARM-20261021-V1]`. This documentation branch is not a default-branch software release.


## 13. Opera AI browser migration feasibility and protected pilot — 21 October 2026

**Requested change:** Use Opera as the Dell autonomous browser, let the local AI operate it with Opera-maintained documentation and GitHub tooling. **Status:** FEASIBILITY_VERIFIED / INSTALL_BLOCKED; no browser switchover, no Opera installation, no new listing job and no loss of the original authenticated Chrome profile.

**Source / Golden Rule 0 check:** Reuse the existing Moksha Linux Opera Bridge source owned by `karanzing1992/moksha_wordpress`, including `docs/OPERA_BRIDGE_CURRENT.md` (v0.6.1+/local v0.6.2; the Supabase v1 remote path is read-only and single-agent; do not claim remote navigation). Primary maintained upstream: `https://github.com/operasoftware/opera-devtools-mcp` (Apache-2.0, README inspected via connected GitHub; file SHA `37476e37202782f3d9cfa1e7b1e9b9b69aed1ed6`) and its official Opera Browser CLI. Legacy `https://github.com/operasoftware/opera-browser-cli` is a **compatibility launcher, no longer independently developed**, per README at SHA `ab4ae5a56f6664008838e1878ab1d51eefa1b510`; do not start a new custom CLI or blindly install an obsolete fork. Reuse Playwright and the existing Dell operator's persistent SQLite job/review gates. See `https://blogs.opera.com/news/2026/08/your-ai-agents-can-use-opera-neon-free-of-charge/`, `https://blogs.opera.com/news/2026/05/opera-browser-cli/` and `https://www.operaneon.com` for plan/capability distinction.

**Platform reality:** Opera Neon native `Do/Make/Research` AI features officially ship for **Windows and macOS**, not Dell Linux. Native Neon agentic AI features require Opera Neon Standard subscription, disallowed under free-first without a critical exception and explicit approval. Linux Opera One free browser + local Dell model via official Opera DevTools MCP/CLI is viable *in principle* as an external-agent setup; free Opera AI chat is not equivalent to Neon native agentic Do. The existing `mac-linux` Linux machine has Opera 137.0.6036.63 at `/usr/bin/opera`, but the isolated generic SSH worker has no active Opera browser/GUI context; prior local Bridge controller/remote authority are distinct and cannot be assumed connected or be commandeered for Dell.

**Dell preflight — live 21 Oct 2026:** Dell is amd64, Node 24.22.0 / npm 11.19.1, >800 GB disk space, existing private desktop Xvfb :99, `dell-ai-operator.service` healthy, Chrome PID `373686` intact. No `opera`/`opera-stable` executable or Opera package was installed on Dell. Vendor official Linux package was found at `https://ftp.opera.com/pub/opera/desktop/137.0.6036.63/linux/opera-stable_137.0.6036.63_amd64.deb`, released 14 Oct 2026 with adjacent `.sha256sum` file. One attempt to download it into a **new user-owned pilot path** `$HOME/opera-browser-pilot/download/` as a nonroot extraction (not system apt install) encountered a long/slow transfer, an SSH timeout and temporary absence of Dell worker heartbeat. The original shell command failed with timeout and unknown exit; inspection after heartbeat returned showed a partial, **unverified** `opera.deb`, no vendor sha downloaded, no extracted browser. A matching live `curl` was stopped deliberately to protect the bridge, and post-check confirmed zero matching vendor-download processes, Dell worker online, original Chrome PID unchanged and operator service active. **Do not treat partial bytes as verified, installed or safe to execute.** Preserve partial file only for a future audited download/resume; no blind retry while network is unstable.

**Architecture after successful vendor install (NOT YET APPLIED):** Run Opera One with a separate restricted profile and localhost-only CDP port; use official `opera-devtools-mcp`/Browser CLI backed by the **same Dell task queue and current owner permission checks**. First test local harmless `example.com` navigation, snapshot, back, and browser-identity process. The local model may use Opera documentation and compact accessibility references as untrusted knowledge; it must not get unconstrained CLI-shell access, arbitrary JS eval, cookie exports, payment or publish actions. Require per-domain navigation allowlist, tab lease and exclusive lock. Only after Dell Opera and CLI smoke tests pass, use existing encrypted owner remote view to log into Let's Goa in Opera itself. **Never copy Chrome cookies/tokens or close Chrome for migration.** Verify `Welcome Moksha Wellness` with server-side authorization, no duplicate activities, and only then switch the original job's `browser_backend` through a reversible operator config change. Explicit owner review remains required for protected submission and final publication. Chrome remains rollback.

**Reuse / cost / rights:** Official Opera One browser is proprietary but is the explicitly requested free browser; the DevTools MCP implementation is Apache-2.0; the older CLI compatibility launcher is MIT licensed but moved upstream. Reuse existing local Qwen/Ollama and no paid Opera Neon plan. No new local browser controller/queue/scheduler should be built. No default-branch software or plugin release was produced here, so do **not** register a verified-live new capability in Master.

**Next single action:** With healthy SSH and sufficiently reliable download, complete the exact signed/vendor hash-checked Opera Linux download and user-local extraction without modifying Chrome or original profiles. If the connection remains slow, evaluate copying a lawfully installed, verified original vendor artifact through an already approved secure transport instead of repeatedly saturating the SSH path. Only proceed to CLI integration and smoke tests after the verified Opera executable exists. Record Docker/OS dependency compatibility and secure CDP restriction before switching any production task.
