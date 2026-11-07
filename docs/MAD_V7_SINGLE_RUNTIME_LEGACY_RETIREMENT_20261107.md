# MAD Reel Engine V7 — single retained runtime and V1–V6 deprecation boundary
Date: 2026-11-07 IST. Owner decision: **V7 only** for Reel Engine, no publishing, do not modify V7 runtime while retiring older operations.

## Source-of-truth operational identity (PROTECTED)
- Owner UI: Cloudflare Pages `mad-v7-owner-private-beta`, canonical `https://mad-v7-owner-private-beta.pages.dev/`; Pages source: `aarondash5-star/delulutech`, branch `feature/mad-reel-v7-owner-20261107`. Do not modify or delete.
- Private HTTP gateway / cleanup: Cloudflare Worker `mad-v7-kv-private-beta`, owner-auth, signed GitHub OIDC, D1/KV; 5-minute cleanup cron. Do not modify, remove its route or its cron.
- GitHub owner render runner: **`.github/workflows/mad-v6-kv-filmcraft.yml` IS V7 PRODUCTION**. Its legacy filename is pinned in Worker `OIDC_WF`; renaming/deleting/disabling it breaks signed V7 authentication. The code executes the V7 cinematic finish and txtai RAG. Leave unchanged.
- Signed render implementation: `services/reel-engine/v6-kv-gateway/{runner.py,worker.mjs,v7_auto_music.py,v7_music_discovery.py,v7_verified_source.py,ffmpeg_v6_adapter.py}`, `services/reel-engine/v7-cinema/`, `services/reel-engine/v7-micro-rag/`, `experiments/reel-engine-v6/` model adapters, `experiments/reel-engine-v5/` source music/model adapters. Old folder names and V6-prefixed job IDs/API paths are **V7 compatibility protocols**, not evidence of an active legacy product.
- **PROTECTED service-binding dependencies, despite V1 names:** `delulutech-ai-reel-projects-v1` is V7 `PROJECT_AUTH`; `delulutech-ai-reel-api-v1` is V7 `DISPATCH_API` for the internal `/internal/v6/dispatch` GitHub Actions wake. Do NOT delete these Workers, their service bindings, credentials or private endpoints. Both already have direct workers.dev subdomains disabled; keep this boundary. Their historic public domains, if any, must be audited before a change.
- **PROTECTED data:** Cloudflare KV `1206d0c653eb4a268a81309d9eea6dce` and attached D1 shared with owner private render state. No KV/D1 deletion, schema change, credential rotation, secrets exposure or source-media migration.
- **PROTECTED V7 QA:** V7 cinematic CI plus V7-dependent tests housed in V6-named `mad-v6-kv-contracts.yml`, `mad-v6-ffmpeg-bridge-ci.yml` and `mad-v6-kv-filmcraft.yml`. Old names are not adequate justification for shutdown.
- V7 remains private and under owner release/publishing approval. Model/RAG/music rights blockers in issue #222 remain open. Retirement of earlier versions is NOT V7 acceptance certification.

## Classification of independent legacy endpoints (NOT V7 runtime)
1. Legacy Cloudflare Pages: `mad-v6-owner-private-beta` and `delulutech-ai-reel-engine-v1` (latter owns `reel.delulutech.in`). Deprecate public entry points after checking custom-domain and V7 owner UI isolation. Preserve rollback documentation, no impact on V7 Pages.
2. Legacy standalone Workers: `mad-v6-kv-private-beta`, `mad-v6-owner-private-beta`, `mad-reel-v5-github-mcp`, `mad-reel-v5-oidc-bridge`, `mad-filmcraft-private-delivery-20261105`, `mad-gate2-inference-stage-20261029`, old MAD Yard one-off preview/review Workers, two transient network QA Workers. Their *public routes* can be retired independently **only after** confirming no V7 binding or customer-facing shared use. Retain code for rollback; never delete shared KV.
3. GitHub independent V5 model/Cloudflare relay: `.github/workflows/mad-v5-cloudflare-bridge.yml` has two autonomous daily cron frequencies (minutes 16 and 46) and owner issue/dispatch triggers. It runs a legacy V5 synthetic/private V1 pickup, **not** the V7 job runner. Disable this autonomous operation after verification. Keep historical archives and receipts.
4. Other V1–V6 workflow CI and manual jobs should be classified per trigger and V7 import before disabling. V7 relies on some old-named regression tests; never blanket delete directories/workflows on the basis of the version string.
5. `delulutech-ai-reel-api-v1` has a separate five-minute `recoverPendingWakes` cron for old V1 media queue; V7 uses its *internal service binding* for dispatch, not the V1 cron. If the V1 cron is retired, retain the script, secret and service binding. Independently verify V7 dispatch still works.

## Staged deprecation procedure / rollback
1. **First consolidate inventory** (this file, verified from GitHub and Cloudflare management APIs). Freeze V7 code, Pages, V7 Worker, OIDC workflow ref, D1, KV, bindings and owner gate. Record source SHA before/after.
2. Stop only obsolete autonomous V1/V5 triggers and independently route-exposed legacy Workers; keep shared V7-dependent service scripts alive.
3. Prefer disabling old public routes and schedule triggers over deleting code, KV, databases, customer media, secrets or Git history. For legacy Pages, remove legacy exposure only after owner UI and domain mapping are accounted for.
4. Read back each Cloudflare change and GitHub main commit; verify protected V7 Worker bindings/subdomain/cron, V7 Pages project, signed workflow and owner-auth status are unchanged. Do **not** send a real render, publish a Reel or change V7 code during deprecation.
5. Rollback legacy routes by restoring their previous workers.dev subdomain state and exact cron schedule / GitHub workflow triggers from source history. Keep V7 intact throughout.
6. Report verified technical changes via a `STACK CHANGE:` main commit and actual Master Registry marker readback; never claim deployed/runtime or full acceptance if only source documentation was changed.

## Evidence baseline
- GitHub main before retirement: `dc0078a13cbeed43a6135b9111e8f1452e5dc7c3`.
- Signed V7 technical canary: GitHub Actions `42363358638` succeeded but final audio selected source ambience; external rights-cleared music and owner-browser upload→download still pending. See issue #222.
- Cloudflare management read on 2026-11-07: V7 Worker has `DB`, `DISPATCH_API`, `PROJECT_AUTH`, `MEDIA_KV`; legacy workers and Pages are separate resources. No V7 production modifications authorized by this inventory.
