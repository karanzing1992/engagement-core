# Native Mobile Application Design — Type Graph

Official references: https://developer.android.com/design/ui/mobile/guides/foundations/accessibility ; https://developer.apple.com/design/human-interface-guidelines/ ; https://developer.apple.com/design/tips/

## Platform-specific layout
Respect Android dp versus iOS points and the device's density, safe areas, font scaling, status bar, dynamic system theme and navigation gestures. Do not simply scale a desktop website. Include offline, network error, permission, disabled, system back, and recovery states.

## Input and accessibility
Android guidance recommends touch targets >=48dp; Apple design tips recommend hit targets >=44pt. These are platform guidance, distinct from WCAG 2.2 web target size criteria. Support native screen readers, text enlargement, keyboard/accessibility services, focus traversal and proper labels. Do not hide primary actions under platform navigation affordances.

## Mobile artistic design
Use authentic content, platform-consistent iconography, semantically mapped contrast tokens, stable component rhythm, meaningful motion respecting reduced-motion preferences and performant loading.

## Acceptance
Test actual supported device/resolution combinations, screenshot readiness, focus and screen reader, touchscreen and system back, non-publishing safety, independent artistic >=95 and final owner approval.