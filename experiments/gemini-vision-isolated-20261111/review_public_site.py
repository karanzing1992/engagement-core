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
ALLOWED = ("gemini-3.6-flash", "gemini-3.8-flash")

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
                im.thumbnail((640, 880))
                out = io.BytesIO()
                im.save(out, format="JPEG", quality=54, optimize=True)
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
    prompt = ("You are an independent visual critique assistant. Examine genuine public "
              "browser screenshots of the Andaz Vibe Stay hospitality website, first mobile "
              "then desktop. Evaluate visual hierarchy, typography, spacing, contrast, "
              "distinctive aesthetics, authenticity, CTA clarity, and responsiveness. "
              "Use only observable evidence. Return strict JSON: "
              '{"observations":["..."],"deficiencies":[{"category":"typography",'
              '"visible_evidence":"...","suggested_revision":"...","priority":"P1"}],'
              '"quality_estimate":0,"verdict":"REVISE"}. '
              "Quality estimate is a model opinion, NOT a certified artistic score. "
              "Do not identify people, invent facts, or approve deployment.")
    parts = [{"text": prompt}]
    for screen in screenshots:
        parts.append({"inline_data": {"mime_type": "image/jpeg",
                                    "data": base64.b64encode(screen["jpeg"]).decode()}})
    response = None
    model = None
    for candidate in available_models[:2]:
        print("GEMINI_SELECTED_MODEL " + candidate, flush=True)
        try:
            response = api("/models/" + candidate + ":generateContent", key,
                           {"contents": [{"parts": parts}],
                            "generationConfig": {"temperature": 0, "responseMimeType": "application/json",
                                                 "maxOutputTokens": 2400}})
            model = candidate
            break
        except RuntimeError as exc:
            if any(tag in str(exc) for tag in ("HTTP_404_VISION", "HTTP_503_VISION", "READ_TIMEOUT_VISION")):
                print("GEMINI_MODEL_CANDIDATE_UNAVAILABLE " + candidate, file=sys.stderr)
                continue
            raise
    if response is None:
        raise RuntimeError("ALL_APPROVED_FLASH_CANDIDATES_UNAVAILABLE")
    candidates = response.get("candidates") or [{}]
    first = candidates[0]
    raw = "".join(part.get("text", "") for part in
                  first.get("content", {}).get("parts", []) if isinstance(part, dict))
    finish = str(first.get("finishReason", "UNKNOWN"))[:35]
    print("GEMINI_RESPONSE_DIAGNOSTIC finish=" + finish
          + " output_characters=" + str(len(raw))
          + " output_tokens=" + str((response.get("usageMetadata") or {}).get("candidatesTokenCount", "unknown")), flush=True)
    if not raw.strip():
        raise RuntimeError("GEMINI_EMPTY_MODEL_TEXT_" + finish)
    try:
        result = validate(json.loads(raw))
    except (ValueError, RuntimeError, TypeError):
        raise RuntimeError("GEMINI_UNUSABLE_JSON_" + finish) from None
    evidence = {"schema": "andaz-gemini-vision-isolated-v1",
                "source": URL, "model": model, "real_api_called": True,
                "viewports": [{"name": s["label"], "dimensions": s["viewport"],
                               "screenshot_sha256": s["sha256"]} for s in screenshots],
                "model_response_sha256": sha(raw.encode()),
                "model_observations": result["observations"][:8],
                "model_deficiencies": result["deficiencies"][:12],
                "model_quality_estimate_not_attested": result["quality_estimate"],
                "model_verdict_not_release": result["verdict"],
                "artistic_score": None, "independently_attested": False,
                "artistic_95_certified": False, "release_authorized": False}
    (ROOT / "receipt.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print("GEMINI_REAL_SCREENSHOT_REVIEW_PASS model=" + model +
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
