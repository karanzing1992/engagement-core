#!/usr/bin/env python3
"""V6 open-license audio: curated CC0 Wikimedia source -> FilmCraft native mixer.

A publicly indexed file is never assumed cleared: re-check primary-source
license metadata, creator, SHA-1 and bytes; preserve CC0 proof in render receipt.
No FFmpeg, no private audio egress to Gemini/Groq.
"""
from __future__ import annotations

from datetime import date
import hashlib
import html
import json
from pathlib import Path
import re
import urllib.parse
import urllib.request
import urllib.error
import wave
import struct
import math

API="https://commons.wikimedia.org/w/api.php"
TITLE="File:Emotional piano.wav"
PAGE="https://commons.wikimedia.org/wiki/File:Emotional_piano.wav"
LICENSE="https://creativecommons.org/publicdomain/zero/1.0/"
CURATED_SHA1="e8c449fba4fe1eb5e67e0923b6b696f2105584c5"
MAX_SIZE=6*1024*1024

class AudioRuntimeError(ValueError):
    pass

def _request(url, *,limit, accept="application/json"):
    req=urllib.request.Request(url,headers={"User-Agent":
        "MAD-V6-FilmCraft-CC0-Audio-QA/1.0 (original Commons source metadata)",
        "Accept":accept})
    try:
        with urllib.request.urlopen(req,timeout=30) as response:
            final=urllib.parse.urlsplit(response.geturl())
            if final.scheme!="https" or final.hostname not in {
                 "commons.wikimedia.org","upload.wikimedia.org"}:
                raise AudioRuntimeError("Audio media redirected away from verified Wikimedia hosts")
            raw=response.read(limit+1)
    except (urllib.error.HTTPError,urllib.error.URLError,TimeoutError) as exc:
        raise AudioRuntimeError("Authoritative CC0 source unavailable") from exc
    if len(raw)>limit:
        raise AudioRuntimeError("Audio source exceeded permitted byte limit")
    return raw

def verified_cc0_audio(workdir: Path, *,minimum_seconds:float, download:bool=True):
    if not (3<=minimum_seconds<=120):
        raise AudioRuntimeError("Requested soundtrack duration invalid")
    args=urllib.parse.urlencode({"action":"query","format":"json","formatversion":"2",
      "titles":TITLE,"prop":"imageinfo","iiprop":"url|size|sha1|extmetadata",
      "iiextmetadatafilter":"LicenseShortName|LicenseUrl|Artist"})
    try:
        metadata=json.loads(_request(API+"?"+args,limit=100000))
        page=metadata["query"]["pages"][0]
        info=page["imageinfo"][0]
    except (TypeError,KeyError,IndexError,ValueError) as exc:
        raise AudioRuntimeError("Commons audio proof unavailable") from exc
    license_name=html.unescape(str(info.get("extmetadata",{}).get("LicenseShortName",{}).get("value",""))).lower()
    license_url=str(info.get("extmetadata",{}).get("LicenseUrl",{}).get("value",""))
    sha1=str(info.get("sha1","")).lower()
    url=str(info.get("url",""))
    if (page.get("title")!=TITLE or "cc0" not in license_name or
       "/publicdomain/zero/" not in license_url or sha1!=CURATED_SHA1 or
       not 1000<int(info.get("size",0))<=MAX_SIZE):
        raise AudioRuntimeError("CC0 primary-source license or SHA-1 proof differs from approved asset")
    if urllib.parse.urlsplit(url).hostname!="upload.wikimedia.org" or not url.startswith("https://"):
        raise AudioRuntimeError("Wikimedia original-media URL must use the approved host")
    result={"audio_mode":"licensed_music",
        "track_title":"Emotional piano.wav","creator":"Kamil-b",
        "original_source_url":PAGE,"original_license_url":LICENSE,
        "license":"CC0","source_media_url":url,"commons_sha1":CURATED_SHA1,
        "rights_source":"Wikimedia Commons original file metadata and CC0 dedication",
        "source_checked_on":date.today().isoformat(),"attribution_required":False,
        "beat_sync_state":"not_certified","published":False}
    if not download:return result
    audio=_request(url,limit=MAX_SIZE,accept="audio/*")
    if len(audio)!=int(info["size"]) or hashlib.sha1(audio).hexdigest()!=CURATED_SHA1:
        raise AudioRuntimeError("Downloaded CC0 audio differs from Commons primary source")
    target=workdir/"approved-cc0-piano.wav"
    target.write_bytes(audio);target.chmod(0o600)
    if not audio.startswith(b"RIFF") or audio[8:12]!=b"WAVE":
        target.unlink(missing_ok=True)
        raise AudioRuntimeError("CC0 source is not a WAV recording")
    try:
        with wave.open(str(target),"rb") as wav:
            rate=wav.getframerate();total=wav.getnframes()/rate
    except (ValueError,EOFError,RuntimeError) as exc:
        raise AudioRuntimeError("CC0 WAV native metadata check failed") from exc
    if total<minimum_seconds:
        raise AudioRuntimeError("CC0 audio shorter than FilmCraft edit")
    result["audio_path"]=str(target)
    result["audio_sha256"]=hashlib.sha256(audio).hexdigest()
    result["audio_bytes"]=len(audio)
    result["duration_seconds"]=round(total,3)
    result["filmcraft_rights"]={
       "human_verified":True, # Approved primary Commons CC0 page reviewed for this curated recording
       "license":"CC0","creator":PAGE,
       "original_source_url":PAGE,"original_license_url":LICENSE,
       "audio_sha256":result["audio_sha256"],
       "source_primary_sha1":CURATED_SHA1}
    result["audio_native_probe_required"]=True
    result["audio_mixed_by"]="FilmCraft"
    return result
