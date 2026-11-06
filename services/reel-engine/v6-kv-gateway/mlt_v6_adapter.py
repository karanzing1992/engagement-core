#!/usr/bin/python3
"""Private MAD V6 MLT/frei0r editor. GStreamer is read-only source/output QA.

Native video editing runs through MLT XML and melt, not GES or an FFmpeg CLI.
Only vetted templates/effects are admitted. Source and output never enter logs.
"""
from __future__ import annotations
import argparse, hashlib, json, math, os, subprocess, sys
from pathlib import Path
import xml.etree.ElementTree as ET

class RenderBlocked(RuntimeError):
    pass

ENGINE="MLT Framework + frei0r"
FPS=30
# Grounded Kdenlive/MLT creative families: each maps to an installed MLT service.
# No third-party artwork or copyrighted theme media is bundled.
TEMPLATES={
 "wellness-cinema":{"contrast":0.55,"brightness":1.05,"font":"Sans","accent":"0xfff4eaff"},
 "earth-editorial":{"contrast":0.58,"brightness":1.01,"font":"Serif","accent":"0xfff2dcff"},
 "guest-story":{"contrast":0.52,"brightness":1.02,"font":"Sans","accent":"0xffffffff"},
 "social-kinetic":{"contrast":0.66,"brightness":1.06,"font":"Sans","accent":"0xffecceff"},
 "nature-minimal":{"contrast":0.51,"brightness":1.00,"font":"Serif","accent":"0xfff6edff"},
 "recovery-reset":{"contrast":0.61,"brightness":1.08,"font":"Sans","accent":"0xffffffff"},
}
# Intentionally small certified list; the full frei0r/Kdenlive ecosystem is
# discoverable but not indiscriminately enabled for AI-directed media.
ALLOWED=frozenset({"color_grade","title","caption"})
def sha256(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):h.update(block)
    return h.hexdigest()

def _prop(node,key,value):
    ET.SubElement(node,"property",{"name":str(key)}).text=str(value)

def _filter(chain,service,options,*,from_frame=0,to_frame=None):
    attrib={"in":str(from_frame)}
    if to_frame is not None:attrib["out"]=str(to_frame)
    f=ET.SubElement(chain,"filter",attrib)
    _prop(f,"mlt_service",service)
    for key,value in options.items():_prop(f,key,value)
    return f

def verify_backend():
    try:
        status=subprocess.run(["melt","-query","filters"],stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,timeout=18,check=True,text=True)
    except (OSError,subprocess.TimeoutExpired,subprocess.CalledProcessError):
        raise RenderBlocked("MLT_BINARY_UNAVAILABLE")
    available=status.stdout
    for service in ("frei0r.contrast0r","dynamictext","brightness"):
        if service not in available:
            raise RenderBlocked("MLT_REQUIRED_EFFECT_UNAVAILABLE")
    try:
        status=subprocess.run(["melt","-query","consumers"],stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,timeout=18,check=True,text=True)
    except (OSError,subprocess.TimeoutExpired,subprocess.CalledProcessError):
        raise RenderBlocked("MLT_CONSUMER_QUERY_FAILED")
    if "avformat" not in status.stdout:raise RenderBlocked("MLT_MP4_ENCODER_UNAVAILABLE")
    return {"engine":ENGINE,"checked":["frei0r.contrast0r","dynamictext","brightness","avformat"]}

def _probe(path,minimum):
    import gi
    gi.require_version("Gst","1.0")
    gi.require_version("GstPbutils","1.0")
    from gi.repository import Gst,GstPbutils
    from ges_v6_adapter import probe as decoder_probe
    Gst.init(None)
    try:info=decoder_probe(Gst,GstPbutils,path,min_duration=minimum)
    except Exception:raise RenderBlocked("MLT_MEDIA_PROBE_FAILED") from None
    return Gst,info

