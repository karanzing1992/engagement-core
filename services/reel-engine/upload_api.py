"""Private resumable-upload API: never buffers a large video into RAM."""
from __future__ import annotations

import hashlib
import hmac
import os
from pathlib import Path
import secrets
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field

from chunked_ingest import CHUNK_BYTES, UploadError, UploadStore

router = APIRouter(tags=["private-media-ingest"])
DATA_ROOT = Path(os.environ.get("REEL_DATA_ROOT", "/data"))
STORE = UploadStore(DATA_ROOT / "resumable")


def require_reel_token(authorization: str = Header(default="")) -> None:
    expected = os.environ.get("REEL_ENGINE_TOKEN", "")
    if len(expected) < 32:
        raise HTTPException(status_code=503, detail="Private ingest unavailable: server token not configured")
    if not authorization.startswith("Bearer ") or not hmac.compare_digest(authorization[7:], expected):
        raise HTTPException(status_code=401, detail="Unauthorized")


class BeginUpload(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    size: int = Field(gt=0)
    sha256: str = Field(min_length=64, max_length=64)
    mime_type: str = "video/mp4"


def _error(e: UploadError):
    raise HTTPException(status_code=e.status_code, detail=str(e)) from e


@router.post("/v1/uploads", dependencies=[Depends(require_reel_token)])
def begin_upload(payload: BeginUpload) -> dict:
    try:
        return STORE.begin(**payload.model_dump())
    except UploadError as e:
        _error(e)


@router.get("/v1/uploads/{upload_id}", dependencies=[Depends(require_reel_token)])
def upload_status(upload_id: str) -> dict:
    try:
        return STORE.status(upload_id)
    except UploadError as e:
        _error(e)


@router.put("/v1/uploads/{upload_id}/chunks/{index}", dependencies=[Depends(require_reel_token)])
async def put_upload_chunk(upload_id: str, index: int, request: Request,
                           x_chunk_sha256: str | None = Header(default=None)) -> dict:
    try:
        # Reject invalid or expired sessions before writing any bytes.
        STORE.status(upload_id)
        # Write into a private temp path; never trust filename or path from URL.
        temp = STORE.root / (".incoming-" + uuid.uuid4().hex + ".part")
        received = 0
        digest = hashlib.sha256()
        try:
            with temp.open("xb") as f:
                async for data in request.stream():
                    received += len(data)
                    if received > CHUNK_BYTES:
                        raise UploadError("Chunk exceeds 8 MiB limit", 413)
                    digest.update(data)
                    f.write(data)
            if not x_chunk_sha256 or not hmac.compare_digest(digest.hexdigest(), x_chunk_sha256):
                raise UploadError("Valid X-Chunk-SHA256 required", 422)
            return STORE.accept_chunk(upload_id, index, temp, sha256=x_chunk_sha256)
        finally:
            temp.unlink(missing_ok=True)
    except UploadError as e:
        _error(e)


@router.post("/v1/uploads/{upload_id}/complete", dependencies=[Depends(require_reel_token)])
def complete_upload(upload_id: str) -> dict:
    try:
        return STORE.complete(upload_id)
    except UploadError as e:
        _error(e)