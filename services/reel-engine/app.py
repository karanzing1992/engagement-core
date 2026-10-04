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

app = FastAPI(title="Reel Engine", version="0.1.0")


@app.get("/health")
def health() -> dict:
    return {"ok": True, "engine": "ffmpeg-mcp-compatible", "headless": True}


@app.post("/v1/render")
def render(
    video: UploadFile = File(...),
    config_json: str = Form(...),
):
    try:
        cfg = json.loads(config_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid config_json: {exc}") from exc

    job_id = uuid.uuid4().hex
    suffix = Path(video.filename or "input.mp4").suffix or ".mp4"
    input_path = UPLOADS / f"{job_id}{suffix}"
    output_path = OUTPUTS / f"{job_id}.mp4"
    job_dir = JOBS / job_id

    with input_path.open("wb") as fh:
        shutil.copyfileobj(video.file, fh)

    try:
        result = render_reel(input_path, output_path, cfg, job_dir)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    meta = job_dir / "result.json"
    meta.write_text(json.dumps(result, indent=2))
    return {
        "job_id": job_id,
        "duration": result["duration"],
        "download_path": f"/v1/jobs/{job_id}/video",
    }


@app.get("/v1/jobs/{job_id}/video")
def job_video(job_id: str):
    path = OUTPUTS / f"{job_id}.mp4"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Render not found")
    return FileResponse(path, media_type="video/mp4", filename=f"{job_id}.mp4")
