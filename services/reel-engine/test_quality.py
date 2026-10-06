from pathlib import Path
import tempfile, subprocess
from quality import media_preflight, detect_silence, retention_report

def test_retention_report_flags_late_hook():
    r=retention_report(10.0,[{"start":3.0,"end":5.0,"text":"hello","kind":"speech"}],[])
    assert "late-hook" in r["warnings"]

def test_preflight_and_silence():
    with tempfile.TemporaryDirectory() as d:
        p=Path(d)/"x.mp4"
        subprocess.run(["ffmpeg","-y","-loglevel","error","-f","lavfi","-i","color=size=320x568:rate=30:duration=1","-f","lavfi","-i","anullsrc=r=48000:cl=stereo","-shortest","-c:v","libx264","-c:a","aac",str(p)],check=True)
        q=media_preflight(p)
        assert q["width"]==320 and q["height"]==568 and q["has_audio"]
        assert isinstance(detect_silence(p),list)
