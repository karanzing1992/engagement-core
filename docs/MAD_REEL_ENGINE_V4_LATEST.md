# MAD Reel Engine V4 — Cloud Execution Architecture and Certified Pilot

**Baseline:** 02 November 2026 (Asia/Kolkata)  
**Technical status:** **CERTIFIED — live-Groq 480×270 synthetic export**  
**Production creative status:** **NOT CERTIFIED — real-footage / full cinematic reel / Moksha M3 remain HOLD**

## Control and execution topology

ChatGPT and the existing MAD Manager retain strategy, rights, approvals and campaign policy. GitHub Actions is a separate *ephemeral render lane*, not a competing Manager service, generic terminal or production WordPress environment.

Flow: **owner-approved plan → GitHub Actions ubuntu-24.04 → Groq Python SDK 0.37.1 / GPT-OSS-20B live JSON → allowlisted edit profile → FilmCraft CLI 0.16.0 (MCP JSON-RPC over subprocess stdio) → clip import/sequence/timeline/export → FFprobe + FFmpeg full decode → artifact with H.264 MP4, receipt and logs**.

There is no native permanent bridge yet between the live MAD Manager and GitHub Actions dispatch, cancellation or artifact collection. ChatGPT can inspect source, workflows, runs and receipts with the connected GitHub app. To initiate from ChatGPT automatically, implement an authorized minimal dispatch/status/artifact connector (GitHub Actions API / existing manager), never a second queue or auth bypass.

## Primary endpoints

- Workflow: https://github.com/karanzing1992/engagement-core/actions/workflows/mad-filmcraft-groq-cloud-pilot.yml
- Runner: [experiments/filmcraft-groq-actions/runner.py](../experiments/filmcraft-groq-actions/runner.py)
- Test plan: [experiments/filmcraft-groq-actions/plan.json](../experiments/filmcraft-groq-actions/plan.json)
- Pilot readme: [experiments/filmcraft-groq-actions/README.md](../experiments/filmcraft-groq-actions/README.md)
- GitHub PR #93: https://github.com/karanzing1992/engagement-core/pull/93 — merged to main.
- Google Docs V4 canonical spec: https://docs.google.com/document/d/1nz3fykPPnN4w3-Qb8TheuansiYNJyxSnbTF4UOVMLDU/edit
- Master Registry event: `[MASTER-STACK-EVENT:MAD-REEL-ENGINE-V4-20261102]`

## Proven certification

| Gate | Evidence |
| --- | --- |
| Initial hosted 480×270 fixture MP4 | [GitHub Actions run #2](https://github.com/karanzing1992/engagement-core/actions/runs/41355657957) — PASS |
| Authenticated GPT-OSS-20B in cloud | [GitHub Actions run #5](https://github.com/karanzing1992/engagement-core/actions/runs/41356306390) — `RUN_MODE: live`, PASS |
| FilmCraft MCP tool protocol | 17 MCP tools enumerated; creation, import, inspect, timeline placement, save and export PASS |
| Technical MP4 output | 2-second synthetic 480×270 H.264; FFprobe duration/codec/dimensions; FFmpeg full decode PASS |
| Evidence artifact | [Video + receipt](https://github.com/karanzing1992/engagement-core/actions/runs/41356306390/artifacts/13103397200), ID `13103397200` |
| Export SHA-256 | `083f88abd96242a8f1dd919aa0a34384fabeff6e1be42fe2243eff19ab1eea32` |

FilmCraft release `v0.16.0` archive SHA-256 is pinned to `588390eee5d7e1634f05794c4f877ddf29494d9cf74405111d67c16cbe215ae9`. Groq official SDK pinned to `0.37.1`. FFmpeg installed explicitly in runner. Workflow uses `permissions: contents: read`, job timeout 12 minutes, 7-day artifact retention, and per-ref concurrency limits.

## Safety and acceptance boundary

**Public repo/artifacts:** synthetic media only. Do not commit, upload or publish Moksha guest imagery, licensed assets or customer records through this public path. `GROQ_API_KEY` is an Actions secret; never expose or rotate credentials through chat/logs. Groq SDK resolved the old Mac `urllib` Cloudflare 403. Free public-runner use still requires quota/cost oversight.

Moksha M2 private campaign packet remains previously verified. Moksha M3 artistic/technical/factual/guest/media-rights and V4.2 mobile browser QA remain independent incomplete gates, and Moksha M4 publication and M5 feedback automation remain owner gated. The Mac thermal protections, Firefox sessions and Mac-only secure-tunnel guard are not to be weakened. The cloud executor is separately authorized and does not attest that the original private Fire & Ice M3 MP4 exists.

## Phased next gates

1. V4.1: narrow authorized GitHub Actions dispatch/status/cancel/artifact tool for existing MAD Manager, with run IDs, idempotency and queue/budget controls.
2. V4.2: private rights-cleared footage intake, storage, provenance and consent metadata; no public artifact leakage.
3. V4.3: 1080×1920 multi-scene 15–30s reel, captions, transitions, soundtrack, mobile framing and audiovisual QA.
4. V4.4: independent technical, art direction, rights/consent and factual verification; owner final review.
5. V4.5: repeated controlled reliability, quota accounting and recovery; only owner-approved M4 publish integration.

**Rollback:** Disable only `.github/workflows/mad-filmcraft-groq-cloud-pilot.yml` or revert its scoped pilot commits; preserve other workflow deployments, GitHub secrets, Mac services, M2/M3 documentation and original media.


## Version supersession — 2 November 2026

**The latest usable creative private-preview version is now V4.1:** [open V4.1](MAD_REEL_ENGINE_V4_1_LATEST.md). This V4 document remains the historical synthetic Groq + FilmCraft MCP cloud-certification baseline. The three real Arambol footage previews (A/B/C) were Groq GPT-OSS 20B planned, but **FFmpeg-rendered locally**, not FilmCraft GitHub cloud rendered. V4.1 is technical-preview usable, not publication rights cleared.
