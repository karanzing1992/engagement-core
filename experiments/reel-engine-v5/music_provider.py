#!/usr/bin/env python3
"""V5 openly licensed third-party music gateway (Openverse + verified local ingest).

- Search openly-licensed audio metadata via public Openverse API (read-only).
- Licensing remains UNVERIFIED until original source rights evidence is supplied.
- Once reviewed and stored in provenance JSON, mix actual pre-existing recording.
- No synthetic/composed soundtracks, external raw video uploads, arbitrary URL
  downloads, unreviewed attribution, or publishing are implemented here.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

SEARCH_URL="https://api.openverse.org/v1/audio/"
ALLOWED_LICENSE={"cc0","pdm","by"}
CC_URL_BASE="https://creativecommons.org/"
MAX_RESULTS=12
ID_PATTERN=re.compile(r"^[0-9a-fA-F-]{30,40}$")


class LicenseError(ValueError):
    pass


def is_https(value):
    try:
        u=urllib.parse.urlsplit(value)
        return u.scheme=="https" and bool(u.hostname) and not u.username
    except ValueError:
        return False


def candidate(item):
    """Normalize source metadata; provider's claim is NOT legal verification."""
    if not isinstance(item,dict):
        return None
    license_name=str(item.get("license","")).lower().strip()
    if license_name not in ALLOWED_LICENSE:
        return None
    track_id=item.get("id","")
    if not isinstance(track_id,str) or not ID_PATTERN.fullmatch(track_id):
        return None
    orig=item.get("foreign_landing_url","")
    license_url=item.get("license_url","")
    media_url=item.get("url","")
    if not (is_https(orig) and is_https(license_url) and is_https(media_url)):
        return None
    if license_name=="by" and not license_url.startswith(CC_URL_BASE+"licenses/by/"):
        return None
    if license_name=="cc0" and not license_url.startswith(CC_URL_BASE+"publicdomain/zero/"):
        return None
    if license_name=="pdm" and not license_url.startswith(CC_URL_BASE+"publicdomain/mark/"):
        return None
    title=str(item.get("title") or "").strip()
    creator=str(item.get("creator") or "").strip()
    if not title or not creator:
        return None
    return {
        "source":"Openverse", "id":track_id,"title":title[:200],"creator":creator[:120],
        "license":license_name,"license_url":license_url,
        "license_version":str(item.get("license_version") or "")[:12],
        "original_source_page":orig,"source_media_url":media_url,
        "provider":str(item.get("provider") or "")[:90],
        "attribution":str(item.get("attribution") or "")[:1000],
        "duration_seconds":item.get("duration"),
        "commercial_use_candidate":True,
        "source_license_independently_verified":False,
        "approved_for_final_render":False,
        "media_downloaded":False,
        "verification_note":"Review the original license page and composer rights; indexes may be incorrect."
    }


def search(query,limit=6,*,opener=None):
    if not isinstance(query,str) or not 1<=len(query.strip())<=180:
        raise ValueError("Music search query must be 1..180 characters")
    if not 1<=limit<=MAX_RESULTS:
        raise ValueError("Music discovery limited to 1..12 suggestions per query")
    qs=urllib.parse.urlencode({"q":query,"license":"cc0,by,pdm",
                                "page_size":limit,"page":1,"category":"music",
                                "mature":"false","filter_dead":"true"})
    url=SEARCH_URL+"?"+qs
    if not url.startswith(SEARCH_URL+"?"):
        raise ValueError("Disallowed API host")
    req=urllib.request.Request(url,headers={
        "User-Agent":"MAD-ReelEngine-V5/1.0 (license-aware discovery; no scraping)",
        "Accept":"application/json"})
    client=opener or urllib.request.urlopen
    try:
        with client(req,timeout=20) as f:
            body=f.read(500001)
    except (urllib.error.HTTPError,urllib.error.URLError,TimeoutError):
        raise LicenseError("Openverse API unavailable; no unlicensed fallback") from None
    if len(body)>500000:
        raise LicenseError("Openverse metadata response too large")
    data=json.loads(body.decode("utf-8"))
    if not isinstance(data.get("results"),list):
        raise LicenseError("Malformed Openverse metadata response")
    tracks=[candidate(x) for x in data["results"]]
    return {"provider":"openverse","query":query,"open_api":True,
            "candidates":[x for x in tracks if x is not None],
            "rights_status":"DISCOVERY_ONLY_UNVERIFIED",
            "downloaded_files":0,"composed_audio":False}


