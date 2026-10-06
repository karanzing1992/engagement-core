"""Additional social publishers for Russian-market distribution.

Credentials stay in environment variables. Brand/channel identifiers belong in
brand config, never in this module.
"""
from __future__ import annotations
import os, requests

class PublishError(RuntimeError): pass

def _post_json(url: str, *, data: dict, files=None, timeout=60) -> dict:
    r=requests.post(url,data=data,files=files,timeout=timeout)
    try: payload=r.json()
    except Exception: payload={"raw":r.text}
    if not r.ok or payload.get("ok") is False or "error" in payload:
        raise PublishError(f"Publisher rejected request: {payload}")
    return payload

def telegram_video(media_url: str, caption: str, chat_id: str) -> dict:
    token=os.environ["TELEGRAM_BOT_TOKEN"]
    return _post_json(
        f"https://api.telegram.org/bot{token}/sendVideo",
        data={"chat_id":chat_id,"video":media_url,"caption":caption[:1024],"supports_streaming":"true"},
    )

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