def _validate(spec):
    work=Path(spec["workdir"]).resolve()
    source=Path(spec["source"]).resolve()
    out=Path(spec["output"]).resolve()
    music=Path(spec["music"]).resolve()
    if any(x.parent!=work for x in (source,music,out)) or not work.is_dir():
        raise RenderBlocked("MLT_PRIVATE_WORKDIR_INVALID")
    if not source.is_file() or not music.is_file():
        raise RenderBlocked("MLT_INPUT_MISSING")
    if sha256(source)!=spec.get("source_sha256") or sha256(music)!=spec.get("music_sha256"):
        raise RenderBlocked("MLT_SOURCE_HASH_MISMATCH")
    profile=(spec.get("width",1080),spec.get("height",1920),spec.get("fps",30))
    if profile not in ((1080,1920,30),(480,270,24)):
        raise RenderBlocked("MLT_EXPORT_PROFILE_INVALID")
    template=spec.get("template_id","wellness-cinema")
    if template not in TEMPLATES:raise RenderBlocked("MLT_TEMPLATE_NOT_ALLOWLISTED")
    cuts=spec.get("cuts")
    operations=spec.get("operations")
    if not isinstance(cuts,list) or not isinstance(operations,list) or len(cuts)!=len(operations) or not 1<=len(cuts)<=16:
        raise RenderBlocked("MLT_EDL_INVALID")
    total=0
    for cut,ops in zip(cuts,operations):
        if not isinstance(cut,dict) or not isinstance(ops,list) or len(ops)>16:
            raise RenderBlocked("MLT_EDL_INVALID")
        a,b=cut.get("start"),cut.get("seconds")
        if type(a) not in (int,float) or type(b) not in (int,float) or not math.isfinite(a) or not math.isfinite(b):
            raise RenderBlocked("MLT_EDL_INVALID")
        if a<0 or not .4<=b<=120:raise RenderBlocked("MLT_EDL_INVALID")
        total+=round(b*profile[2])
        for op in ops:
            if not isinstance(op,dict) or op.get("name") not in ALLOWED or not isinstance(op.get("parameters",{}),dict):
                raise RenderBlocked("MLT_EFFECT_NOT_ALLOWLISTED")
            if op["name"] in ("title","caption"):
                txt=op["parameters"].get("text")
                if not isinstance(txt,str) or not 1<=len(txt.strip())<=90 or any(ord(c)<32 for c in txt):
                    raise RenderBlocked("MLT_TITLE_INVALID")
    hook=spec.get("hook","")
    if not isinstance(hook,str) or len(hook)>90 or any(ord(c)<32 for c in hook):
        raise RenderBlocked("MLT_HOOK_INVALID")
    if not 24<=total<=120*profile[2]:
        raise RenderBlocked("MLT_REEL_DURATION_INVALID")
    return work,source,music,out,cuts,operations,template,profile,total

def _text(chain,text,font,size,color,outframe):
    # MLT native dynamictext renders actual pixels, not metadata-only overlays.
    _filter(chain,"dynamictext",{
        "argument":text,"family":font,"size":size,"weight":650,
        "fgcolour":color,"bgcolour":"0x00000060",
        "geometry":"5%/57%:90%x20%:100",
        "halign":"centre","valign":"middle","pad":12,
    },to_frame=outframe)

