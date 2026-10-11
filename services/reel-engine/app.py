from __future__ import annotations

import json
import hmac
import os
import shutil
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile, Header
from fastapi.responses import FileResponse

from music_library import ingest_track, list_tracks, rank_tracks, select_track
from renderer import render_reel
from multi_renderer import render_multiple, MultiClipError
from verified_logo import overlay_verified_logo
from geo_policy import GeoPolicyError, validate_render_config
from upload_api import router as private_upload_router
from multi_api import router as private_multiclip_router
from media_handoff import publish_media, delete_media
from quality import media_preflight, detect_silence
from social_publishers import capabilities

ROOT = Path(os.environ.get("REEL_DATA_ROOT", "/data"))
UPLOADS = ROOT / "uploads"
JOBS = ROOT / "jobs"
OUTPUTS = ROOT / "outputs"
MUSIC = ROOT / "music"
for p in (UPLOADS, JOBS, OUTPUTS, MUSIC):
    p.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Reel Engine", version="0.5.0")
app.include_router(private_upload_router)
app.include_router(private_multiclip_router)


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
            "media-preflight",
            "dead-air-analysis",
            "goa-india-geography-guard",
            "private-resumable-upload",
            "private-multiclip-queue",
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
    # Fail before saving inputs or using compute. Captions saying Goa do not
    # make a foreign stock clip Goa/India-relevant.
    try:
        regional_check = validate_render_config(cfg)
    except GeoPolicyError as exc:
        raise HTTPException(status_code=422, detail=f"Goa/India media policy: {exc}") from exc

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
        # Final Moksha drafts must use the immutable approved Google Drive logo;
        # no filename search, AI reconstruction, auto-publishing or unverified fallback.
        if str(cfg.get("brand", "")).strip().lower() == "moksha":
            branded_output = job_dir / "verified-logo-final.mp4"
            provenance = overlay_verified_logo(
                output_path,
                branded_output,
                brand="moksha",
                placement=str(cfg.get("placement", "reel")),
                wp_token=os.environ.get("MRS_BRAND_ASSET_TOKEN") or None,
                cache_dir=ROOT / "verified-brand-assets",
            )
            shutil.move(str(branded_output), str(output_path))
            provenance["output_video"] = str(output_path)
            result["official_logo"] = provenance
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    result["geography"] = regional_check
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



# Private, request-authenticated multi-source video endpoint. The cloud renderer
# accepts multiple streamed uploads; connectors may still need a byte transfer
# bridge, provided by the WordPress upload vault rather than public URL sharing.
def _require_render_token(provided: str | None) -> None:
    expected=os.environ.get("REEL_ENGINE_API_TOKEN", "")
    if len(expected) < 32:
        raise HTTPException(status_code=503,detail="Private render authentication not configured")
    if not provided or not hmac.compare_digest(expected,provided):
        raise HTTPException(status_code=403,detail="Invalid private render authorization")


def _private_job(job_id: str) -> bool:
    return (JOBS/job_id/"private-multi.flag").exists()


def _require_if_private(job_id: str, token: str | None) -> None:
    if _private_job(job_id):
        _require_render_token(token)


