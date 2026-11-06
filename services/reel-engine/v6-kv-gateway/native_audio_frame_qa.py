#!/usr/bin/env python3
"""Real native FilmCraft frame export and CC0 audio-mix private synthetic QA."""
from pathlib import Path
import json,os,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import filmcraft_v6_adapter as fc
from frame_sampling_v6 import export_native_source_frames
from audio_runtime_v6 import select_cc0

cli=os.environ["FILMCRAFT_CLI"]
root=Path(os.environ["RUNNER_TEMP"])/"mad-v6-native-audio-frame-test"
root.mkdir(mode=0o700,parents=True,exist_ok=True)
srcdir=root/"source"
source=srcdir/"source.mp4"
src=fc.render(cli=cli,workdir=srcdir,output=source,
  cuts=[{"start":0.,"seconds":4.,"source_index":0}],operations=[[]],
  hook="GENERIC PRODUCT - SYNTHETIC QA",width=480,height=270,fps=24)
assert src["filmcraft_only"] and src["ffmpeg_invocations"]==0
frames=export_native_source_frames(cli=cli,workdir=root/"frames",source=source,duration=4.)
assert len(frames)==3 and all(a["generated_by"]=="FilmCraft.file.exportFrame" for a in frames)
print("MAD_V6_FILMCRAFT_NATIVE_JPEG_FRAMES_PASS",len(frames),[x["bytes"] for x in frames])
music=select_cc0(root/"audio",query="ambient music",minimum_duration=4.)
rec=fc.render(cli=cli,workdir=root/"mixed",output=root/"mixed"/"output.mp4",
  source=source,source_rights_cleared=True,source_sha256=src["sha256"],
  music=music["path"],music_rights=music["rights"],
  cuts=[{"start":0.,"seconds":3.5,"source_index":0}],
  operations=[[{"id":"v6_s00_e00","name":"color_grade","parameters":{"contrast":12}}]],
  hook="GENERIC PRODUCT",width=480,height=270,fps=24)
assert rec["filmcraft_only"] and rec["ffmpeg_invocations"]==0
assert rec["music_native_probed"] and rec["mixed_audio_stream_native_verified"],"Native FilmCraft output audio absent"
assert rec["soundtrack_sha256"]==music["audio_sha256"]
assert rec["soundtrack_license_method"]=="automatic_CC0_catalog"
print("MAD_V6_NATIVE_CC0_AUDIO_FILMCRAFT_MIX_PASS",json.dumps({
 "output_bytes":rec["bytes"],"output_sha256":rec["sha256"],
 "audio_track_sha256":music["audio_sha256"],"license":music["license"],
 "audio_stream_verified":rec["mixed_audio_stream_native_verified"],"filmcraft_only":True,
 "source_frames":len(frames),"published":False}))
