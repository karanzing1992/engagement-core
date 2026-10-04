from pathlib import Path
import subprocess
import tempfile

from captions import normalize_events, write_ass

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    ass = root / "captions.ass"
    out = root / "caption-smoke.mp4"

    events = normalize_events([
        {
            "start": 0.0,
            "end": 2.0,
            "text": "Goa has a slower side",
        }
    ])
    write_ass(
        events,
        ass,
        style={
            "play_res_x": 1080,
            "play_res_y": 1920,
            "font_size": 64,
            "y": 1280,
            "active_color": "#DDE9CF",
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
