#!/usr/bin/env python3
"""Render an approval-only, evidence-based 9:16 walking-break Reel.
All footage comes from explicitly identified Pexels free-use source videos.
No automated posting or social integration is performed.
"""
import os
import re
import subprocess
from pathlib import Path
from PIL import ImageFont

ROOT=Path(".")
INPUT=ROOT/"assets"
OUTPUT=ROOT/"output"
OUTPUT.mkdir(exist_ok=True)

def run(cmd):
    print("+", " ".join(str(c) for c in cmd), flush=True)
    subprocess.run([str(c) for c in cmd],check=True)

def probe(p):
    cp=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(p)],capture_output=True,text=True,check=True)
    return float(cp.stdout.strip())

# Each act is original, licensed video. We cut distinct portions to avoid
# accidental duplication and loop only if an original is shorter.
acts=[
 ("goa_morning.mp4",0.4,8.5),
 ("goa_walk_sunset.mp4",0.8,9.0),
 ("goa_morning.mp4",8.2,7.5),
 ("goa_walk_sunset.mp4",9.3,7.0),
]
clips=[]
for i,(name,start,duration) in enumerate(acts):
    source=INPUT/name
    orig_length=probe(source)
    # repeated-source starts are adjusted to the original's duration.
    start=min(start,max(0,orig_length-1.5))
    target=OUTPUT/f"segment_{i}.mp4"
    vf=(
       "scale=1080:1920:force_original_aspect_ratio=increase,"
       "crop=1080:1920,setsar=1,fps=24,format=yuv420p,"
       "eq=brightness=-0.055:saturation=0.89"
    )
    run(["ffmpeg","-nostdin","-hide_banner","-loglevel","error","-y",
         "-stream_loop","-1","-i",source,"-ss",f"{start:.3f}","-t",f"{duration:.3f}",
         "-vf",vf,"-an","-c:v","libx264","-preset","veryfast","-crf","22",
         "-pix_fmt","yuv420p","-movflags","+faststart",target])
    clips.append(target)

# Cross-dissolve four acts: 32.0 - 3*0.65 = 30.05 seconds.
xoffset1=8.5-0.65
xoffset2=8.5+9.0-2*0.65
xoffset3=8.5+9.0+7.5-3*0.65
filtergraph=(
    f"[0:v][1:v]xfade=transition=fade:duration=0.65:offset={xoffset1:.3f}[v1];"
    f"[v1][2:v]xfade=transition=fade:duration=0.65:offset={xoffset2:.3f}[v2];"
    f"[v2][3:v]xfade=transition=fade:duration=0.65:offset={xoffset3:.3f},"
    "fps=24,format=yuv420p[vout]"
)
base=OUTPUT/"base_walking.mp4"
cmd=["ffmpeg","-nostdin","-hide_banner","-loglevel","error","-y"]
for c in clips:cmd+=["-i",c]
cmd+=["-filter_complex",filtergraph,"-map","[vout]","-an","-t","30",
      "-c:v","libx264","-preset","veryfast","-crf","21","-pix_fmt","yuv420p",
      "-movflags","+faststart",base]
run(cmd)

# Each word appears in its final position and remains until the complete
# sentence is visible. No jumping or moving text blocks.
phrases=[
 ("Sitting for hours?",0.6,5.2),
 ("Your body loves a little movement.",5.2,10.5),
 ("Even short walking breaks can help.",10.5,16.9),
 ("They can reduce after-meal blood sugar rises.",16.9,23.7),
 ("Try two minutes during long sitting.",23.7,29.6),
]
fontpath="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
size=69
font=ImageFont.truetype(fontpath,size)
max_width=920
line_height=103
def width(s):
    return font.getlength(s)
def split_lines(s):
    lines=[]
    cur=""
    for word in s.split():
        probe=(cur+" "+word).strip()
        if cur and width(probe)>max_width:
            lines.append(cur);cur=word
        else:cur=probe
    if cur:lines.append(cur)
    return lines