def build_xml(spec):
    work,source,music,out,cuts,operations,template,profile,total=_validate(spec)
    fps=profile[2]
    template_data=TEMPLATES[template]
    Gst,srcinfo=_probe(source,2.5)
    _Gst,musicinfo=_probe_audio(music)
    if musicinfo["duration"]+0.08<total/fps:
        raise RenderBlocked("MLT_MUSIC_TOO_SHORT")
    if any(c["start"]+c["seconds"]>srcinfo["duration"]+.02 for c in cuts):
        raise RenderBlocked("MLT_SOURCE_BOUNDS")
    root=ET.Element("mlt",{"producer":"master","title":"MAD V6 Private MLT","root":str(work)})
    ET.SubElement(root,"profile",{
       "description":"MAD V6 9:16 private" if profile[0]==1080 else "MAD V6 synthetic",
       "width":str(profile[0]),"height":str(profile[1]),
       "progressive":"1","frame_rate_num":str(fps),"frame_rate_den":"1",
       "sample_aspect_num":"1","sample_aspect_den":"1",
       "display_aspect_num":str(profile[0]),"display_aspect_den":str(profile[1]),"colorspace":"709"})
    source_video=ET.SubElement(root,"playlist",{"id":"video_sequence"})
    _prop(source_video,"shotcut:name","Verified footage")
    nops=0
    effect_ids=[]
    for i,(cut,ops) in enumerate(zip(cuts,operations)):
        start=round(cut["start"]*fps)
        frames=round(cut["seconds"]*fps)
        chain=ET.Element("chain",{"id":"clip_"+str(i)})
        _prop(chain,"mlt_service","avformat")
        _prop(chain,"resource",str(source))
        _prop(chain,"mute_on_pause",0)
        _filter(chain,"frei0r.contrast0r",{"0":template_data["contrast"]},to_frame=start+frames-1)
        nops+=1;effect_ids.append("template:"+template+":contrast")
        if template_data["brightness"]!=1:
            _filter(chain,"brightness",{"level":template_data["brightness"]},to_frame=start+frames-1)
            nops+=1;effect_ids.append("template:"+template+":brightness")
        for op in ops:
            effect=op["name"]
            if effect=="color_grade":
                param=op["parameters"]
                delta=float(param.get("contrast",0))
                if not math.isfinite(delta) or not -100<=delta<=100:
                    raise RenderBlocked("MLT_GRADE_INVALID")
                _filter(chain,"frei0r.contrast0r",{"0":round(max(.05,min(.95,.5+delta/400)),3)},to_frame=start+frames-1)
            elif effect in ("title","caption"):
                _text(chain,op["parameters"]["text"],template_data["font"],
                      53 if effect=="caption" else 76,template_data["accent"],start+frames-1)
            nops+=1;effect_ids.append(str(op.get("id",effect)))
        if i==0 and spec.get("hook",""):
            _text(chain,spec["hook"],template_data["font"],88,template_data["accent"],
                  start+min(frames-1,round(2.5*fps)-1))
            nops+=1;effect_ids.append("hook")
        root.insert(1+i,chain)
        ET.SubElement(source_video,"entry",{"producer":"clip_"+str(i),"in":str(start),"out":str(start+frames-1)})
    audio_chain=ET.Element("chain",{"id":"original_audio"})
    _prop(audio_chain,"mlt_service","avformat")
    _prop(audio_chain,"resource",str(music))
    _prop(audio_chain,"audio_index",0)
    root.insert(len(cuts)+1,audio_chain)
    audio_playlist=ET.SubElement(root,"playlist",{"id":"approved_original_soundtrack"})
    ET.SubElement(audio_playlist,"entry",{"producer":"original_audio","in":"0","out":str(total-1)})
    tractor=ET.SubElement(root,"tractor",{"id":"master","in":"0","out":str(total-1)})
    ET.SubElement(tractor,"track",{"producer":"video_sequence"})
    ET.SubElement(tractor,"track",{"producer":"approved_original_soundtrack","hide":"video"})
    transition=ET.SubElement(tractor,"transition",{"in":"0","out":str(total-1)})
    for key,value in {"mlt_service":"mix","a_track":"0","b_track":"1","start":"0.8","end":"0.8","combine":"1"}.items():
        _prop(transition,key,value)
    xml_path=work/"private-mlt-timeline.xml"
    ET.ElementTree(root).write(xml_path,encoding="utf-8",xml_declaration=True)
    return {"xml":xml_path,"output":out,"source":source,"music":music,
            "width":profile[0],"height":profile[1],"fps":fps,
            "duration":total/fps,"operations":nops,"effect_ids":effect_ids,
            "template_id":template}

