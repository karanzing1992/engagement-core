# Design RAG 2.1.0 × Autonomous UI/UX Engine 2.1.0 — Dell engineering promotion

**Date:** 2026-11-11. **Classification:** VERIFIED_LIVE_DELL_ENGINE_ONLY. **Website production:** NOT CHANGED.

## Source and immutable release

- Candidate: `karanzing1992/engagement-core` commit `12788a4ef50ebd4a8bc794ad9444cf1354df74d5`, branch `feat/design-rag-engine-v2.1-gemini-bridge-20261111`. The candidate branch is not represented here as default-branch merge or public deployment.
- Canonical Dell source snapshot: `~/.local/share/dev-design-rag-v1/releases/2.1.0-12788a4ef50ebd4a/`.
- Active Dell pointer: `~/.local/share/dev-design-rag-v1/active` -> pinned release snapshot.
- Owner-scoped launchers: `~/.local/bin/design-rag`, `~/.local/bin/uiux-engine`, `~/.local/bin/design-vision-bridge`.
- Design RAG 2.1 uses `~/.local/share/dev-design-rag-v1/runtime-overlay-2.1.0-12788a4`: a **private 2.1 manifest**, with symlinks to the existing data, graphs, owner ACL and ledger under `runtime` (no duplicated customer/project data). Old `runtime/knowledge_manifest_v2.json` stays at 2.0.0 so unupgraded clients are compatible. Engine V2.1 remains backward compatible with original V2 workspaces and consumes the original shared graph.
- A different preexisting `runtime-v2.1` directory was detected and **not modified**; the overlay has a distinct name to avoid destructive collisions.
- Original Dell source under `source/` and V2.0 attested worktree at `2de2b388d3291f850c6de23ce68a6f45c4ee2f2f` remain preserved.

## Post-activation certification

Executed directly against the installed release snapshot (not just a GitHub clone):

- Design knowledge: 34/34 unit tests PASS.
- Engine certification: 9/9 PASS.
- Security: 13/13 PASS.
- Orchestration: 4/4 PASS.
- Trusted vision advisory bridge: 14/14 PASS.
- **Total: 74/74 verified tests.**
- New V2.1 engine workspace created from the real Andaz baseline and recorded engine-state version `2.1.0`; RAG query returned `READY`, version `2.1.0`, 11 scoped sources.
- Live launcher status returned knowledge version 2.1.0; live query returned version 2.1.0.
- Existing V2.0 workspace read successfully through promoted engine.
- Deliberately incomplete artistic verification still yields `BLOCKED` from the release gate with `production_release_allowed=false`.
- An independent second check from neutral working directory verified old source returns knowledge version 2.0.0.
- On-host release receipt `runtime/active-design-release.json` SHA256 `7b3ffc52775c02bb9cb2d93d8aa8d6dee6c12f4777410306b4fbef14f8328bb8`. Five detailed test logs under `runtime/receipts/v21-promotion-20261111/`.

## Capability and blockers

The V2.1 Design RAG and UI/UX Engine are available for **new Dell jobs using the versioned launchers**. The secure 12-image manifest and fail-closed authentic-review ingestion contract are implemented, but the GitHub owner-only public-page model run is not evidence of private Dell image certification. The independent Ed25519 trust registry and genuinely calibrated >=95/100 artistic score remain unprovisioned/not independently attested. No website preview, merge, production release or customer-data transfer was authorized by this promotion. The original 2.0 client and storage can be used for rollback.

## Rollback operator note

Use the retained `source/experiments/dev-design-rag-v1` (2.0.0) and the unchanged `runtime` manifest (2.0.0). Do not delete or modify the original runtime graphs, review ledger or V2.0 workspaces. Retire the new launchers/active symlink only under the verified owner-scoped Dell change path. No automatic swap of private keys, production domain or customer content is required.

## Next bounded gates

1. Securely provision and independently authenticate the private Dell vision execution path with isolated service principal and one-image-at-a-time Gemini 3.5 Flash-Lite calls.
2. Collect 12 real screenshot reviews bound to exact site/build/QA hashes; keep advisory review distinct from independent art signing.
3. Complete independent calibration and genuine >=95/100 approval, fresh QA/Lighthouse/recovery, and a private preview.
4. Obtain owner approval before any separate production website deployment.
