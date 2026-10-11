"""Low-cost, one-shot private WordPress -> GitHub Actions -> WordPress Reel worker.

Runs only on a temporary GitHub runner. Authenticates with the existing DFG
deployment secret via a separate HMAC context. Sends no raw videos to public
GitHub artifacts, logs, CDN URLs, or social channels.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import shutil
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from tempfile import TemporaryDirectory

from multi_renderer import render_multiple, probe_media
from verified_logo import overlay_verified_logo, SHA256

SITE = os.environ.get("MRS_SITE_URL","https://mokshagoa.com").rstrip("/")
EXPECTED_HOST = urllib.parse.urlsplit(SITE).hostname
API = SITE + "/wp-json/wp-control/v1/media-studio/ingest/"
CHUNK = 4 * 1024 * 1024
SOURCE_MAX = 800 * 1024 * 1024


def token_from_existing_hook() -> str:
    raw=os.environ.get("MOKSHA_DFG_ENGAGEMENT_CORE_URL","")
    p=urllib.parse.urlsplit(raw)
    if p.scheme!="https" or p.hostname!=EXPECTED_HOST:
        raise RuntimeError("Stored first-party deployment URL must match the configured site")
    secret=urllib.parse.parse_qs(p.query).get("secret",[""])[0]
    if len(secret)<20: raise RuntimeError("Existing deployment secret is missing")
    return hmac.new(secret.encode(),b"mrs-media-queue-v1",hashlib.sha256).hexdigest()


class WP:
    def __init__(self, token: str):
        self.token=token

    def call(self, path: str, *, method: str="GET", json_data=None, data=None, digest=None) -> bytes:
        if json_data is not None:
            data=json.dumps(json_data,separators=(",",":")).encode()
        headers={"X-WP-Control-Media-Token":self.token,
                 "User-Agent":"Moksha-Reel-Worker/1.0"}
        if json_data is not None:
            headers["Content-Type"]="application/json"
        elif digest is not None:
            headers["Content-Type"]="application/octet-stream"
            headers["X-Chunk-SHA256"]=digest
        url=API+path.lstrip("/")
        last=None
        for attempt in range(4):
            try:
                request=urllib.request.Request(url,data=data,headers=headers,method=method)
                with urllib.request.urlopen(request,timeout=90) as response:
                    # Individual downloads are at most 4 MiB. Do not return a 231 MB string.
                    return response.read(CHUNK+2048)
            except Exception as exc:
                last=exc
                if attempt<3:time.sleep(2**attempt)
        raise RuntimeError("Private WordPress transfer failed after retries") from last

    def j(self, path: str, method="GET", data=None) -> dict:
        result=json.loads(self.call(path,method=method,json_data=data))
        if not result.get("ok",False):
            raise RuntimeError("WordPress rejected a private upload operation")
        return result


def download_sources(wp: WP, record: dict, folder: Path) -> list[Path]:
    inputs=[]
    ident=record["id"]
    if not isinstance(ident,str) or len(ident)!=32 or any(x not in "0123456789abcdef" for x in ident):
        raise ValueError("Unrecognized upload identifier")
    files=record["files"]
    if not 1<=len(files)<=8: raise ValueError("Invalid video count")
    for index, meta in enumerate(files):
        size=int(meta["size"])
        expected=str(meta["sha256"]).lower()
        count=int(meta["parts"])
        if not 1024 <= size <= SOURCE_MAX or count!=(size+CHUNK-1)//CHUNK:
            raise ValueError("Implausible source size/chunk count")
        if len(expected)!=64 or not all(x in "0123456789abcdef" for x in expected):
            raise ValueError("Source integrity record is missing")
        ext=Path(str(meta["name"])).suffix.lower()
        if ext not in (".mp4",".mov",".m4v"):raise ValueError("Unsupported clip type")
        target=folder/f"source-{index}{ext}"
        hashstream=hashlib.sha256()
        written=0
        with target.open("xb") as f:
            for part in range(count):
                payload=wp.call(f"{ident}/source-part/{index}/{part}")
                part_expected=min(CHUNK,size-part*CHUNK)
                if len(payload)!=part_expected:
                    raise ValueError(f"Source {index+1} part {part} changed size during transfer")
                hashstream.update(payload)
                f.write(payload)
                written+=len(payload)
        if written!=size or not hmac.compare_digest(hashstream.hexdigest(),expected):
            target.unlink(missing_ok=True)
            raise ValueError("Uploaded original SHA-256 failed integrity verification")
        probe_media(target)
        inputs.append(target)
        print(f"Verified private source {index+1}: {size} bytes, SHA-256 matches.",flush=True)
    return inputs


def upload_private_preview(wp: WP, ident: str, video: Path):
    total=video.stat().st_size
    if total> SOURCE_MAX:raise ValueError("Encoded output unexpectedly large")
    digest=hashlib.sha256()
    with video.open("rb") as f:
        for chunk in iter(lambda:f.read(CHUNK),b""):digest.update(chunk)
    sha=digest.hexdigest()
    wp.j(f"{ident}/render-start",method="POST",data={"size":total,"sha256":sha})
    with video.open("rb") as f:
        i=0
        while True:
            chunk=f.read(CHUNK)
            if not chunk:break
            result=json.loads(wp.call(f"{ident}/render-chunk/{i}",method="POST",
                                      data=chunk,digest=hashlib.sha256(chunk).hexdigest()))
            if not result.get("ok"):raise RuntimeError("WordPress failed to store private output chunk")
            i+=1
    done=wp.j(f"{ident}/render-finish",method="POST",data={})
    if done.get("status")!="preview_ready_private":
        raise RuntimeError("Cloud render was not accepted as private preview")
    print(f"Private final uploaded: {total} bytes, verified {sha[:14]}…, publishing disabled.",flush=True)


def process_session(wp: WP, record: dict):
    with TemporaryDirectory(prefix="moksha-reel-private-") as d:
        root=Path(d)
        originals=download_sources(wp,record,root)
        result=root/"cut-30s.mp4"
        work=root/"work"
        cfg={"target_seconds":float(record.get("target_seconds",30)),
             "width":720,"height":1280,"fps":25}
        summary=render_multiple(originals,result,cfg,work)
        # Only the byte-identical original from the official Drive source is allowed.
        mirror=Path(__file__).resolve().parents[2]/"assets/brand/moksha-logo-source.jpg"
        if not mirror.exists() or hashlib.sha256(mirror.read_bytes()).hexdigest()!=SHA256:
            raise RuntimeError("Approved official logo is absent or changed")
        cache=root/"verified-brand-assets"
        cache.mkdir()
        shutil.copy2(mirror,cache/"moksha-approved-master.jpg")
        final=root/"moksha-30-second-private-final.mp4"
        branding=overlay_verified_logo(result,final,brand="moksha",placement="reel",cache_dir=cache)
        output=probe_media(final)
        if not output["has_audio"] or abs(output["duration"]-cfg["target_seconds"])>0.28:
            raise RuntimeError("Final has incorrect duration/audio after official logo")
        if branding.get("logo",{}).get("sha256")!=SHA256:
            raise RuntimeError("Official logo provenance failed validation")
        print(f"Two-source private Reel rendered: {output['duration']:.2f}s, {output['width']}x{output['height']}",flush=True)
        upload_private_preview(wp,record["id"],final)
        return summary


def main():
    wp=WP(token_from_existing_hook())
    ready=wp.j("ready").get("sessions",[])
    if "--check" in sys.argv:
        # Cheap queue poll: no ffmpeg boot, no video download, no rerender.
        print(len(ready))
        return
    if not ready:
        print("No pending private uploads; no FFmpeg work, no GitHub artifact.",flush=True)
        return
    # Limit to one session/run for predictable CPU, memory, and retention.
    record=ready[0]
    process_session(wp,record)


if __name__=="__main__":
    main()