def stamp(seconds):
    minutes=int(seconds//60)
    sec=seconds-minutes*60
    return f"0:{minutes:02d}:{sec:05.2f}"

header="""[Script Info]
Title: Wellness Word by Word
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Main,DejaVu Sans,69,&H00FFFFFF,&H00FFFFFF,&H8C091B20,&H00000000,1,0,0,0,100,100,0,0,1,3.7,1.7,7,0,0,0,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
events=[]
for phrase,start,end in phrases:
    lines=split_lines(phrase)
    line_count=len(lines)
    y0=1060-(line_count-1)*line_height/2
    words=phrase.split()
    # A smooth buildup followed by 2.5 seconds of complete-sentence hold.
    available=max(0.75,(end-start)-2.6)
    cursor=0
    for li,line in enumerate(lines):
        line_width=width(line)
        xpos=(1080-line_width)/2
        for word in line.split():
            token=(word+" ")
            token_width=width(token)
            begin=start+0.22+cursor*available/max(1,len(words))
            xpos_word=xpos+width(" ".join(line.split()[:len(line.split())-len(line.split())])) if False else xpos
            # Words use anchored text positions across each line, no layout jump.
            color="&H00FFFFFF"
            # Subtle warm editorial highlight, never flashing.
            if word.lower().strip(".,!?") in ("movement","walking","minutes"):
                color="&H00CFECFF"
            tags=r"{\an7\pos("+f"{xpos:.1f},{y0+li*line_height:.1f}"+r")\fad(240,440)\1c"+color+r"}"
            events.append(f"Dialogue: 0,{stamp(begin)},{stamp(end)},Main,,0,0,0,,{tags}{word}")
            xpos+=token_width
            cursor+=1
# Correct placement: PIL word + space gives the same approximate advance
# used by the chosen bundled DejaVu Sans font.
ass=OUTPUT/"word_by_word.ass"
ass.write_text(header+"\n".join(events)+"\n",encoding="utf-8")
print("WORDS",len(events),flush=True)

# Overlay official, verified public WordPress logo MARK (no substitute).
# The source has the icon only: avoid replacing it with generated lettering.
logo=INPUT/"official_logo_mark.png"
audio=INPUT/"approved_music_source.mp4"
final=OUTPUT/"movement_break_GOA_beachwalk_FINAL_1080x1920.mp4"
# Dark semi-transparent caption-zone scrim, preserving bright Goa footage.
fcomplex=(
    "[0:v]drawbox=x=0:y=895:w=1080:h=510:color=black@0.26:t=fill,"
    f"subtitles={ass.as_posix()}:fontsdir=/usr/share/fonts/truetype/dejavu[vid];"
    "[1:v]scale=104:104,format=rgba,colorchannelmixer=aa=0.19[mark];"
    "[vid][mark]overlay=x=W-w-48:y=H-h-180:format=auto[v];"
    "[2:a]volume=0.92,afade=t=in:st=0:d=1.3,"
    "afade=t=out:st=27.5:d=2.5[a]"
)
run(["ffmpeg","-nostdin","-hide_banner","-loglevel","error","-y",
     "-i",base,"-loop","1","-i",logo,"-i",audio,
     "-filter_complex",fcomplex,"-map","[v]","-map","[a]",
     "-t","30","-c:v","libx264","-preset","veryfast","-crf","19",
     "-pix_fmt","yuv420p","-r","24","-c:a","aac","-b:a","160k",
     "-movflags","+faststart",final])
run(["ffprobe","-v","error","-show_entries",
     "stream=codec_name,width,height:format=duration,size",
     "-of","default=noprint_wrappers=1",final])

for idx,t in enumerate((2,7.5,13,20.5,27.5)):
    run(["ffmpeg","-nostdin","-hide_banner","-loglevel","error","-y",
         "-ss",str(t),"-i",final,"-frames:v","1","-vf","scale=360:640",
         OUTPUT/f"preview_{idx}.jpg"])
(OUTPUT/"README.txt").write_text(
  "Wellness Knowledge - 2-Minute Walking Break\n"
  "Approval preview only. Nothing was published or scheduled.\n"
  "Source A: https://www.pexels.com/video/tranquil-morning-at-goa-beach-34648932/\n"
  "Source B: https://www.pexels.com/video/silhouette-of-a-couple-walking-on-the-beach-at-sunset-10918852/\n"
  "Both are free to use under the Pexels License: https://www.pexels.com/license/\n"
  "Music: Placid Ambient by MusicLFiles, CC BY 4.0; extracted from the previously approved video, edited. https://creativecommons.org/licenses/by/4.0/\n"
  "Official icon: authenticated mokshagoa.com WordPress media asset Logo-Mark.png\n"
  "Reel caption: Short walking breaks can make a difference when you've been sitting for a long time. Studies suggest they can help reduce short-term after-meal glucose rises compared with uninterrupted sitting. Try a gentle two-minute walk during long sitting periods. MYTH or FACT? Tiny movement breaks matter. #MovementMatters #WellnessKnowledge #HealthyHabits #MoveMoreSitLess\n"
  "Interaction: MYTH or FACT poll, Story answer FACT. Poll sticker must be added natively on publication.\n"
)
print("DONE",final,flush=True)
