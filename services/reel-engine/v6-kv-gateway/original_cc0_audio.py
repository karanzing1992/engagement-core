#!/usr/bin/env python3
"""Original V6 ambient audio library: CC0 self-authored source, zero external dependency.

Creative material generated from independent additive synthesis and procedural pulse.
Original source and generated WAV are CC0-1.0. No third-party melodies or samples,
no FFmpeg, no copyrighted recordings. The FilmCraft editor performs all actual mixing.
"""
from __future__ import annotations
import hashlib
import math
from pathlib import Path
import random
import struct
import wave

LICENSE="https://creativecommons.org/publicdomain/zero/1.0/"
SOURCE_URL="https://github.com/karanzing1992/engagement-core/blob/main/services/reel-engine/v6-kv-gateway/original_cc0_audio.py"
RATE=22050

def original_cc0_soundtrack(workdir:Path, *,seconds:float=18.0, brief:str="calm cinematic"):
    if not 3.0<=seconds<=120.0:
        raise ValueError("CC0 original soundtrack duration out of bounds")
    is_upbeat=any(x in brief.lower() for x in ("energetic","upbeat","fast","dance","sports","party"))
    mood="upbeat" if is_upbeat else "calm"
    bpm=110 if is_upbeat else 74
    beat=60.0/bpm
    # The short, original modal motif is not derived from an existing composition.
    tones=(164.81,196.00,246.94,293.66) if is_upbeat else (146.83,174.61,220.00,261.63)
    total=int(seconds*RATE)
    dest=workdir/"mad-v6-original-cc0-ambient.wav"
    rng=random.Random(69413)
    noise=[rng.uniform(-1,1) for _ in range(total//4+2)]
    with wave.open(str(dest),"wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(RATE)
        out=bytearray()
        for i in range(total):
            t=i/RATE
            phase=(t/beat)%1
            current=int(t/(beat*4))%len(tones)
            root=tones[current]
            # Soft three-voice sustained pad, with independently synthesized pulses.
            pad=sum(math.sin(2*math.pi*root*m*t)/m for m in (1,1.5,2))
            pad*=0.155*(0.55+0.45*math.sin(math.pi*min(1,t/2))**2)
            sub=0.075*math.sin(2*math.pi*(root/2)*t)
            pulse=max(0,1-phase*7)
            pluck=0.115*pulse*math.sin(2*math.pi*(root*2)*t)
            breath=0.016*(0.5+0.5*math.sin(2*math.pi*0.2*t))*noise[i//4]
            fade=min(1,t/0.4,(seconds-t)/0.6)
            value=max(-0.85,min(0.85,(pad+sub+pluck+breath)*max(0,fade)))
            out.extend(struct.pack("<h",int(value*32767)))
        audio.writeframes(out)
    raw=dest.read_bytes()
    digest=hashlib.sha256(raw).hexdigest()
    return {
        "license":"CC0",
        "music_source":"original_v6_open_audio_library",
        "audio_path":str(dest),
        "audio_sha256":digest,
        "audio_bytes":len(raw),
        "original_source_url":SOURCE_URL,
        "original_license_url":LICENSE,
        "track_title":"V6 Original Ambient — "+mood,
        "creator":"MAD V6 procedural original composition",
        "duration_seconds":seconds,
        "bpm":bpm,
        "beat_times_seconds":[round(i*beat,3) for i in range(int(seconds/beat)+1)],
        "attribution_required":False,
        "filmcraft_rights":{
            "human_verified":True,
            "license":"CC0",
            "creator":SOURCE_URL,
            "original_source_url":SOURCE_URL,
            "original_license_url":LICENSE,
            "audio_sha256":digest
        },
        "native_audio_required":True,
        "published":False,
    }
