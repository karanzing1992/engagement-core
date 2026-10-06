import os
from social_publishers import capabilities

def test_capabilities_are_explicit(monkeypatch):
    for key in ["TELEGRAM_BOT_TOKEN","VK_ACCESS_TOKEN","OK_ACCESS_TOKEN","OK_APPLICATION_KEY"]:
        monkeypatch.delenv(key,raising=False)
    c=capabilities()
    assert set(c)=={"telegram","vk","ok","snapchat"}
    assert c["telegram"]["mode"]=="server-auto"
    assert c["snapchat"]["requires_device_confirmation"] is True


def test_telegram_album_builds_media_group(monkeypatch):
    import social_publishers as sp
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN","test-token")
    calls=[]
    def fake_post(url, *, data, files=None, timeout=60):
        calls.append((url,data))
        if url.endswith("/sendMediaGroup"):
            return {"ok":True,"result":[{"message_id":11},{"message_id":12}]}
        return {"ok":True,"result":{"message_id":13}}
    monkeypatch.setattr(sp,"_post_json",fake_post)
    result=sp.telegram_post_multi(
        "<b>Hello</b> 🔥",
        [
            {"type":"photo","url":"https://example.com/a.jpg"},
            {"type":"video","url":"https://example.com/b.mp4"},
        ],
        [{"key":"primary","chat_id":"-1001234567890","level":"primary","enabled":True}],
    )
    assert result["ok"] is True
    assert result["sent"][0]["mode"]=="album"
    assert calls[0][0].endswith("/sendMediaGroup")
    media=__import__("json").loads(calls[0][1]["media"])
    assert [x["type"] for x in media]==["photo","video"]
    assert media[0]["caption"]=="<b>Hello</b> 🔥"

def test_telegram_rejects_invalid_album_mix():
    import social_publishers as sp
    try:
        sp._telegram_validate_media([
            {"type":"audio","url":"https://example.com/a.mp3"},
            {"type":"photo","url":"https://example.com/a.jpg"},
        ])
    except sp.PublishError as exc:
        assert "audio albums" in str(exc)
    else:
        raise AssertionError("Expected invalid album mix to be rejected")


def test_vk_publish_builds_group_wall_post(monkeypatch):
    import social_publishers as sp
    monkeypatch.setenv("VK_ACCESS_TOKEN","test-token")
    uploaded=[]
    calls=[]
    monkeypatch.setattr(sp,"_vk_upload_wall_photo",lambda url,owner_id: uploaded.append((url,owner_id)) or "photo-123_456")
    def fake_api(method,data):
        calls.append((method,data))
        return {"post_id":99}
    monkeypatch.setattr(sp,"_vk_api",fake_api)
    result=sp.vk_publish(
        "Привет 🔥",
        "-123",
        media=[{"type":"photo","url":"https://example.com/a.jpg"}],
        link="https://mokshagoa.com/",
    )
    assert result["post_id"]==99
    assert uploaded==[("https://example.com/a.jpg","-123")]
    assert calls[-1][0]=="wall.post"
    assert calls[-1][1]["from_group"]==1
    assert calls[-1][1]["attachments"]=="photo-123_456,https://mokshagoa.com/"


def test_ok_signature_matches_documented_algorithm(monkeypatch):
    import hashlib
    import social_publishers as sp
    access_token="access"
    secret="secret"
    params={"method":"users.getCurrentUser","application_key":"public","format":"json"}
    session_secret=hashlib.md5((access_token+secret).encode()).hexdigest().lower()
    joined="".join(f"{k}={params[k]}" for k in sorted(params))
    expected=hashlib.md5((joined+session_secret).encode()).hexdigest().lower()
    assert sp._ok_signature(params,access_token,secret)==expected

def test_ok_publish_builds_group_mediatopic(monkeypatch):
    import social_publishers as sp
    monkeypatch.setenv("OK_ACCESS_TOKEN","access")
    monkeypatch.setenv("OK_APPLICATION_KEY","public")
    monkeypatch.setenv("OK_APPLICATION_SECRET","secret")
    monkeypatch.setenv("OK_GROUP_ID","123")
    monkeypatch.setattr(sp,"_ok_upload_photos",lambda urls,group_id:["photo-token-1"] if urls else [])
    calls=[]
    def fake_api(method,params=None):
        calls.append((method,params or {}))
        return "topic-77"
    monkeypatch.setattr(sp,"_ok_api",fake_api)
    result=sp.ok_publish(
        "Привет 🌿",
        "123",
        media=[{"type":"photo","url":"https://example.com/a.jpg"}],
        link="https://mokshagoa.com/",
    )
    assert result["ok"] is True
    assert result["topic_id"]=="topic-77"
    method,payload=calls[-1]
    assert method=="mediatopic.post"
    assert payload["type"]=="GROUP_THEME"
    attachment=__import__("json").loads(payload["attachment"])
    assert attachment["media"][0]["type"]=="text"
    assert attachment["media"][1]["list"][0]["id"]=="photo-token-1"
    assert attachment["media"][2]["url"]=="https://mokshagoa.com/"
