#!/usr/bin/python3
"""Synthetic-only integration smoke: GES must output VISIBLE video plus audio."""
from __future__ import annotations
import hashlib,json,os,subprocess,sys,tempfile
from pathlib import Path
def run(*argv):
    subprocess.run(argv,check=True,stdout=subprocess.DEVNULL,timeout=90)
def main():
    root=Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory(prefix="mad-v6-ges-smoke-") as folder:
        w=Path(folder)
        src=w/"test-pattern.mp4";music=w/"test-tone.wav";out=w/"ges-output.mp4"
        run("gst-launch-1.0","-q","videotestsrc","pattern=ball","num-buffers=120",
            "!","video/x-raw,width=640,height=360,framerate=30/1",
            "!","videoconvert","!","x264enc","tune=zerolatency","speed-preset=ultrafast",
            "!","h264parse","!","mp4mux","!","filesink","location="+str(src))
        run("gst-launch-1.0","-q","audiotestsrc","wave=sine","num-buffers=350",
            "!","audioconvert","!","audioresample","!",
            "audio/x-raw,rate=48000,channels=2","!","wavenc","!","filesink","location="+str(music))
        spec={"source":str(src),"source_sha256":hashlib.sha256(src.read_bytes()).hexdigest(),
              "music":str(music),"music_sha256":hashlib.sha256(music.read_bytes()).hexdigest(),
              "workdir":str(w),"output":str(out),
              "cuts":[{"start":0.0,"seconds":3.0,"source_index":0}],
              "operations":[[{"id":"c1","name":"color_grade","parameters":{"contrast":12}}]],
              "hook":"VISIBLE FOOTAGE TEST","width":480,"height":270,"fps":24}
        (w/"spec.json").write_text(json.dumps(spec))
        run("/usr/bin/python3",str(root/"ges_v6_adapter.py"),"--spec",str(w/"spec.json"),"--receipt",str(w/"receipt.json"))
        # Independent consented source-frame decode exercises the actual Gemini sampler.
        from ges_frame_samples import extract
        frames=extract(w,src,4.0,consent=True,source_sha256=spec["source_sha256"])
        assert len(frames)==3 and all(f["bytes"]>1024 for f in frames)
        # Platform-profile smoke: reject missing visuals even at Instagram geometry.
        spec["output"]=str(w/"ges-vertical.mp4")
        spec["width"]=1080
        spec["height"]=1920
        spec["fps"]=30
        (w/"vertical-spec.json").write_text(json.dumps(spec))
        run("/usr/bin/python3",str(root/"ges_v6_adapter.py"),"--spec",str(w/"vertical-spec.json"),"--receipt",str(w/"vertical-receipt.json"))
        vertical=json.loads((w/"vertical-receipt.json").read_text())
        assert vertical["width"]==1080 and vertical["height"]==1920
        assert vertical["visual_presence_check"]["visible"] is True and vertical["output_audio_verified"] is True
        print("MAD_V6_GES_VERTICAL_VISIBLE_AUDIO_PASS",vertical["bytes"])
        result=json.loads((w/"receipt.json").read_text())
        assert result["engine"]=="GStreamer Editing Services"
        assert result["gstreamer_only"] is True and result["filmcraft_only"] is False
        assert result["output_audio_verified"] is True
        assert result["visual_presence_check"]["visible"] is True
        assert result["visual_presence_check"]["frames_examined"]>=3
        assert result["sha256"]==hashlib.sha256(out.read_bytes()).hexdigest()
        assert result["width"]==480 and result["height"]==270
        print("MAD_V6_GES_SYNTHETIC_VIDEO_AND_AUDIO_PASS",result["bytes"])
if __name__=="__main__":main()
