# MAD Reel Engine V4 — Groq + FilmCraft MCP public cloud executor

An isolated, reproducible **2-second / 480×270** synthetic-video integration pilot.

- Public test assets only. **No Moksha footage, client media, private host paths, credentials, or tokens** are committed.
- Runs **FilmCraft CLI v0.16.0** in headless **MCP** mode and exports an MP4 on a GitHub-hosted Ubuntu runner.
- The default `fixture` mode replays a small, previously Groq-generated editing plan. It proves the **MCP/FFmpeg/cloud export** path, **not** live Groq inference in GitHub.
- `live` mode (available on default branch `main`) calls Groq GPT-OSS-20B through the official Python SDK. Configure the GitHub Actions secret `GROQ_API_KEY` under **Settings → Secrets and variables → Actions**. No secret is needed for the initial smoke.
- Use **Actions → MAD Reel Engine V4 | Groq FilmCraft Cloud** to run `workflow_dispatch` in `fixture` or `live` mode. Push CI is scoped to this workflow and pilot files on main or its original development branch.
- Output: `mad-filmcraft-pilot` Actions artifact with MP4, FFprobe QA receipt, and sanitized logs.

## Controls

The runner accepts only the fixed 480×270, 24-fps, two-second test profile. LLM output is parsed and allowlisted, not used as shell code. No publishing, WordPress deployment, or external uploads are performed. `permissions: contents: read`. The job has a timeout; failed runs upload diagnostic artifacts. The FilmCraft release archive SHA-256 is pinned.

## Scope and follow-up

This pilot is deliberately separate from MAD production and the existing WP deployment workflows. Both the synthetic fixture export and the authenticated live-Groq synthetic export passed on 02 November 2026; this is Reel Engine V4 technical certification only, not real-media cinematic M3 certification. Use a new isolated media store for real footage; never add originals to this public repository.

See `../../.github/workflows/mad-filmcraft-groq-cloud-pilot.yml` for the execution pipeline.

## Live cloud acceptance test

The live `GROQ_API_KEY` test is initiated by a narrowly scoped commit with `[live-groq]` in its message, or by selecting `live` in manual workflow dispatch. The API key remains an Actions secret; do not put credentials in repository files.

## Reel Engine V4 status (02 Nov 2026)

**Technical PASS:** [live GitHub Actions run #5](https://github.com/karanzing1992/engagement-core/actions/runs/41356306390) with Groq GPT-OSS-20B, MCP 17 tools, successful 2-second 480×270 H.264 export. [Video and receipt artifact](https://github.com/karanzing1992/engagement-core/actions/runs/41356306390/artifacts/13103397200); MP4 SHA-256 `083f88abd96242a8f1dd919aa0a34384fabeff6e1be42fe2243eff19ab1eea32`.

**Not certified:** real-source privacy/rights, 1080×1920 reel, transition/caption/music artistic review, production MAD Manager dispatch, or social publishing. See [MAD Reel Engine V4 canonical repository handover](../../docs/MAD_REEL_ENGINE_V4_LATEST.md). Historical Mac M3 HOLD and the thermal/Firefox policy remain unchanged.
