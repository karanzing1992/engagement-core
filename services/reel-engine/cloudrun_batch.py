"""Private one-shot Cloud Run Reel draft worker; no public endpoints or publishing."""
from __future__ import annotations
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

MAX_TOTAL_BYTES = 48 * 1024 * 1024
MAX_MANIFEST_BYTES = 128 * 1024

def gs_object(uri: str) -> tuple[str, str]:
    if not isinstance(uri, str) or not uri.startswith("gs://"):
        raise ValueError("A private gs:// URI is required")
    p = urlsplit(uri)
    if p.scheme != "gs" or p.username or p.password or p.port or p.query or p.fragment:
        raise ValueError("Invalid private GCS URI")
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{2,62}", p.netloc):
        raise ValueError("Invalid GCS bucket name")
    key = p.path.lstrip("/")
    if not key or len(key) > 300 or "\\" in key or any(x in (".", "..", "") for x in key.split("/")):
        raise ValueError("Invalid object path")
    return p.netloc, key

def prefix(value: str) -> tuple[str, str]:
    if not isinstance(value, str) or not value.endswith("/"):
        raise ValueError("GCS prefix must end with /")
    bucket, key = gs_object(value + "_probe")
    return bucket, key[:-len("_probe")]

def validate_manifest(spec: dict, source_prefix: str, output_prefix: str) -> dict:
    from geo_policy import validate_render_config
    if not isinstance(spec, dict) or spec.get("schema_version") != 1:
        raise ValueError("Unsupported batch manifest version")
    job_id = spec.get("job_id")
    if not isinstance(job_id, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{7,49}", job_id):
        raise ValueError("Invalid batch job ID")
    assets = spec.get("source_objects")
    if not isinstance(assets, list) or not 1 <= len(assets) <= 4:
        raise ValueError("Pilot supports 1-4 approved clips")
    source_bucket, source_key_prefix = prefix(source_prefix)
    output_bucket, output_key_prefix = prefix(output_prefix)
    if source_bucket == output_bucket and source_key_prefix == output_key_prefix:
        raise ValueError("Source and output prefixes must differ")
    seen = set()
    for item in assets:
        if not isinstance(item, dict):
            raise ValueError("Source objects must include uri and checksum")
        bucket, key = gs_object(item.get("uri"))
        digest = item.get("sha256", "")
        if bucket != source_bucket or not key.startswith(source_key_prefix):
            raise ValueError("Source outside approved private prefix")
        if not re.fullmatch(r"[0-9a-f]{64}", str(digest)):
            raise ValueError("Exact SHA-256 required for every source")
        if (bucket, key) in seen:
            raise ValueError("Duplicate source object")
        seen.add((bucket, key))
    config = spec.get("config")
    if not isinstance(config, dict) or len(config.get("source_provenance", [])) != len(assets):
        raise ValueError("One provenance record required per source")
    if config.get("brand") != spec.get("brand"):
        raise ValueError("Brand mismatch")
    # Pilot is unbranded only; approved transparent logo pipeline is pending.
    if spec.get("brand") != "generic":
        raise ValueError("Pilot is unbranded only; approved transparent logo adapter pending")
    if (int(config.get("width", 720)), int(config.get("height", 1280))) != (720, 1280):
        raise ValueError("Pilot requires 720x1280 vertical output")
    if int(config.get("fps", 25)) != 25 or float(config.get("target_seconds", 30)) != 30:
        raise ValueError("Pilot requires 30 seconds at 25fps")
    validate_render_config(config)
    return {"job_id": job_id, "assets": assets, "config": config,
            "source_bucket": source_bucket, "output_bucket": output_bucket,
            "output_key": output_key_prefix + job_id + ".mp4",
            "report_key": output_key_prefix + job_id + ".json"}

def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()

def main() -> None:
    from google.cloud import storage
    from multi_renderer import render_multiple
    manifest_uri = os.environ["REEL_BATCH_MANIFEST_URI"]
    source_prefix = os.environ["REEL_BATCH_SOURCE_PREFIX"]
    output_prefix = os.environ["REEL_BATCH_OUTPUT_PREFIX"]
    bucket_id, manifest_key = gs_object(manifest_uri)
    source_bucket_id, source_dir = prefix(source_prefix)
    if bucket_id != source_bucket_id or not manifest_key.startswith(source_dir):
        raise ValueError("Manifest must be in approved source prefix")
    client = storage.Client()
    manifest_blob = client.bucket(bucket_id).blob(manifest_key)
    manifest_blob.reload()
    if not manifest_blob.size or manifest_blob.size > MAX_MANIFEST_BYTES:
        raise ValueError("Manifest missing or too large")
    spec = json.loads(manifest_blob.download_as_bytes().decode("utf-8"))
    plan = validate_manifest(spec, source_prefix, output_prefix)

    with tempfile.TemporaryDirectory(prefix="reel-batch-") as temporary:
        root = Path(temporary)
        paths = []
        total = 0
        for i, asset in enumerate(plan["assets"]):
            source_bucket, key = gs_object(asset["uri"])
            blob = client.bucket(source_bucket).blob(key)
            blob.reload()
            total += int(blob.size or 0)
            if not blob.size or total > MAX_TOTAL_BYTES:
                raise ValueError("Pilot source size budget exceeded")
            path = root / f"source-{i}.mp4"
            blob.download_to_filename(str(path))
            if path.stat().st_size != blob.size or _sha256(path) != asset["sha256"]:
                raise ValueError("Source checksum/size mismatch")
            paths.append(path)
        output = root / "draft.mp4"
        result = render_multiple(paths, output, plan["config"], root / "working")
        output_bucket = client.bucket(plan["output_bucket"])
        video = output_bucket.blob(plan["output_key"])
        video.upload_from_filename(str(output), content_type="video/mp4", if_generation_match=0)
        report = output_bucket.blob(plan["report_key"])
        safe_result = {k: result[k] for k in ("duration", "width", "height", "fps", "sections")}
        report.upload_from_string(json.dumps({"job_id":plan["job_id"],
          "output_uri":f"gs://{plan['output_bucket']}/{plan['output_key']}",
          "private":True,"publishing_enabled":False,"render":safe_result}),
          content_type="application/json",if_generation_match=0)
    print(json.dumps({"ok":True,"job_id":plan["job_id"],"private":True,"published":False}))

if __name__ == "__main__":
    main()
