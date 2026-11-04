# DeluluTech AI Reel Engine 1.0 — canonical three-phase product plan
Date: 2026-11-04 | Owner: DeluluTech | Backend: MAD Reel Engine V5
Status: Phase 1 execution authorized; Phase 2 and Phase 3 DOCUMENTED ONLY.

## Phase 1 — branded NextChat PWA, private owner access, API bridge
- Select and reuse https://github.com/ChatGPTNextWeb/NextChat under its MIT license; pin upstream source revision and preserve upstream LICENSE notices when distributed. Fork/vendor or automate a reproducible upstream import; no clean-room reimplementation of a chat app.
- Deploy **AI Reel Engine 1.0 by DeluluTech** as a mobile-and-desktop PWA at a dedicated DeluluTech subdomain (proposed `reel.delulutech.in`), without interfering with `delulutech.in` or WordPress Manager.
- Integrate with existing owner Cloudflare D1-backed synthetic job bridge `mad-reel-v5-oidc-bridge` and `karanzing1992/engagement-core` GitHub Actions workflow. Do not copy/rotate existing `GROQ_API_KEY` or `GEMINI_API_KEY` outside the existing GitHub Actions secret store. The backend already accepts **signed GitHub OIDC**, not anonymous web clients; build a separately authenticated user-facing BFF and narrow authorization boundary before enabling browser job submissions.
- Owner-only authenticated beta first. Use Cloudflare Access / zero-cost established identity mechanism; do NOT put bearer/API secrets in browser bundles, localStorage, repo files or URLs. Enforce server-side identity, allowlisted owner, CSRF, rate limits, idempotency, and private per-user status scope.
- Show honest states: connected, accepted, running, completed/failed; job ID, status and safe private technical receipt. Processing is currently **SYNTHETIC TECHNICAL CERTIFICATION ONLY**. Do NOT claim real user video upload, music/artistic approval or published real reels until private-media and rights gates are passed.
- Build and deploy with CI, browser/mobile QA, negative auth tests and rollback. Keep app closed to non-owner users until Phase 2 identity, quota and isolation checks. No paid upgrades without explicit approval.
- Web-first installable PWA; Android APK is future packaging, not required for Phase 1.

## Phase 2 — multi-user queue, fair scheduling, dynamic ETA
- Add per-user authenticated submissions, immutable owner/tenant identity, one active render per user, two waiting per user default (configurable), one global FFmpeg worker initially, provider quota backoff.
- D1 is canonical queue, not GitHub Actions concurrency. Enforce fair round-robin per owner, bounded claims/leases, retries, cancellation, dedupe, stale-job repair, queue/capacity limits, private results and expiry.
- Replace/augment twice-hourly schedule with authenticated event-driven worker wake-up and keep schedule for recovery. Do not assume GitHub Actions schedule is prompt or guaranteed.
- UI must show queue position, **estimated start range and completion range** derived from historical per-job-type durations and current throughput, not invented minutes. Refresh periodically; show `Estimating` until calibrated.
- Load-test concurrent users, cross-user isolation, no lost/replaced work, budget/free-tier caps, delivery notifications and replay denial before public access.
- Phase 2 remains **planned**, not implemented or certified by the Phase 1 launch.

## Phase 3 — AI prompt suggester and creative direction
- Optional Groq/Gemini-backed helper that drafts or refines hooks, storyboards, shot lists, emotional pacing, styles, typography and licensed soundtrack search instructions; no raw guest video to models without consent.
- Brand templates and multilingual prompts with user-editable output, human approval and traceable creative decisions; use the same server-side model secrets and respect provider quotas.
- Do not requeue or lose render position while drafting. No automated social publication or unlicensed music. Research OSS reuse, rights and independent artistic QA first.
- Phase 3 remains **planned**, not implemented or certified by the Phase 1 launch.

## Security and dependencies
- Source of truth: `experiments/reel-engine-v5/cloudflare-oidc/README.md`; signed synthetic issue #123 proof and GitHub run 41798627740.
- User-facing auth bridge and real video intake remain separate from the currently verified **GitHub workload-only OIDC** trust boundary.
- The unrelated Cloudflare `mad-reel-v5-github-mcp` remains unconfigured; do not claim ChatGPT or third-party MCP availability.
- Strict default: no secret disclosure, no unauthenticated job submission, no public guest assets, no new paid infrastructure.
- Rollback: independently disable the new frontend/API route, restore prior domain record, preserve existing backend, users' authenticated queue state and unrelated DeluluTech projects.

## Open-source / reuse / cost gate
- NextChat: upstream MIT (https://github.com/ChatGPTNextWeb/NextChat/blob/main/LICENSE), license notice must remain in redistributed copies.
- Reuse existing GitHub OIDC, Cloudflare Workers+D1, GitHub Actions and FFmpeg. Avoid paying for additional platforms; verify any new host's commercial/free-tier conditions before public launch.
- Phase 1 acceptance: verified live URL on DeluluTech domain, owner login, actual chat request reaches authorized server BFF and produces a verified backend receipt, unauthenticated rejection, and mobile PWA QA. Website-only/health-only evidence is not acceptance.
