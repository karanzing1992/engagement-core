#!/usr/bin/python3
"""MAD V6 GStreamer Editing Services renderer (no FilmCraft, no FFmpeg CLI).
Uses system GES 1.24 Python introspection. Media never leaves isolated job temp.
"""
from __future__ import annotations
import argparse, hashlib, json, math, os, sys
from pathlib import Path

class RenderBlocked(RuntimeError): pass

def sha256(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda:f.read(1048576),b""):h.update(block)
    return h.hexdigest()

def backend():
    import gi
    gi.require_version("Gst","1.0")
    gi.require_version("GES","1.0")
    gi.require_version("GstPbutils","1.0")
    from gi.repository import Gst,GES,GstPbutils
    Gst.init(None)
    GES.init()
    for el in ("uridecodebin","videoconvert","videoscale","x264enc","mp4mux","appsink"):
        if not Gst.ElementFactory.find(el):
            raise RenderBlocked("GSTREAMER_REQUIRED_ELEMENT_MISSING")
    return Gst,GES,GstPbutils

def probe(Gst,GstPbutils,path):
    d=GstPbutils.Discoverer.new(15*Gst.SECOND)
    info=d.discover_uri(Path(path).resolve().as_uri())
    vids=info.get_video_streams() or []
    if not vids:raise RenderBlocked("VIDEO_STREAM_MISSING")
    duration=info.get_duration()/Gst.SECOND
    if not (2.5<=duration<=480):raise RenderBlocked("VIDEO_DURATION_INVALID")
    return {"duration":duration,"width":vids[0].get_width(),"height":vids[0].get_height(),
        "audio":bool(info.get_audio_streams())}

