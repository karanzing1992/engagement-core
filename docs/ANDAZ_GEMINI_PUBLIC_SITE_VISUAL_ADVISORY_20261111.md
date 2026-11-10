# Andaz Vibe Stay — public-site Gemini visual advisory (5 routes × 2 viewports)
Date: 2026-11-11 IST
Source: `karanzing1992/engagement-core`, GitHub Actions run #42902936148
Workflow: `.github/workflows/andaz-gemini-five-routes-trusted-20261111.yml`
Model: authenticated `gemini-3.5-flash-lite` using the existing Reel Engine GitHub Actions `GEMINI_API_KEY`
Evidence: [successful Actions run](https://github.com/karanzing1992/engagement-core/actions/runs/42902936148)
Artifact: `andaz-trusted-public-route-vision-42902936148`, ID `13803313149`, archive SHA-256 `6d8146970822272db95e1e050745d534f70c8394e1e408756b28a1d32b0e1e95`; decoded `receipt.json` SHA-256 `da8610746d1e133eb614107cdda9684ab0063d968ee191c1f8ec48ffaf7f45a5`. Short-lived raw artifact (1-day retention) contains only public-page review JSON and hashes; no screenshot bytes or API key.

## Verified transport and scope
- Owner-only GitHub PR job finished **SUCCESS**, secret scoped to inference step, contents-read permission, same-repo owner checks, no merge or production writes.
- Five publicly accessible routes `/`, `/rooms`, `/experiences`, `/explore`, `/contact`; above-the-fold viewport capture at 390 × 844 (mobile) and 1440 × 900 (desktop): **10 genuine one-image Gemini responses** and 10 distinct screenshot hashes; all provider finish reasons `STOP`.
- First inference encountered HTTP 503 once, recovered on bounded retry. Remaining separate requests succeeded. No provider availability guarantees.
- Dell isolated technical route `engine-smoke.html` is NOT on the public site (HTTP 404). These public screenshot hashes are NOT the hashes of the previously verified Dell-local 12-image fixture.
- `artistic_score=null`; `independently_attested=false`; `artistic_95_certified=false`; `release_authorized=false`. Do not substitute this advisory for an independent trusted artistic certificate, full-page review or production gate.

## Model-generated, non-certified design suggestions
Treat all points as hypotheses to verify against source design and screenshots, not as objective design measurements or automatic editing instructions.

| Route | Mobile critique | Desktop critique |
|---|---|---|
| Home | Two competing booking/exploration CTAs; wrapped feature bullets; weak contrast on italic subheadline | Muted/low-contrast supporting copy; fragmented CTAs; illustration tags need clearer label contrast |
| Rooms | Room-illustration disclaimer may weaken trust or need better proximity to room visuals; dense text; unclear section break | Supporting-copy contrast; competing availability/booking CTAs; empty right-side hero lacks authentic visual anchor |
| Experiences | Low-contrast eyebrow labels; ragged body text; no prominent hero CTA | Light supporting copy; crowded header navigation; weak overline contrast |
| Explore | Awkward headline wrapping; competing map/place actions; tight paragraph spacing | Muted body-copy contrast; competing CTAs; unbalanced empty right-side hero |
| Contact | WhatsApp/phone action not button-like enough; low-contrast overlines; dense instructions | Subheadline contrast; booking-header visual hierarchy; weak separation between inquiry sections |

## Ranked next design actions for Generic Design RAG V2
1. Check actual WCAG contrast ratios rather than accepting model claims of accessibility problems unmeasured.
2. Consolidate one principal conversion CTA per route while preserving alternate actions as secondary links; verify booking contact path.
3. Improve mobile typography/spacing where screenshot-grounded, then run 320/390/768/1440 browser assertions on the isolated new build.
4. Replace conceptual illustrations with **actual approved Andaz room photographs** only where supported by real property inventory. Never fabricate room photos, invent amenities or change real pricing.
5. Preserve the exact user-supplied **official Andaz gold logo geometry**; do not generate approximate wordmarks.
6. Repeat actual screenshot review on the changed isolated build, compare hashes, and obtain separate calibrated ≥95 signed independent certification before any preview release.

## Intake and custody
This is **PUBLIC_SITE_ADVISORY_ONLY**. It may be copied to a separate Dell review evidence folder as *non-authoritative design feedback*, not into the generic foundation rules or trusted signed-review register. Do not call it a judgment of the isolated Dell fixture. Existing GitHub Actions key is **never copied** to Dell. Production and customer data remain untouched.
