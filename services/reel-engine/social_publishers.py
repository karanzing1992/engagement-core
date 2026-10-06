"""Additional social publishers for Russian-market distribution.

Credentials stay in environment variables. Brand/channel identifiers belong in
brand config, never in this module.
"""
from __future__ import annotations
import json, os, requests

class PublishError(RuntimeError): pass

def _post_json(url: str, *, data: dict, files=None, timeout=60) -> dict:
    r=requests.post(url,data=data,files=files,timeout=timeout)
    try: payload=r.json()
    except Exception: payload={"raw":r.text}
    if not r.ok or payload.get("ok") is False or "error" in payload:
        raise PublishError(f"Publisher rejected request: {payload}")
    return payload

def telegram_video(media_url: str, caption: str, chat_id: str) -> dict:
    """Backward-compatible single-destination Telegram publish."""
    token=os.environ["TELEGRAM_BOT_TOKEN"]
    return _post_json(
        f"https://api.telegram.org/bot{token}/sendVideo",
        data={"chat_id":chat_id,"video":media_url,"caption":caption[:1024],"supports_streaming":"true"},
    )

def telegram_video_multi(media_url: str, caption: str, destinations: list[dict], *, levels=None, targets=None) -> dict:
    """Publish one video to every matching enabled Telegram destination."""
    token=os.environ["TELEGRAM_BOT_TOKEN"]
    levels=set(levels or [])
    targets=set(targets or [])
    sent=[]
    failed=[]

    for destination in destinations:
        if not destination.get("enabled", True):
            continue
        key=str(destination.get("key",""))
        chat_id=str(destination.get("chat_id","")).strip()
        level=str(destination.get("level","primary"))
        if targets and key not in targets and chat_id not in targets:
            continue
        if levels and level not in levels:
            continue
        if not chat_id:
            continue
        try:
            payload=_post_json(
                f"https://api.telegram.org/bot{token}/sendVideo",
                data={"chat_id":chat_id,"video":media_url,"caption":caption[:1024],"supports_streaming":"true"},
            )
            sent.append({"key":key,"chat_id":chat_id,"level":level,"message_id":payload.get("result",{}).get("message_id")})
        except Exception as exc:
            failed.append({"key":key,"chat_id":chat_id,"level":level,"error":str(exc)})

    if not sent:
        raise PublishError(f"Telegram publish failed for all matching destinations: {failed}")
    return {"ok":not failed,"sent":sent,"failed":failed}

TELEGRAM_MEDIA_TYPES={"photo","video","animation","audio","document"}

def _telegram_validate_media(media: list[dict]) -> list[dict]:
    clean=[]
    for item in media or []:
        kind=str(item.get("type","")).strip().lower()
        url=str(item.get("url","")).strip()
        if kind not in TELEGRAM_MEDIA_TYPES:
            raise PublishError(f"Unsupported Telegram media type: {kind or 'unknown'}")
        if not url.startswith(("https://","http://")):
            raise PublishError("Telegram media needs a public HTTP(S) URL")
        clean.append({"type":kind,"url":url,"name":str(item.get("name",""))})
    if len(clean)>10:
        raise PublishError("Telegram albums support at most 10 media items")
    if len(clean)>1:
        kinds={item["type"] for item in clean}
        if "animation" in kinds:
            raise PublishError("GIF/animation must be sent as a single Telegram item")
        if "audio" in kinds and kinds!={"audio"}:
            raise PublishError("Telegram audio albums must contain audio only")
        if "document" in kinds and kinds!={"document"}:
            raise PublishError("Telegram document albums must contain documents only")
    return clean

