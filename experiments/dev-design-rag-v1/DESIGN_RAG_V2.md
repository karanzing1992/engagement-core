# DEV DESIGN RAG V2 — Dell live handover (2026-11-10)

This upgrades the knowledge+retrieval layer of existing Design RAG 1.0. Existing authenticated scope registry and review ledger keep their v1 storage format; CLI status exposes knowledge_version 2.0.0 and queries return version 2.0.0.

## New capability
- Four immutable source-backed, BRAND-NEUTRAL V2 generic modules: UI/UX foundations, interaction patterns, verified 2025–2026 awards/trends and independent QA/release.
- Current Andaz V6 brand record indexed only under brand/andaz; the current project V6 brief is pinned ahead of history.
- Versioned source manifest under knowledge/manifest-v2.json; deployed at runtime/knowledge_manifest_v2.json.
- Deterministic BM25 rank+source and per-layer budgets against existing isolated LightRAG chunk stores. No paid inference, no raw JSON truncation.
- Default DesignKnowledge.query() returns bounded packet_text, source list, historical exclusions, SHA256 and estimated token budget (<=9000 chars), plus compatible layers keys.

## Use
From authenticated Dell CLI, set PYTHONPATH to experiments/dev-design-rag-v1 source, then call python -m dev_design_rag --root ~/.local/share/dev-design-rag-v1/runtime query --project andaz-vibe-stay --prompt "Current V6 design instructions and 2026 award examples".
Agents should consume packet_text, not the entire JSON or legacy reports. Abort if version, current IDs, scope ACL, source hashes or token budget fail. Do not duplicate the project brief inside the same model input.

## Governance
Generic/shared stays public and brand-neutral. Source authority: current owner/project/brand > normative universal standards > historic evaluations (diagnostic only) > award inspiration. Prior designs remain indexed for learning but are not active instructions. A new brief gets a new immutable document ID and manifest update. Independent 95/100 actual-screen artistic review and all functional/accessibility QA remain mandatory before production approval.
Awards are links and paraphrased lessons, NOT licenses to copy imagery, copyrighted layouts or source.
Tests: runtime/receipts/v2-unittest.out (34 passed), runtime/receipts/query-v2-20261110.json, runtime/receipts/v2-*.json.
Backup: dev-design-rag-v1/backups/design-rag-v1-presync-20261110 and git commit history. Do not restore a shared graph without explicit owner approval.

## V2.1 source revision (2026-11-11)
RAG knowledge layer 2.1.0; engine new workspaces 2.1.0; storage registry 1.0.0 remains unchanged. Original 2.0 workspaces read-compatible, never rewritten. Added encrypted review handoff, provenance checks and advisory-only import; no signed independent gate bypass.
