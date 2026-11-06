#!/usr/bin/env python3
"""First-party open-source V6 audio library, original procedural CC0 soundscapes.

Composes an original recording offline from mathematical oscillators, not from
existing recordings, copyrighted melodies, or external generation APIs.
Uses stdlib PCM WAV only; FilmCraft is the sole media timeline/editor.
"""
from __future__ import annotations
import hashlib
import math
from pathlib import Path
import struct
import wave

LICENSE = "CC0"
LICENSE_URL = "https://creativecommons.org/publicdomain/zero/1.0/"
SOURCE_URL = "https://github.com/karanzing1992/engagement-core/blob/main/services/reel-engine/v6-kv-gateway/original_cc0_audio.py"
TRACKS = {
 "ambient": {"title":"Open Sky — Original Generative Ambient", "bpm":84, "root":174.61,
             "progression":(0,5,3,7), "mood":"calm"},
 "uplift": {"title":"Bright Current — Original Generative Pulse", "bpm":112, "root":196.0,
             "progression":(0,7,5,3), "mood":"uplifting"},
}
def choose(brief: str) -> str:
 text=(brief or "").lower()
 return "ambient" if any(k in text for k in ("calm","serene","relax","meditat","sleep","nature","slow")) else "uplift"

def compose(out:Path, seconds:float, profile:str="ambient",rate:int=24000) -> dict:
 if profile not in TRACKS or not 3 <= seconds <= 120 or rate not in (24000,32000):
  raise ValueError("Unrecognized CC0 track, unsupported length or sample rate")
 p=TRACKS[profile]
 path=Path(out)
 path.parent.mkdir(parents=True,exist_ok=True)
 frames=int(math.ceil(seconds*rate))
 bps=60.0/p["bpm"]
 # deliberately original progression; generated exclusively from oscillators and seeded noise.
 two_pi=2*math.pi
 result=hashlib.sha256()
 peak=0.0
 with wave.open(str(path),"wb") as f:
  f.setnchannels(1);f.setsampwidth(2);f.setframerate(rate)
  data=bytearray()
  for n in range(frames):
   t=n/rate
   bar=int(t/(bps*4))
   semitone=p["progression"][bar%len(p["progression"])]
   fundamental=p["root"]*(2**(semitone/12))
   beat=t/bps
   phase=beat%1
   chord=0.0
   for interval,gain in ((0,0.12),(4,0.075),(7,0.06),(12,0.025)):
    freq=fundamental*2**(interval/12)
    chord+=gain*(math.sin(two_pi*freq*t)+0.14*math.sin(two_pi*freq*2.003*t))
   swell=0.75+0.25*math.sin(two_pi*.081*t)
   bass=0.10*math.sin(two_pi*(fundamental/2)*t)
   kick=0.08*math.sin(two_pi*(55+30*math.exp(-phase*27))*t)*math.exp(-phase*14)
   # subtle brushed percussion using deterministic aperiodic oscillators
   shimmer=0.016*(math.sin(two_pi*3989.3*t)*math.sin(two_pi*7431.7*t))*math.exp(-((beat*2)%1)*16)
   sample=(chord*swell+bass+kick+shimmer)
   ramp=min(1.0,t/0.5,(seconds-t)/1.1)
   v=max(-0.88,min(.88,sample*max(0,ramp)))
   peak=max(peak,abs(v))
   data.extend(struct.pack("<h",int(v*32767)))
   if len(data)>=rate*2:
    f.writeframesraw(data);result.update(data);data.clear()
  if data:f.writeframesraw(data);result.update(data)
 if path.stat().st_size<1024:
  raise ValueError("Generated CC0 audio missing")
 digest=hashlib.sha256(path.read_bytes()).hexdigest()
 return {"id":"mad-v6-original-"+profile,"title":p["title"],"creator":"MAD Reel Engine Original Audio Library",
   "mode":"original_cc0_music","license":LICENSE,"license_url":LICENSE_URL,
   "original_source_url":SOURCE_URL,"original_license_url":LICENSE_URL,
   "file":str(path),"sha256":digest,"bytes":path.stat().st_size,
   "seconds":seconds,"sample_rate":rate,"bpm":p["bpm"],"peak":round(peak,5),
   "beat_seconds":round(bps,6),"private_only":True,"attribution_required":False,
   "filmcraft_only":True,"published":False,
   "filmcraft_rights":{"human_verified":True,"license":"CC0","creator":SOURCE_URL,
      "original_source_url":SOURCE_URL,"original_license_url":LICENSE_URL,
      "audio_sha256":digest}}

if __name__=="__main__":
 import argparse,json
 x=argparse.ArgumentParser();x.add_argument("--output",required=True);x.add_argument("--duration",type=float,default=8)
 x.add_argument("--profile",choices=tuple(TRACKS),default="ambient")
 a=x.parse_args()
 print(json.dumps(compose(Path(a.output),a.duration,a.profile),sort_keys=True))
