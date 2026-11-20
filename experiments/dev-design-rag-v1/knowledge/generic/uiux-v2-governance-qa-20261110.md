# GENERIC UI/UX KNOWLEDGE V2 — EVALUATION, VERSION GOVERNANCE, RELEASE
Version: 2.0.0 | Reviewed: 2026-11-10 | Layer: generic/shared | ACTIVE
Sources: https://www.w3.org/TR/WCAG22/ ; https://www.w3.org/WAI/ARIA/apg/ ; https://web.dev/explore/learn-core-web-vitals ; https://www.nngroup.com/articles/ten-usability-heuristics/ ; https://www.nngroup.com/articles/state-of-ux-2026/

## Version and authority order
Current explicit owner instruction > current approved brand identity > active project brief > applicable normative technical standards > historical review evidence > awards and exploratory trends. A prior palette or style is NOT binding when superseded. Keep immutable historical records for diagnosis; never merge deprecated aesthetic instructions into the active brief. All retrieval excerpts must have source_id, layer, source_url, active/historical status and rank rationale. A globally truncated serialized query is a retrieval failure; compile compact independent chunks within an explicit token budget.

## Artistic review is independent
Example balanced rubric, 100 points: identity 15, composition and hierarchy 15, typography 12, authenticity and honest imagery 14, mobile art direction 12, information architecture/task efficiency 12, interaction feedback 6, performance 8, originality 6. Scores only count from named independent reviewers who actually inspect exact desktop/mobile screenshots and cite evidence. Do not self-score. Global gate >=95/100 and APPROVE if owner policy requires it.
Hard failure regardless of score: fake photography or unsupported claim, missing core page, broken primary action, critical/serious WCAG violations, horizontal overflow, nonworking menu/keyboard, missing provenance, wrong source hash, failure to honor reduced motion or owner approval.

## Release controls and source fidelity
Release artifact must be deterministic and version controlled; source-to-deploy hash receipt required. Test the same build subsequently published; verify live routes, real content, image load, accessibility, tasks, HTTPS, security headers and noindex staging. HTTP 200 or Vercel READY is transport success, not design success. Never use dummy placeholder pages to masquerade as a completed five-page site.
Production change always requires explicit owner approval. Preview draft must explicitly be marked uncertified unless all required gates passed. Avoid leaking customer media or internal source files.

## QA examples
Responsive 320/390/768/1440: no overflow, correct hero cropping, CTA immediately available, no broken images. Navigation: toggle aria-expanded true/false, Escape when appropriate, focus restore, links complete. Forms: date order validation, error recovery, truthful outcome. Direct booking/WhatsApp: no false automatic confirmation.
Performance: field 75th percentile LCP <=2.5s, INP <=200ms, CLS <=0.1; Lighthouse lab scores separately and by device; production SEO vs intentionally noindex preview measured separately. If independent reviewer or real field evidence absent say UNVERIFIED.
Automation: one job per project/source hash, bounded model context and tokens, checkpoint and small-task resume on rate-limit, never switch to paid without approval. Owner source assets must preserve their geometry and licensed rights.

