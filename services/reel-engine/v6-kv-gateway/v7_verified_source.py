#!/usr/bin/env python3
"""MAD V7: independently recheck Commons music source then use automatically.

Owner policy: do not require a person to approve every publicly reusable song.
Not a legal guarantee: fail closed on mismatched / uncertain source licenses.
Only immutable file pages at commons.wikimedia.org are auto-admitted; Openverse
may index those files. Other hosts remain metadata-only pending provider adapters.
All downloaded files remain in the already-private ephemeral GitHub runner.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re
import urllib.parse
import urllib.request

MAX_BYTES=16*1024*1024
MAX_JSON=320000
LICENSE_ROOT="https://creativecommons.org/"
EXT={".mp3",".ogg",".opus",".wav",".flac",".m4a"}

class AutoLicenseBlocked(ValueError):
    pass

def _url(url:str,host:str)->str:
    if not isinstance(url,str) or len(url)>1700:
        raise AutoLicenseBlocked("SOURCE_URL_INVALID")
    p=urllib.parse.urlsplit(url)
    if p.scheme!="https" or p.hostname!=host or p.port not in (None,443) or p.username or p.password or p.fragment:
        raise AutoLicenseBlocked("SOURCE_HOST_DENIED")
    return p.path

def _request(url:str,*,opener=None,cap:int=MAX_JSON)->bytes:
    req=urllib.request.Request(url,headers={
        "User-Agent":"MAD-ReelEngine-V7-licensed-source/1.0 (Commons attribution audit)",
        "Accept":"application/json, audio/*"})
    if opener is None:
        # Avoid credentials and unexpected off-host redirects when fetching bytes.
        client=urllib.request.build_opener(_NoRedirect()).open
    else:
        client=opener
    try:
        with client(req,timeout=20) as res:
            if hasattr(res,"geturl") and res.geturl()!=url:
                raise AutoLicenseBlocked("SOURCE_REDIRECT_BLOCKED")
            size=(getattr(res,"headers",{}) or {}).get("Content-Length")
            if size and int(size)>cap:
                raise AutoLicenseBlocked("SOURCE_TOO_LARGE")
            raw=res.read(cap+1)
    except AutoLicenseBlocked:
        raise
    except Exception:
        raise AutoLicenseBlocked("SOURCE_UNAVAILABLE") from None
    if len(raw)>cap:
        raise AutoLicenseBlocked("SOURCE_TOO_LARGE")
    return raw

class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        raise AutoLicenseBlocked("SOURCE_REDIRECT_BLOCKED")

def _license(info:dict)->str:
    ext=info.get("extmetadata") or {}
    def val(key:str)->str:
        item=ext.get(key) or {}
        return item.get("value","") if isinstance(item,dict) else ""
    label=val("LicenseShortName").strip().lower()
    url=val("LicenseUrl").strip()
    if label.startswith("cc0") and url.startswith(LICENSE_ROOT+"publicdomain/zero/"):
        return "cc0"
    if label.startswith("public domain") and url.startswith(LICENSE_ROOT+"publicdomain/mark/"):
        return "pdm"
    if re.fullmatch(r"cc by (?:2\.0|2\.5|3\.0|4\.0)(?: international)?",label) and \
            url.startswith(LICENSE_ROOT+"licenses/by/"):
        return "by"
    raise AutoLicenseBlocked("SOURCE_LICENSE_NOT_AUTOMATICALLY_ELIGIBLE")

def _source_meta(track:dict,opener=None)->dict:
    if not isinstance(track,dict) or track.get("license") not in {"cc0","pdm","by"}:
        raise AutoLicenseBlocked("CATALOG_LICENSE_DENIED")
    orig=track.get("original_source_page") or track.get("source_page") or ""
    path=_url(orig,"commons.wikimedia.org")
    if not path.startswith("/wiki/File:") or not path[len("/wiki/File:"):]:
        raise AutoLicenseBlocked("COMMONS_FILE_PAGE_REQUIRED")
    title=urllib.parse.unquote(path.split("/wiki/",1)[1]).replace("_"," ")
    if "/" in title or len(title)>230 or not title.startswith("File:"):
        raise AutoLicenseBlocked("COMMONS_TITLE_INVALID")
    params=urllib.parse.urlencode({
        "action":"query","format":"json","titles":title,
        "prop":"imageinfo","iiprop":"url|mediatype|extmetadata|mime|size"})
    api="https://commons.wikimedia.org/w/api.php?"+params
    _url(api,"commons.wikimedia.org")
    try:
        obj=json.loads(_request(api,opener=opener))
        pages=list(obj["query"]["pages"].values())
        if len(pages)!=1 or pages[0].get("title","").replace("_"," ")!=title:
            raise AutoLicenseBlocked("SOURCE_FILE_MISMATCH")
        info=pages[0]["imageinfo"][0]
    except (KeyError,IndexError,ValueError,TypeError) as exc:
        if isinstance(exc,AutoLicenseBlocked):raise
        raise AutoLicenseBlocked("COMMONS_METADATA_INVALID") from None
    if info.get("mediatype")!="AUDIO":
        raise AutoLicenseBlocked("SOURCE_NOT_AUDIO")
    lic=_license(info)
    if lic!=track["license"]:
        raise AutoLicenseBlocked("SOURCE_LICENSE_CONFLICT")
    ext=info.get("extmetadata") or {}
    label=(ext.get("LicenseUrl") or {}).get("value","")
    if label!=track.get("license_url"):
        raise AutoLicenseBlocked("SOURCE_LICENSE_URL_CONFLICT")
    original=info.get("url","")
    media_path=_url(original,"upload.wikimedia.org")
    if not media_path.startswith("/wikipedia/commons/") or not any(media_path.lower().endswith(s) for s in EXT):
        raise AutoLicenseBlocked("MEDIA_PATH_DENIED")
    # The V5 search URL may include tracking queries; compare canonical path.
    proposed=track.get("source_media_url")
    if proposed and _url(proposed,"upload.wikimedia.org")!=media_path:
        raise AutoLicenseBlocked("MEDIA_SOURCE_MISMATCH")
    artist=(ext.get("Artist") or {}).get("value","")
    if not isinstance(artist,str) or not artist.strip():
        raise AutoLicenseBlocked("SOURCE_CREATOR_MISSING")
    # Preserve punctuation but strip HTML for TASL caption attribution.
    from html import unescape
    creator=unescape(re.sub(r"<[^>]*>"," ",artist)).strip()
    if not creator or len(creator)>150 or "requires verification" in creator.lower():
        raise AutoLicenseBlocked("SOURCE_CREATOR_UNVERIFIED")
    restriction=" ".join(str((ext.get(k) or {}).get("value","")) for k in ("Restrictions","ImageDescription"))
    if re.search(r"copyright violation|deletion request|non.?commercial|no.?derivative|rights reserved",restriction,re.I):
        raise AutoLicenseBlocked("SOURCE_EXPLICIT_RESTRICTION")
    size=info.get("size")
    if type(size) is not int or not 1024<=size<=MAX_BYTES:
        raise AutoLicenseBlocked("MEDIA_SIZE_NOT_ELIGIBLE")
    return {"source_page":orig.split("?",1)[0],"title":title[5:][:150],
            "creator":creator,"media_url":original,"license":lic,
            "license_url":label,"size":size,"source_kind":"wikimedia_commons"}

def admit(track:dict,workdir:Path,required_seconds:float,*,opener=None,probe=None)->dict:
    """Machine-check source + bytes: an owner-authorized *automatic* admission.

    Caller supplies ffmpeg_editor.probe. Never call this from synthetic job mode.
    """
    meta=_source_meta(track,opener=opener)
    path=Path(workdir)
    if not path.is_dir():
        raise AutoLicenseBlocked("PRIVATE_WORKDIR_MISSING")
    ext=Path(urllib.parse.urlsplit(meta["media_url"]).path).suffix.lower()
    if ext not in EXT:
        raise AutoLicenseBlocked("MEDIA_EXTENSION_DENIED")
    output=path/("source-auto-music"+ext)
    # Never save files outside this job directory.
    if output.exists():
        raise AutoLicenseBlocked("AUTO_AUDIO_ALREADY_EXISTS")
    try:
        raw=_request(meta["media_url"],opener=opener,cap=MAX_BYTES)
        if len(raw)!=meta["size"]:
            raise AutoLicenseBlocked("MEDIA_LENGTH_MISMATCH")
        output.write_bytes(raw)
        if probe is None:
            raise AutoLicenseBlocked("AUDIO_PROBE_REQUIRED")
        p=probe(output,require_video=False)
        if float(p["duration"])<float(required_seconds)-.1:
            raise AutoLicenseBlocked("AUTO_MUSIC_TOO_SHORT")
        digest=hashlib.sha256(raw).hexdigest()
        lic={"by":"CC BY","cc0":"CC0","pdm":"PDM"}[meta["license"]]
        credit=f'{meta["title"]} — {meta["creator"]} | {lic} | {meta["license_url"]} | {meta["source_page"]}'
        if len(credit)>850:
            raise AutoLicenseBlocked("CREDIT_TOO_LONG")
        rights={"human_verified":False,"automatic_source_verified":True,
           "verification_method":"commons_api_live",
           "license":lic,"original_source_url":meta["source_page"],
           "source_license_proof_url":meta["source_page"],
           "original_license_url":meta["license_url"],
           "attribution_approved":bool(credit),
           "credit_text":credit}
        return {"path":output,"sha256":digest,"rights":rights,
           "provenance":{"mode":"source_auto_verified","automatic_source_verified":True,
             "verification_method":"commons_api_live","source":meta["source_page"],
             "media_url":meta["media_url"],"title":meta["title"],"creator":meta["creator"],
             "license":meta["license"],"license_url":meta["license_url"],
             "sha256":digest,"attribution_required":meta["license"]=="by",
             "credit_text":credit,"attribution_in_manifest":True,
             "published":False}}
    except Exception:
        output.unlink(missing_ok=True)
        raise
