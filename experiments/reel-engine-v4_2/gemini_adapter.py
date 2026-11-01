#!/usr/bin/env python3
"""MAD Reel Engine V4.2: Gemini vision connector. Network and media are opt-in.

This is a *separate* provider adapter. It never publishes, modifies WordPress,
changes the MAD Mac host binding, or exports secret values. Python stdlib only.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import urllib.error
import urllib.request

BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
MODEL = "gemini-3.8-flash"
MAX_FRAMES = 8
MAX_BODY_BYTES = 3_000_000


class GeminiUnavailable(RuntimeError):
    pass


def key_from_environment():
    """Environment or a 0600 file outside public source. Never print the key."""
    key = os.environ.get("GEMINI_API_KEY", "") or os.environ.get("GOOGLE_API_KEY", "")
    if key:
        return key.strip()
    path = os.environ.get("GEMINI_API_KEY_FILE")
    if not path:
        return ""
    p = Path(path).expanduser()
    if not p.is_file():
        return ""
    if p.stat().st_mode & (stat.S_IRWXG | stat.S_IRWXO):
        raise GeminiUnavailable("Gemini secret file permissions must be 0600")
    return p.read_text(encoding="utf-8").strip()


def make_request(url, key, payload=None, *, timeout=35, opener=None):
    """REST requests with the secret strictly in a header, never URL or log."""
    if not key:
        raise GeminiUnavailable("No Gemini credential configured")
    if not url.startswith(BASE_URL + "/"):
        raise ValueError("External API host rejected")
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    if data is not None and len(data) > MAX_BODY_BYTES:
        raise ValueError("Gemini request body exceeds allowed size")
    headers = {"x-goog-api-key": key, "Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers,
                                 method="GET" if data is None else "POST")
    opener = opener or urllib.request.urlopen
    try:
        with opener(req, timeout=timeout) as response:
            result = response.read(1_000_001)
    except urllib.error.HTTPError as exc:
        # Provider response bodies can reflect sensitive request data: do not emit them.
        raise GeminiUnavailable("Gemini API returned HTTP %s" % exc.code) from None
    except urllib.error.URLError:
        raise GeminiUnavailable("Gemini transport unavailable") from None
    if len(result) > 1_000_000:
        raise GeminiUnavailable("Gemini response exceeded allowed size")
    return json.loads(result.decode("utf-8"))


def visible_model_names(result):
    return sorted({
        m.get("name", "")[7:] for m in result.get("models", [])
        if m.get("name", "").startswith("models/")
    })


def extract_json(response):
    candidates = response.get("candidates", [])
    if not candidates:
        raise GeminiUnavailable("Gemini returned no candidates")
    parts = candidates[0].get("content", {}).get("parts", [])
    raw = "".join(p.get("text", "") for p in parts if isinstance(p, dict))
    if not raw.strip():
        raise GeminiUnavailable("Gemini returned no text")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise GeminiUnavailable("Gemini result must be a JSON object")
    return data


def sample_frame(source, second):
    if not Path(source).is_file():
        raise ValueError("Source video missing")
    args = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
            "-ss", str(second), "-i", str(source), "-frames:v", "1",
            "-vf", "scale=384:-2", "-q:v", "5", "-f", "mjpeg", "pipe:1"]
    p = subprocess.run(args, capture_output=True, timeout=18, check=True)
    data = p.stdout
    if not data.startswith(b"\xff\xd8") or len(data) > 260_000:
        raise ValueError("Invalid sampled video frame")
    return data


def frame_request(frames, brand_rules):
    if not 1 <= len(frames) <= MAX_FRAMES:
        raise ValueError("Frame count outside allowed bounds")
    parts = [{
        "text": (
            "You are a factual video shot logger, not a creative fiction writer. "
            "For each supplied frame in order, describe visible action, objects, "
            "shot composition, people (without identifying them), light and "
            "possible Instagram hook; do NOT invent actions between frames, "
            "location specifics, client identity or endorsements. "
            "Label uncertainty. Return JSON object with 'shots' array, each "
            "entry with index, timestamp_seconds, visible, hook_potential, "
            "uncertainties. Brand rules are context only, not source evidence:\n"
            + brand_rules[:4500]
            + "\nThe frames below are time-ordered screenshots from one video."
        )
    }]
    for idx, (second, jpeg) in enumerate(frames):
        if not jpeg.startswith(b"\xff\xd8"):
            raise ValueError("Only JPEG frame bytes accepted")
        parts.append({"text": "Source timestamp %.2fs (frame %d)" % (second, idx)})
        parts.append({"inline_data": {"mime_type": "image/jpeg",
                                       "data": base64.b64encode(jpeg).decode("ascii")}})
    return {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json",
                             "maxOutputTokens": 1800},
    }


def run_preflight(args):
    key = key_from_environment()
    info = {"provider": "gemini", "model": args.model, "key_present": bool(key),
            "network_tested": False, "media_uploaded": False,
            "free_tier_verified": False}
    if args.verify_connection:
        if not args.accept_free_tier_terms:
            raise GeminiUnavailable("Explicit --accept-free-tier-terms required")
        if not key:
            raise GeminiUnavailable("Create a Google AI Studio key and configure it outside Git")
        models = make_request(BASE_URL + "/models?pageSize=100", key)
        info["network_tested"] = True
        info["model_available"] = args.model in visible_model_names(models)
        if not info["model_available"]:
            raise GeminiUnavailable("Requested model is unavailable for this API key")
    return info


def run_vision(args):
    key = key_from_environment()
    if not key:
        raise GeminiUnavailable("Gemini key missing; video remains private")
    if not (args.allow_external_frames and args.rights_and_consent_cleared
            and args.accept_free_tier_terms):
        raise GeminiUnavailable(
            "Vision blocked: need --allow-external-frames, "
            "--rights-and-consent-cleared and --accept-free-tier-terms"
        )
    source = Path(args.source)
    if not source.is_file() or not args.brand_file:
        raise ValueError("Source file and brand file required")
    # Strict local input, no arbitrary URLs, no uploading the entire video.
    times = [float(x.strip()) for x in args.timestamps.split(",") if x.strip()]
    if not 1 <= len(times) <= MAX_FRAMES or any(x < 0 or x > 3600 for x in times):
        raise ValueError("Choose between one and eight valid timestamps")
    frames = [(t, sample_frame(source, t)) for t in times]
    payload = frame_request(frames, Path(args.brand_file).read_text(encoding="utf8"))
    result = make_request(BASE_URL + "/models/" + args.model + ":generateContent",
                          key, payload, timeout=55)
    report = extract_json(result)
    return {"provider": "gemini", "model": args.model, "source_sha256":
            hashlib.sha256(source.read_bytes()).hexdigest(),
            "sample_timestamps": times, "media_uploaded": True,
            "private_review_only": True, "observation": report}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Gemini integration with fail-closed media policy")
    ap.add_argument("action", choices=["preflight", "vision"])
    ap.add_argument("--model", default=MODEL, choices=[
        "gemini-3.8-flash", "gemini-3.6-flash",
        "gemini-2.5-flash", "gemini-2.5-flash-lite"])
    ap.add_argument("--verify-connection", action="store_true")
    ap.add_argument("--accept-free-tier-terms", action="store_true",
                    help="You understand free-tier input can be used to improve Google products")
    ap.add_argument("--allow-external-frames", action="store_true")
    ap.add_argument("--rights-and-consent-cleared", action="store_true")
    ap.add_argument("--source")
    ap.add_argument("--brand-file")
    ap.add_argument("--timestamps", default="0,5,10,15,20,25")
    args = ap.parse_args(argv)
    try:
        result = run_preflight(args) if args.action == "preflight" else run_vision(args)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (GeminiUnavailable, ValueError, json.JSONDecodeError,
            subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)[:160]}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
