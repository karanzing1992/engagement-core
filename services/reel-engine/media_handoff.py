"""Public media handoff for social publishing.

Uploads rendered media to an S3-compatible object store and returns a direct
HTTPS URL that third-party publishers (Metricool, Meta, etc.) can fetch.

Required env:
  MEDIA_S3_ENDPOINT
  MEDIA_S3_BUCKET
  MEDIA_S3_ACCESS_KEY
  MEDIA_S3_SECRET_KEY
  MEDIA_PUBLIC_BASE_URL

Optional:
  MEDIA_S3_REGION=auto
  MEDIA_TTL_HOURS=48
"""
from __future__ import annotations
import hashlib, mimetypes, os, time
from pathlib import Path
from urllib.parse import quote
import boto3

def _client():
    return boto3.client(
        "s3",
        endpoint_url=os.environ["MEDIA_S3_ENDPOINT"],
        aws_access_key_id=os.environ["MEDIA_S3_ACCESS_KEY"],
        aws_secret_access_key=os.environ["MEDIA_S3_SECRET_KEY"],
        region_name=os.getenv("MEDIA_S3_REGION", "auto"),
    )

def publish_media(path: str, brand: str = "default") -> dict:
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(path)
    digest = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
    safe_brand = "".join(c for c in brand.lower() if c.isalnum() or c in "-_") or "default"
    key = f"social/{safe_brand}/{time.strftime('%Y/%m/%d')}/{digest}-{p.name}"
    content_type = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
    _client().upload_file(
        str(p), os.environ["MEDIA_S3_BUCKET"], key,
        ExtraArgs={"ContentType": content_type, "CacheControl": "public,max-age=172800"},
    )
    base = os.environ["MEDIA_PUBLIC_BASE_URL"].rstrip("/")
    return {
        "url": f"{base}/{quote(key, safe='/')}",
        "key": key,
        "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
        "bytes": p.stat().st_size,
        "expires_after_hours": int(os.getenv("MEDIA_TTL_HOURS", "48")),
    }

def delete_media(key: str) -> None:
    _client().delete_object(Bucket=os.environ["MEDIA_S3_BUCKET"], Key=key)
