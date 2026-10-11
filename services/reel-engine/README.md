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


## Canonical Moksha logo (automatic, fail-closed)

Set `"brand": "moksha"` in a Reel Engine `config_json` request. After the base video is rendered, the engine automatically calls `verified_logo.overlay_verified_logo`, preserves the existing audio track, and applies the **original official logo only after the hook**, on a brief closing segment (or an unobtrusive safe-area card for Story).

This asset was sourced from the explicit Google Drive master `Moksha_Logo_Source_01.jpeg` (file ID `1XwmlYRfjfkcnbEOlJLNJc8bGHm9uxkyv`). Exact SHA-256: `76e89b83667827da4b5d89143fb267f4000a9392eff685129c838c3d0b24748c`. `assets/brand/moksha-logo-source.jpg` in the repository is a **byte-for-byte mirror**, not a new logo.

For signed WordPress identity lookup, provision `MRS_BRAND_ASSET_TOKEN` as a scoped worker secret. This is derived from our existing WP Control HMAC context `mrs-brand-assets-v1`. When that token is unavailable or WordPress is temporarily unreachable, the helper uses the **immutable commit-pinned GitHub copy of the approved Drive master**, and still validates the exact SHA-256 checksum. If both sources are unavailable or modified, it blocks export; it does not generate, approximate, redraw, recolor or substitute a logo. The logo's original black background is preserved.

Render provenance appears under `result.official_logo`. The system does not publish or schedule social content. Do not use this mode for a technical test that intentionally omits branding; omit `brand=moksha` on synthetic fixtures.

For existing pre-rendered drafts, a cloud worker can explicitly run:

```sh
python services/reel-engine/verified_logo.py \
  --input path/to/unbranded-draft.mp4 \
  --output path/to/officially-branded-private-preview.mp4 \
  --brand moksha --placement reel
```

`python -m unittest -q test_verified_logo.py` checks the original bytes, cache tampering, valid/invalid source lookup, offline fallback and an actual FFmpeg overlay. The `ops/brand-assets/registry.json` policy controls the approval requirements for future brands and variants.
