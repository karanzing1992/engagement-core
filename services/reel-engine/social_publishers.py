"""Additional social publishers for Russian-market distribution.

Credentials stay in environment variables. Brand/channel identifiers belong in
brand config, never in this module.
"""
from __future__ import annotations
import hashlib, json, os, requests

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
        target_match=(not targets) or key in targets or chat_id in targets
        level_match=(not levels) or level in levels
        if targets and levels:
            if not (target_match or level_match):
                continue
        elif not (target_match and level_match):
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

def _vk_api(method: str, data: dict) -> dict:
    token=os.environ["VK_ACCESS_TOKEN"]
    payload={"access_token":token,"v":os.getenv("VK_API_VERSION","5.199"),**data}
    r=requests.post(f"https://api.vk.com/method/{method}",data=payload,timeout=60)
    try: body=r.json()
    except Exception: body={"raw":r.text}
    if not r.ok or "error" in body:
        raise PublishError(f"VK rejected {method}: {body}")
    return body.get("response",{})

def _vk_upload_wall_photo(media_url: str, owner_id: str) -> str:
    owner=int(owner_id)
    params={}
    if owner<0:
        params["group_id"]=abs(owner)
    server=_vk_api("photos.getWallUploadServer",params)
    upload_url=server.get("upload_url")
    if not upload_url:
        raise PublishError("VK did not return a wall upload URL")

    source=requests.get(media_url,timeout=60)
    source.raise_for_status()
    content_type=source.headers.get("content-type","image/jpeg").split(";")[0]
    uploaded=requests.post(
        upload_url,
        files={"photo":("upload.jpg",source.content,content_type)},
        timeout=90,
    )
    try: up=uploaded.json()
    except Exception: up={"raw":uploaded.text}
    if not uploaded.ok or not all(k in up for k in ("photo","server","hash")):
        raise PublishError(f"VK photo upload failed: {up}")

    save={"photo":up["photo"],"server":up["server"],"hash":up["hash"]}
    if owner<0:
        save["group_id"]=abs(owner)
    else:
        save["user_id"]=owner
    photos=_vk_api("photos.saveWallPhoto",save)
    photo=photos[0] if isinstance(photos,list) and photos else {}
    if not photo.get("owner_id") or not photo.get("id"):
        raise PublishError(f"VK did not return saved photo id: {photos}")
    return f"photo{photo['owner_id']}_{photo['id']}"

def vk_publish(message: str, owner_id: str, media=None, link: str="") -> dict:
    """Publish text/link/photos to a VK wall/community."""
    attachments=[]
    photos=[m for m in (media or []) if m.get("url")]
    if len(photos)>10:
        raise PublishError("VK publisher accepts at most 10 photos per post")
    for item in photos:
        if item.get("type","photo")!="photo":
            raise PublishError("VK automated publisher currently accepts photo media")
        attachments.append(_vk_upload_wall_photo(str(item["url"]),owner_id))
    if link:
        attachments.append(link)

    data={"owner_id":owner_id,"message":message}
    if int(owner_id)<0:
        data["from_group"]=1
    if attachments:
        data["attachments"]=",".join(attachments)
    return _vk_api("wall.post",data)

def vk_wall_post(message: str, owner_id: str, attachments: str="") -> dict:
    """Backward-compatible VK wall.post helper."""
    data={"owner_id":owner_id,"message":message}
    if int(owner_id)<0:
        data["from_group"]=1
    if attachments:
        data["attachments"]=attachments
    return _vk_api("wall.post",data)

def _ok_signature(params: dict, access_token: str, application_secret: str) -> str:
    filtered={k:str(v) for k,v in params.items() if k not in {"access_token","session_key","sig"}}
    joined="".join(f"{k}={filtered[k]}" for k in sorted(filtered))
    session_secret=hashlib.md5((access_token+application_secret).encode("utf-8")).hexdigest().lower()
    return hashlib.md5((joined+session_secret).encode("utf-8")).hexdigest().lower()

def _ok_api(method: str, params=None):
    access_token=os.environ["OK_ACCESS_TOKEN"]
    app_key=os.environ["OK_APPLICATION_KEY"]
    app_secret=os.environ["OK_APPLICATION_SECRET"]
    data={"method":method,"application_key":app_key,"format":"json",**(params or {})}
    data["sig"]=_ok_signature(data,access_token,app_secret)
    data["access_token"]=access_token
    r=requests.post("https://api.ok.ru/fb.do",data=data,timeout=60)
    try: payload=r.json()
    except Exception: payload={"raw":r.text}
    if not r.ok or (isinstance(payload,dict) and "error_code" in payload):
        raise PublishError(f"OK rejected {method}: {payload}")
    return payload

def _ok_upload_photos(urls: list[str], group_id: str) -> list[str]:
    if not urls:
        return []
    if len(urls)>10:
        raise PublishError("Odnoklassniki publisher accepts at most 10 photos per post")
    upload=_ok_api("photosV2.getUploadUrl",{"gid":group_id,"count":len(urls)})
    upload_url=upload.get("upload_url") if isinstance(upload,dict) else None
    if not upload_url:
        raise PublishError(f"OK did not return photo upload URL: {upload}")

    files={}
    for index,url in enumerate(urls,1):
        src=requests.get(url,timeout=60)
        src.raise_for_status()
        ctype=src.headers.get("content-type","image/jpeg").split(";")[0]
        files[f"pic{index}"]=(f"photo{index}.jpg",src.content,ctype)
    r=requests.post(upload_url,files=files,timeout=120)
    try: payload=r.json()
    except Exception: payload={"raw":r.text}
    if not r.ok or not isinstance(payload,dict) or not isinstance(payload.get("photos"),dict):
        raise PublishError(f"OK photo upload failed: {payload}")
    tokens=[str(item.get("token")) for item in payload["photos"].values() if isinstance(item,dict) and item.get("token")]
    if not tokens:
        raise PublishError("OK photo upload returned no media tokens")
    return tokens

def ok_publish(message: str, group_id: str, media=None, link: str="") -> dict:
    blocks=[]
    if message:
        blocks.append({"type":"text","text":message})
    photo_urls=[]
    for item in media or []:
        if item.get("type","photo")!="photo":
            raise PublishError("Odnoklassniki automated publisher currently accepts photo media")
        if item.get("url"):
            photo_urls.append(str(item["url"]))
    tokens=_ok_upload_photos(photo_urls,group_id)
    if tokens:
        blocks.append({"type":"photo","list":[{"id":token} for token in tokens]})
    if link:
        blocks.append({"type":"link","url":link})
    if not blocks:
        raise PublishError("Odnoklassniki post needs text, photo, or link")
    attachment=json.dumps({"media":blocks},ensure_ascii=False,separators=(",",":"))
    topic_id=_ok_api("mediatopic.post",{
        "type":"GROUP_THEME",
        "gid":group_id,
        "attachment":attachment,
        "onBehalfOfGroup":"true",
    })
    return {"ok":True,"group_id":group_id,"topic_id":str(topic_id),"photo_count":len(photo_urls),"requires_approved_app":True}

def ok_capability() -> dict:
    # OK group publishing requires an approved application and GROUP_CONTENT/PHOTO_CONTENT.
    return {"ready":bool(os.getenv("OK_ACCESS_TOKEN") and os.getenv("OK_APPLICATION_KEY") and os.getenv("OK_APPLICATION_SECRET") and os.getenv("OK_GROUP_ID")),
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
