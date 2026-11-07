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
import time
from datetime import datetime,timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
import re
import urllib.error
import urllib.parse
import urllib.request

MAX_BYTES=16*1024*1024
MAX_JSON=320000
LICENSE_ROOT="https://creativecommons.org/"
EXT={".mp3",".ogg",".opus",".wav",".flac",".m4a"}
# A contact-identifiable User-Agent is required by Wikimedia's robot policies.
USER_AGENT="MAD-ReelEngine/1.1 (https://github.com/karanzing1992/engagement-core; audio provenance verification) Python-urllib"
# Transfer at most four serial ranges for the existing 16 MiB admission limit.
MEDIA_CHUNK=4*1024*1024
MAX_SEGMENT_RETRIES=2
MAX_RETRY_WAIT=30
PACING_SECONDS=0.35

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
        "User-Agent":USER_AGENT,
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

def _retry_after(value:str|None,attempt:int)->float:
    """Honor Retry-After as seconds or HTTP-date; fail closed on long waits."""
    if value:
        try:
            delay=float(value.strip())
        except (TypeError,ValueError):
            try:
                when=parsedate_to_datetime(value)
                if when.tzinfo is None:
                    when=when.replace(tzinfo=timezone.utc)
                delay=(when-datetime.now(timezone.utc)).total_seconds()
            except (TypeError,ValueError,OverflowError):
                delay=5*(2**attempt)
        return max(0.0,delay)
    return float(5*(2**attempt))

