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
