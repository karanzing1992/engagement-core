# Headless Reel Engine

Programmatic short-form video renderer for Goa Wellness / Goa Reset and later brand adapters.

## Backend

The Docker image installs the upstream MIT-licensed **ffmpeg-mcp-video-editor** pinned to:

`c65cd584c5ee1a54d2069ef8c523524216d5fb31`

It also exposes a small HTTP orchestration layer for deterministic Reel renders. No editor UI is required.

## API

`POST /v1/render`

Multipart fields:

- `video`: source media
- `config_json`: JSON timeline/config

The response returns a job ID and a download route.

## Design rules

- Brand-specific behavior lives in `configs/`.
- Rendering stays brand-agnostic.
- CTA hold and audio/video fade are enforced by configuration.
- Source overlays can be handled per segment using `crop_top`.
- Render output is H.264/AAC MP4 with faststart.
- Upstream FFmpeg-MCP remains available in the image for richer MCP-driven operations such as scene detection, face tracking, captions, contact sheets and inspection.

## Local run

```bash
docker build -t engagement-reel-engine .
docker run --rm -p 8080:8080 -v $PWD/data:/data engagement-reel-engine
```

Then call `POST http://localhost:8080/v1/render`.

## Next layer

The selector/orchestrator can use vidIQ/outlier research and visual scene scoring to generate the segment timeline before calling this renderer. Publishing remains a separate adapter.
