# Reel/Shorts production — versioned evidence and operational notes

**Skill version:** 1.0.0, source authored 11 Oct 2026, project Moksha Social Media. **Status taxonomy:** documented Skill source / tested engine / confirmed scheduled / confirmed published / blocked.

## Source-backed architecture

| Component | Verified evidence | Status (11 Oct 2026) |
| --- | --- | --- |
| Core private Reel Engine v0.5, secure large uploads and multi-clip queue | [Merged PR #39](https://github.com/karanzing1992/engagement-core/pull/39); [release run 38122299053](https://github.com/karanzing1992/engagement-core/actions/runs/38122299053); [operator README](https://github.com/karanzing1992/engagement-core/blob/main/services/reel-engine/README.resumable.md) | CI-tested and GHCR-released; long-running worker host **not confirmed deployed** |
| WordPress private resumable upload and ephemeral authenticated worker | [Private WordPress ingest source](https://github.com/karanzing1992/engagement-core/blob/main/src/class-grec-media-ingest.php); [worker source](https://github.com/karanzing1992/engagement-core/blob/main/services/reel-engine/render_ready_sessions.py); [worker workflow](https://github.com/karanzing1992/engagement-core/blob/main/.github/workflows/media-ingest-worker.yml) | Source committed; prior successful empty-queue worker run **does not** prove a new clip completed in WordPress |
| Direct attachment-first production procedure | [Documented runbook](https://github.com/karanzing1992/engagement-core/blob/main/docs/reel-engine-assistant-operating-procedure.md) | Source committed; actual 30-second Reel rendered locally within 11 Oct ChatGPT session |
| Authentic brand mark | [Source verification implementation](https://github.com/karanzing1992/engagement-core/blob/main/services/reel-engine/verified_logo.py) | Approved Moksha original validated by SHA-256; NEVER AI-substitute |
| Regional footage gate | [Provenance gate](https://github.com/karanzing1992/engagement-core/blob/main/services/reel-engine/geo_policy.py) | Human evidence required. Some user-uploaded 11 Oct coastal footage had **not** been independently geolocated/licensed on source receipt |
| Actual production and distribution workflow | Verified within 11 Oct 2026 user session: 30s “Breathe With the Tide”, two output profiles and cover; Metricool account `moksha.goa`, 11 authenticated scheduling records | 11 scheduled Metricool destinations were **PENDING at readback**, not confirmed published; English-only campaign; Russian destinations excluded |
| Snapchat publishing | [Snapchat publisher source](https://github.com/karanzing1992/engagement-core/blob/main/src/class-grec-snap-public-api.php) | Snapchat profile/OAuth read verified; Spotlight attempt returned HTTP 403; **not published** |

## Incident lessons encoded as required QA

1. **Connector egress restriction:** file references rejected with `BLOCKED_FILE_REFERENCE` at Canva, Descript, or Drive. Correct resolution was direct access to mounted video file bytes; do not claim engine codec failure.
2. **Large-file transfer:** a 231 MB source could be mounted locally; alternative private 8 MiB resumable ingest was assembled and SHA-checked. No manual splitting if native access works.
3. **Embedded audio contamination:** user flagged unwanted narration/music even after “nature only.” Never carry audio from composite input; construct the final from silent video plus separate approved nature sound.
4. **10.6-second cutoff defect:** user flagged a 10 s dropout; audio stream was 10.6 s inside a 30 s video. Verify audio track duration and 30 s audible timeline independently before delivery.
5. **Readable caption/brand overlay:** user flagged text location and repeated “Moksha.” Corrected scene typography uses central safe margins, stronger contrast and one final official logo, with source text checked around clip transitions.
6. **Geo/licensing:** subject matter such as coastline alone does not prove Goa geography. Before public publishing, require verified original capture location and rights; human-review gate cannot be inferred from “looks local.”
7. **Cross-platform planning:** verify brand and destinations individually, including Pinterest board. Pinterest tool rejected an unverified textual board name and accepted a verified numeric ID. Published vs scheduled is not interchangeable. English-only campaigns must not route through Russian groups.

## QA acceptance for each finished 30-second video

| Gate | Release condition |
| --- | --- |
| Provenance | Every visual and soundtrack has known source, license/right-to-use and geographic claims supported |
| Visual | 1080×1920 9:16; source pixels normalized; no unwanted embedded or cropped text |
| Captions | Safe margins, contrasting backgrounds, mobile-readable without duplicate text or persistent brand watermark |
| Authentic brand | Approved exact logo SHA-256; placement on closing segment |
| Audio | Newly assembled ambience where required; complete 30 s, no music/speech if nature-only; no dropout at edits/loops |
| Export | H.264/AAC playable master; H.264/AAC smaller optional share copy; ffprobe confirms independent audio/video duration |
| Distribution | Only authorized languages/destinations; owner confirms rights/geography; each network returns accepted job or verifiable live URL |
| Reporting | Exact scheduled date/time, job identity, PENDING/POSTED/FAILED; unverified channel not called success |

## Reuse / rollback

- Instructions are neutral to editing platform; source video may be owned, licensed Commons/Canva/other stock with license and location evidence. Brand-specific official logos and account credentials always remain isolated.
- If the Skill causes confusion, disable/remove the Skill installation or revert the tagged GitHub source commit. It has **no automatic deployment or account mutation**.
- Keep existing first-party WordPress/Engagement Core systems, avoid extra GitHub Actions spend, and do not create a second Stack Registry sync worker.
