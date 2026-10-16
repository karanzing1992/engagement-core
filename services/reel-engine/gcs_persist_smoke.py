"""One-shot synthetic FFmpeg-to-private-GCS smoke; never touches real footage.

This module is base64-encoded as the `python3 -c` argument of a manually
executed disposable Cloud Run Job. No public URLs, no tenant data, no posting.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

from google.cloud import storage

PROJECT = "focused-premise-510518-g6"
BUCKET = "reel-pilot-drafts-focused-premise-510518-g6-pilot2"
PREFIX = "smoke/cpu-gcs-20261013-01"
VIDEO_KEY = PREFIX + ".mp4"
REPORT_KEY = PREFIX + ".json"
EXPECTED_SECONDS = 5.0
EXPECTED_FRAMES = 125


def run_command(args: list[str]) -> str:
    result = subprocess.run(args, check=True, capture_output=True, text=True, timeout=90)
    return result.stdout


def verify_video(path: Path) -> dict:
    probe = json.loads(run_command([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=codec_name,width,height,r_frame_rate,nb_frames",
        "-show_entries", "format=duration,size", "-of", "json", str(path),
    ]))
    streams = probe.get("streams", [])
    if len(streams) != 1:
        raise RuntimeError("One video stream required")
    video = streams[0]
    info = probe.get("format", {})
    duration = float(info.get("duration", 0))
    size = int(info.get("size", 0))
    if not (
        video.get("codec_name") == "h264"
        and video.get("width") == 720
        and video.get("height") == 1280
        and video.get("r_frame_rate") == "25/1"
        and int(video.get("nb_frames", 0)) == EXPECTED_FRAMES
        and abs(duration - EXPECTED_SECONDS) < 0.05
        and size == path.stat().st_size
        and 0 < size < 15 * 1024 * 1024
    ):
        raise RuntimeError("Encoded video quality/duration/size gate failed")
    return {
        "codec": "h264", "width": 720, "height": 1280,
        "fps": 25, "frames": EXPECTED_FRAMES, "duration_seconds": duration,
        "bytes": size,
    }


def render_and_upload(client=None, command_runner=run_command) -> dict:
    with tempfile.TemporaryDirectory(prefix="reel-gcs-smoke-") as directory:
        path = Path(directory) / "synthetic.mp4"
        command_runner([
            "ffmpeg", "-hide_banner", "-nostdin", "-loglevel", "error",
            "-f", "lavfi", "-i", "testsrc2=size=720x1280:rate=25",
            "-t", "5", "-an", "-c:v", "libx264", "-preset", "ultrafast",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-y", str(path),
        ])
        if not path.is_file():
            raise RuntimeError("FFmpeg did not produce expected private MP4")
        info = verify_video(path)
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        client = client or storage.Client(project=PROJECT)
        bucket = client.bucket(BUCKET)
        video_blob = bucket.blob(VIDEO_KEY)
        video_blob.metadata = {
            "sha256": sha, "source": "synthetic-lavfi-testsrc2",
            "published": "false", "content-approval": "smoke-only",
        }
        video_blob.upload_from_filename(
            str(path), content_type="video/mp4", if_generation_match=0,
        )
        report = {
            "schema_version": 1, "kind": "synthetic-private-cloudrun-smoke",
            "source": "lavfi-testsrc2", "no_real_footage": True,
            "public": False, "published": False, "project": PROJECT,
            "video_uri": f"gs://{BUCKET}/{VIDEO_KEY}",
            "sha256": sha, **info,
        }
        report_blob = bucket.blob(REPORT_KEY)
        report_blob.upload_from_string(
            json.dumps(report, sort_keys=True), content_type="application/json",
            if_generation_match=0,
        )
        # This job's service account has Object Creator, not Object Viewer.
        # Independent object readback and checksum validation happen from Cloud Shell.
        print("GCS_PRIVATE_SMOKE=" + json.dumps(report, sort_keys=True), flush=True)
        return report


if __name__ == "__main__":
    render_and_upload()
