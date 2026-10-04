from __future__ import annotations

import json
import os
import shutil
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from renderer import render_reel

ROOT = Path(os.environ.get("REEL_DATA_ROOT", "/data"))
UPLOADS = ROOT / "uploads"
JOBS = ROOT / "jobs"
OUTPUTS = ROOT / "outputs"
for p in (UPLOADS, JOBS, OUTPUTS):
    p.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Reel Engine", version="0.2.0")


@app.get("/health")
def health() -> dict:
    return {
        "ok": True,
        "engine": "ffmpeg-mcp-compatible",
        "headless": True,
        "features": ["srt", "music-input", "beat-sync", "ambient-mix"],
    }


def _save_upload(upload: UploadFile | None, path: Path) -> Path | None:
    if upload is None:
        return None
    with path.open("wb") as fh:
        shutil.copyfileobj(upload.file, fh)
    return path


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

    music_path = None
    if music:
        music_suffix = Path(music.filename or "music.mp3").suffix or ".mp3"
        music_path = _save_upload(music, UPLOADS / f"{job_id}-music{music_suffix}")

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

    (job_dir / "result.json").write_text(json.dumps(result, indent=2))
    return {
        "job_id": job_id,
        "duration": result["duration"],
        "bpm": (result.get("music_sync") or {}).get("bpm"),
        "segment_durations": result.get("segment_durations"),
        "download_path": f"/v1/jobs/{job_id}/video",
        "srt_path": f"/v1/jobs/{job_id}/srt",
    }


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
