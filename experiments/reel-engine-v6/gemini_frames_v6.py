"""Constrain source-grounded Gemini image parts to native FilmCraft JPEGs."""
from pathlib import Path
import base64
import hashlib

class FrameRejected(ValueError): pass

def inline_parts(shots,frames):
    if not frames:return []
    if not isinstance(frames,list) or len(frames)>3:
        raise FrameRejected("Maximum three source frames")
    ids={x["id"] for x in shots}
    parts=[]
    for f in frames:
        if not isinstance(f,dict) or f.get("shot_id") not in ids or f.get("generated_by")!="FilmCraft.file.exportFrame":
            raise FrameRejected("Not a verified native FilmCraft frame")
        p=Path(f.get("path",""))
        if p.suffix.lower() not in (".jpg",".jpeg") or not p.is_file() or p.is_symlink():
            raise FrameRejected("Native private source JPEG missing")
        data=p.read_bytes()
        if not 1024<=len(data)<=60000 or data[:2]!=bytes((255,216)) or data[-2:]!=bytes((255,217)):
            raise FrameRejected("Not a bounded JPEG frame")
        if hashlib.sha256(data).hexdigest()!=f.get("sha256"):
            raise FrameRejected("Private image digest mismatch")
        sec=f.get("seconds")
        if not isinstance(sec,(float,int)) or not 0<=sec<=480:
            raise FrameRejected("Untrusted frame timestamp")
        parts.append({"text":"Native FilmCraft sampled frame for shot "+f["shot_id"]+" at "+str(round(sec,3))+" seconds. Only describe what is visible."})
        parts.append({"inline_data":{"mime_type":"image/jpeg","data":base64.b64encode(data).decode("ascii")}})
    return parts