@app.post("/v1/render-multi")
def render_multi(
    videos: list[UploadFile] = File(...),
    config_json: str = Form(...),
    x_reel_engine_token: str | None = Header(default=None),
):
    _require_render_token(x_reel_engine_token)
    try:
        cfg=json.loads(config_json)
    except (TypeError,ValueError) as exc:
        raise HTTPException(status_code=400,detail=f"Invalid render JSON: {exc}") from exc
    if len(videos)<1 or len(videos)>8:
        raise HTTPException(status_code=400,detail="One to eight video sources required")
    try:
        regional_check=validate_render_config(cfg)
    except GeoPolicyError as exc:
        raise HTTPException(status_code=422,detail=f"Goa/India video policy: {exc}") from exc
    if regional_check["clips_verified"] != len(videos):
        raise HTTPException(status_code=422,detail="Each uploaded video needs a distinct verified source record")

    job_id=uuid.uuid4().hex
    workdir=JOBS/job_id
    workdir.mkdir(parents=True,exist_ok=False)
    (workdir/"private-multi.flag").write_text("review-only\n",encoding="utf-8")
    inputs=[]
    target=OUTPUTS/f"{job_id}.mp4"
    try:
        for i,media in enumerate(videos):
            suffix=Path(media.filename or "clip.mp4").suffix.lower()
            if suffix not in (".mp4",".mov",".m4v"):
                raise HTTPException(status_code=400,detail=f"Source {i+1}: unsupported video extension")
            source=UPLOADS/f"{job_id}-{i}{suffix}"
            amount=0
            with source.open("xb") as stream:
                while True:
                    chunk=media.file.read(1024*1024)
                    if not chunk:break
                    amount+=len(chunk)
                    if amount > 800*1024*1024:
                        raise HTTPException(status_code=413,detail=f"Source {i+1} exceeds 800 MB")
                    stream.write(chunk)
            if amount < 1024:
                raise HTTPException(status_code=400,detail=f"Source {i+1} is empty")
            inputs.append(source)

        info=render_multiple(inputs,target,cfg,workdir)
        if str(cfg.get("brand","")).lower()=="moksha":
            official=workdir/"branded-official-logo.mp4"
            data=overlay_verified_logo(
                target,official,brand="moksha",
                placement=str(cfg.get("placement","reel")),
                wp_token=os.environ.get("MRS_BRAND_ASSET_TOKEN") or None,
                cache_dir=ROOT/"verified-brand-assets",
            )
            shutil.move(str(official),str(target))
            info["official_logo"]=data
        info["geography"]=regional_check
        info["job_id"]=job_id
        (workdir/"result.json").write_text(json.dumps(info,indent=2))
        return {"job_id":job_id,"status":"preview_ready_private",
                "duration":info["duration"],"download_path":f"/v1/jobs/{job_id}/video",
                "published":False,"requires_review":True}
    except HTTPException:
        target.unlink(missing_ok=True)
        raise
    except (MultiClipError,ValueError) as exc:
        target.unlink(missing_ok=True)
        raise HTTPException(status_code=422,detail=str(exc)) from exc
    except Exception as exc:
        target.unlink(missing_ok=True)
        raise HTTPException(status_code=500,detail="Private multi-clip processing failed") from exc
    finally:
        for path in inputs:
            path.unlink(missing_ok=True)

@app.get("/v1/jobs/{job_id}")
def job_result(job_id: str, x_reel_engine_token: str | None = Header(default=None)):
    _require_if_private(job_id, x_reel_engine_token)
    path = JOBS / job_id / "result.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Job not found")
    return json.loads(path.read_text())


@app.get("/v1/jobs/{job_id}/video")
def job_video(job_id: str, x_reel_engine_token: str | None = Header(default=None)):
    _require_if_private(job_id, x_reel_engine_token)
    path = OUTPUTS / f"{job_id}.mp4"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Render not found")
    return FileResponse(path, media_type="video/mp4", filename=f"{job_id}.mp4")


@app.get("/v1/jobs/{job_id}/srt")
def job_srt(job_id: str, x_reel_engine_token: str | None = Header(default=None)):
    _require_if_private(job_id, x_reel_engine_token)
    path = OUTPUTS / f"{job_id}.srt"
    if not path.exists():
        raise HTTPException(status_code=404, detail="SRT not found")
    return FileResponse(path, media_type="application/x-subrip", filename=f"{job_id}.srt")


@app.post("/v1/jobs/{job_id}/publish-media")
def publish_job_media(job_id: str, brand: str = Query("default")):
    if _private_job(job_id):
        raise HTTPException(status_code=403, detail="Private video cannot be published by worker")
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


@app.get("/v1/jobs/{job_id}/quality")
def job_quality(job_id: str, x_reel_engine_token: str | None = Header(default=None)):
    _require_if_private(job_id, x_reel_engine_token)
    path = OUTPUTS / f"{job_id}.mp4"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Render not found")
    try:
        preflight = media_preflight(path)
        silence = detect_silence(path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Quality analysis failed: {exc}") from exc
    return {"preflight": preflight, "silence": silence}


@app.get("/v1/social/capabilities")
def social_capabilities():
    return capabilities()
