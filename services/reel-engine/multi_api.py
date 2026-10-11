"""Authenticated background render queue for 2+ uploaded video assets.

Persist job specifications before starting. Interrupted jobs can retry on process
restart, and users poll a private status endpoint instead of holding a long HTTP
connection for FFmpeg. No social publishing, private preview only.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import shutil
import threading
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from chunked_ingest import UploadError, _save_json
from geo_policy import GeoPolicyError, validate_render_config
from multiclip import assemble_multiclip, validate_timeline
from upload_api import STORE, require_reel_token
from verified_logo import overlay_verified_logo

router = APIRouter(tags=["private-multiclip-render"])
BASE = Path(os.environ.get("REEL_DATA_ROOT", "/data"))
JOBS = BASE / "private_multiclip_jobs"
VIDEOS = BASE / "private_multiclip_outputs"
JOBS.mkdir(parents=True, exist_ok=True)
VIDEOS.mkdir(parents=True, exist_ok=True)
QUEUE = ThreadPoolExecutor(max_workers=1, thread_name_prefix="reel-multi")
_QUEUE_LOCK = threading.Lock()
_PENDING: set[str] = set()


class Clip(BaseModel):
    source_index: int = Field(ge=0)
    start: float = Field(ge=0)
    end: float = Field(gt=0)


class MultiRenderRequest(BaseModel):
    asset_ids: list[str] = Field(min_length=1, max_length=20)
    cuts: list[Clip] = Field(min_length=1, max_length=20)
    duration_seconds: float = Field(default=30, ge=10, le=180)
    width: int = Field(default=1080, ge=360, le=1920)
    height: int = Field(default=1920, ge=640, le=3840)
    fps: int = 30
    audio_source_index: int | None = None
    audio_volume: float = Field(default=0.7, ge=0, le=1)
    config: dict


def _job_path(job_id: str) -> Path:
    if len(job_id) != 32 or not all(c in "0123456789abcdef" for c in job_id):
        raise HTTPException(status_code=404, detail="Job not found")
    path = JOBS / job_id / "job.json"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Job not found")
    return path


def _read(job_id: str) -> dict:
    return json.loads(_job_path(job_id).read_text(encoding="utf-8"))


def _write(job_id: str, value: dict) -> None:
    path = JOBS / job_id
    path.mkdir(exist_ok=True)
    _save_json(path / "job.json", value)


def _execute(job_id: str) -> None:
    job = _read(job_id)
    attempt = int(job.get("attempt", 0)) + 1
    job.update(status="running", attempt=attempt, updated_at=time.time())
    _write(job_id, job)
    cfg = job["request"]
    workdir = JOBS / job_id
    output = VIDEOS / f"{job_id}.mp4"
    intermediate = workdir / "unbranded.mp4"
    try:
        paths = [STORE.resolve(asset) for asset in cfg["asset_ids"]]
        report = assemble_multiclip(
            paths, cfg["cuts"], intermediate, workdir,
            duration=cfg["duration_seconds"], width=cfg["width"],
            height=cfg["height"], fps=cfg["fps"],
            audio_source_index=cfg["audio_source_index"],
            audio_volume=cfg["audio_volume"],
        )
        logo = None
        if str(cfg["config"].get("brand", "")).strip().lower() == "moksha":
            logo = overlay_verified_logo(
                intermediate, output, brand="moksha",
                placement=str(cfg["config"].get("placement", "reel")),
                wp_token=os.environ.get("MRS_BRAND_ASSET_TOKEN") or None,
                cache_dir=BASE / "verified-brand-assets",
            )
        else:
            shutil.move(intermediate, output)
        job.update(status="completed", updated_at=time.time(),
                   report=report, official_logo=logo,
                   video_path=f"/v1/render/multi/{job_id}/video")
    except Exception as e:
        output.unlink(missing_ok=True)
        job.update(status="failed", updated_at=time.time(),
                   error_type=type(e).__name__, error=str(e)[-900:])
    finally:
        _write(job_id, job)
        with _QUEUE_LOCK:
            _PENDING.discard(job_id)


def _enqueue(job_id: str) -> None:
    with _QUEUE_LOCK:
        if job_id in _PENDING:
            return
        if len(_PENDING) >= 3:
            raise HTTPException(status_code=429, detail="Render queue full; retry later")
        _PENDING.add(job_id)
    QUEUE.submit(_execute, job_id)


@router.on_event("startup")
def recover_interrupted() -> None:
    """Recover the earliest interrupted queued jobs after worker restart."""
    for path in sorted(JOBS.glob("*/job.json"), key=lambda p: p.stat().st_mtime):
        try:
            job = json.loads(path.read_text())
            if job.get("status") not in ("queued", "running"):
                continue
            if int(job.get("attempt", 0)) >= 3:
                job["status"] = "failed"
                job["error"] = "Maximum automatic retries exceeded"
                _write(job["job_id"], job)
                continue
            _enqueue(job["job_id"])
        except (ValueError, OSError, HTTPException):
            # Do not erase a job with damaged metadata; keep for admin review.
            continue


@router.post("/v1/render/multi", dependencies=[Depends(require_reel_token)],
             status_code=status.HTTP_202_ACCEPTED)
def render_multiple(payload: MultiRenderRequest) -> dict:
    data = payload.model_dump()
    if len(payload.config.get("source_provenance", [])) != len(payload.asset_ids):
        raise HTTPException(status_code=422, detail="One human-verified geographic source record per video required")
    try:
        provenance = validate_render_config(payload.config)
    except GeoPolicyError as e:
        raise HTTPException(status_code=422, detail="Goa/India footage policy: " + str(e)) from e
    try:
        paths = [STORE.resolve(asset) for asset in payload.asset_ids]
        validate_timeline(paths, data["cuts"], duration=payload.duration_seconds,
                          width=payload.width, height=payload.height, fps=payload.fps)
    except UploadError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e)) from e
    with _QUEUE_LOCK:
        if len(_PENDING) >= 3:
            raise HTTPException(status_code=429, detail="Render queue full; retry later")
    job_id = uuid.uuid4().hex
    job = {"job_id": job_id, "status": "queued", "attempt": 0,
           "created_at": time.time(), "updated_at": time.time(),
           "publishing_enabled": False, "schedule_enabled": False,
           "geography": provenance, "request": data}
    _write(job_id, job)
    _enqueue(job_id)
    return {"job_id": job_id, "status": "queued", "publishing_enabled": False,
            "status_path": f"/v1/render/multi/{job_id}",
            "video_path": f"/v1/render/multi/{job_id}/video"}


@router.get("/v1/render/multi/{job_id}", dependencies=[Depends(require_reel_token)])
def multi_status(job_id: str) -> dict:
    data = _read(job_id)
    # Expose only workflow status and provenance, never full private creative specs.
    return {k: v for k, v in data.items() if k != "request"}


@router.get("/v1/render/multi/{job_id}/video", dependencies=[Depends(require_reel_token)])
def multi_video(job_id: str):
    data = _read(job_id)
    if data.get("status") != "completed":
        raise HTTPException(status_code=409, detail="Render not completed")
    path = VIDEOS / f"{job_id}.mp4"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Video not available")
    return FileResponse(path, media_type="video/mp4", filename="moksha-private-reel.mp4")