# GENERIC UI/UX KNOWLEDGE V2 — FOUNDATIONS
Version: 2.0.0 | Reviewed: 2026-11-10 | Layer: generic/shared | Status: ACTIVE
Domain: brand-neutral websites, mobile apps, dashboards, hospitality, ecommerce and editorial.
Priority: enforce universal standards, then adapt to registered project / owner brief. Do not import brand facts into shared knowledge.
Evidence types: NORMATIVE standard > researched usability principle > measured product outcome > award inspiration > design hypothesis. When they conflict, requirements and measured evidence win.
Sources: W3C WCAG 2.2 https://www.w3.org/TR/WCAG22/ ; WAI APG https://www.w3.org/WAI/ARIA/apg/ ; Nielsen Norman 10 heuristics https://www.nngroup.com/articles/ten-usability-heuristics/ (last reviewed 2024); Google Core Web Vitals https://developers.google.com/search/docs/appearance/core-web-vitals ; NN/g State of UX 2026 https://www.nngroup.com/articles/state-of-ux-2026/ (2026-01-16).

## 01. User outcomes and information architecture
Define audience, user intents, actual business/user outcome, critical flows and content inventory before styling. Put a truthful value proposition, recognizable navigation and primary action early in the journey. Separate discover, compare, decide and contact/checkout. Preserve all proven existing features during redesign. Do not convert an established five-route website to one pretty homepage. Give users clear way back, current location, error recovery, feedback and real-world vocabulary.
NN/g ten heuristics: system-status visibility; real-world language; user freedom/undo; consistency; error prevention; recognition over recall; efficiency; minimalism serving the task; actionable error recovery; contextual help. These are heuristics, not automatic success badges.

## 02. Visual hierarchy, composition and typography
Use a deliberate focal point, scale contrast, modular spacing rhythm, disciplined alignment, readable scan paths, clear grouping and generous but purposeful negative space. Every section should have distinct information, not repeated cards. Combine compelling brand authenticity with conversion clarity.
Typography system: define display/title/body/small roles using fluid type where warranted, controlled line lengths, line-height, weights, minimum practical mobile readability and actual downloadable font/license strategy. Load fonts correctly; declare robust fallbacks; avoid invisible text.
Use design tokens for neutral surfaces, ink, accent, semantic success/warning/error, borders, type scale, density and motion. Test contrast in *computed* colours on final rendered page; avoid untested fashionable low-contrast palettes.

## 03. Inclusive, accessible controls — WCAG 2.2 AA baseline
WCAG 2.2 is the current published WCAG 2 recommendation in this knowledge snapshot; meet applicable A/AA success criteria. Body text contrast at least 4.5:1, large text at least 3:1, non-text essential UI components 3:1 where applicable. Never assume icons alone communicate action.
2.5.8 AA targets at least 24×24 CSS px or meet applicable spacing/exceptions; prefer 44×44 touch-friendly targets when practical (recommendation, not WCAG rule). Keyboard operate all functions; visible focus and focus not obscured; skip to content; semantic headings; predictable labels, accessible names and roles. For dialogs and disclosure menus: accurate expanded state, Escape handling when appropriate, focus placement and return. Reduced motion preference is respected; never trap scrolling or focus.
Automated axe checks are necessary but not sufficient. Add manual keyboard and screen-reader evaluations for critical flows.
Source examples: https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum and https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum

## 04. Performance is a design constraint
Core Web Vitals: LCP <=2.5s, INP <=200ms and CLS <=0.1 at the 75th percentile of field visits where available. These are field-experience measures, not an interchangeable Lighthouse lab score. Optimize image crops/resolutions/srcset/sizes, reserve width and height, lazy-load below-fold media, do not lazy-load the true LCP hero, preload only justified critical assets, limit blocking JS and animation. Use layout-first CSS, progressive enhancement and content-first performance.
Evaluate at 320,390,768,1440px and representative touch/keyboard states. Avoid horizontal overflow, hidden navigation, invisible CTA and unbounded image intrinsic sizes.

## 05. Content trust and ethical imagery
Only claim facilities, prices, reviews, staff, availability, sustainability, certifications and real-world outcomes supported by approved evidence. Stock/generative imagery must never masquerade as an actual business location. For user-supplied photos preserve provenance, crop sensibly, avoid deceptive retouching and keep asset original intact. Content honesty and functional integrity outrank originality. When no image is available, communicate honestly; do not create false photography.

## 06. Award inspiration boundary
Award-winning websites can spark rhythm, visual experimentation and expressive typography. They do not authorize copying artwork, logos, layouts verbatim, media, source code or proprietary content. They do not prove WCAG compliance, business conversion or runtime performance. Prefer independently created licensed assets. Confirm commercial usage/licensing separately.