def _probe_audio(path):
    import gi
    gi.require_version("Gst","1.0")
    gi.require_version("GstPbutils","1.0")
    from gi.repository import Gst,GstPbutils
    Gst.init(None)
    d=GstPbutils.Discoverer.new(15*Gst.SECOND)
    try:info=d.discover_uri(path.as_uri())
    except Exception:raise RenderBlocked("MLT_MUSIC_PROBE_FAILED") from None
    if not info.get_audio_streams():raise RenderBlocked("MLT_MUSIC_AUDIO_MISSING")
    return Gst,{"duration":info.get_duration()/Gst.SECOND}

def render(spec):
    verify_backend()
    entry=build_xml(spec)
    xml=entry["xml"];out=entry["output"]
    argv=["melt",str(xml),"-silent","-consumer","avformat:"+str(out),
          "f=mp4","vcodec=libx264","acodec=aac","ab=160k",
          "pix_fmt=yuv420p","crf=23","preset=veryfast",
          "real_time=-1","threads=2","audio_channels=2","ar=48000"]
    try:
        subprocess.run(argv,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
            timeout=min(600,max(65,entry["duration"]*14)),check=True,cwd=str(xml.parent))
    except subprocess.TimeoutExpired:raise RenderBlocked("MLT_RENDER_TIMEOUT") from None
    except (OSError,subprocess.CalledProcessError):
        raise RenderBlocked("MLT_RENDER_COMMAND_FAILED") from None
    if not out.is_file() or out.stat().st_size<4096:
        raise RenderBlocked("MLT_OUTPUT_MISSING")
    Gst,metadata=_probe(out,1.)
    if metadata["width"]!=entry["width"] or metadata["height"]!=entry["height"] or not metadata["audio"]:
        raise RenderBlocked("MLT_OUTPUT_MEDIA_INVALID")
    if abs(metadata["duration"]-entry["duration"])>.5:
        raise RenderBlocked("MLT_OUTPUT_DURATION_INVALID")
    from ges_v6_adapter import check_frames
    try:
        srcdur=_probe(entry["source"],2.5)[1]["duration"]
        visual=check_frames(Gst,entry["source"],out,srcdur,metadata["duration"],spec["cuts"])
    except Exception:raise RenderBlocked("MLT_VIDEO_DECODE_INVALID") from None
    if visual.get("visible") is not True:raise RenderBlocked("MLT_VISUAL_CONTENT_MISSING")
    return {"engine":ENGINE,"mlt_only":True,"frei0r_verified":True,
        "gstreamer_only":False,"filmcraft_only":False,
        "ffmpeg_invocations":0,"libav_codec_backend":True,
        "rendered":True,"sha256":sha256(out),"bytes":out.stat().st_size,
        "width":entry["width"],"height":entry["height"],"fps":entry["fps"],
        "duration_seconds":metadata["duration"],"output_audio_verified":metadata["audio"],
        "music_native_probed":True,"audio_mixed":metadata["audio"],
        "template_id":entry["template_id"],"template_effect_ids":entry["effect_ids"],
        "operations_requested":entry["operations"],
        "operations_command_accepted":entry["operations"],
        "operations_visually_verified":0,"visual_presence_check":visual,
        "independent_visual_and_audio_review":"PENDING",
        "creative_complete":False,"published":False}

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--spec",required=True)
    ap.add_argument("--receipt",required=True)
    x=ap.parse_args()
    try:
        p=json.loads(Path(x.spec).read_text())
        rec=render(p)
        Path(x.receipt).write_text(json.dumps(rec,separators=(",",":")))
        print("MAD_V6_MLT_PRIVATE_DECODED_VIDEO_AND_AUDIO_PASS")
    except Exception as e:
        print("MAD_V6_MLT_RENDER_BLOCKED "+(str(e) if isinstance(e,RenderBlocked) else "UNCLASSIFIED"),file=sys.stderr)
        raise SystemExit(2)
