# MAD Reel Engine V5 — Owner-Private Technical Beta Release

**2026-11-05 09:48 UTC. Verdict: OWNER-PRIVATE TECHNICAL BETA DEPLOYED AND VERIFIED. PUBLIC/MULTIUSER BETA: NO-GO.**

## Production endpoints and precise source

- User PWA: https://reel.delulutech.in/ — Cloudflare Pages project `delulutech-ai-reel-engine-v1`, primary account `3409ce0fa4794fb024c570d141ef0521`.
- Live canonical Pages production deployment `42280947-2e22-4ff0-864b-95ff5e3e945a`, `success`. Source: private `aarondash5-star/delulutech`, production branch `feature/ai-reel-engine-v1-nextchat-20261104`, commit `fb70bf19b6b6f4362e3af943dbcdee90b8ca30dd`, merged [PWA PR #45](https://github.com/aarondash5-star/delulutech/pull/45).
- PWA [GitHub Actions build and production smoke #42004618991](https://github.com/aarondash5-star/delulutech/actions/runs/42004618991): **build=success**, **production-smoke=success**. Source status regression `reel-version-state.test.ts`: **6 passing tests**. Static PWA export was built and packaged as three-day private rollback artifact.
- Owner API https://reel-api.delulutech.in; Projects API https://reel-projects.delulutech.in. Both Workers confirmed to retain encrypted `MAD_GITHUB_ACTIONS_DISPATCH_TOKEN` and `MAD_OWNER_CODE_SHA256`, D1 bindings, and Media KV on Owner API.

## Mobile frontend acceptance (actual production PWA, browser network simulated)

Using Cloudflare Browser Rendering on live https://reel.delulutech.in/ with *intercepted synthetic API calls* and **never sending a real owner code or private footage**:

- **320px** viewport: 0px horizontal overflow. Simulated user completed (1) entry, (2) create project, (3) 3269-byte synthetic file upload (init, chunk PUT, complete, attach), (4) consent controls, (5) save project direction, (6) submit render, (7) refresh status to ready and load private preview + receipt. **7/7 browser flow stages passed**.
- **390px** viewport: 0px horizontal overflow; Projects, Studio, Renders, Settings and private login visible.
- Live unauthenticated requests to Projects and private-video-preview endpoints each returned **401**; browser read the responses normally.
- Real PWA stale-render regression after successful Cloudflare deployment: a *mocked* old queued version with an expired job TTL no longer shows active rendering; Render button enabled, truthful refresh says expired, pressing Render creates one fresh synthetic mocked version, **0px horizontal overflow** at 320px.
- These are **frontend simulated transport tests**, not full positive-authentication end-to-end tests against the production APIs; do not claim otherwise.

## Certified backend integration

Authoritative independent [production GitHub dispatch/render certification](MAD_V5_CLOUDFLARE_GITHUB_EVENT_DISPATCH_CERT_20261105.md):
- Signed `workflow_dispatch` received HTTP 204 with one wake attempt.
- GitHub Actions [run #42000927850](https://github.com/karanzing1992/engagement-core/actions/runs/42000927850) passed: OIDC private source claim, Groq creative planning, actual FFmpeg render, private KV upload and completion.
- Synthetic job `madmedia-e21959e8-a375-4083-a7c5-0edaf22d2cef` reached `review_ready`, 45,756 bytes and private KV SHA256 matched D1 `644075f0addd4737e797debcbe691b3f2ea400d4db3e154167e8604b1ca28c1d`; not published.
- D1 live check before release: 3 project records, 6 message records, 3 project-version records; project/message/version persistence exists. Job list was 6 review_ready and 2 historical failed, no active jobs.

## Beta access/limitations — keep gates honest

- Access remains **owner-only** using existing owner access code. No public signup, open browsing of project data, social publishing or guest-footage render executed as part of this release.
- The user can now test https://reel.delulutech.in on phone/desktop with the **existing** owner access code. Real positive-auth mobile upload→project→render→history→preview with an authenticated owner session is *still an owner acceptance gate* because this automation does not possess the original plaintext access code.
- A real-source artistic release needs explicit people/footage consent, independently checked music rights and independent visual/artistic signoff. Synthetic technical acceptance is **not** a quality certification; prior report had nine proposed effects not executed.
- Public/multiuser beta remains **NO-GO** until actual per-user tenant isolation, storage segregation, rate/quota controls, sessions/revocation, retention/privacy policy and owner-approved security/real-media QA are implemented and independently certified.
- GitHub Actions GitHub-issued event-driven rendering and five-minute recovery watchdog remain operational. Free-tier resources retained. No additional Cloudflare billing or hosted rendering tier introduced.

## Rollback

- PWA: in Cloudflare Pages `delulutech-ai-reel-engine-v1`, rollback to production deployment immediately before `42280947-2e22-4ff0-864b-95ff5e3e945a` if mobile UI regressions emerge; backend unchanged by PR #45.
- Repo: revert merge `fb70bf19b6b6f4362e3af943dbcdee90b8ca30dd` on private `aarondash5-star/delulutech` production branch; rerun GitHub Actions owner PWA CI. Retain D1 source and user records.
- Do not roll back authenticated dispatch fix without a documented emergency: it repaired a verified Cloudflare unsupported redirect bug.

## Owner-accepted scope

**Released:** Owner-private technical beta for project-based Reel Studio, synthetic end-to-end rendering infrastructure, working mobile UI/preview affordances, persisted creative state and human review-only private drafts.

**Not released:** Public/multiuser self-service beta, verified cinema-quality guest reels, rights-certified music, automatic publishing.
