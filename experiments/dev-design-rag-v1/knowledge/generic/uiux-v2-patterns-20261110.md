# GENERIC UI/UX KNOWLEDGE V2 — REUSABLE PATTERNS AND EXAMPLES
Version: 2.0.0 | Reviewed 2026-11-10 | Layer generic/shared | ACTIVE
Sources: https://www.w3.org/WAI/ARIA/apg/ ; https://www.nngroup.com/articles/ten-usability-heuristics/ ; https://www.w3.org/TR/WCAG22/ ; https://web.dev/explore/learn-core-web-vitals

## P01 Editorial authentic-image hero
Good: one sharp value proposition, one truthfully sourced photo, recognizable brand identity, visible primary action and understated secondary action. Use asymmetric composition only where it survives mobile. Responsive image has width, height, object-fit, responsive sources and concise descriptive alt text. Don't put compulsory animations before the primary action. Reject fake location photos and dramatic artwork that slows LCP.

## P02 Responsive mobile navigation
Good: native button with aria-controls and truthful aria-expanded; no open menu left after Escape; keyboard focus visible and returned to trigger. Touch-friendly spacing; menu must work at 320, 390 and 768 CSS px. Bad: menu visually opens but aria-expanded stays false and Escape does nothing (real regression example, generalized).

## P03 Real-world product/room comparison
Good: consistent comparison dimensions, accurately verified labels, availability and rates or 'confirm with team', link per choice. A single photographed room cannot represent distinct room types unless clearly marked. Use editorial rows or compact table when cards repeat. Bad: fabricated rates and duplicated image posing as multiple physical spaces.

## P04 Booking, enquiry and contact
Good: labels, number of people, date-order validation, clear summary, recovery from errors, real confirmation only after a confirmed server action. For external messaging, accurately label 'Enquire on WhatsApp', never imply reserved, prepaid or guaranteed inventory. Provide no-fake-price fallback. Preserve entered input and show corrective inline error. Keyboard submission and error focus required.

## P05 Directory and filtering
Good: clear query input, actual filtered count, understandable empty state, working reset, consistent data, grounded locations and map links. Never invent businesses, prices, reviews or travel times. Bad: visual search box that does not filter.

## P06 Varied editorial content
Good: mix image narrative, typographic feature, comparison, testimonial only with authentic attribution, concise facts, list, place guide and one conversion CTA. Avoid identical card grid for every section. Use CSS grid minmax(0,1fr), max-width:100% images and tested mobile overflow.

## P07 Feedback states
Loading: visible progress or reserved skeleton without layout jumps. Empty state: meaningful explanation and recovery. Error: say what did/didn't happen, support retry and do not claim success. New data state must reflect verified confirmation, not optimistic promise where consequence is irreversible.

## P08 Controlled motion and optional 3D
Motion should clarify relationship or affordance, not become navigation obstacle. Prefer transform/opacity where smooth. Respect prefers-reduced-motion; no autoplay unmuted video or scroll hijack. Test immersive work with accessible static fallback and real low-bandwidth devices.

## P09 Design-system semantics
Use versioned, semantic design tokens, documented component variants, consistent keyboard and interaction behavior. Keep brand palettes out of generic knowledge. Component visual variants cannot silently mutate component interaction contracts. Reuse stable open-source patterns with verified licenses where possible.

## P10 Concrete QA examples
Mobile test at 390px: nav button opens, toggles aria-expanded to true, Escape closes; all menu links target existing pages. Main image constrained to viewport, no scrollWidth overflow; primary CTA enters actual service or accurately labeled external messaging. Axe reports zero critical/serious; test 320/390/768/1440; no deceptive content. Repeat live tests on same build hash after deployment.

