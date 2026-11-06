"""Private three-frame sampler using native GStreamer decoding and JPEG encoding."""
import base64,hashlib
from pathlib import Path
import gi
gi.require_version("Gst","1.0")
from gi.repository import Gst
from ges_v6_adapter import RenderBlocked

def jpeg_frame(path,at):
    Gst.init(None)
    pipeline=Gst.Pipeline.new("private-frame-sampler")
    src=Gst.ElementFactory.make("uridecodebin")
    queue=Gst.ElementFactory.make("queue")
    conv=Gst.ElementFactory.make("videoconvert")
    scale=Gst.ElementFactory.make("videoscale")
    caps=Gst.ElementFactory.make("capsfilter")
    enc=Gst.ElementFactory.make("jpegenc")
    sink=Gst.ElementFactory.make("appsink")
    if any(x is None for x in (src,queue,conv,scale,caps,enc,sink)):
        raise RenderBlocked("GSTREAMER_FRAME_EXPORT_ELEMENT_MISSING")
    src.props.uri=Path(path).resolve().as_uri()
    caps.props.caps=Gst.Caps.from_string("video/x-raw,width=640,height=360,pixel-aspect-ratio=1/1")
    sink.props.sync=False
    sink.props.max_buffers=1
    sink.props.drop=True
    for e in (src,queue,conv,scale,caps,enc,sink):pipeline.add(e)
    if not queue.link(conv) or not conv.link(scale) or not scale.link(caps) or not caps.link(enc) or not enc.link(sink):
        raise RenderBlocked("GSTREAMER_FRAME_EXPORT_LINK_FAILED")
    def on_pad(_source,pad):
        c=pad.get_current_caps()
        if c is not None and c.to_string().startswith("video/"):
            pad.link(queue.get_static_pad("sink"))
    src.connect("pad-added",on_pad)
    try:
        if pipeline.set_state(Gst.State.PAUSED)==Gst.StateChangeReturn.FAILURE:
            raise RenderBlocked("GSTREAMER_FRAME_EXPORT_PAUSE_FAILED")
        pipeline.get_state(8*Gst.SECOND)
        if not pipeline.seek_simple(Gst.Format.TIME,Gst.SeekFlags.FLUSH|Gst.SeekFlags.ACCURATE,round(at*Gst.SECOND)):
            raise RenderBlocked("GSTREAMER_FRAME_SEEK_FAILED")
        pipeline.set_state(Gst.State.PLAYING)
        frame=sink.emit("try-pull-sample",10*Gst.SECOND)
        if not frame:raise RenderBlocked("GSTREAMER_FRAME_NOT_DECODED")
        b=frame.get_buffer()
        ok,m=b.map(Gst.MapFlags.READ)
        if not ok:raise RenderBlocked("GSTREAMER_FRAME_READ_FAILED")
        try:payload=bytes(m.data)
        finally:b.unmap(m)
        if len(payload)<1024 or payload[:2]!=bytes.fromhex("ffd8") or payload[-2:]!=bytes.fromhex("ffd9"):
            raise RenderBlocked("GSTREAMER_FRAME_INVALID_JPEG")
        return payload
    finally:pipeline.set_state(Gst.State.NULL)

def extract(workdir,source,duration,*,count=3,consent=False,source_sha256=""):
    if consent is not True:raise RenderBlocked("EXTERNAL_AI_VISUAL_CONSENT_MISSING")
    if not 1<=count<=3 or not 3<=duration<=480:raise RenderBlocked("SOURCE_FRAME_DURATION_INVALID")
    p=Path(source).resolve()
    if p.parent!=Path(workdir).resolve():
        raise RenderBlocked("SOURCE_OUTSIDE_PRIVATE_WORKDIR")
    if hashlib.sha256(p.read_bytes()).hexdigest()!=source_sha256:
        raise RenderBlocked("SOURCE_FRAME_CHECKSUM_INVALID")
    frames=[]
    total=0
    for i in range(count):
        second=min(duration-.1,duration*(i+.5)/count)
        image=jpeg_frame(p,second)
        total+=len(image)
        if total>3*1024*1024:raise RenderBlocked("FRAME_DATA_BUDGET_EXCEEDED")
        frames.append({"time_seconds":round(second,3),"mime_type":"image/jpeg",
                       "data":base64.b64encode(image).decode(),
                       "sha256":hashlib.sha256(image).hexdigest(),
                       "bytes":len(image)})
    return frames
