#!/usr/bin/env python3
"""Synthetic-only (zero customer data) V4.2 Gemini -> Groq 120B -> 20B -> FFmpeg pilot.

NEVER point this program at user footage. It synthesizes its own five scenes and
sends only its own small JPEG drawings to Gemini; no brand secrets, no third-party
people, and no real client media. Each stage must succeed to certify the run.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from PIL import Image, ImageDraw
from gemini_adapter import BASE_URL, MODEL, GeminiUnavailable, extract_json, frame_request, make_request
from creative_director import check_concepts, compile_edl, _call_groq

HERE = Path(__file__).resolve().parent
OUT = HERE / "synthetic_output"
OUT.mkdir(parents=True, exist_ok=True)
COLORS = ["#204E6C", "#587545", "#A77A4D", "#D4A55B", "#18382F"]
SCENES = [
    ("Water reflections", "flat blue water with light ripples", "#204E6C"),
    ("Leaves in daylight", "green tree foliage against warm background", "#587545"),
    ("Coastal stones", "brown layered stones with sandy shadows", "#A77A4D"),
    ("Warm sunlight", "golden sunlight through a dark silhouette", "#D4A55B"),
    ("Forest evening", "deep forest greenery with subtle soft light", "#18382F")
]
BRAND = ("Moksha Wellness visual direction only: rooted in nature, quietly premium, "
         "authentic sensory footage, Forest #18382F, Ivory #F9F5EA, restrained "
         "Gold #C5A15A. Never claim synthetic scenes are the Moksha venue. "
         "No medical claims, fake guests or logos; artistic preview only.")
def paint(i, name, desc, color):
    img = Image.new("RGB", (360, 640), color)
    d = ImageDraw.Draw(img)
    if i == 0:
        for y in range(160, 620, 38):
            d.arc((12, y, 340, y+110), 0, 180, fill="#9BC5D1", width=4)
    elif i == 1:
        d.line((190, 650, 175, 60), fill="#554735", width=24)
        for x,y in [(75,130),(230,150),(100,250),(265,300)]:
            d.ellipse((x-82,y-66,x+82,y+66), fill="#7B9852", outline="#C7D28F", width=3)
    elif i == 2:
        for box in [(20,330,220,430),(120,230,335,330),(40,455,335,570)]:
            d.rounded_rectangle(box,radius=17,fill="#D4BA93",outline="#654936",width=8)
    elif i == 3:
        d.ellipse((90,120,275,305), fill="#FBE7A2")
        for x in [60,105,155,220,280]:
            d.line((x,640,x+35,325), fill="#234438",width=28)
    else:
        for x in [30,105,200,310]:
            d.line((x,640,x-15,90),fill="#0B2923",width=29)
            d.ellipse((x-84,55,x+85,285),fill="#42684B",outline="#94A86D",width=4)
    # Accurate, on-art labels explicitly mark every image as a generated test fixture.
    d.rectangle((0,555,360,640),fill="#18382F")
    d.text((22,579), "SYNTHETIC TEST - " + str(i+1),fill="#F9F5EA")
    png=OUT/("scene_%s.png"%(i+1))
    jpg=OUT/("scene_%s.jpg"%(i+1))
    img.save(png)
    img.save(jpg,quality=83)
    return jpg.read_bytes()

def call_gemini():
    key=os.environ.get("GEMINI_API_KEY","")
    if not key:
        raise RuntimeError("GEMINI_API_KEY missing")
    imgs=[(float(i*8),paint(i,*scene)) for i,scene in enumerate(SCENES)]
    payload=frame_request(imgs,BRAND)
    response=None
    for attempt in range(3):
        try:
            response=make_request(BASE_URL + "/models/" + MODEL + ":generateContent",key,payload,timeout=75)
            break
        except GeminiUnavailable as e:
            if "HTTP 503" not in str(e) or attempt == 2:
                raise
            print("GEMINI_TRANSIENT_503_RETRY", attempt + 1, flush=True)
            time.sleep(3 * (attempt + 1))
    extracted=extract_json(response)
    # This is not trusted footage provenance: inspect the result and keep only text.
    if not isinstance(extracted.get("shots"),list) or not extracted["shots"]:
        raise RuntimeError("Gemini did not describe the synthetic frames")
    (OUT/"gemini_observations.json").write_text(json.dumps(extracted,indent=2))
    return extracted

def call_director(gemini):
    key=os.environ.get("GROQ_API_KEY","")
    if not key:
        raise RuntimeError("GROQ_API_KEY missing")
    from groq import Groq
    client=Groq(api_key=key,timeout=65,max_retries=0)
    shots={}
    for i,(name,desc,color) in enumerate(SCENES):
        sid="S"+str(i+1)
        # Synthetic source facts authored directly by this same generator.
        shots[sid]={"id":sid,"start":i*8.0,"duration":8.0,
                    "visible":desc}
    prompt=(
      "You are the senior film creative director. On these SYNTHETIC DRAWINGS ONLY, "
      "generate three original and genuinely DIFFERENT storyboards. "
      "Use the image descriptions returned by Gemini as visual corroboration; "
      "if uncertain follow verified source descriptions. "
      "Output only JSON object with key versions, exactly 3 versions A,B,C. "
      "Each: id, name, hook, narrative, segments exactly 6 entries. "
      "Each segment: shot_id one of S1..S5, duration_seconds exactly 2.5, "
      "caption short 0..35 characters. Reuse source shots if necessary. "
      "Open with distinct shots for A,B,C. Keep 15s per version. "
      "Storytelling distinct by pacing, theme and ordering; not merely text. "
      "No invented Moksha setting, characters or music. \nBRAND: " + BRAND +
      "\nSYNTHETIC SOURCE: " + json.dumps(shots) +
      "\nGEMINI OBSERVATIONS: " + json.dumps(gemini)[:6500])
    raw=_call_groq(client,"openai/gpt-oss-120b",prompt,0.85,tokens=4700)
    concepts=check_concepts(raw,shots)
    (OUT/"director_120b.json").write_text(json.dumps({"versions":concepts},indent=2))
    return client,shots,concepts

def call_execution(client,concepts):
    prompt=("You are ONLY the technical editor. The creative storyboards are approved "
            "and unchangeable. Output JSON object with key edits, mapping each ID A/B/C "
            "to {pace: 'serene'|'medium'|'kinetic', transition: 'cut'}. "
            "Use no shell commands, file paths, online media, or new footage. "
            "Never change source timestamps. Here are the plans: "
            + json.dumps(concepts)[:6500])
    result=_call_groq(client,"openai/gpt-oss-20b",prompt,0.15,tokens=950)
    vals=result.get("edits")
    if not isinstance(vals,dict) or set(vals)!={"A","B","C"}:
        raise RuntimeError("20B returned invalid execution style plan")
    for id_,v in vals.items():
        if v.get("pace") not in {"serene","medium","kinetic"} or v.get("transition") != "cut":
            raise RuntimeError("20B attempted unapproved edit parameter")
    (OUT/"execution_20b.json").write_text(json.dumps(vals,indent=2))
    return vals

def render(concepts,shots,styles):
    edls=compile_edl(concepts,shots)
    (OUT/"verified_edl.json").write_text(json.dumps(edls,indent=2))
    outputs=[]
    for v in edls:
        concat=OUT/("version_%s.ffconcat"%v["id"])
        lines=["ffconcat version 1.0"]
        for c in v["commands"]:
            id_=int(c["shot_id"][1:])
            lines.append("file 'scene_%s.png'"%id_)
            lines.append("duration %.3f"%c["duration_seconds"])
        lines.append("file 'scene_%s.png'"%int(v["commands"][-1]["shot_id"][1:]))
        concat.write_text("\n".join(lines)+"\n")
        out=OUT/("version_%s.mp4"%v["id"])
        subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y",
                        "-safe","0","-f","concat","-i",str(concat),"-vf",
                        "fps=%d,format=yuv420p" % {"serene":12,"medium":15,"kinetic":20}[styles[v["id"]]["pace"]],"-an","-c:v","libx264",
                        "-threads","2","-preset","ultrafast","-crf","29",
                        "-t","15","-movflags","+faststart",str(out)],
                        check=True,timeout=90)
        ffprobe=subprocess.run(["ffprobe","-v","error","-show_entries",
                                "stream=width,height,codec_name",
                                "-show_entries","format=duration","-of","json",
                                str(out)],capture_output=True,text=True,check=True,timeout=15)
        probe=json.loads(ffprobe.stdout)
        if not any(s.get("codec_name")=="h264" and s.get("width")==360 and s.get("height")==640 for s in probe["streams"]):
            raise RuntimeError("Video export invalid")
        subprocess.run(["ffmpeg","-hide_banner","-v","error","-i",str(out),"-f","null","-"],
                        check=True,capture_output=True,timeout=45)
        outputs.append({"version":v["id"],"duration":float(probe["format"]["duration"]),
                        "sha256":hashlib.sha256(out.read_bytes()).hexdigest(),
                        "file":out.name,"bytes":out.stat().st_size})
        print("SYNTHETIC_RENDER_PASS",v["id"],outputs[-1]["sha256"],flush=True)
    return outputs

def main():
    receipt={"version":"4.2-synthetic-smoke","provider_order":
             ["gemini-3.8-flash","openai/gpt-oss-120b","openai/gpt-oss-20b","ffmpeg"],
             "real_media_uploaded":False,"real_media_rendered":False,
             "real_media_publishing":False,"status":"STARTED"}
    try:
        gemini=call_gemini()
        print("GEMINI_SYNTHETIC_VISION_PASS",len(gemini["shots"]),flush=True)
        client,shots,concepts=call_director(gemini)
        print("GROQ_120B_DIRECTOR_PASS",len(concepts),flush=True)
        styles=call_execution(client,concepts)
        print("GROQ_20B_STYLE_PASS",flush=True)
        receipt["outputs"]=render(concepts,shots,styles)
        receipt["status"]="PASS"
        print("V42_SYNTHETIC_ALL_STAGES_PASS",flush=True)
    except Exception as e:
        receipt["status"]="FAIL"
        receipt["error"]=type(e).__name__ + ": " + str(e)[:250]
        print("V42_SYNTHETIC_FAIL",receipt["error"],flush=True)
        raise
    finally:
        (OUT/"synthetic_certification_receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")

if __name__=="__main__":
    main()