def render(spec):
    Gst,GES,GstPbutils=backend()
    output=Path(spec["output"]).resolve();work=Path(spec["workdir"]).resolve()
    source=Path(spec["source"]).resolve()
    if not source.is_file() or source.parent!=work or output.parent!=work:
        raise RenderBlocked("SOURCE_OUTSIDE_PRIVATE_WORKDIR")
    if sha256(source)!=spec.get("source_sha256"):
        raise RenderBlocked("SOURCE_HASH_MISMATCH")
    source_info=probe(Gst,GstPbutils,source)
    width,height,fps=spec.get("width",1080),spec.get("height",1920),spec.get("fps",30)
    if (width,height,fps) not in ((1080,1920,30),(480,270,24)):
        raise RenderBlocked("EXPORT_PROFILE_INVALID")
    cuts=spec.get("cuts") or []
    ops=spec.get("operations") or []
    if len(cuts)!=len(ops) or not (1<=len(cuts)<=16):
        raise RenderBlocked("EDIT_LIST_INVALID")
    total=0.
    for cut,actions in zip(cuts,ops):
        start,secs=float(cut["start"]),float(cut["seconds"])
        if not(0<=start and .4<=secs<=120 and start+secs<=source_info["duration"]+.03):
            raise RenderBlocked("CUT_SOURCE_BOUNDS")
        if not isinstance(actions,list):raise RenderBlocked("EFFECTS_INVALID")
        for op in actions:
            if op.get("name") not in ("color_grade","title","caption"):
                raise RenderBlocked("UNSUPPORTED_GES_EFFECT")
            if op.get("name") in ("title","caption"):
                line=str(op.get("parameters",{}).get("text","")).strip()
                if not(1<=len(line)<=90):raise RenderBlocked("TITLE_TEXT_MISSING")
        total+=secs
    if not (1<=total<=120):raise RenderBlocked("REEL_DURATION_INVALID")
    musicfile=spec.get("music")
    music=None
    if musicfile:
        music=Path(musicfile).resolve()
        if music.parent!=work or not music.is_file() or sha256(music)!=spec.get("music_sha256"):
            raise RenderBlocked("MUSIC_ADMISSION_REJECTED")
        music_info=probe_audio(Gst,GstPbutils,music)
        if music_info["duration"]+.05<total:raise RenderBlocked("MUSIC_TOO_SHORT")
    timeline=GES.Timeline.new_audio_video()
    base=timeline.append_layer()
    tracktype=GES.TrackType.VIDEO | (GES.TrackType.AUDIO if source_info["audio"] else GES.TrackType.UNKNOWN)
    asset=GES.UriClipAsset.request_sync(source.as_uri())
    cursor=0.
    confirmed=0
    for cut,actions in zip(cuts,ops):
        start,seconds=float(cut["start"]),float(cut["seconds"])
        clip=base.add_asset(asset,round(cursor*Gst.SECOND),round(start*Gst.SECOND),
                            round(seconds*Gst.SECOND),tracktype)
        if not clip:raise RenderBlocked("GES_VIDEO_CLIP_INSERT_FAILED")
        for op in actions:
            name=op["name"]
            if name=="color_grade":
                v=op.get("parameters",{})
                c=max(.8,min(1.3,1.0+float(v.get("contrast",0))/100))
                effect=GES.Effect.new("videobalance contrast="+str(c))
                if not effect or not clip.add(effect):
                    raise RenderBlocked("GES_COLOR_GRADE_FAILED")
            else:
                line=op["parameters"]["text"]
                title=GES.TitleClip.new()
                title.set_text(line)
                title.set_font_desc("Sans Bold 55")
                title.props.start=round(cursor*Gst.SECOND)
                title.props.duration=round(min(seconds,2.8)*Gst.SECOND)
                # Each title gets its own video layer. GES rejects overlapping
                # timeline clips within the same layer in multisegment edits.
                title_layer=timeline.append_layer()
                if not title_layer.add_clip(title):
                    raise RenderBlocked("GES_TITLE_INSERT_FAILED")
            confirmed+=1
        cursor+=seconds
    hook=str(spec.get("hook","")).strip()
    if hook:
        title=GES.TitleClip.new()
        title.set_text(hook[:90])
        title.set_font_desc("Sans Bold 68")
        title.props.start=0
        title.props.duration=round(min(2.5,total)*Gst.SECOND)
        hook_layer=timeline.append_layer()
        if not hook_layer.add_clip(title):raise RenderBlocked("GES_HOOK_INSERT_FAILED")
    if music:
        layer=timeline.append_layer()
        music_asset=GES.UriClipAsset.request_sync(music.as_uri())
        sound=layer.add_asset(music_asset,0,0,round(total*Gst.SECOND),GES.TrackType.AUDIO)
        if not sound:raise RenderBlocked("GES_MUSIC_TRACK_REJECTED")
    timeline.commit()
    pipe=GES.Pipeline.new()
    if not pipe.set_timeline(timeline):raise RenderBlocked("GES_TIMELINE_REJECTED")
    prof=GstPbutils.EncodingContainerProfile.new(
        "mad-v6","Private GStreamer MP4",
        Gst.Caps.from_string("video/quicktime,variant=(string)iso"),None)
    vp=GstPbutils.EncodingVideoProfile.new(
        Gst.Caps.from_string("video/x-h264"),None,
        Gst.Caps.from_string("video/x-raw,width=(int)%d,height=(int)%d,framerate=(fraction)%d/1,pixel-aspect-ratio=(fraction)1/1"%(width,height,fps)),1)
    if not prof.add_profile(vp):raise RenderBlocked("GES_VIDEO_ENCODING_PROFILE_REJECTED")
    ap=GstPbutils.EncodingAudioProfile.new(
        Gst.Caps.from_string("audio/mpeg,mpegversion=(int)4"),None,
        Gst.Caps.from_string("audio/x-raw,rate=(int)48000,channels=(int)2"),1)
    if not prof.add_profile(ap):raise RenderBlocked("GES_AUDIO_ENCODING_PROFILE_REJECTED")
    if not pipe.set_render_settings(output.as_uri(),prof):
        raise RenderBlocked("GES_RENDER_SETTINGS_REJECTED")
    if not pipe.set_mode(GES.PipelineFlags.RENDER):
        raise RenderBlocked("GES_RENDER_MODE_REJECTED")
    try:
        if pipe.set_state(Gst.State.PLAYING)==Gst.StateChangeReturn.FAILURE:
            raise RenderBlocked("GES_PLAYBACK_PIPELINE_FAILURE")
        bus=pipe.get_bus()
        msg=bus.timed_pop_filtered(round(min(600,max(50,total*12))*Gst.SECOND),
            Gst.MessageType.EOS|Gst.MessageType.ERROR)
        if msg is None:raise RenderBlocked("GES_RENDER_TIMEOUT")
        if msg.type==Gst.MessageType.ERROR:raise RenderBlocked("GES_RENDER_BUS_ERROR")
    finally:pipe.set_state(Gst.State.NULL)
    if not output.exists() or output.stat().st_size<4096:
        raise RenderBlocked("GES_OUTPUT_MISSING")
    out_info=probe(Gst,GstPbutils,output)
    if out_info["width"]!=width or out_info["height"]!=height or not out_info["audio"]:
        raise RenderBlocked("GES_OUTPUT_STREAMS_INVALID")
    # Audio metadata and a video track are necessary but not sufficient.
    visual=check_frames(Gst,source,output,source_info["duration"],out_info["duration"],cuts)
    if not visual["visible"]:raise RenderBlocked("GES_VISUAL_CONTENT_MISSING")
    digest=sha256(output)
    return {"engine":"GStreamer Editing Services","gstreamer_only":True,
        "filmcraft_only":False,"ffmpeg_invocations":0,"rendered":True,
        "sha256":digest,"bytes":output.stat().st_size,"width":width,
        "height":height,"fps":fps,"duration_seconds":out_info["duration"],
        "output_audio_verified":out_info["audio"],"source_audio_detected":source_info["audio"],
        "music_native_probed":bool(music),"operations_requested":confirmed,
        "operations_command_accepted":confirmed,
        "operations_visually_verified":0,
        "visual_presence_check":visual,"creative_complete":False,
        "independent_visual_and_audio_review":"PENDING","published":False}

