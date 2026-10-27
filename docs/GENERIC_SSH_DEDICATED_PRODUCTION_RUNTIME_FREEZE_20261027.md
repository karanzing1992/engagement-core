# Generic SSH — Exclusive Production Runtime and Change Freeze

**Owner directive:** 27 October 2026 · **Status:** POLICY RECORDED / CURRENT HOSTING STILL SHARED / MIGRATION NOT STARTED.

**Tracking and authorization:** [P0 Issue #83](https://github.com/karanzing1992/engagement-core/issues/83). This document is governance only. It does not assert enforcement of GitHub branch protections, deployment permissions or isolated runtime.

## Binding production policy

1. **Generic SSH is production infrastructure.** Its gateway, OAuth service, PostgreSQL state, key material, deploy/rollback identities, release pipeline and worker daemons MUST be exclusive to Generic SSH. No CRM, MAD, Andaz, Pine, WP Manager, Shaadi, developer sandboxes, other projects, customer data or support channels may host, redeploy, modify or reuse that runtime.
2. **Global change freeze, now.** No source edits, deploys, auth/callback edits, dependency updates, schema migrations, service restarts, sudo/root/SSH-key changes, version bumps, worker re-pairing or refresh-token workarounds on the currently live Generic SSH installation by other projects. Critical security/remediation or controlled migration exception requires fresh explicit owner-scoped authorization, baseline hashes, independent safety tests, rollback and receipts.
3. Existing Dell and Mac pairs, approved sudo rights, three SSH transport lanes per device, worker queue receipts/journals and host assignments are preserved. Other projects may *consume* SSH as an authorized tool for their own bounded tasks, but cannot administer, configure or own the generic SSH **service runtime**. Consumer permissions remain separately project-scoped; access to the shared Dell/Mac hardware is not exclusive physical isolation.
4. No shared OAuth callback, authorization token, service role, worker key, database, SMTP, monitoring secrets, configuration namespace or CI deployment identity across projects. Do not reuse secrets from the old shared project in the new dedicated runtime. Keep Ashwakaal Support Channels as an entirely separate workstream with separate access/data.
5. Documentation may be updated to record evidence, but that does not unlock a production release. An untested code or documentation commit is not a deployment.

## Verified existing shared baseline — do not mistake this for the target

- Existing project: `saczglesalubroyaucqe` = `constituency-ops-v1`, Mumbai (`ap-south-1`), shared with unrelated functions and data.
- Existing live Generic SSH Edge Function: `generic-linux-automator` v10; published Edge source SHA256 `717858d13a2047de90b8c0bc0047f9d86393b293dece1a55e974c4f67ffb6fbc`; owner OAuth function `owner-oauth-login` v6. Old runbook describing gateway v6 is historical, NOT current production proof. Reconcile under future approved documentation-only update.
- On 27 October 2026 14:47:50Z `/mcp` returned 200, then repeated HTTP 401 starting 14:47:57Z. Gateway `/worker/poll` continued HTTP 200 and Dell 3 lane heartbeats were healthy. Investigate refresh-token/client auth after isolation, do not fix by bypass.
- Source ownership currently `karanzing1992/engagement-core`; this shared repository is not a substitute for independent production deploy ownership.

## Exclusive target architecture

1. **Own Supabase production project**, recommended `generic-ssh-production`, Mumbai, NOT another Edge Function in `constituency-ops-v1`. If owner requires isolated billing/administrators, create its own Supabase organization as well.
2. Own Supabase Auth tenant, user identities and OAuth client/resource metadata/redirect allowlist, RLS and private tables, role-scoped service keys, dedicated function URLs, independent logs/monitoring and recovery snapshots. No user/credential/customer records copied from other projects.
3. Existing Dell/Mac each retain Generic SSH-owned nonroot daemon/service namespace and three foreground worker lanes with journals and control limits, but no other project may change or occupy daemon runtime. Literal isolated host OS/CPU requires dedicated hosts or VMs: a project-isolated Supabase gateway does not physically isolate Dell/Mac.
4. Separate source/release ownership and allowlist: changes only after owner signoff, immutable promoted artifact, pinned source SHA, reviewed CI, branch/ruleset and deployment target restrictions, no cross-project deploy token or automatic shared Monorepo deployment to production.
5. New runtime should be provisioned before cutover. Prepare database migration using nonsecret schema, enable separately authorized owner and worker identities, verify negative cross-project permissions, and cut over one client/host at a time only after acceptance.

## Must-pass release gates before declaring VERIFIED_ISOLATED

- Dedicated Supabase project id and organization/billing owner confirmed, no credentials/data/function runtime shared; new Edge and owner OAuth are independent.
- Existing live release captured and hashed with restore plan; dedicated release passes lint, schema, auth, security and same-version rollback.
- Fresh OAuth owner sign-in, expiry/refresh/reconnect, invalid token 401, backend unavailable 503, other-account rejection, replay rejection and account isolation QA.
- Dell and Mac each pass control, operations and development terminal receipts (6/6) with preserved permission boundaries, no uncertain task replay; worker restart, host reboot and WAN reconnect tested.
- Consumer cutover by explicit owner approval; prove every existing workflow continues without broken host access. Restore old route if verification fails; retire old shared runtime *only after* new route is proven.
- Verified zero unapproved project migrations, shared deploy access, live customer data transfer, release privileges or paid spend; include source and terminal receipts.
- Record Master platform change via authorized Supabase event inbox; do not claim Master document published without verified readback.

## Change-control exceptions

Only an explicit Generic SSH owner-approved critical security repair or owner-authorized migration may modify the production service. Each action must be scoped to an exact artifact, approval, rollback and independent QA, and never grant additional root/sudo powers implicitly. Standard development and other project automation must be incapable of deploying to the isolated production project.

**Important:** Until the new project and IAM controls are deployed and independently verified, this is a recorded owner freeze, not technical enforcement. Do not mark isolation complete.
