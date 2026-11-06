"""Private FFmpeg frame sampler for Gemini visual research (consent required)."""
import base64,hashlib,subprocess
from pathlib import Path
from ffmpeg_v6_adapter import RenderBlocked,sha256
def extract(workdir,source,duration,*,count=3,consent=False,source_sha256=""):
 if consent is not True:raise RenderBlocked("EXTERNAL_AI_VISUAL_CONSENT_MISSING")
 if type(count) is not int or not 1<=count<=3 or not 3<=duration<=480:
  raise RenderBlocked("SOURCE_FRAME_DURATION_INVALID")
 root=Path(workdir).resolve();path=Path(source).resolve()
 if path.parent!=root or not path.is_file() or sha256(path)!=source_sha256:
  raise RenderBlocked("SOURCE_FRAME_CHECKSUM_INVALID")
 frames=[];size=0
 for index in range(count):
  second=min(duration-.1,duration*(index+.5)/count)
  argv=["ffmpeg","-hide_banner","-loglevel","error","-ss",str(second),"-i",str(path),
        "-vf","scale=640:360:force_original_aspect_ratio=decrease:pad=640:360:(ow-iw)/2:(oh-ih)/2",
        "-frames:v","1","-f","image2pipe","-vcodec","mjpeg","-q:v","5","-"]
  try:result=subprocess.run(argv,capture_output=True,check=True,timeout=25)
  except (OSError,subprocess.CalledProcessError,subprocess.TimeoutExpired):
   raise RenderBlocked("FFMPEG_FRAME_EXTRACT_FAILED") from None
  pic=result.stdout;size+=len(pic)
  if len(pic)<1024 or pic[:2]!=b"\xff\xd8" or pic[-2:]!=b"\xff\xd9" or size>3*1024*1024:
   raise RenderBlocked("FFMPEG_FRAME_INVALID_OR_TOO_LARGE")
  frames.append({"time_seconds":round(second,3),"mime_type":"image/jpeg",
                 "data":base64.b64encode(pic).decode(),
                 "sha256":hashlib.sha256(pic).hexdigest(),"bytes":len(pic)})
 return frames
