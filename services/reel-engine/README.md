# Headless Reel Engine

Programmatic short-form video renderer for Goa Wellness / Goa Reset and later brand adapters.

## Backend

The image installs the upstream MIT-licensed **ffmpeg-mcp-video-editor**, pinned to:

`c65cd584c5ee1a54d2069ef8c523524216d5fb31`

The service is headless. It exposes HTTP endpoints for Reel rendering, SRT generation,
licensed music ingestion/ranking, beat analysis and music-synced cuts.

## Render API

`POST /v1/render` as multipart form data:

- `video` — source video
- `config_json` — timeline + brand settings
- `music` — optional explicit music track
- `subtitles` — optional supplied SRT

If no `music` file is supplied and `audio.music_library.auto_select=true`, the
engine selects a commercially-cleared track from `/data/music` using mood, BPM,
platform and audio features, then uses that track for beat synchronization.

The response includes the selected music metadata, detected BPM, snapped shot
durations, MP4 route and SRT route.

## Music library

`POST /v1/music` accepts:

- `track` — audio file
- `metadata_json` — rights + descriptive metadata

Minimum metadata:

```json
{
  "title": "Example Track",
  "artist": "Artist",
  "license": "royalty-free-commercial",
  "commercial_use": true,
  "platforms": ["instagram", "youtube", "facebook"],
  "tags": ["serene", "organic", "premium", "wellness"],
  "license_source": "invoice/license URL or internal record"
}
```

Accepted automatic-selection licenses are deliberately restricted to:
`owned`, `original`, `cc0`, `public-domain`,
`royalty-free-commercial`, and `licensed-commercial`.

Optional `license_expires` is enforced. Expired tracks are excluded.

Other music endpoints:

- `GET /v1/music?platform=instagram` — list usable tracks
- `GET /v1/music/rank?moods=serene,organic&target_bpm=104&platform=instagram`
- `GET /v1/jobs/{job_id}` — render metadata including music choice
- `GET /v1/jobs/{job_id}/video`
- `GET /v1/jobs/{job_id}/srt`

## Goa Wellness defaults

The Goa Wellness preset requests:

- moods: serene, organic, premium, wellness, cinematic
- target BPM: 104
- allowed BPM range: 82–116
- Instagram clearance
- 4 beats per visual cut
- 1.2–3.0 second normal shot window
- 2.8 second minimum CTA hold
- ambient source sound underneath selected music
- 1.8 second music fade
- SRT sidecar output

## Local run

```bash
docker build -t engagement-reel-engine .
docker run --rm -p 8080:8080 -v $PWD/data:/data engagement-reel-engine
```

No editor UI is required.

## Public media handoff

Rendered media can be uploaded to any S3-compatible object store before social publishing. This avoids expiring ChatGPT/Drive URLs and gives Metricool/Meta a direct HTTPS media URL.

Environment variables: `MEDIA_S3_ENDPOINT`, `MEDIA_S3_BUCKET`, `MEDIA_S3_ACCESS_KEY`, `MEDIA_S3_SECRET_KEY`, `MEDIA_PUBLIC_BASE_URL`; optional `MEDIA_S3_REGION` and `MEDIA_TTL_HOURS`.

Flow: render -> `publish_media()` -> direct public URL -> publisher -> verify -> `delete_media()` (or bucket lifecycle expiry).
