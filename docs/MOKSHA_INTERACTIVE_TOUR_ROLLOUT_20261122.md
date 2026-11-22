# Moksha Interactive Tour + Sales Experience — rollout v1
Date: 2026-11-22. Owner task tracker: [#310](https://github.com/karanzing1992/engagement-core/issues/310).

**State: PHASE1_STARTED / SOURCE_ONLY.** No production deployment, paid service, Google Flow render, website mutation, booking integration, public guest-footage upload or AI release has occurred.

## Outcome
Make the authentic Moksha environment explorable on its own website and via shareable links, with optional future AI and CRM connectors. Google Flow is used to enhance selected real footage; actual interactive branching, analytics and conversion exist in owned web code, not in a generated flat video.

## Source audit
Owner-provided `1000128884.mp4`: 169.619 seconds, 720×1280 H.264 at 30 fps, AAC. Private seven-chapter prototype: Arrival (00:02–00:13), Space (00:17–00:29), Sauna (00:35–00:47), Ice Bath (00:51–01:04), Water Ritual (01:15–01:28; exact ritual ID pending), Mud (01:43–01:57), Afterglow (02:25–02:37). Local review package is private, and must not be committed to this public source repo.

## System
- Frontend: dependency-free HTML5 video/JS/CSS navigation, 7 chapter selection buttons, responsive styling, keyboard focus, video load fallback.
- Branding: use the existing real Moksha asset `assets/brand/moksha-logo-source.jpg`; no synthetic substitute.
- Media: original and derived customer clips stay private until media/guest rights and hosting are approved.
- Booking: existing first-party home route may link to `https://mokshagoa.com/` as a safe non-booking link; do not guess a booking form, price or availability.
- Hosting: review owned WordPress deployment and Cloudflare infrastructure before proposing third-party hosting or spending. R2/Stream cost gate required before provisioning.
- Data: Phase 1 no PII, cookies, GA4 collection, AI or CRM writes. Future capture is consent-based and tenant-scoped.
- Site integration: later separate owner-approved staging PR in `karanzing1992/moksha_wordpress`. No existing website files touched by this branch.

## Rollout
1. **Phase 1**: private 7-chapter navigable source preview, Flow proof shots (arrival/sauna/mud) only after rights approval, certified source fidelity + mobile QA. **Started**.
2. **Phase 2**: deploy isolated website embed to staging, per-ritual deep links, approved booking/WhatsApp route, opt-in GA4 funnel, QR/social distribution; separate release gate.
3. **Phase 3**: optional transparent AI guide with approved knowledge, multilingual content and safe, modular CRM/booking connectors (no fabricated health claims or booking confirmation).
4. **Phase 4**: genuine 360° capture for spatial tour; do not fabricate 3D geometry from the source portrait video.

## Reuse / Golden Rule 0 / cost
Reuse owner-provided footage, existing public official logo and existing engagement-core / WordPress work. Browser native APIs avoid dependency, licence, security and fee overhead. No third-party npm packages, paid API credits or cloud resources provisioned. Evaluate maintained open-source 360 player only when Phase 4 is authorized. Rollback: remove isolated preview; production remains unchanged.

## Phase 1 acceptance
- [x] Original media metadata and scene audit.
- [x] Seven encoded private local review clips and responsive private player package (maintained outside repository).
- [x] Source-only GitHub tracking issue and review branch.
- [ ] Confirm commercial use, guest face/voice rights and Flow upload authorization.
- [ ] Review actual official logo in browser, verify water-ritual label and approved booking URL.
- [ ] Android/mobile (320px min) + desktop end-to-end interaction and media tests; the local browser harness was blocked by runtime administrator policy, **NOT passed**.
- [ ] 3 Flow-enhanced proof scenes and independent reality/visual acceptance; no paid credits without approval.
- [ ] Staging embed, accessible subtitles/transcript, consent, analytics, security, page load and rollback QA.
- [ ] Explicit owner production release approval.

## Master synchronization
This branch and issue are an engineering checkpoint only. Formal canonical Master Stack synchronization follows [protocol](MASTER_STACK_UPDATE_PROTOCOL.md) after a verifiable default-branch SHA or independently verified platform change, Doc readback, and consumer acknowledgement. Never label this prototype DEPLOYED or FULLY_SYNCED. 