def probe_audio(Gst,GstPbutils,path):
    d=GstPbutils.Discoverer.new(15*Gst.SECOND)
    info=d.discover_uri(path.as_uri())
    if not info.get_audio_streams():raise RenderBlocked("MUSIC_AUDIO_STREAM_MISSING")
    return {"duration":info.get_duration()/Gst.SECOND}

def sample_gray(Gst,path,seconds):
    # Native GStreamer decoder + appsink: no video frames written to disk or logged.
    pipe=Gst.Pipeline.new(None)
    src=Gst.ElementFactory.make("uridecodebin")
    queue=Gst.ElementFactory.make("queue")
    cv=Gst.ElementFactory.make("videoconvert")
    scale=Gst.ElementFactory.make("videoscale")
    cap=Gst.ElementFactory.make("capsfilter")
    sink=Gst.ElementFactory.make("appsink")
    if any(x is None for x in (src,queue,cv,scale,cap,sink)):
        raise RenderBlocked("VISUAL_DECODER_UNAVAILABLE")
    src.set_property("uri",Path(path).as_uri())
    cap.set_property("caps",Gst.Caps.from_string("video/x-raw,format=GRAY8,width=64,height=64"))
    sink.set_property("sync",False)
    sink.set_property("max-buffers",2)
    sink.set_property("drop",True)
    for el in (src,queue,cv,scale,cap,sink):pipe.add(el)
    if not queue.link(cv) or not cv.link(scale) or not scale.link(cap) or not cap.link(sink):
        raise RenderBlocked("VISUAL_DECODER_LINK_FAILED")
    def padded(source,pad):
        caps=pad.get_current_caps()
        if caps is not None and caps.to_string().startswith("video/"):
            pad.link(queue.get_static_pad("sink"))
    src.connect("pad-added",padded)
    try:
        pipe.set_state(Gst.State.PAUSED)
        pipe.get_state(8*Gst.SECOND)
        pipe.seek_simple(Gst.Format.TIME,Gst.SeekFlags.FLUSH|Gst.SeekFlags.KEY_UNIT,round(seconds*Gst.SECOND))
        pipe.set_state(Gst.State.PLAYING)
        sample=sink.emit("try-pull-sample",8*Gst.SECOND)
        if not sample:raise RenderBlocked("VIDEO_FRAME_NOT_DECODABLE")
        buf=sample.get_buffer()
        ok,mapping=buf.map(Gst.MapFlags.READ)
        if not ok:raise RenderBlocked("FRAME_READ_FAILED")
        try:
            data=bytes(mapping.data)
        finally:buf.unmap(mapping)
        if not data:raise RenderBlocked("FRAME_EMPTY")
        mean=sum(data)/len(data)
        variance=sum((v-mean)**2 for v in data)/len(data)
        return {"mean":round(mean,2),"variance":round(variance,2)}
    finally:pipe.set_state(Gst.State.NULL)

def check_frames(Gst,source,output,source_duration,output_duration,cuts):
    times=[min(output_duration*.3,1.5),output_duration*.55,output_duration*.75]
    sample_out=[sample_gray(Gst,output,max(.1,t)) for t in times]
    # Source is independently decoded; prevent approval of black output over visible input.
    mid=float(cuts[0]["start"])+min(float(cuts[0]["seconds"])*.5,source_duration*.5)
    sample_source=sample_gray(Gst,source,max(.1,mid))
    seen=max(x["variance"] for x in sample_out)
    threshold=max(4.0,min(20.,sample_source["variance"]*.15))
    return {"visible":sum(x["variance"]>threshold for x in sample_out)>=2,"output_variance_peak":round(seen,2),
        "source_variance_reference":sample_source["variance"],"threshold":round(threshold,2),
        "frames_examined":len(sample_out),"method":"gstreamer_native_gray_frames"}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--spec",required=True)
    p.add_argument("--receipt",required=True)
    a=p.parse_args()
    try:
        spec=json.loads(Path(a.spec).read_text())
        result=render(spec)
        Path(a.receipt).write_text(json.dumps(result,separators=(",",":")))
        print("MAD_V6_GES_RENDER_VISUAL_CHECK_PASS",flush=True)
    except Exception as ex:
        # No source name, URI, metadata or media is revealed to logs.
        print("MAD_V6_GES_RENDER_FAILED "+(str(ex) if isinstance(ex,RenderBlocked) else type(ex).__name__),file=sys.stderr)
        raise SystemExit(2)
if __name__=="__main__":main()
