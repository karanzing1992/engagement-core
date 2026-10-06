from __future__ import annotations

import json
import os
import shutil
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from music_library import ingest_track, list_tracks, rank_tracks, select_track
from renderer import render_reel
from media_handoff import publish_media, delete_media

ROOT = Path(os.environ.get("REEL_DATA_ROOT", "/data"))
UPLOADS = ROOT / "uploads"
JOBS = ROOT / "jobs"
OUTPUTS = ROOT / "outputs"
MUSIC = ROOT / "music"
for p in (UPLOADS, JOBS, OUTPUTS, MUSIC):
    p.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Reel Engine", version="0.4.0")


@app.get("/health")
def health() -> dict:
    return {
        "ok": True,
        "engine": "ffmpeg-mcp-compatible",
        "headless": True,
        "features": [
            "srt",
            "music-input",
            "music-library",
            "auto-music-ranking",
            "beat-sync",
            "ambient-mix",
            "public-media-handoff",
        ],
        "music_tracks": len(list_tracks(MUSIC)),
    }


def _save_upload(upload: UploadFile | None, path: Path) -> Path | None:
    if upload is None:
        return None
    with path.open("wb") as fh:
        shutil.copyfileobj(upload.file, fh)
    return path


def _public_track(track: dict | None) -> dict | None:
    if not track:
        return None
    hidden = {"path"}
    return {k: v for k, v in track.items() if k not in hidden}


@app.post("/v1/music")
def add_music(
    track: UploadFile = File(...),
    metadata_json: str = Form(...),
):
    try:
        metadata = json.loads(metadata_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid metadata_json: {exc}") from exc

    suffix = Path(track.filename or "track.mp3").suffix or ".mp3"
    incoming = UPLOADS / f"music-{uuid.uuid4().hex}{suffix}"
    _save_upload(track, incoming)

    try:
        result = ingest_track(incoming, MUSIC, metadata)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        incoming.unlink(missing_ok=True)

    return {"track": _public_track(result)}


@app.get("/v1/music")
def get_music(
    platform: str = Query("instagram"),
):
    return {"tracks": [_public_track(x) for x in list_tracks(MUSIC, platform=platform)]}


@app.get("/v1/music/rank")
def get_music_ranking(
    moods: str = Query(""),
    target_bpm: float | None = Query(None),
    bpm_min: float | None = Query(None),
    bpm_max: float | None = Query(None),
    platform: str = Query("instagram"),
    limit: int = Query(5, ge=1, le=25),
):
    mood_list = [x.strip().lower() for x in moods.split(",") if x.strip()]
    ranked = rank_tracks(
        MUSIC,
        moods=mood_list,
        target_bpm=target_bpm,
        bpm_min=bpm_min,
        bpm_max=bpm_max,
        platform=platform,
        limit=limit,
    )
    return {"tracks": [_public_track(x) for x in ranked]}


@app.post("/v1/render")
def render(
    video: UploadFile = File(...),
    config_json: str = Form(...),
    music: UploadFile | None = File(None),
    subtitles: UploadFile | None = File(None),
):
    try:
        cfg = json.loads(config_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid config_json: {exc}") from exc

    job_id = uuid.uuid4().hex
    job_dir = JOBS / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    input_suffix = Path(video.filename or "input.mp4").suffix or ".mp4"
    input_path = _save_upload(video, UPLOADS / f"{job_id}{input_suffix}")
    assert input_path is not None

    selected_music = None
    music_path = None
    if music:
        music_suffix = Path(music.filename or "music.mp3").suffix or ".mp3"
        music_path = _save_upload(music, UPLOADS / f"{job_id}-music{music_suffix}")
        selected_music = {
            "source": "upload",
            "title": music.filename or "uploaded music",
        }
    else:
        library_cfg = cfg.get("audio", {}).get("music_library", {})
        if library_cfg.get("auto_select", False):
            selected_music = select_track(MUSIC, library_cfg)
            if selected_music:
                music_path = Path(str(selected_music["path"]))
                selected_music = {**selected_music, "source": "library"}
            elif library_cfg.get("required", False):
                raise HTTPException(
                    status_code=422,
                    detail="No commercially-cleared music track matched the requested selector",
                )

    srt_path = None
    if subtitles:
        srt_path = _save_upload(subtitles, UPLOADS / f"{job_id}.srt")

    output_path = OUTPUTS / f"{job_id}.mp4"

    try:
        result = render_reel(
            input_path,
            output_path,
            cfg,
            job_dir,
            music_path=music_path,
            srt_path=srt_path,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    result["selected_music"] = _public_track(selected_music)
    (job_dir / "result.json").write_text(json.dumps(result, indent=2))
    return {
        "job_id": job_id,
        "duration": result["duration"],
        "bpm": (result.get("music_sync") or {}).get("bpm"),
        "segment_durations": result.get("segment_durations"),
        "selected_music": result.get("selected_music"),
        "download_path": f"/v1/jobs/{job_id}/video",
        "srt_path": f"/v1/jobs/{job_id}/srt",
    }


@app.get("/v1/jobs/{job_id}")
def job_result(job_id: str):
    path = JOBS / job_id / "result.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Job not found")
    return json.loads(path.read_text())


@app.get("/v1/jobs/{job_id}/video")
def job_video(job_id: str):
    path = OUTPUTS / f"{job_id}.mp4"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Render not found")
    return FileResponse(path, media_type="video/mp4", filename=f"{job_id}.mp4")


@app.get("/v1/jobs/{job_id}/srt")
def job_srt(job_id: str):
    path = OUTPUTS / f"{job_id}.srt"
    if not path.exists():
        raise HTTPException(status_code=404, detail="SRT not found")
    return FileResponse(path, media_type="application/x-subrip", filename=f"{job_id}.srt")


@app.post("/v1/jobs/{job_id}/publish-media")
def publish_job_media(job_id: str, brand: str = Query("default")):
    path = OUTPUTS / f"{job_id}.mp4"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Render not found")
    try:
        media = publish_media(str(path), brand=brand)
    except KeyError as exc:
        raise HTTPException(status_code=503, detail=f"Media storage is not configured: {exc.args[0]}") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Media upload failed: {exc}") from exc
    record = JOBS / job_id / "published-media.json"
    record.write_text(json.dumps(media, indent=2))
    return media


@app.delete("/v1/jobs/{job_id}/publish-media")
def delete_job_media(job_id: str):
    record = JOBS / job_id / "published-media.json"
    if not record.exists():
        raise HTTPException(status_code=404, detail="Published media record not found")
    media = json.loads(record.read_text())
    try:
        delete_media(media["key"])
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Media cleanup failed: {exc}") from exc
    record.unlink(missing_ok=True)
    return {"deleted": True, "key": media["key"]}
