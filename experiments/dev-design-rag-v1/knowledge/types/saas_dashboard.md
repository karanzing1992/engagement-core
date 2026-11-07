# SaaS Dashboard UI/UX — Type Graph

Public principles only. References: https://www.nngroup.com/articles/ten-usability-heuristics/ ; https://www.w3.org/TR/wcag/ ; https://designsystem.digital.gov/components/

## Dense information design
Organize metrics by decisions users take rather than visually attractive charts. Display units, time range, comparisons and missing-data semantics. Use progressive disclosure and consistent filters. Never invent revenue, customers, rankings or other metrics. Charts need accessible text equivalents and distinguishable series.

## State and permissions
Design loading, empty, error, permission-denied, read-only, draft, running, success and rollback states; a glossy empty state must not hide actual blockers. Show read versus write capabilities and audit context before consequential actions. Make data-entry actions reversible and focus-aware where possible.

## Navigation and component libraries
Use semantic reusable tokens, scalable table layouts, keyboard/focus management, clear search/sort and filtering, and pagination/virtualization for large datasets. Honor user roles and avoid cross-account data leakage. Adapt on narrow screens with deliberate prioritization, not illegible squashing.

## Acceptance
Synthetic tenant data only during QA, no cross-tenant access, contrast+keyboard+screen-reader testing, table sort/filter functional evidence, Lighthouse where web-based, independent artifact-scoped artistic >=95, separate owner release.