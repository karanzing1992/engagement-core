# DEV DESIGN RAG 1.0

**Design Intelligence RAG — shared UI/UX, brand/project-isolated knowledge, review capture and release-quality enforcement**

Version: **1.0.0** · Date: **2026-11-07** · Source repository: \`karanzing1992/engagement-core\` · Branch: \`feat/dev-design-rag-v1-20261107\` · Status: **Dell isolated pilot verified; source changes not merged to main; consumer-wide rollout pending**.

## 1. Purpose and owner decisions

The existing Andaz LightRAG experience is reused as the foundation of a general Design Intelligence tool rather than becoming a global mix of customer brands. It implements seven owner instructions:

1. Strictly separate **generic UI/UX knowledge**, **project-type knowledge**, **brand knowledge**, and **project-specific knowledge**, with isolated graph storage.
2. **Capture every review emitted through the DEV DESIGN RAG tool**, not only approved reviews; journal and retry any failed indexing.
3. Make acceptance checks **executable**, not merely instructions in RAG context.
4. Apply **independent artistic >=95/100 and APPROVE** as a **global, non-overridable tool rule** rather than an Andaz preference.
5. Reuse LightRAG and enhance it with independent, primary-source UI, UX, accessibility, color, responsive, design-system and artistic guidance.
6. Create a catalogue of **project-type graphs and separately registered brand/project graphs**; do not expose one brand to another.
7. Document the tested capability and unresolved adoption gates as **DEV DESIGN RAG 1.0**.

The 95-point artistic threshold is an owner-chosen quality gate, **not a scientific guarantee that any model's scores are perfectly objective**. Art review always describes a specific artifact and scope, never unreviewed pages.

## 2. Stack and source/cost gate

- **Core RAG:** existing locally deployed [HKUDS LightRAG](https://github.com/HKUDS/LightRAG), Dell v1.5.7, MIT license; original copyright/license obligations apply.
- **Embedding:** existing local [Ollama](https://ollama.com/) \`all-minilm\` 384-dimensional embedding, no external model calls for indexing/retrieval.
- **Backend and journal:** existing Python 3.12, SQLite stdlib WAL, \`httpx\`, \`numpy\`, \`networkx\` reused from installed Dell environment; review queue and deterministic custom graph chunks implemented with minimal local glue.
- **Audit evidence producers:** existing Playwright + axe-core + Lighthouse CI; independent Gemini Vision via the owner's separately approved API runner; the API may be subject to quotas and must not be silently substituted with paid providers.
- **Cost:** existing locally operated tools/free/open-source libraries; no new purchased SaaS, paid API call, host fee or secret was provisioned by this sprint.
- **Licensing:** LightRAG MIT; source articles/standards are referenced and paraphrased, not copied wholesale; imagery is never introduced without verified applicable rights.
- **Reuse rationale:** separate storage directories and deterministic type/brand/project routing reuse LightRAG directly rather than building a new vector database or proprietary RAG.

## 3. Four independent graph layers

| Layer | Physical namespace | Sharing rule | Data allowed |
|---|---|---|---|
| Generic | \`graphs/generic/shared\` | Shared across registered, authenticated design projects | W3C/NNGroup/Material/MDN/USWDS/public design principles only |
| Project type | \`graphs/types/<type>\` | Shared only when a project is registered to that type | Hospitality/SaaS/mobile/ecommerce/editorial/game UI patterns |
| Brand | \`graphs/brands/<brand>\` | Only projects explicitly bound to that same registered brand | Brand identity, verbal/visual rules, owned positioning and assets |
| Project | \`graphs/projects/<project>\` | One project's authorized workers only | Its detailed scope, project-specific reviews, design decisions, QA receipts |

**Hard separation:** all scopes have their own independent LightRAG working directory, entity graph, vector files and source corpus. Retrieval is ordered **generic → registered type → registered brand → selected project**, assembled by server-side registry, not free-form user input. Arbitrary user-provided paths, graph names, symlinks, unknown principals, wrong owner/brand bindings and off-project reads are denied. Shared knowledge rejects known brand/customer markers; always prefer manual classification of ambiguous sources.

**Security boundary:** isolated directories are mode 0700 with sensitive registry/SQLite files 0600, behind the existing owner-authenticated Dell SSH execution channel. This is *application-layer and same-Unix-user file isolation*, not an independently authenticated multi-tenant HTTP API or separate Unix-user sandbox. Do not expose the CLI as a public API without a full issuer/role/audience auth and OS isolation review.

The pre-existing 35-node Andaz graph remains at its original location and is **not** spliced into shared knowledge. Its approved brand brief and dated audit documents were instead independently imported into the correct new private layers. No original Andaz, Moksha, WordPress or customer database was modified.

## 4. Project-type coverage and onboarding

The current registered types, each with an independent local LightRAG graph and source notes, are:

- \`hospitality\`: booking vs enquiry, accommodation discovery, truthful imagery, guest journey.
- \`saas_dashboard\`: data hierarchy, states, permissions, dense tables, audit and undo.
- \`mobile_native\`: Android dp/48dp guidance and Apple pt/44pt guidance, accessibility, permissions and back navigation.
- \`ecommerce\`: honest product information, checkout, verified totals, privacy, reversible actions.
- \`editorial_content\`: page hierarchy, credible photography, captions, media provenance and publication gates.
- \`interactive_game\`: gameplay HUD, control affordances, performance and 3D visual clarity.

Dynamic **brand registration** and **project registration** are exposed through owner-only \`register-brand\` and \`register-project\` CLI commands. A project must bind to one recognized brand and one recognized project type. It receives new empty private graph storage. There is no automatic cross-brand cloning. Brand/project graph onboarding must be approved by the owner and limited to that tenant's permitted scope.

## 5. Generic design foundation — referenced sources

- [W3C WCAG 2.2](https://www.w3.org/TR/wcag/): 4.5:1 normal text and 3:1 qualifying large text (AA) subject to exceptions; 3:1 non-text information-bearing controls; 24 CSS px pointer target rule with exceptions; labels, focus, reflow and keyboard.
- [NN/g Ten Usability Heuristics](https://www.nngroup.com/articles/ten-usability-heuristics/) and [Visual Hierarchy](https://www.nngroup.com/articles/visual-hierarchy-ux-definition/): consistency, error prevention, clear feedback, meaningful hierarchy and user control.
- [Google Material semantic role tokens](https://developer.android.com/codelabs/m3-design-theming): color/on-color pairings, semantic roles, accessible theme system.
- [U.S. Web Design System](https://designsystem.digital.gov/): reusable typography, forms, navigation, design tokens, accessible component patterns.
- [Apple Human Interface Guidelines](https://developer.apple.com/design/human-interface-guidelines/) and [Android accessibility guidance](https://developer.android.com/design/ui/mobile/guides/foundations/accessibility): platform-specific interactions, native expectations and minimum touch target recommendations.
- [MDN accessibility CSS/JS](https://developer.mozilla.org/en-US/docs/Learn_web_development/Core/Accessibility/CSS_and_JavaScript): semantic layout, accessible controls, focus and zoom.
- [Google Core Web Vitals](https://developers.google.com/search/docs/appearance/core-web-vitals): field LCP <=2.5s, INP <=200ms, CLS <=0.1; separate Lighthouse lab from field performance.
- [Creative Commons licenses](https://creativecommons.org/cc-licenses/): lawful attribution, modification credit and disclosure for any image/audio assets.

Source text is *summarized* and versioned in \`knowledge/generic/design_basics.md\`, with explicit URLs and project-type companion files. Generic content may be reused by other brands **without exporting client-specific reviews to the shared layer**.

## 6. Every-review ingestion lifecycle

Each review emitted through this tool must call the synchronous \`record_completed_review(registry, receipt)\` adapter **or** atomically deliver its JSON to the per-project \`inbox/<project>/<review-id>.json\` followed by \`inbox-sync\`.

1. Validate required project identity, scope, artifact SHA256, source URL, reviewer, outcome and findings; reject known secrets and wrong-project receipts.
2. Write an immutable event into the **project-only** SQLite WAL journal with \`(project,review_id)\` uniqueness. Identical replays deduplicate; changed replays are blocked.
3. Index its evidence into the matching project's LightRAG graph only; a failing artistic review is indexed just as thoroughly as a passing one.
4. Archive successfully indexed events under \`processed/<project>\` with their original payload. Failed events remain in the inbox or journal for **deterministic reconciliation**; no silent omission.
5. Refuse release while any review for the project is not indexed, including malformed inbox entries. Quality decisions are built from the whole immutable history and exact artifact digest—**not cherry-picked best scores**.

The original three Andaz Gemini artistic reviews **54 REJECT, 68 REVISE, 96 APPROVE**, plus six historical browser/accessibility/performance/interaction review records, were migrated as separate records from previously verified evidence. They are **historical evidence**, not synthetic new passes.

**Important coverage boundary:** the guarantee currently applies to reviews routed through the **new DEV DESIGN RAG hook/inbox**. Existing external Gemini/GitHub and unrelated app workflows must emit their receipts to the approved intake adapter before they become automatically indexed. An authenticated GitHub/remote-webhook to Dell has NOT been deployed here; claiming complete ingestion across all unrelated apps would be incorrect. No public webhook or unauthenticated agent access is permitted.

## 7. Deterministic artistic and functional release gates

The global registry \`policy.json\` fixes:
- **Artistic score >=95/100** from an independent reviewer, for the **exact artifact SHA** being released.
- Independent artistic verdict **APPROVE**. All independent critiques of that same artifact must pass: any later or lower review cannot be ignored.
- Required technical review kinds: \`playwright\`, \`axe_wcag\`, \`lighthouse_mobile\`, \`lighthouse_desktop\`, \`keyboard\`; each must carry a passing receipt for that artifact.
- No pending/failed review ingestion.
- **Separate final owner release approval**, not granted by this design-RAG CLI.

A missing review, a score of 94, REVISE, a failed/absent technical test, wrong artifact digest, unindexed result or absent owner approval **all cause BLOCKED**. Project manifests cannot lower the global artistic floor or turn off owner approval; policy tampering causes registry startup failure.

**Enforcement integration:** The CLI provides a fail-closed \`gate\` command suitable for CI and the design orchestration release step. The pure-Python GitHub Actions workflow tests the policy and security invariants on branch/PR. This branch **does not silently change an existing unrelated project's deployment workflow or GitHub branch-protection settings**; every consuming development/release pipeline must explicitly call this gate and prove a consumer ACK before it is considered tool-wide adopted in that pipeline.

A Gemini artistic APPROVE is not evidence that GDPR/security/legal/checkout/real-property claims or WCAG compliance are certified. Owner approval is still mandatory.

## 8. Current Dell implementation / tested status

- Runtime root: \`/var/lib/generic-linux-automator-exec/.local/share/dev-design-rag-v1/runtime\`
- Source path: \`.../dev-design-rag-v1/source/experiments/dev-design-rag-v1/\`
- Legacy source/rollback: \`/var/lib/generic-linux-automator-exec/.local/share/andaz-autonomous-website-pilot-20261106/storage/\` (read-only source of truth, preserved)
- Graph instances: **9** = 1 generic + 6 type + 1 Andaz brand + 1 Andaz project. Each has separate LightRAG entity/vector/chunk storage.
- Historical reviews ingested: **9 total** = 3 artistic, 3 accessibility, 1 functional, 1 performance, 1 UX.
- Review backlog after verified backfill: **0**.
- Local embeddings only; no paid LLM/API indexing calls.
- Source-level isolated security/policy/review unit tests: **27/27 passed** after last review-hook update (expand as new regressions are added).
- Real Dell four-layer \`LightRAG.aquery(mode=naive,only_need_context=True)\` retrieval: **PASS**. Tested source-backed WCAG, hospitality patterns, Andaz brand and project-specific Gemini evidence, with **no Andaz brand leakage into shared generic or hospitality graph context**.
- GitHub isolated certification workflow \`.github/workflows/dev-design-rag-v1-certify.yml\` created; check its job result before claiming independent GitHub CI completed.
- Owner production release: **NOT REQUESTED / NOT GRANTED**.
- No public design-RAG MCP/HTTP service, app plugin installation or other project's permission migration was performed.

## 9. Commands (owner Dell execution only)

From \`experiments/dev-design-rag-v1\`, using the approved isolated Dell Python environment:

\`\`\`bash
PYTHONPATH=. python -m dev_design_rag --root "$DESIGN_RAG_ROOT" init
PYTHONPATH=. python -m dev_design_rag.bootstrap --root "$DESIGN_RAG_ROOT" --legacy-root "$ANDAZ_LEGACY" --stage generic
PYTHONPATH=. python -m dev_design_rag.bootstrap --root "$DESIGN_RAG_ROOT" --legacy-root "$ANDAZ_LEGACY" --stage types
PYTHONPATH=. python -m dev_design_rag.bootstrap --root "$DESIGN_RAG_ROOT" --legacy-root "$ANDAZ_LEGACY" --stage brand
PYTHONPATH=. python -m dev_design_rag.bootstrap --root "$DESIGN_RAG_ROOT" --legacy-root "$ANDAZ_LEGACY" --stage project
PYTHONPATH=. python -m dev_design_rag.bootstrap --root "$DESIGN_RAG_ROOT" --legacy-root "$ANDAZ_LEGACY" --stage reviews
PYTHONPATH=. python -m dev_design_rag --root "$DESIGN_RAG_ROOT" status --project andaz-vibe-stay
PYTHONPATH=. python -m dev_design_rag --root "$DESIGN_RAG_ROOT" query --project andaz-vibe-stay --prompt "How should I design the hero and meet WCAG?"
PYTHONPATH=. python -m dev_design_rag --root "$DESIGN_RAG_ROOT" review-complete --receipt /path/to/authorized_review.json
PYTHONPATH=. python -m dev_design_rag --root "$DESIGN_RAG_ROOT" inbox-sync --project andaz-vibe-stay
PYTHONPATH=. python -m dev_design_rag --root "$DESIGN_RAG_ROOT" gate --project andaz-vibe-stay --artifact-sha YOUR_64_HEX_SHA
\`\`\`

Onboarding:
\`\`\`bash
PYTHONPATH=. python -m dev_design_rag --root "$DESIGN_RAG_ROOT" register-brand --brand my-brand --display-name "My Brand" --owner ownerid
PYTHONPATH=. python -m dev_design_rag --root "$DESIGN_RAG_ROOT" register-project --project my-project --brand my-brand --project-type saas_dashboard --owner ownerid
\`\`\`

The \`gate\` command intentionally **never accepts a self-declared \`--owner-approved\` flag**. The separate signed owner approval process remains external to this capability.

## 10. Outstanding integration and security hardening

1. Connect each approved project/worker/reviewer to \`record_completed_review\` or the scoped inbox and test its **actual** publisher receipt. Existing unrelated producers remain consumer-pending until independently verified.
2. Ensure source reviews are authenticated/cryptographically attested by actual reviewer/provider runners before a production-quality gate consumes them. Current owner CLI is trusted by authenticated SSH; external untrusted JSON must not be allowed to self-certify.
3. Before exposing multi-user or remote MCP access, introduce OS-level tenant isolation, properly authenticated issuer/audience/role binding and secret-safe service-level API. Same-Unix-user permissions alone are not a public multitenant security boundary.
4. Mark the GitHub design certification check as a required deployment/PR gate **only** in approved project pipelines; do not change unrelated branch protections without owner review.
5. Expand review feedback into curated project-type knowledge only after manual anonymization and source verification; project-specific review text stays private.
6. Obtain per-project consumer acknowledgement and owner release approval before any production rollout. Staging graph/indexing completion is not a production change.

## 11. Rollback and preservation

The original Andaz LightRAG remains untouched. The DEV DESIGN RAG root is a separate deployment tree. To stop using the new service, stop invoking the new owner CLI, disable its consuming design-gate hook in the *approved integration only*, and use the original Andaz graph. Preserve event journal/source/checksums for evidence; do not delete review receipts. Never delete or overwrite another project's graph, permissions, media or production files. Source branch can be reverted without modifying a deployed public website.

**Acceptance terminology:** \`LOCAL_GRAPH_AND_REVIEW_ENGINE_VERIFIED\` = graph and policy tests complete. \`CONSUMER_WIDE_ADOPTED\` needs all consuming tools to acknowledge review emission and release gate. \`PRODUCTION_RELEASED\` requires explicit owner sign-off and verified deployment. Do not equate these states.
