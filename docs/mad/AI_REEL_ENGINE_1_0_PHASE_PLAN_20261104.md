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

## Phase 1 correction and owner test candidate — 2026-11-04
**SUPERSEDES THE EARLIER SYNTHETIC-ONLY PHASE 1 DEFINITION ABOVE.** Owner clarified that the MVP must edit real video, not merely accept prompts. Implemented in `engagement-core` pull request #130, merged commit `77e177f2d1b3500b8137e18cff1c9d0ce56071f4`. Standalone NextChat PWA `https://reel.delulutech.in` includes **Upload & Edit Real Video** panel, owner access-code auth, 80 MiB MP4/MOV/WebM source intake via private 4 MiB KV chunks, individual SHA-256 validation, consent/rights/external-AI checkboxes, queued media job, signed GitHub OIDC real-media V5 render lane, H.264/AAC 1080x1920 technical private review MP4, receipt, status and protected download. No guest footage enters public GitHub artifacts. Video auto-expires in private KV after 48 hours.

**Internal technical evidence:** synthetic-original 4.2 second source MP4 SHA256 `421b9e40958eace3446370f1c3eef5954a3a23b6fbcdeb3f1c9ecd992333f800`, source ID `upload-5c409a5c-998b-4ae6-9e68-d79848af1fe4`, private job `madmedia-1f18a6a0-771e-4c7a-a1aa-c80fd3f08ec9`, GitHub run `41820373167` successful, D1 state `review_ready`, output H264/AAC 1080×1920 30fps full decode, output SHA256 `e18e52ff56f9e46a3d7427077276488623d966ae8a603c5949acbcf776fd28c6`, size 37,524 bytes, output chunk count 1, zero error, creative model called but source-only fallback recorded. Negative checks: anonymous owner media POST HTTP401, foreign Origin HTTP403, unsigned OIDC media POST HTTP401, trusted PWA upload preflight HTTP204. Separate GitHub CI gates pass.

**Certification boundary:** This test used a tool-seeded synthetic file in private KV/D1, NOT the browser's live file picker or a real guest clip. Actual interactive PWA upload and review by owner remains the next acceptance gate before any public rollout. This release is an OWNER PRIVATE PILOT, not a public production-capable, music-rights-certified or artistically approved product. Third-party soundtrack license proof/selection/sound sync and end-to-end live guest video visual quality are NOT yet certified; original source audio is preserved. Phase 2 multiuser fair queue/ETA and Phase 3 prompt assistant remain planned-only. Do not claim full owner artistic certification until actual private footage trial and rights review.