def _download_media(meta:dict,output:Path,*,opener=None,sleeper=None)->tuple[str,str]:
    """Download one checked Wikimedia original using *sequential* ranged reads.

    The original API's SHA1 is mandatory: computing our own SHA256 alone would
    fingerprint corruption, not authenticate bytes against the source.
    """
    size=meta["size"]
    expected=meta["sha1"]
    _url(meta["media_url"],"upload.wikimedia.org")
    if not 1024<=size<=MAX_BYTES or not re.fullmatch(r"[a-z0-9]{20,40}",expected):
        raise AutoLicenseBlocked("MEDIA_ORIGINAL_DIGEST_INVALID")
    client=opener or urllib.request.build_opener(_NoRedirect()).open
    pause=time.sleep if sleeper is None else sleeper
    hashed=hashlib.sha256()
    source_hash=hashlib.sha1()
    offset=0
    strong_etag=None
    with output.open("xb") as target:
        while offset<size:
            end=min(size-1,offset+MEDIA_CHUNK-1)
            expected_bytes=end-offset+1
            headers={"User-Agent":USER_AGENT,"Accept":"audio/*",
                     "Range":f"bytes={offset}-{end}"}
            if strong_etag and offset:
                headers["If-Range"]=strong_etag
            for attempt in range(MAX_SEGMENT_RETRIES+1):
                request=urllib.request.Request(meta["media_url"],headers=headers)
                try:
                    with client(request,timeout=20) as response:
                        if hasattr(response,"geturl") and response.geturl()!=meta["media_url"]:
                            raise AutoLicenseBlocked("SOURCE_REDIRECT_BLOCKED")
                        status=getattr(response,"status",200)
                        h=getattr(response,"headers",{}) or {}
                        # 200 is only acceptable for the initial, entire file;
                        # never append a full response to already stored segments.
                        if status==206:
                            found=re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)",
                                               str(h.get("Content-Range","")))
                            if not found or tuple(map(int,found.groups()))!=(offset,end,size):
                                raise AutoLicenseBlocked("MEDIA_CONTENT_RANGE_MISMATCH")
                            cap=expected_bytes
                        elif status==200 and offset==0:
                            cap=size
                        else:
                            raise AutoLicenseBlocked("MEDIA_RANGE_NOT_SUPPORTED")
                        length=h.get("Content-Length")
                        if length is not None:
                            try:
                                if int(length)!=cap:raise AutoLicenseBlocked("MEDIA_LENGTH_MISMATCH")
                            except ValueError:
                                raise AutoLicenseBlocked("MEDIA_LENGTH_MISMATCH") from None
                        etag=h.get("ETag")
                        if offset==0 and isinstance(etag,str) and etag.startswith('"') and etag.endswith('"'):
                            strong_etag=etag
                        data=response.read(cap+1)
                        if len(data)!=cap:
                            raise AutoLicenseBlocked("MEDIA_LENGTH_MISMATCH")
                        target.write(data)
                        hashed.update(data)
                        source_hash.update(data)
                        offset+=len(data)
                        if status==200:
                            offset=size
                        break
                except urllib.error.HTTPError as error:
                    if error.code not in (429,503):
                        raise AutoLicenseBlocked("SOURCE_UNAVAILABLE") from None
                    if attempt>=MAX_SEGMENT_RETRIES:
                        raise AutoLicenseBlocked("SOURCE_RATE_LIMITED") from None
                    delay=_retry_after((error.headers or {}).get("Retry-After"),attempt)
                    if delay>MAX_RETRY_WAIT:
                        raise AutoLicenseBlocked("SOURCE_RETRY_AFTER_TOO_LONG") from None
                    pause(delay)
                except AutoLicenseBlocked:
                    raise
                except Exception:
                    raise AutoLicenseBlocked("SOURCE_UNAVAILABLE") from None
            if offset<size:
                # One requester, short politeness spacing, never parallel ranges.
                pause(PACING_SECONDS)
    # MediaWiki's imageinfo SHA1 is base36 (some deployments use hex).
    actual=source_hash.hexdigest()
    if re.fullmatch(r"[0-9a-f]{40}",expected):
        good=actual==expected
    else:
        good=int(actual,16)==int(expected,36)
    if not good:
        raise AutoLicenseBlocked("MEDIA_ORIGINAL_SHA1_MISMATCH")
    return hashed.hexdigest(),actual

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
        "prop":"imageinfo|categories","cllimit":"max",
        "iiprop":"url|mediatype|extmetadata|mime|size|sha1"})
    api="https://commons.wikimedia.org/w/api.php?"+params
    _url(api,"commons.wikimedia.org")
    try:
        obj=json.loads(_request(api,opener=opener))
        pages=list(obj["query"]["pages"].values())
        if len(pages)!=1 or pages[0].get("title","").replace("_"," ")!=title:
            raise AutoLicenseBlocked("SOURCE_FILE_MISMATCH")
        # Commons originals imported from other platforms can claim CC BY before
        # an independent Commons reviewer confirms the upstream license.
        # Read hidden review categories in the *same* canonical API response.
        # No categories / incomplete category pagination is not proof of review.
        categories=pages[0].get("categories")
        if not isinstance(categories,list) or not categories or "continue" in obj:
            raise AutoLicenseBlocked("SOURCE_LICENSE_REVIEW_UNKNOWN")
        if any(re.search(r"license review needed|copyright violation|license dispute|possibly unfree",
                         str(cat.get("title","")),re.I) for cat in categories
               if isinstance(cat,dict)):
            raise AutoLicenseBlocked("SOURCE_LICENSE_REVIEW_PENDING")
        # Automated release requires affirmative evidence of first-party authorship,
        # not merely a third-party catalog's CC label. Existing owner-reviewed
        # private library remains separately eligible under its reviewer receipts.
        if not any(str(cat.get("title","")).casefold()=="category:self-published work"
                   for cat in categories if isinstance(cat,dict)):
            raise AutoLicenseBlocked("SOURCE_AUTHORSHIP_REVIEW_REQUIRED")
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
    original_sha1=info.get("sha1")
    if not isinstance(original_sha1,str) or not re.fullmatch(r"[a-z0-9]{20,40}",original_sha1):
        raise AutoLicenseBlocked("MEDIA_ORIGINAL_DIGEST_MISSING")
    return {"source_page":orig.split("?",1)[0],"title":title[5:][:150],
            "creator":creator,"media_url":original,"license":lic,
            "license_url":label,"size":size,"sha1":original_sha1,
            "source_kind":"wikimedia_commons"}

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
        digest,original_sha1=_download_media(meta,output,opener=opener)
        if output.stat().st_size!=meta["size"]:
            raise AutoLicenseBlocked("MEDIA_LENGTH_MISMATCH")
        if probe is None:
            raise AutoLicenseBlocked("AUDIO_PROBE_REQUIRED")
        p=probe(output,require_video=False)
        if float(p["duration"])<float(required_seconds)-.1:
            raise AutoLicenseBlocked("AUTO_MUSIC_TOO_SHORT")
        lic={"by":"CC BY","cc0":"CC0","pdm":"PDM"}[meta["license"]]
        credit=(f'{meta["title"]} — {meta["creator"]} | {lic} | '
                f'{meta["license_url"]} | {meta["source_page"]} | '
                'Adaptation: excerpted, synchronized to video, mixed and audio-level adjusted.')
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
             "sha256":digest,"original_sha1":original_sha1,
              "transfer_method":"serial_http_range", "attribution_required":meta["license"]=="by",
             "credit_text":credit,"attribution_in_manifest":True,
             "published":False}}
    except Exception:
        output.unlink(missing_ok=True)
        raise
