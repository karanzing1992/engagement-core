#!/usr/bin/env python3
"""Single bounded Groq inference admission test. No media or secret logging."""
import json
import os
import sys
import urllib.error
import urllib.request

MODEL = "openai/gpt-oss-20b"
key = os.environ.get("GROQ_API_KEY", "")
if not key:
    print("MAD_GROQ_INFERENCE_BLOCKED missing_secret")
    raise SystemExit(2)
payload = {
    "model": MODEL,
    "messages": [{"role": "user", "content": "Reply with exactly the single word READY."}],
    "max_completion_tokens": 160,
    "temperature": 0,
    "reasoning_effort": "low",
    "stream": False
}
req = urllib.request.Request(
    "https://api.groq.com/openai/v1/chat/completions",
    method="POST",
    data=json.dumps(payload, separators=(",", ":")).encode(),
    headers={"Authorization": "Bearer " + key,
             "Content-Type": "application/json",
             "Accept": "application/json",
             "User-Agent": "MAD-V5-Groq-Inference-Smoke/1.0"}
)
try:
    with urllib.request.urlopen(req, timeout=35) as response:
        if response.status != 200:
            raise RuntimeError("Unexpected provider status")
        result = json.load(response)
except urllib.error.HTTPError as exc:
    print("MAD_GROQ_INFERENCE_BLOCKED http_status", exc.code)
    raise SystemExit(3)
except Exception as exc:
    print("MAD_GROQ_INFERENCE_BLOCKED transport", type(exc).__name__)
    raise SystemExit(4)
choices = result.get("choices") or []
answer = (choices[0].get("message") or {}).get("content", "") if choices else ""
if result.get("model") != MODEL or not isinstance(answer, str) or not answer.strip():
    print("MAD_GROQ_INFERENCE_BLOCKED invalid_response")
    raise SystemExit(5)
print("MAD_GROQ_INFERENCE_PASS model", MODEL, "reply_present", True, "media_sent", False)