def read_evidence(evidence_path, track):
    """Manual independent verification, retained as an audit file.
    A search result alone is NEVER permission to reuse a recording.
    """
    data=json.loads(Path(evidence_path).read_text(encoding="utf-8"))
    if data.get("reviewer_confirmed_rights") is not True:
        raise LicenseError("Rights reviewer has not approved track")
    if data.get("original_source_page") != track.get("original_source_page"):
        raise LicenseError("Evidence source page mismatch")
    if data.get("license_url") != track.get("license_url"):
        raise LicenseError("Evidence license differs from search metadata")
    if data.get("track_id") != track.get("id"):
        raise LicenseError("Evidence track ID mismatch")
    if track.get("license") not in ALLOWED_LICENSE:
        raise LicenseError("License not in safe commercial/editable set")
    if not is_https(data.get("source_license_proof_url","")):
        raise LicenseError("Original source license proof URL required")
    if not isinstance(data.get("reviewed_by"),str) or len(data["reviewed_by"])<2:
        raise LicenseError("Reviewer identity required")
    if not isinstance(data.get("reviewed_on"),str) or len(data["reviewed_on"])<10:
        raise LicenseError("Review date required")
    if track["license"]=="by":
        if not data.get("attribution_approved"):
            raise LicenseError("CC BY requires attribution")
    return data


