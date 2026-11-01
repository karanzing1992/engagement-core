# MAD FilmCraft + Groq — public GitHub Actions pilot

An isolated, reproducible **2-second / 480×270** synthetic-video integration pilot.

- Public test assets only. **No Moksha footage, client media, private host paths, credentials, or tokens** are committed.
- Runs **FilmCraft CLI v0.16.0** in headless **MCP** mode and exports an MP4 on a GitHub-hosted Ubuntu runner.
- The default `fixture` mode replays a small, previously Groq-generated editing plan. It proves the **MCP/FFmpeg/cloud export** path, **not** live Groq inference in GitHub.
- Optional `live` mode (only after workflow is on the default branch) calls Groq GPT-OSS-20B through the official Python SDK. Configure the GitHub Actions secret `GROQ_API_KEY` under **Settings → Secrets and variables → Actions**. No secret is needed for the initial smoke.
- Use **Actions → MAD FilmCraft Groq Cloud Pilot** to run `workflow_dispatch` once this workflow is on the default branch. Automatic `push` test is restricted to this pilot branch and these pilot files.
- Output: `mad-filmcraft-pilot` Actions artifact with MP4, FFprobe QA receipt, and sanitized logs.

## Controls

The runner accepts only the fixed 480×270, 24-fps, two-second test profile. LLM output is parsed and allowlisted, not used as shell code. No publishing, WordPress deployment, or external uploads are performed. `permissions: contents: read`. The job has a timeout; failed runs upload diagnostic artifacts. The FilmCraft release archive SHA-256 is pinned.

## Scope and follow-up

This pilot is deliberately separate from MAD production and the existing WP deployment workflows. Promote only after the synthetic export and live-Groq (secret-gated) run both pass. Use a new isolated media store for real footage; never add originals to this public repository.

See `../../.github/workflows/mad-filmcraft-groq-cloud-pilot.yml` for the execution pipeline.