def _telegram_send_post(token: str, chat_id: str, text: str, media: list[dict]) -> dict:
    media=_telegram_validate_media(media)
    base=f"https://api.telegram.org/bot{token}"
    caption=text if len(text)<=1024 else ""
    message_ids=[]

    if not media:
        if not text:
            raise PublishError("Telegram post needs text or media")
        payload=_post_json(f"{base}/sendMessage",data={"chat_id":chat_id,"text":text,"parse_mode":"HTML"})
        message_ids.append(payload.get("result",{}).get("message_id"))
        return {"mode":"text","message_ids":message_ids}

    if len(media)==1:
        item=media[0]
        methods={
            "photo":("sendPhoto","photo"),
            "video":("sendVideo","video"),
            "animation":("sendAnimation","animation"),
            "audio":("sendAudio","audio"),
            "document":("sendDocument","document"),
        }
        method,field=methods[item["type"]]
        data={"chat_id":chat_id,field:item["url"]}
        if caption:
            data.update({"caption":caption,"parse_mode":"HTML"})
        if item["type"]=="video":
            data["supports_streaming"]="true"
        payload=_post_json(f"{base}/{method}",data=data)
        message_ids.append(payload.get("result",{}).get("message_id"))
        mode=f"single-{item['type']}"
    else:
        album=[]
        for index,item in enumerate(media):
            entry={"type":item["type"],"media":item["url"]}
            if index==0 and caption:
                entry.update({"caption":caption,"parse_mode":"HTML"})
            if item["type"]=="video":
                entry["supports_streaming"]=True
            album.append(entry)
        payload=_post_json(f"{base}/sendMediaGroup",data={"chat_id":chat_id,"media":json.dumps(album)})
        message_ids.extend(m.get("message_id") for m in payload.get("result",[]) if m.get("message_id") is not None)
        mode="album"

    if text and not caption:
        payload=_post_json(f"{base}/sendMessage",data={"chat_id":chat_id,"text":text,"parse_mode":"HTML"})
        message_ids.append(payload.get("result",{}).get("message_id"))
    return {"mode":mode,"message_ids":message_ids}

def telegram_post_multi(text: str, media: list[dict], destinations: list[dict], *, levels=None, targets=None) -> dict:
    """Publish rich Telegram content to matching groups/channels."""
    token=os.environ["TELEGRAM_BOT_TOKEN"]
    levels=set(levels or [])
    targets=set(targets or [])
    sent=[]
    failed=[]
    media=_telegram_validate_media(media)

    for destination in destinations:
        if not destination.get("enabled",True):
            continue
        key=str(destination.get("key",""))
        chat_id=str(destination.get("chat_id","")).strip()
        level=str(destination.get("level","primary"))
        if targets and key not in targets and chat_id not in targets:
            continue
        if levels and level not in levels:
            continue
        if not chat_id:
            continue
        try:
            result=_telegram_send_post(token,chat_id,text,media)
            sent.append({"key":key,"chat_id":chat_id,"level":level,**result})
        except Exception as exc:
            failed.append({"key":key,"chat_id":chat_id,"level":level,"error":str(exc)})

    if not sent:
        raise PublishError(f"Telegram publish failed for all matching destinations: {failed}")
    return {"ok":not failed,"sent":sent,"failed":failed}

def vk_wall_post(message: str, owner_id: str, attachments: str="") -> dict:
    """Publish once VK media has been uploaded and represented as an attachment id."""
    token=os.environ["VK_ACCESS_TOKEN"]
    data={"access_token":token,"v":os.getenv("VK_API_VERSION","5.199"),"owner_id":owner_id,"message":message}
    if attachments:data["attachments"]=attachments
    return _post_json("https://api.vk.com/method/wall.post",data=data)

def ok_capability() -> dict:
    # OK requires an approved application before mediatopic publishing is usable.
    return {"ready":bool(os.getenv("OK_ACCESS_TOKEN") and os.getenv("OK_APPLICATION_KEY")),
            "requires_approved_app":True,"mode":"mediatopic"}

def snapchat_capability() -> dict:
    # Creative Kit hands video to Snapchat preview; it is not an unattended server-side organic post API.
    return {"ready":False,"mode":"android-creative-kit-handoff","requires_device_confirmation":True}

def capabilities() -> dict:
    return {
      "telegram":{"ready":bool(os.getenv("TELEGRAM_BOT_TOKEN")),"mode":"server-auto"},
      "vk":{"ready":bool(os.getenv("VK_ACCESS_TOKEN")),"mode":"server-auto-after-media-upload"},
      "ok":ok_capability(),
      "snapchat":snapchat_capability(),
    }
