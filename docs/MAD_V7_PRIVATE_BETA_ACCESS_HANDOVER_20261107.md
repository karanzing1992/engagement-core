# MAD Reel Engine V7 — Private Beta Access & Acceptance Handover

**Verified:** 2026-11-07 (IST). **Release classification:** PRIVATE_BETA_INTERFACE_LIVE / GATEWAY_HEALTHY / CI_SYNTHETIC_RENDER_CERTIFIED / REAL_GUEST_MEDIA_END_TO_END_NOT_YET_CERTIFIED. **Audience:** owner-only beta testers. **Publishing:** disabled.

## Owner beta URL
**Open:** https://mad-v7-owner-private-beta.pages.dev/

Live public-page readback returned the DeluluTech "AI Reel Engine 1.0" PRIVATE ACCESS page. The owner-access prompt specifies current V7 owner code (may normalize an `nk-` prefix); legacy `mj-` codes are not accepted. No owner code or password is embedded in this document or delivered through chat. The page is a private login gate, not an anonymous upload/render service.

**Cloudflare Pages source:** project `mad-v7-owner-private-beta`; production branch `feature/mad-reel-v7-owner-20261107`; linked GitHub source repository `delulutech`; Pages project and subdomain independently confirmed. Cloudflare's latest recorded deployments were previews, some queued; the exact production frontend commit behind the canonical URL was **not** independently pinned during this check. The live URL and login content **were** tested.

## Private render gateway
**Health:** https://mad-v7-kv-private-beta.karanbizweb360.workers.dev/health

Read-only HTTP response returned `ready:true`, `storage:cloudflare_kv`, `dispatch_connected:true`, `requires_github_vault_token:false`, `published:false`. This establishes live gateway reachability; it does not prove that any new authenticated owner job completed through the entire UI today.

**Worker:** Cloudflare `mad-v7-kv-private-beta`; deployment `ad0b35bf-5fcf-42b3-897f-d2ff29557e11`, version `c37241ab-22e6-4133-8bd9-bb707308080f` (100% traffic at last readback). Existing bindings retained: `DB` (D1), `DISPATCH_API`, `MEDIA_KV`, `PROJECT_AUTH`. Original access/OIDC controls and no-public-publishing mode remain in place.

## Engine / soundtrack capabilities
- Source repository: https://github.com/karanzing1992/engagement-core .
- Core verified automatic original-source audio implementation: https://github.com/karanzing1992/engagement-core/pull/211 , merged main SHA `91b7290b9daf6360d6e3c9ec840b62cbed2de864`.
- Commons shortlist hotfix: https://github.com/karanzing1992/engagement-core/pull/212 , merged main SHA `9f98162c9564b849af09173d4c414536d7ce3803`.
- V7 uses FFmpeg editing/finishing, Groq soundtrack candidate ranking, open-license discovery from V5 Openverse and Wikimedia Commons, and txtai reel best-practices retrieval with official Meta/Instagram citation entries.
- When the pre-cleared V6 private music library has no eligible track, V7 may ingest and mix an original **Wikimedia Commons** recording after fresh, bounded MediaWiki original-file license checks (CC0, Public Domain Mark or CC BY), direct media-host check, attribution manifest, actual audio probe and byte/SHA verification. This also applies when the Commons recording is found through Openverse. Other Openverse music hosts remain **discovery-only** until independently implemented and verified. An indexing site's blanket "free" classification never overrides an explicit source restriction.
- Automatic source music toggle in the signed private runner workflow: `MAD_V7_AUTO_SOURCE_MUSIC_ENABLED=true`. Preserve rollback path `false` and original private V6 reviewed-track selection.
- All **five** PR CI workflows passed for #211 and #212; the source-auto admission tests included real FFmpeg V7 audiovisual render and full decode using **synthetic** fixture media, not a genuine third-party licensed track.

## Owner beta test sequence
1. Open the verified beta URL and sign in with the existing V7 owner code. Do not share the code with guests or place it in source files.
2. Create or open a project; upload one owned/consented video clip; enter a simple human creative brief (e.g., cinematic Earth Rejuvenation reel, approximately 30 seconds). Never mark consent or music rights falsely.
3. Start a private V7 render; observe dispatch, processing status, recovery after refresh, and any fail-closed error.
4. When the preview appears, **watch and listen** end-to-end: visual frames present, authentic edit, 9:16 portrait framing, legible captions, music level and fades, selected track provenance and applicable CC BY attribution.
5. Download the private MP4 before the existing 30-minute delivery expiration; inspect file with `ffprobe` and review on mobile. No automatic post or public rollout.
6. Record beta result and evidence: job ID, backend status, input/output SHA256, exact soundtrack and source license URL, attribution, reviewer notes, render duration and any failure stage. Do not record original guest video, secrets or access codes in public issues.

## Acceptance and known limits
- **Confirmed:** live owner-code page, Cloudflare Pages project identity, live KV/dispatch gateway health, code presence in GitHub main, existing private Worker version and bindings, synthetic GitHub CI audiovisual end-to-end pass, source-verified music code and strict signed receipt gate.
- **Not confirmed by this access check:** successful owner login and operations behind the login gate, current frontend commit matching the last Pages preview, a real owner video job from the V7 UI through published-private result, real music from a new third-party URL mixed in that job, automatic caption attribution on every outgoing channel, and artistic sign-off. These require owner-authenticated beta acceptance.
- **Release posture:** private beta only, never label production-ready or public, keep original owner publishing approval and private media expiry. UI access does not independently certify the backend's full feature coverage.

## Rollback and canonical context
**Worker prior reference:** `bf49a29f-6b64-4e20-bdec-b43e77c0b714`. **Source before #211:** `8199d546302d2ad600e7b9bf8c355ac0de3325f2`. Owner may disable automatic music by setting the V7 runner toggle to `false`; do not change secrets or private gateway access for a UI beta experiment.

This is a status/access handover, not a new production feature release or a claim that real media has been certified.
