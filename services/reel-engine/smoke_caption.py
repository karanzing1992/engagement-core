from pathlib import Path
import subprocess
import tempfile

from captions import write_reel_ass

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    ass = root / "captions.ass"
    out = root / "caption-smoke.mp4"

    events = [
        {
            "kind": "hook",
            "start": 0.0,
            "end": 0.75,
            "text": "Goa has a slower side",
        },
        {
            "kind": "body",
            "start": 0.85,
            "end": 1.35,
            "text": "Rain changes the pace.",
        },
        {
            "kind": "cta",
            "start": 1.45,
            "end": 1.95,
            "text": "Comment GOA",
        },
    ]

    write_reel_ass(
        events,
        ass,
        style={
            "play_res_x": 1080,
            "play_res_y": 1920,
            "font_size": 56,
            "hook_font_size": 66,
            "cta_font_size": 62,
            "hook_y": 690,
            "body_y": 1280,
            "cta_y": 960,
        },
    )

    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", "color=c=black:s=1080x1920:d=2:r=30",
            "-vf", f"ass={ass}",
            "-an", "-c:v", "libx264", "-preset", "ultrafast",
            "-t", "2", str(out),
        ],
        check=True,
    )
    if not out.exists() or out.stat().st_size < 1000:
        raise RuntimeError("Caption smoke render did not produce a valid MP4")
