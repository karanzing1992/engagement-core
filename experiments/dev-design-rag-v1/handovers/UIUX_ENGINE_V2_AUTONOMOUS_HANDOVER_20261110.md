# Generic Design RAG V2 × Autonomous UI/UX Engine — Owner Handover
Date/time: 2026-11-10, approximately 21:25 IST
Status: **ENGINEERING PATH VERIFIED; FULL AUTONOMOUS RELEASE CERTIFICATION BLOCKED**
Scope: reusable, brand-neutral Dell DEV DESIGN RAG + autonomous UI/UX engine. Isolated Andaz test only; production/OTA/social remain untouched.

## Authoritative source and addresses
- Dell working repository: `~/.local/share/dev-design-rag-v1/source` branch `feat/design-rag-v2-20261110`
- Knowledge RAG source: `experiments/dev-design-rag-v1/dev_design_rag/knowledge_v2.py`
- Engine source: `experiments/dev-design-rag-v1/engine/` (`core.py`, `cli.py`, `agent.py`, `qa-site.cjs`, `lighthouse.py`, `reviewer.py`)
- Actual RAG runtime: `~/.local/share/dev-design-rag-v1/runtime`
- QA test fixture: `~/.local/share/dev-design-rag-v1/certification/uiux-v2-andaz-fixture-20261110`
- Existing master policy/validator: `runtime/autonomous_ui_workflow.json`, `runtime/verify_autonomous_ui_flow.py`
- Backup: `~/.local/share/dev-design-rag-v1/backups/design-rag-v1-presync-20261110`
- Existing GitHub source sync issue: https://github.com/karanzing1992/engagement-core/issues/256
- Master Stack prior confirmed #346: RAG V2 source-grounded knowledge with 34/34 unit tests; source only locally committed at checkpoint `aeba4f3e3e7a1bedb7380a59f2b28175b7c3a6aa`.
- Owner policy: generic Design RAG, four isolated layers; current owner/project > current brand > standards > historic as diagnostic; free/open-source first; all genuine source-media; independent >=95/100 and verdict APPROVE; final owner production permission required.

## Verified work in THIS integration sprint
1. Brand-isolated RAG V2 packet retrieved and snapshotted into fixture: estimated 2,669 tokens; input source hash recorded; prepared from pre-existing five-page Andaz V6 retry baseline in a new isolated workspace.
2. **Actual Matrix free GPT-OSS-20B** concept generated with owner-approved SOP task packet and under router's 2,048-byte public prompt cap. Initial attempts failed `SOP_TASK_PACKET_REQUIRED`, `PUBLIC_PROMPT_MAX_2048_BYTES` and replay guard; controller corrected, accepted design-model output 3,879 bytes. This is not independent artistic approval.
3. **Actual isolated OpenCode/Groq OSS-120B coding** generated new `engine-smoke.html` via verified `read` and `write` tool events (not manually authored website code), with output-site hash `0f3d5997889a3a6fff0d93cc8ed19adc8633a53bd89b608a285a213ed4e013b1`. Original 5 pages preserved. First run was denied by scoped path config, adapter fixed with task-specific config and sandbox; successful follow-up file-write completed in ~17s.
4. Browser automation + axe: **24/24** cases PASS over six pages at 320/390/768/1440; **24** actual screenshots captured and hashed. Screenshot provenance tied to identical source hash.
5. Actual isolated Lighthouse on the new agent-created page: **mobile perf 100, accessibility 100, best practices 96; desktop perf 98, accessibility 100, best practices 96**. SEO 54 on test page, not a production SEO claim. Critically these Lighthouse scores are for the **test page**, NOT every route.
6. Integration gate explicitly returns `BLOCKED` for preview: missing independent artistic review/receipt >=95. Production release additionally blocked by owner release authority. Source & QA hashes checked.
7. Local vision reviewer `qwen3-vl:2b-instruct` attempted review of real screenshot pair, **FAILED** with `VISUAL_MODEL_TIMEOUT_OR_ERROR:HTTPError`; no independent artistic score was issued. Model readiness/capacity is unresolved, previous 78s timeout also known. No publication.
8. Review receiver validates screenshot hashes, build hash, independent reviewer identity, complete page coverage and a local HMAC attestation. **Caveat:** local shared-user HMAC does not create an organizational trust boundary; reviewer authentication/attestation needs security review before treating externally supplied verdicts as trusted.

## Remaining blockers to claim 'fully ready'
- Resolve local vision API HTTPError and certify an independent, truthful full-screen 6-page mobile+desktop artistic assessment. Never invent >=95 or claim approval from browser QA. If model capacity insufficient, choose an authorized free alternate with license/API verification. Keep independent from writer.
- Test failure/malicious reviewer receipts: forged signature, wrong source hash, wrong screenshots, missing pages, fabricated 95 and partial review must all fail closed. Keep reviewer secret separate from code-writing agent.
- Require Lighthouse + source hashes for complete critical site/route coverage; current perf scores only represent smoke page.
- Add run-level orchestration: stage checkpoints, bounded retry/backoff, idempotent resume after model throttle/permission failures and single job status. Currently controller exposes CLI stages; **not** fully unattended continuous autopilot, and no scheduled job was enabled.
- Hook the generic checked preview deployment tool into the same gate (independent Vercel deployments previously bypassed the policy). Production approval must remain external/owner-authenticated. No deployment occurred in this sprint.
- Reconcile divergent remote V1 branch and push new review branch/PR without force, no public main mutation. Existing #256 tracks issue. Existing `uiux_auto/` and `uiux-certification/` untracked folders may be another worker; inspect before adopting/overwriting.
- Run broad cross-project tenant-isolation, security, negative, rate-limit and multi-run tests; confirm result not brand-specific.
- Record Master Stack event for engineering integration, with DOC_VERIFIED but consumers/GitHub SYNC_PENDING until actual acknowledgements.

## Next bounded execution sequence
1. Read this handover and inspect current `engine-state.json`, SHA, screenshots, staged source and current connector status. Do not rerun already-successful work or modify live sites.
2. Diagnose Ollama vision HTTPError using small model availability request and returned HTTP status (without leaking private media); run independent all-page screenshot review or document BLOCKED.
3. Extend negative tests of signed receipts and invariant checks. Verify Lighthouse on all critical pages; audit mobile/performance.
4. Add deterministic orchestrator with owner SOP + model token limits, per-job checkpoints, fail-closed preview adapter and real deployment hash check; test on isolated brand-neutral fixture.
5. Certify only stages supported by actual receipts, publish GitHub source review branch if safely reconciled, update Master Registry, then deliver final acceptance report and owner-only release decision.

## Safety and accurate reporting
Do not call this a completed automatic UI/UX delivery platform yet. Do not falsely report the V6 site artistically accepted. A 24/24 browser pass does not satisfy the 95/100 artistic gate. Do not alter the property production website, owner account, secrets, OTA or paid routing. Do not reveal keys or publish guest data. Historical/archival knowledge stays indexed but excluded from active aesthetic generation.
