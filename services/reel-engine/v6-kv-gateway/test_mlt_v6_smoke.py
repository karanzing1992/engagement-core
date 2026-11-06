#!/usr/bin/python3
"""MLT V6 native synthetic media smoke with real decoded output frames/audio."""
import hashlib,json,subprocess,tempfile,sys
from pathlib import Path
import xml.etree.ElementTree as ET
import mlt_v6_adapter as mlt

def run(argv):
    subprocess.run(argv,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                   timeout=80,check=True)

def test():
    with tempfile.TemporaryDirectory(prefix="mad-v6-mlt-") as tmp:
        w=Path(tmp)
        video=w/"synthetic.mp4"
        music=w/"original-cc0-music.wav"
        run(["gst-launch-1.0","-q","videotestsrc","pattern=ball","num-buffers=120",
             "!","video/x-raw,width=480,height=270,framerate=30/1",
             "!","videoconvert","!","x264enc","tune=zerolatency","speed-preset=ultrafast",
             "!","h264parse","!","mp4mux","!","filesink","location="+str(video)])
        run(["gst-launch-1.0","-q","audiotestsrc","wave=sine","num-buffers=400",
             "!","audioconvert","!","audioresample","!",
             "audio/x-raw,rate=48000,channels=2","!","wavenc","!",
             "filesink","location="+str(music)])
        assert len(mlt.TEMPLATES)>=6
        backend=mlt.verify_backend()
        assert backend["engine"]=="MLT Framework + frei0r"
        spec={
            "workdir":str(w),"source":str(video),"music":str(music),
            "source_sha256":mlt.sha256(video),"music_sha256":mlt.sha256(music),
            "output":str(w/"output.mp4"),"width":480,"height":270,"fps":24,
            "template_id":"wellness-cinema",
            "cuts":[{"start":0.0,"seconds":1.5,"source_index":0},
                    {"start":1.5,"seconds":1.5,"source_index":1}],
            "operations":[[
                 {"id":"c1","name":"color_grade","parameters":{"contrast":15}},
                 {"id":"t1","name":"title","parameters":{"text":"BREATHE"}}],
                [{"id":"c2","name":"caption","parameters":{"text":"MOKSHA RESET"}}]],
            "hook":"THE ELEMENTAL RESET"}
        entry=mlt.build_xml(spec)
        source=ET.parse(entry["xml"]).getroot()
        services=[x.text for x in source.findall(".//property[@name='mlt_service']")]
        assert "frei0r.contrast0r" in services and "dynamictext" in services
        assert "mix" in services and "avformat" in services
        rec=mlt.render(spec)
        assert rec["engine"]=="MLT Framework + frei0r"
        assert rec["mlt_only"] and rec["frei0r_verified"]
        assert rec["output_audio_verified"]
        assert rec["visual_presence_check"]["visible"]
        assert rec["visual_presence_check"]["frames_examined"]==3
        assert rec["sha256"]==hashlib.sha256(Path(spec["output"]).read_bytes()).hexdigest()
        assert rec["width"]==480 and rec["height"]==270
        assert rec["published"] is False
        print("MAD_V6_MLT_480_VISIBLE_AUDIO_PASS",rec["bytes"],flush=True)
        # Production display geometry, source itself is synthetic.
        spec["output"]=str(w/"vertical.mp4")
        spec["width"]=1080;spec["height"]=1920;spec["fps"]=30
        second=mlt.render(spec)
        assert second["width"]==1080 and second["height"]==1920
        assert second["visual_presence_check"]["visible"] and second["output_audio_verified"]
        print("MAD_V6_MLT_1080x1920_VISIBLE_AUDIO_PASS",second["bytes"],flush=True)
        spec["template_id"]="unsupported_random_plugin"
        try:mlt.render(spec)
        except mlt.RenderBlocked as exc:
            assert str(exc)=="MLT_TEMPLATE_NOT_ALLOWLISTED"
        else:raise AssertionError("Unsafe plugin ID was accepted")
if __name__=="__main__":
    try:test()
    except Exception as e:
        print("MAD_V6_MLT_NATIVE_SMOKE_FAILED",type(e).__name__,
              (str(e) if isinstance(e,mlt.RenderBlocked) else ""),file=sys.stderr)
        raise
