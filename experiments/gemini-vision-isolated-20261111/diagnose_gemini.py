#!/usr/bin/env python3
"""Bounded Gemini diagnosis: metadata, text, one synthetic image; no release."""
import base64
import io
import json
import os
from pathlib import Path
import socket
import sys
import urllib.error
import urllib.request
from PIL import Image, ImageDraw

BASE = "https://generativelanguage.googleapis.com/v1beta"
OUT = Path("out/private-gemini-vision-review")
OUT.mkdir(parents=True, exist_ok=True)

def request(path, key, body=None):
    assert path.startswith("/models") and ".." not in path
    payload = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        BASE + path, data=payload,
        headers={"x-goog-api-key": key, "Content-Type": "application/json"},
        method="POST" if payload else "GET")
    try:
        with urllib.request.urlopen(req, timeout=24) as response:
            return json.loads(response.read(300000))
    except urllib.error.HTTPError as exc:
        raise RuntimeError("HTTP_" + str(exc.code)) from None
    except (TimeoutError, socket.timeout, urllib.error.URLError):
        raise RuntimeError("NETWORK_TIMEOUT") from None

def generate(key, model, parts):
    result=request("/models/"+model+":generateContent",key,{
       "contents":[{"parts":parts}],
       "generationConfig":{"temperature":0,"maxOutputTokens":160}
    })
    candidates=result.get("candidates") or []
    if not candidates:
        raise RuntimeError("NO_CANDIDATES")
    candidate=candidates[0]
    message="".join(p.get("text","") for p in candidate.get("content",{}).get("parts",[]) if isinstance(p,dict))
    return {"finish_reason":candidate.get("finishReason"),
            "text":message[:240],
            "response_length":len(message),
            "usage":(result.get("usageMetadata") or {}).get("candidatesTokenCount")}

def main():
    key=os.getenv("GEMINI_API_KEY","")
    if not key:
        raise RuntimeError("SECRET_NOT_CONFIGURED")
    metadata=request("/models?pageSize=100",key)
    supported={m.get("name","").removeprefix("models/") for m in metadata.get("models",[])
               if "generateContent" in m.get("supportedGenerationMethods",[])}
    allowed=("gemini-3.5-flash-lite","gemini-3.8-flash","gemini-3.6-flash")
    choices=[m for m in allowed if m in supported]
    if not choices:
        raise RuntimeError("NO_ALLOWED_MODEL")
    model=choices[0]
    print("MODEL_DISCOVERY_OK candidate="+model+" count="+str(len(choices)),flush=True)
    diag={"schema":"gemini-api-diagnostic-v1","model":model,"metadata_ok":True,
          "text":{"status":"NOT_RUN"},"image":{"status":"NOT_RUN"},
          "artistic_score":None,"release_authorized":False}
    try:
        r=generate(key,model,[{"text":"Reply with exactly the single word READY."}])
        diag["text"]={"status":"PASS" if "READY" in r["text"].upper() else "UNEXPECTED_TEXT",
                      "finish_reason":r["finish_reason"],"characters":r["response_length"],
                      "output_tokens":r["usage"]}
        print("TEXT_PROBE_"+diag["text"]["status"],flush=True)
    except RuntimeError as e:
        diag["text"]={"status":"BLOCKED","reason":str(e)}
        print("TEXT_PROBE_BLOCKED_"+str(e),flush=True)
    img=Image.new("RGB",(96,96),"#d21b25")
    draw=ImageDraw.Draw(img)
    draw.rectangle((8,8,88,88),fill="#ed1018")
    buffer=io.BytesIO()
    img.save(buffer,format="PNG")
    part={"inline_data":{"mime_type":"image/png","data":base64.b64encode(buffer.getvalue()).decode()}}
    try:
        r=generate(key,model,[{"text":"What is the dominant color in this image? Respond with one color word."},part])
        status="PASS" if "red" in r["text"].lower() else "UNEXPECTED_TEXT"
        diag["image"]={"status":status,"finish_reason":r["finish_reason"],
                       "characters":r["response_length"],"output_tokens":r["usage"],
                       "recognizes_red":status=="PASS"}
        print("IMAGE_PROBE_"+status,flush=True)
    except RuntimeError as e:
        diag["image"]={"status":"BLOCKED","reason":str(e)}
        print("IMAGE_PROBE_BLOCKED_"+str(e),flush=True)
    # Actual live website screenshot: one compressed public-frame test, no JSON mode.
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True)
            try:
                page=browser.new_page(viewport={"width":390,"height":844},service_workers="block")
                response=page.goto("https://andazgoa.com/",wait_until="domcontentloaded",timeout=45000)
                if not response or response.status>=400:
                    raise RuntimeError("PUBLIC_SITE_UNAVAILABLE")
                page.wait_for_timeout(1000)
                raw=page.screenshot(type="png",full_page=False)
            finally:
                browser.close()
        screenshot=Image.open(io.BytesIO(raw)).convert("RGB")
        screenshot.thumbnail((384,512))
        f=io.BytesIO()
        screenshot.save(f,format="JPEG",quality=49,optimize=True)
        encoded=f.getvalue()
        if not 1000 < len(encoded) < 200000:
            raise RuntimeError("IMAGE_SIZE_UNEXPECTED")
        p={"inline_data":{"mime_type":"image/jpeg","data":base64.b64encode(encoded).decode()}}
        r=generate(key,model,[{"text":"Describe in one short sentence what this website screenshot shows."},p])
        status="PASS" if len(r["text"].strip())>=8 else "EMPTY_RESPONSE"
        diag["actual_site_single_image"]={"status":status,
               "finish_reason":r["finish_reason"],"output_characters":r["response_length"],
               "compressed_bytes":len(encoded)}
        print("ACTUAL_SITE_SINGLE_IMAGE_"+status,flush=True)
    except Exception as e:
        diag["actual_site_single_image"]={"status":"BLOCKED","reason":str(e)[:80]}
        print("ACTUAL_SITE_SINGLE_IMAGE_BLOCKED_"+str(e)[:80],flush=True)
    (OUT/"diagnostic.json").write_text(json.dumps(diag,indent=2)+"\n")
    if diag["image"]["status"]!="PASS" or diag["text"]["status"]!="PASS" or diag.get("actual_site_single_image",{}).get("status")!="PASS":
        raise RuntimeError("MODEL_CAPABILITY_NOT_CERTIFIED")
    print("GEMINI_BASIC_MULTIMODAL_VERIFIED; ARTISTIC_CERTIFICATION_NOT_GRANTED")

if __name__=="__main__":
    try: main()
    except Exception as exc:
        print("DIAGNOSTIC_FAIL_CLOSED "+str(exc)[:80],file=sys.stderr)
        sys.exit(1)
