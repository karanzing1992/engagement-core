#!/usr/bin/env python3
"""Bounded automated CC0 soundtrack discovery/ingest for owner-private FilmCraft."""
from __future__ import annotations
from pathlib import Path
import hashlib,json,ipaddress,re,socket,urllib.parse,urllib.request,os

API="https://api.openverse.org/v1/audio/"
USER_AGENT="MAD-V6-private-FilmCraft-CC0/1"
MAX_AUDIO=8*1024*1024

class AudioUnavailable(RuntimeError): pass

def public_https(u:str)->bool:
    try:
        p=urllib.parse.urlsplit(u)
        if p.scheme!="https" or not p.hostname or p.username or p.password or p.port not in (None,443):
            return False
        host=p.hostname.lower().strip(".")
        if host=="localhost" or host.endswith(".local") or host.endswith(".internal") or len(host)>200:
            return False
        try:
            return ipaddress.ip_address(host).is_global
        except ValueError:
            return bool(re.fullmatch(r"[a-z0-9.-]+",host)) and "." in host
    except (ValueError,TypeError):
        return False

class RedirectGuard(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        if not public_https(newurl):raise AudioUnavailable("Unsafe audio redirect")
        return super().redirect_request(req,fp,code,msg,headers,newurl)

def read_url(url,max_bytes=MAX_AUDIO,timeout=15):
    if not public_https(url):raise AudioUnavailable("Non-public or non-HTTPS music URL")
    request=urllib.request.Request(url,headers={"User-Agent":USER_AGENT,"Accept":"application/json, audio/*"})
    with urllib.request.build_opener(RedirectGuard()).open(request,timeout=timeout) as res:
        if not public_https(res.geturl()):raise AudioUnavailable("Untrusted audio redirect")
        length=res.headers.get("Content-Length")
        if length and int(length)>max_bytes:raise AudioUnavailable("Audio exceeds free-tier limit")
        data=res.read(max_bytes+1)
    if len(data)>max_bytes:raise AudioUnavailable("Audio exceeds free-tier limit")
    return data

def select_cc0(workdir:Path,query:str="ambient nature music",minimum_duration:float=3.0):
    if not 3<=minimum_duration<=120:raise AudioUnavailable("Invalid timeline duration")
    if not isinstance(query,str) or len(query)>100:raise AudioUnavailable("Invalid search")
    workdir.mkdir(mode=0o700,parents=True,exist_ok=True)
    params=urllib.parse.urlencode({"q":query,"license":"cc0","page_size":12})
    try:payload=json.loads(read_url(API+"?"+params,128000))
    except Exception as exc:raise AudioUnavailable("Openverse CC0 discovery unavailable") from exc
    for record in payload.get("results",[])[:12]:
        if not isinstance(record,dict) or record.get("license")!="cc0":continue
        license_url=record.get("license_url","")
        if not (isinstance(license_url,str) and license_url.startswith("https://creativecommons.org/publicdomain/zero/")):continue
        url=record.get("url","");page=record.get("foreign_landing_url","")
        if not public_https(url) or not public_https(page):continue
        duration=record.get("duration",0)
        if not isinstance(duration,(int,float)) or duration/1000<minimum_duration+.5:continue
        if isinstance(record.get("filesize"),int) and record["filesize"]>MAX_AUDIO:continue
        typ=str(record.get("filetype","")).lower().split("/")[-1]
        if typ not in ("wav","mp3","flac","ogg","oga","mpeg"):continue
        ext=".mp3" if typ in ("mp3","mpeg") else ".ogg" if typ=="oga" else "."+typ
        try:
            data=read_url(url)
            if len(data)<2048 or data[:10].lstrip().startswith(b"<"):continue
            path=workdir/("openverse-cc0"+ext)
            path.write_bytes(data);path.chmod(0o600)
            sha=hashlib.sha256(data).hexdigest()
            return {"path":path,"track_id":record.get("id"),"track_title":str(record.get("title",""))[:160],
              "creator":str(record.get("creator") or "Unknown")[:160],
              "license":"CC0","license_url":license_url,"source_url":page,
              "download_url":url,"audio_sha256":sha,"bytes":len(data),
              "license_check":"automatic_Openverse_CC0_metadata_only_not_independently_verified",
              "rights":{"human_verified":False,"automatic_cc0_metadata_checked":True,
                "license":"CC0","creator":page,"original_source_url":page,
                "original_license_url":license_url,"audio_sha256":sha}}
        except (OSError,ValueError,AudioUnavailable,TimeoutError) as exc:
            if os.environ.get('MAD_V6_AUDIO_DIAGNOSTIC')=='true':
                print('CC0_AUDIO_SOURCE_REJECTED',type(exc).__name__,getattr(exc,'code','none'))
            continue
    raise AudioUnavailable("No compatible CC0 soundtrack available; never silently substitute commercial audio")
