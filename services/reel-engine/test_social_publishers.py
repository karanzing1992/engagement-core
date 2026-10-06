import os
from social_publishers import capabilities

def test_capabilities_are_explicit(monkeypatch):
    for key in ["TELEGRAM_BOT_TOKEN","VK_ACCESS_TOKEN","OK_ACCESS_TOKEN","OK_APPLICATION_KEY"]:
        monkeypatch.delenv(key,raising=False)
    c=capabilities()
    assert set(c)=={"telegram","vk","ok","snapchat"}
    assert c["telegram"]["mode"]=="server-auto"
    assert c["snapchat"]["requires_device_confirmation"] is True
