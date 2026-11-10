#!/usr/bin/env python3
"""Review-only Gemini vision handshake against PUBLIC Andaz site, without key disclosure."""
import base64
import hashlib
import io
import json
import os
import socket
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request
from PIL import Image

ROOT = Path("out/private-gemini-vision-review")
URL = "https://andazgoa.com/"
API = "https://generativelanguage.googleapis.com/v1beta"
ALLOWED = ("gemini-3.5-flash-lite",)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def api(path, key, body=None):
    assert path.startswith("/models") and ".." not in path
    data = None if body is None else json.dumps(body).encode()
    headers = {"x-goog-api-key": key, "Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(API + path, data=data, headers=headers,
                                 method="GET" if data is None else "POST")
    phase = "MODEL_LIST" if data is None else "VISION_INFERENCE"
    for attempt in range(2):
        print("GEMINI_STAGE_" + phase + "_ATTEMPT_" + str(attempt + 1), flush=True)
        try:
            with urllib.request.urlopen(req, timeout=38) as response:
                raw = response.read(1000000)
            return json.loads(raw)
        except urllib.error.HTTPError as exc:
            if exc.code == 503 and attempt == 0:
                print("GEMINI_TRANSIENT_503_" + phase + " retry=1", file=sys.stderr)
                time.sleep(3)
                continue
            raise RuntimeError("GEMINI_HTTP_" + str(exc.code) + "_" + phase) from None
        except (TimeoutError, socket.timeout):
            raise RuntimeError("GEMINI_READ_TIMEOUT_" + phase) from None
        except urllib.error.URLError:
            raise RuntimeError("GEMINI_NETWORK_UNAVAILABLE_" + phase) from None
    raise RuntimeError("GEMINI_RETRIES_EXHAUSTED_" + phase)

def choose_models(metadata):
    models = metadata.get("models", [])
    available = {m.get("name", "").removeprefix("models/")
                 for m in models if "generateContent" in m.get("supportedGenerationMethods", [])}
    selected = [name for name in ALLOWED if name in available]
    print("GEMINI_FREE_REVIEW_ALLOWLIST_AVAILABLE " + ",".join(selected), flush=True)
    if not selected:
        raise RuntimeError("NO_APPROVED_FLASH_MODEL_IN_AUTHENTICATED_LIST")
    return selected

def capture_public():
    from playwright.sync_api import sync_playwright
    ROOT.mkdir(parents=True, exist_ok=True)
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            for label, width, height in (("mobile", 390, 844), ("desktop", 1440, 900)):
                context = browser.new_context(viewport={"width": width, "height": height},
                                              device_scale_factor=1,
                                              service_workers="block")
                page = context.new_page()
                response = page.goto(URL, wait_until="domcontentloaded", timeout=45000)
                if response is None or response.status >= 400:
                    raise RuntimeError("PUBLIC_SITE_HTTP_FAILURE")
                page.wait_for_timeout(1800)
                # Do not retain the raw screenshot in GitHub artifacts.
                raw = page.screenshot(full_page=False, type="png")
                if len(raw) < 5000:
                    raise RuntimeError("INVALID_BROWSER_SCREENSHOT")
                im = Image.open(io.BytesIO(raw)).convert("RGB")
                im.thumbnail((384, 512))
                out = io.BytesIO()
                im.save(out, format="JPEG", quality=49, optimize=True)
                encoded = out.getvalue()
                if len(encoded) > 360000:
                    raise RuntimeError("IMAGE_BODY_LIMIT")
                results.append({"label": label, "viewport": [width, height],
                                "sha256": sha(raw), "jpeg": encoded})
                context.close()
        finally:
            browser.close()
    return results

def validate(data):
    expected = {"observations", "deficiencies", "quality_estimate", "verdict"}
    if not isinstance(data, dict) or set(data) != expected:
        raise RuntimeError("INVALID_REVIEW_KEYS")
    if not isinstance(data["observations"], list) or not data["observations"]:
        raise RuntimeError("MISSING_OBSERVATIONS")
    if not isinstance(data["deficiencies"], list):
        raise RuntimeError("INVALID_DEFICIENCIES")
    if type(data["quality_estimate"]) is not int or not 0 <= data["quality_estimate"] <= 100:
        raise RuntimeError("INVALID_ESTIMATE")
    if data["verdict"] not in ("REVISE", "CANDIDATE"):
        raise RuntimeError("INVALID_VERDICT")
    return data

def main():
    # This workflow is owner-only and never accepts arbitrary URLs, models or prompts.
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        raise RuntimeError("GITHUB_GEMINI_SECRET_UNAVAILABLE")
    models = api("/models?pageSize=100", key)
    available_models = choose_models(models)
    screenshots = capture_public()
    # Provider debug fix: separate image reviews and avoid two-image JSON generation overload.
    evidence = {"schema": "andaz-gemini-vision-isolated-v2",
                "source": URL, "model": available_models[0], "real_api_called": True,
                "viewports": [{"name": s["label"], "dimensions": s["viewport"],
                               "screenshot_sha256": s["sha256"]} for s in screenshots],
                "reviews": [], "artistic_score": None,
                "independently_attested": False,
                "artistic_95_certified": False, "release_authorized": False}
    for screen in screenshots:
        print("GEMINI_REVIEW_VIEWPORT " + screen["label"], flush=True)
        prompt = (
            "Review this actual public Andaz Vibe Stay hospitality website screenshot. "
            "Give three specific, visually grounded improvements to hierarchy, spacing, "
            "readability, authenticity or branding, plus one positive. "
            "Only mention what is clearly visible. No numeric score or deployment approval.")
        image = {"inline_data": {"mime_type": "image/jpeg",
                                "data": base64.b64encode(screen["jpeg"]).decode()}}
        reply = api("/models/" + available_models[0] + ":generateContent", key,
                    {"contents": [{"parts": [{"text": prompt}, image]}],
                     "generationConfig": {"temperature": 0, "maxOutputTokens": 650}})
        candidates = reply.get("candidates") or [{}]
        first = candidates[0]
        raw = "".join(p.get("text", "") for p in first.get("content", {}).get("parts", []) if isinstance(p, dict))
        if len(raw.strip()) < 70:
            raise RuntimeError("GEMINI_INSUFFICIENT_VISUAL_REVIEW_" + screen["label"])
        evidence["reviews"].append({
            "viewport": screen["label"],
            "model_observations": raw[:4500],
            "raw_response_sha256": sha(raw.encode()),
            "finish_reason": str(first.get("finishReason", "UNKNOWN"))[:32],
            "provider_output_tokens": (reply.get("usageMetadata") or {}).get("candidatesTokenCount"),
            "certified": False})
        print("GEMINI_REVIEW_" + screen["label"].upper() + "_PASS chars=" + str(len(raw)), flush=True)
    (ROOT / "receipt.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print("GEMINI_REAL_SCREENSHOT_REVIEW_PASS model=" + available_models[0] +
          " screenshots=2 artistic_certification=NOT_GRANTED")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        ROOT.mkdir(parents=True, exist_ok=True)
        (ROOT / "failed.json").write_text(json.dumps({
            "status": "BLOCKED", "reason": str(exc)[:100],
            "artistic_score": None, "release_authorized": False}, indent=2) + "\n")
        print("GEMINI_ART_REVIEW_FAIL_CLOSED " + str(exc)[:100], file=sys.stderr)
        sys.exit(1)
