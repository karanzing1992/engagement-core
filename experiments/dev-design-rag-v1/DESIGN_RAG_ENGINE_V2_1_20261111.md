# Generic Design RAG 2.1.0 × Autonomous UI/UX Engine 2.1.0
Date: 2026-11-11. Isolated candidate — no deployment or production changes.

## Versions and compatibility
- Design RAG target 2.1.0; accepts historical source manifest schema 2.0.0 or 2.1.0, with pinned owner > brand > generic > type precedence.
- Autonomous UI/UX Engine target 2.1.0, creates version 2.1.0 workspaces, validates existing 2.0.0 workspaces without reformatting. No automatic release or migration of production environments.
- Vision bridge protocol 1.0.0, with 6-route × 390px/1440px screenshot hashes, QA digest, site treehash, job and project bindings. A technical smoke page is not a marketing route.
- Existing art signer / independent >=95 gate deliberately unchanged.

## Secure Gemini bridge
engine/vision_bridge.py prepare --workspace /path/to/workspace creates a mode-0600 LOCAL-ONLY manifest, no image transfer. The existing owner-only GitHub Actions Gemini API key is not copied to Dell. A future registered isolated self-hosted Dell runner or approved encrypted private transport is required before genuine private screenshot inference. The inspected local runner directory is not registered. Cloud-hosted runner screenshots of the public website are not equivalent evidence for the Dell-built site.
vision_bridge.py ingest --workspace ... --receipt ... accepts only a full 12-image digest-bound, authentic Gemini 3.5 Flash-Lite response with separate Ed25519 trusted-runner signature verified against a root-owned /etc/moksha-uiux-v2/trusted-vision-advisories.json registry. At this checkpoint the registry is NOT present, so the receiver intentionally fails closed. No self-asserted JSON can become authenticated review. The signature is for advisory feedback provenance only, NOT the separate trusted independent artistic certification.
vision_bridge.py correction --workspace ... emits limited brand/RAG-governed corrective directions from authenticated source-matched feedback; stale site builds fail. All model notes are untrusted evidence, not instructions to override safeguards.

## Verification boundaries
Existing public five-route/10-image Gemini Actions run: https://github.com/karanzing1992/engagement-core/actions/runs/42902936148 — real authenticated inference, public website only.
Six isolated local fixture routes verified via source manifest; private transfer and independent artistic inference are BLOCKED until protected runner onboarding and signer keys. No numeric artistic score, no signed >=95, no preview/production approval.
No screenshots or API keys committed. No automatic GitHub Actions runner registration; must provision scoped registration, hardened runner isolation, allowlisted workflow and signer custody first.

## Rollback
Switch back to the preserved source worktree attested-engine-20261110 at commit 2de2b388d3291f850c6de23ce68a6f45c4ee2f2f. This release candidate has no production side effects. Reject 2.1 new workspaces with old tooling rather than silently mutating them. No removal of the previous 2.0 knowledge manifest from original local runtime.

## Evidence requirements before release
- Registered isolated Dell reviewer runner; owner-scoped only; security tests for arbitrary PRs, symlink exfiltration, fork triggers and secret disclosure.
- 12 REAL Gemini private screenshot reviews of exact site hash, model trace, Ed25519 advisory provenance, signed independently assessed >=95, fresh Lighthouse and accessibility checks.
- Owner preview approval and separate production release gate.
