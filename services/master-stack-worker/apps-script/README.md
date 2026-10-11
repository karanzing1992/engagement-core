# Moksha Master Stack Worker — External Google scheduler

## Status — 11 October 2026
- **Independent Apps Script has been installed and manually executed in the document owner's Google account.** A live GitHub → Google Docs synchronization was confirmed by readback from the master registry for three different source repositories: `gpt-pine-engineer`, `mokshasitemap`, and `synergistica-website`. Each canary was published once; no production code was deployed.
- **Apps Script trigger:** `installMasterSyncTrigger` was previously run by the owner, but an **unattended time-triggered execution has not yet been independently verified** through the Google Apps Script Executions log. Manual sync is verified, not an hourly SLA.
- **GitHub instructions:** all nine allowlisted repositories now include the shared, tested two-route protocol and know to label real changes `STACK CHANGE:`.
- **Google Apps Script source:** [Code.gs](./Code.gs). The installed code should match this current source; GitHub commits do not update existing Apps Script projects automatically.
- **Separate Supabase inbox:** external non-GitHub changes are submitted via the connected Supabase app, then handled by an existing hourly connected Master Inbox Sync task. Apps Script v1 does not access private Supabase tables.
- **Supabase Cron:** separate internal health-monitoring tasks, not a direct Google Docs publisher.
- **ChatGPT Project boundary:** repository files do not automatically become persistent Instructions in individual ChatGPT Projects. Follow the [reusable instruction](../../../docs/MASTER_STACK_UPDATE_PROTOCOL.md) and add it to each Project explicitly when required.

## One-time install in the Google account that can edit the registry

1. Open https://script.google.com/home/projects/create and create a project named `Moksha Master Stack Worker`.
2. In its `Code.gs` editor, replace the starter code with the reviewed contents of [Code.gs](./Code.gs). Save.
3. Open **Project Settings → Script Properties** and add `GH_READ_TOKEN`: a **fine-grained GitHub token with Contents: Read-only** access scoped only to the nine repositories (required for private repos; public repos work without it).
4. Select `installMasterSyncTrigger` in the function selector, click **Run**, and approve Google's authorizations for reading the owner's Google Doc and making outbound requests. The script creates its own hourly time trigger.
5. Run `runMasterStackSync` once as an initial dry baseline. The script will capture each available repository HEAD SHA without importing historical work on the first run. Use `masterStackStatus` to inspect trigger configuration and successful runs.
6. Check Google Apps Script **Executions** and the registry document for new factual entries once a new source commit has been made.

**Do not paste GitHub access tokens in ChatGPT, commit them to GitHub, or give the script any Supabase service-role credential.** Script Properties remain available to the script owner. If the token is missing, the worker handles only public GitHub repositories and reports private repository HTTP 404 errors.

## What it does
- Hourly independent trigger: compare nine allowlisted `karanzing1992` repos to stored per-repo HEAD cursors.
- Inspect only newer GitHub commits and their changed files.
- Publish source-verified releases/features/security/capability updates into the document using the owner's native `DocumentApp` permissions.
- Add idempotent `[MASTER-GITHUB-CHANGE:repo:SHA]` markers, original commit URLs, affected-file list and source-only disclosure. Never claim deployment approval.
- Cap documents to 20 updates per cycle, fail closed when a cursor is outside the latest 30 commits, and never advance cursor on failed/incomplete inspection.
- No GitHub Actions runner minutes; no ChatGPT task slot needed *once the script is independently installed*.

## Relationship to Supabase inbox
The external Apps Script v1 is a **GitHub-commit-to-Google-Doc publisher**. It is not currently wired to read `public.master_stack_change_events` directly. The connected ChatGPT hourly task can separately verify and publish pending Supabase inbox events. A future dedicated restricted-access API or Google OAuth service-account integration may unify both. Avoid putting a Supabase service-role key into Google Script Properties: this Supabase project also hosts unrelated application data.

The connected hourly task has already been adjusted to **Supabase-inbox-only** publication (plus optional security advisories). This prevents overlapping GitHub discovery. Do not reenable its GitHub commit scanning while the independent Apps Script collector is active.

## Operational caveats
- Google Apps Script hourly triggers run within Google's scheduling window, not guaranteed at exactly the top of an hour.
- New private repository changes require `GH_READ_TOKEN` scoped read-only.
- Repositories with more than 30 new commits before a check are intentionally paused to prevent silent skipped updates; investigate logs and manually reconcile the SHA cursor.
- Google Docs update sources should be reviewed; the script adds source facts and never changes website, permissions, booking data or production code.
- Apps Script quotas and GitHub rate limits still apply; this avoids ChatGPT task limits, not provider quotas.

Master registry: https://docs.google.com/document/d/1-dSumLKkhmpzqGF2P-4x5_ZNUh9JamH3ApfXv4y4EeM/edit
Shared architecture: https://docs.google.com/document/d/1ybmMCLX_9gy2SUAL9_h-8HpTWBVWt_ksbTShHn1FF5w/edit

## Fix applied — 11 October 2026

The initial Google Apps Script source used an unsupported `DocumentApp.flush()` at the end of `runMasterStackSync`, causing `TypeError: DocumentApp.flush is not a function` (earlier line 126).

**Quick correction in the already-open Apps Script project:** replace `DocumentApp.flush();` with `doc.saveAndClose();`, save, and rerun `runMasterStackSync`.

**Recommended full correction:** replace the project's entire `Code.gs` with the [current source](./Code.gs) and save. The revised version also buffers GitHub SHA cursors until after the master Doc is saved and the newly appended markers are verified by reading the Doc again. This prevents silent loss of commits when a Google Docs write fails. Pending markers are unique, so reruns skip already-published entries.

**Important:** Updating this GitHub source does not update an existing independent script.google.com Apps Script project. The owner must copy the corrected source into Apps Script (or use an explicitly authorized deployment process). Run `runMasterStackSync`, then `masterStackStatus` and inspect the execution log; initial `lastPublished: 0` is normal when all repos are already baselined.

