# CRM G1 — Art Direction & Mobile Quality Review

**Review type:** Preliminary authored visual inspection + automated Chrome evidence.  
**Status:** `NEEDS_INDEPENDENT_ART_REVIEW / OWNER_VISUAL_ACCEPTANCE_PENDING`.  
**Not an independent third-party artistic certification. Not a functional CRM release.**

## Evidence

Actual Dell Chrome/Playwright screenshots captured from the isolated G1 prototype at **390px** on all 15 routes plus representative **360 / 768 / 1440** screenshots. Source: [CRM G1 wireframe branch](https://github.com/karanzing1992/engagement-core/pull/76). Machine-readable 253/253 browser checks have zero reported horizontal overflow or JavaScript errors. The screenshot files are stored in the isolated Dell QA artifact directory, not in production WordPress or the open-source app.

## Observed mobile visual strengths

- Strong hierarchy from module title to content; recognizable communication, customer and deal routes.
- Consistent calm blue/white palette and reusable input/card patterns, referencing the approved Tabler visual direction.
- Five persistent mobile navigation destinations and an explicit back route; drawer and Escape workflow tested.
- Synthetic-data disclosure visibly distinguishes the design preview from a working, provider-connected CRM.
- Conversation demo separates outgoing reply, internal note and customer context. Mobile pipeline has explicit stage/action alternatives to dragging.

## Findings and actions

| Severity | Finding | Status / follow-up |
|---|---|---|
| P1 | Chip controls were below preferred 44px touch size and some muted labels were pale | **Adjusted** minimum chip target to 44px and darker muted/nav colors; browser QA rerun 253/253 |
| P1 | Synthetic-demo disclosure plus preview-state selector consumes substantial first-fold space on phones | Acceptable in design QA environment; **remove review-only chrome** in any actual CRM implementation |
| P1 | Full WCAG 2.2 AA contrast, assistive-technology and keyboard-path audit is not covered by the 253 responsive browser assertions | **Open**: dedicated accessibility reviewer and evidence required |
| P1 | Real conversations, provider errors, draft persistence and CRM transactional writes are unimplemented; static sample is deliberately synthetic | **Open by design**: separate G2+ functional approval and backend/API testing |
| P1 | 1024px desktop hides the customer-context column to prioritize readability; true three-pane chat emerges on larger desktop widths | **Review with owner** against final desktop acceptance |
| P1 | No verified separate CRM image-capable Art Director has assessed the screenshots | **Open**: require independent visual/UX human review or model-assisted critique reported as advisory, never as acceptance |
| P2 | Portrait and screen-width tests exist; landscape orientation, software-keyboard resize and screen-zoom robustness have not been independently certified | Add to full product QA; do not claim complete mobile accessibility |

## Dev Tool Yard continuous-work / art-director audit (26 Oct 2026)

Existing **Manager Governance V3** continuously observes controller tasks, records state-change events and warns on stalled queue items. It **does not run repeated creative iterations**. Reuse this manager for read-only CRM status and task evidence; do not create a duplicate manager.

The existing `bhm-shaadi-ai-art-director.timer` is **Shaadi-specific** (30-minute one-shot, art source and visual reference pinned to Shaadi). Its state has evolved during this task: at an earlier check it said `waiting_for_local_vision_model`, and on later live readback it reported `candidate_needs_visual_review` with **2 cycles**, `quality_pass=false` and `owner_approved=false`. These state changes **do not** grant CRM authority and do not prove CRM visual review.

A future CRM-specific design reviewer must use a narrowly scoped, separate synthetic dataset and evidence folder, reference the exact `crm_wireframe_g1_v1` quality contract and the G1 source commit, issue defect receipts, and stop at owner review. Do not imply unattended creative production or AI art-direction success without terminal worker receipts.

## Gate result

**Engineering browser QA:** PASS (253/253 after targeted mobile legibility refinements).  
**Structural wireframe presence:** PRESENT for all 15.  
**Independent art/UX approval:** PENDING.  
**Owner design acceptance:** PENDING.  
**Controller-reviewed patch worker:** project enrolled; unsigned exact-contract intake fails closed.  
**WordPress CRM functional implementation / production:** NO-GO.