def sha256_file(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()


def verify_audio(path,runner=None):
    if not Path(path).is_file() or Path(path).stat().st_size<1000:
        raise LicenseError("Audio file missing/empty")
    run=runner or subprocess.run
    res=run(["ffprobe","-v","error","-show_entries",
             "stream=codec_type:format=duration","-of","json",str(path)],
            capture_output=True,text=True,timeout=20,check=True)
    d=json.loads(res.stdout)
    if not any(s.get("codec_type")=="audio" for s in d.get("streams",[])):
        raise LicenseError("File does not contain audio")
    duration=float(d["format"]["duration"])
    if not 1.0<=duration<=7200:
        raise LicenseError("Unsupported audio duration")
    return duration


def ingest(track_json,evidence_json,local_audio,out_dir):
    """No network download. User supplies a reviewed, original-source file."""
    track=json.loads(Path(track_json).read_text(encoding="utf-8"))
    if "id" not in track or track.get("license") not in ALLOWED_LICENSE:
        raise LicenseError("Invalid selected music record")
    evidence=read_evidence(evidence_json,track)
    original=Path(local_audio)
    duration=verify_audio(original)
    output=Path(out_dir);output.mkdir(parents=True,exist_ok=True)
    suffix=original.suffix.lower()
    if suffix not in {".mp3",".wav",".ogg",".flac",".m4a",".opus"}:
        raise LicenseError("Unsupported audio extension")
    stored=output/("approved_audio"+suffix)
    shutil.copy2(original,stored)
    digest=sha256_file(stored)
    credit=(
      "Music: "+track["title"]+" — "+track["creator"]+"\n"
      +"Original track: "+track["original_source_page"]+"\n"
      +"License: "+track["license"].upper()+" "+track["license_url"]+"\n"
      +"Changes: may be trimmed, faded, normalized and/or volume balanced.\n"
      +"License independently checked: "+evidence["source_license_proof_url"]+"\n"
      +"Reviewed: "+evidence["reviewed_by"]+" "+evidence["reviewed_on"]+"\n")
    (output/"MUSIC_CREDITS.txt").write_text(credit,encoding="utf8")
    manifest={"license_verified_by_reviewer":True,"approval_for_private_editing":True,
              "track":track,"evidence":evidence,"audio_filename":stored.name,
              "audio_sha256":digest,"duration_seconds":duration,
              "attribution_file":"MUSIC_CREDITS.txt",
              "original_recording":True,"composed_audio":False}
    (output/"music_provenance.json").write_text(
      json.dumps(manifest,indent=2,ensure_ascii=False)+"\n",encoding="utf8")
    return manifest


def mix(video,approved_audio_dir,outfile,*,duration=None):
    """Final music is a real approved recording, not a generated soundtrack."""
    origin=Path(approved_audio_dir)
    m=json.loads((origin/"music_provenance.json").read_text(encoding="utf8"))
    if m.get("license_verified_by_reviewer") is not True:
        raise LicenseError("Track rights were not approved")
    if m.get("composed_audio") is not False:
        raise LicenseError("Generated music forbidden by V5 policy")
    audio=origin/m["audio_filename"]
    if sha256_file(audio)!=m["audio_sha256"]:
        raise LicenseError("Music asset hash mismatch")
    if not Path(video).is_file():
        raise LicenseError("Input video missing")
    target=Path(outfile)
    if target.resolve()==Path(video).resolve():
        raise LicenseError("Cannot overwrite original video")
    target.parent.mkdir(parents=True,exist_ok=True)
    dur=duration
    if dur is None:
        probe=subprocess.run(["ffprobe","-v","error","-show_entries",
                              "format=duration","-of","default=nokey=1:noprint_wrappers=1",str(video)],
                             text=True,capture_output=True,check=True,timeout=18)
        dur=float(probe.stdout.strip())
    if not (1.0<=float(dur)<=180.0):
        raise LicenseError("Music mix duration outside approved batch profile")
    fade_start=max(0.0,float(dur)-1.1)
    probe_audio=subprocess.run(["ffprobe","-v","error","-select_streams","a",
        "-show_entries","stream=index","-of","json",str(video)],
        capture_output=True,text=True,timeout=18,check=True)
    has_source_ambience=bool(json.loads(probe_audio.stdout).get("streams",[]))
    music_chain="volume=0.62,afade=t=out:st="+str(round(fade_start,3))+":d=1.1"
    if has_source_ambience:
        # Never discard the original source ambience: mix it under the licensed
        # recording, with a final loudness ceiling. Only after source rights QA.
        mix_filter=("[0:a:0]volume=0.3[amb];[1:a:0]"+music_chain+
                    "[mus];[amb][mus]amix=inputs=2:duration=first:normalize=0,"
                    "loudnorm=I=-16:TP=-1.5:LRA=11[outa]")
    else:
        mix_filter="[1:a:0]"+music_chain+",loudnorm=I=-16:TP=-1.5:LRA=11[outa]"
    args=["ffmpeg","-y","-hide_banner","-loglevel","error",
          "-i",str(video),"-stream_loop","-1","-i",str(audio),
          "-filter_complex",mix_filter,"-map","0:v:0","-map","[outa]",
          "-t",str(round(float(dur),3)),"-c:v","copy","-c:a","aac",
          "-b:a","160k","-movflags","+faststart",str(target)]
    subprocess.run(args,check=True,timeout=150)
    return {"music_provenance_verified":True,"music_track":m["track"]["title"],
            "video":str(target),"video_sha256":sha256_file(target),
            "composed_audio":False,"published":False,"original_ambience_preserved":has_source_ambience}


def main():
    p=argparse.ArgumentParser()
    sub=p.add_subparsers(dest="cmd",required=True)
    s=sub.add_parser("search")
    s.add_argument("--query",required=True)
    s.add_argument("--limit",type=int,default=6)
    s.add_argument("--output",required=True)
    i=sub.add_parser("ingest")
    i.add_argument("--track",required=True)
    i.add_argument("--evidence",required=True)
    i.add_argument("--audio",required=True)
    i.add_argument("--output-dir",required=True)
    m=sub.add_parser("mix")
    m.add_argument("--video",required=True)
    m.add_argument("--music-dir",required=True)
    m.add_argument("--output",required=True)
    args=p.parse_args()
    try:
        if args.cmd=="search":
            data=search(args.query,args.limit)
            out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True)
            out.write_text(json.dumps(data,indent=2,ensure_ascii=False)+"\n")
        elif args.cmd=="ingest":
            data=ingest(args.track,args.evidence,args.audio,args.output_dir)
        else:
            data=mix(args.video,args.music_dir,args.output)
        print(json.dumps({"status":"PASS","data":data},ensure_ascii=False))
    except (LicenseError,ValueError,OSError,subprocess.SubprocessError,KeyError) as exc:
        print(json.dumps({"status":"BLOCKED","reason":str(exc)[:240]}),
              file=sys.stderr)
        return 2
    return 0

if __name__=="__main__":
    sys.exit(main())
