# META CORE Lane A — Independent Security Review Package

**Review-only branch:** \`audit/meta-core-lane-a-security-20261110\`  
**Frozen source commit:** \`25acc4dd4f4577356fb335ad7ec105c19446c076\`  
**Original security PR:** https://github.com/karanzing1992/engagement-core/pull/262  
**Original parent:** \`feat/meta-core-lane-a-final-provider-20261110\` (PR #261 head)  
**Formal acceptance register:** https://github.com/karanzing1992/engagement-core/issues/263  
**Status:** SOURCE_ONLY, REVIEW_PENDING, NO_MERGE, NO_DEPLOY.

## Boundary and scope

This review branch was created directly from the source commit above. Any commits after that immutable source commit should only add reviewer documentation and isolated test workflows. The product code must remain byte-for-byte equivalent to the frozen source commit. Before acceptance, compare the entire \`integrations/meta/whatsapp-mcp/\` subtree at this branch against the frozen source.

**Important GitHub limitation:** Branches do not provide collaborator access isolation. This repository is public, and adding a collaborator grants repository-level permissions. If the reviewer needs access isolated from other repository content, use a separate private review repository with a vetted source-only export instead. Do not use any owner-controlled alternative account as an "independent" reviewer.

The review-only PR **must compare this audit branch to parent branch \`feat/meta-core-lane-a-final-provider-20261110\`** so the reviewer sees actual changes in PR #262, not merely the added audit docs and CI. Never merge the audit PR.

## Reviewer checklist

- Confirm source commit and original #262 diff equivalence, with no product-code changes on audit branch.
- Examine authentication/tenant scope, grants default disabled, WABA+activation ownership, 24-hour consent/template/billable-send policy, mutation IDs, replay and dedupe boundaries.
- Probe Proxy/accessor/thenable behavior before authentication, argument snapshot TOCTOU, and nested output sanitization; test P1 array override/leak and P2 analytics clicked/cost shapes.
- Assess sender/source URL, SSRF and redirect/egress boundaries; live provider egress is NOT validated in Lane A. Check missing trust or resource boundaries.
- Confirm exactly **109/109 passing Node tests and npm audit 0** on original source SHA using GitHub Actions #42868609545; original **CodeQL security-extended 30/30 JS source files / zero SARIF findings**, GitHub Actions #42868609114. Verify fresh isolated reviewer workflow run with actual findings count and the three-day SARIF artifact.
- Review dependency licenses and pinned checkout/setup-node/CodeQL actions. All tests use synthetic inputs and no Meta/WACRM credentials.
- Report P0/P1/P2 findings with file paths and reproductions. Never alter frozen source branch to "make tests pass"; request a separate security fix PR, then invalidate stale approvals.

## Formal approval and owner decision

**Reviewer:** A real, qualified independent person not controlling the owner accounts. They must review the full source diff and submit a GitHub \`APPROVED\` review on the review-only PR, referencing the exact immutable code commit, the audit PR head, test links and remaining risk. A \`COMMENTED\` review or passing CodeQL is not approval. This review-only PR does not convey authorization to merge #262.

**Owner:** Verify reviewer identity and independence, compare frozen source-equivalence, close accepted review findings after confirmation, then record \`SOURCE_SECURITY_ACCEPTED_FOR_CONSOLIDATION_ONLY\` or \`NO_GO\` on issue #263 with the review URL, exact SHAs, test evidence, risk limits and date. Accepting source review only authorizes preparation of a non-destructive #215→#257→#258→#261→#262 ancestry reconciliation. Production, branch merges and all live Meta/WACRM interactions require separate review and explicit authorization.

### Decision record fields

- Reviewer GitHub username:
- Independence + review permissions confirmed:
- Reviewed source SHA: \`25acc4dd4f4577356fb335ad7ec105c19446c076\`
- Audit branch / audit PR head:
- Reviewed full diff (yes/no):
- Passing CI / CodeQL links and SARIF count:
- P0/P1/P2 remaining:
- Residual risks, including trusted-provider Promise assimilation:
- Approval URL and timestamp:
- Owner decision / issue #263 comment:

**No live grants, credentials, customer data, production changes, paid messaging, phone migration or real Meta Graph requests.** Lane B has separate issuer/OAuth, WACRM custody/outbox and Meta sandbox gates. Ashwakaal — Support Channels separate. Do not submit SOURCE_ONLY review activity as VERIFIED_LIVE in Supabase Master.
