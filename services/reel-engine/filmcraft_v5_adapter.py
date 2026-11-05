#!/usr/bin/env python3
"""MAD V5 FilmCraft-only editing adapter, pinned CLI/MCP.
No FFmpeg, FFprobe, synthetic audio generator, or fallback video editor.
The caller supplies consented source and a validated source-grounded EDL.
"""
from __future__ import annotations
import argparse, hashlib, json, os, selectors, subprocess, time
from pathlib import Path

TICKS_PER_SECOND = 254_016_000_000
VERIFIED_EFFECTS = {"color_grade", "lumetri", "blur", "gaussian_blur", "motion",
                    "zoom", "transition", "motion_typography", "title", "caption",
                    "audio_gain"}
MAX_OPS = 64

class FilmCraftError(RuntimeError): pass

class MCP:
    def __init__(self, cli: str, workdir: Path):
        exe=Path(cli)
        if not exe.is_file() or not os.access(exe, os.X_OK):
            raise FilmCraftError("FILMCRAFT_CLI not executable; no FFmpeg fallback")
        self.p=subprocess.Popen([str(exe),"mcp"],stdin=subprocess.PIPE,stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,text=True,bufsize=1,cwd=str(workdir),
            env={**os.environ,"RUST_BACKTRACE":"0"})
        self.next_id=0
        res=self.request("initialize",{"protocolVersion":"2025-03-26","capabilities":{},
              "clientInfo":{"name":"mad-v5-filmcraft-only","version":"0.1"}})
        if not res.get("result"): raise FilmCraftError("FilmCraft MCP handshake rejected")
        self.p.stdin.write(json.dumps({"jsonrpc":"2.0","method":"notifications/initialized","params":{}})+"\n")
        self.p.stdin.flush()
        toolset=self.request("tools/list",{}).get("result",{}).get("tools",[])
        self.tools={t["name"] for t in toolset}
        required={"command_run","media_import","project_inspect","sequence_inspect"}
        if not required.issubset(self.tools):
            raise FilmCraftError("FilmCraft MCP lacks required editing tools")
    def request(self, method: str, params: dict, timeout: int=100):
        self.next_id+=1
        rid=self.next_id
        self.p.stdin.write(json.dumps({"jsonrpc":"2.0","id":rid,"method":method,"params":params})+"\n")
        self.p.stdin.flush()
        selector=selectors.DefaultSelector()
        selector.register(self.p.stdout,selectors.EVENT_READ)
        try:
            stop=time.monotonic()+timeout
            while time.monotonic()<stop:
                if not selector.select(min(1,max(0,stop-time.monotonic()))):continue
                line=self.p.stdout.readline()
                if not line:raise FilmCraftError("FilmCraft MCP terminated")
                try:reply=json.loads(line)
                except ValueError:continue
                if reply.get("id")!=rid:continue
                if reply.get("error"):
                    raise FilmCraftError("FilmCraft MCP request failed")
                return reply
            raise FilmCraftError("FilmCraft MCP call timeout")
        finally:selector.close()
    def tool(self, name: str, args: dict, timeout: int=110):
        if name not in self.tools:raise FilmCraftError("Unavailable FilmCraft tool: "+name)
        reply=self.request("tools/call",{"name":name,"arguments":args},timeout)
        data=reply.get("result",{})
        txt="\n".join(part.get("text","") for part in data.get("content",[]) if part.get("type")=="text")
        if data.get("isError"):raise FilmCraftError("FilmCraft "+name+" failed (details redacted)")
        try:return json.loads(txt)
        except ValueError:raise FilmCraftError("FilmCraft tool returned invalid structured response")
    def cmd(self,id: str,params:dict,timeout:int=110):
        return self.tool("command_run",{"id":id,"params":params},timeout)
    def close(self):
        if self.p.poll() is None:
            self.p.terminate()
            try:self.p.wait(timeout=5)
            except subprocess.TimeoutExpired:self.p.kill();self.p.wait(timeout=3)

def find_item(data, basename):
    if isinstance(data,dict):
        if data.get("name")==basename and isinstance(data.get("item"),int):return data["item"]
        for v in data.values():
            found=find_item(v,basename)
            if found is not None:return found
    elif isinstance(data,list):
        for v in data:
            found=find_item(v,basename)
            if found is not None:return found
    return None

def validate_edl(cuts:list[dict], ops:list[list[dict]], source_duration:float|None):
    if not isinstance(cuts,list) or not 1<=len(cuts)<=16 or len(cuts)!=len(ops):
        raise FilmCraftError("FilmCraft accepts one to sixteen timed sections")
    total=0.
    for i,(cut,actions) in enumerate(zip(cuts,ops)):
        seconds=float(cut.get("seconds",0));start=float(cut.get("start",0))
        if not .4<=seconds<=120 or start<0 or (source_duration is not None and start+seconds>source_duration+.02):
            raise FilmCraftError("Timeline section exceeds source bounds")
        if not isinstance(actions,list) or len(actions)>MAX_OPS:raise FilmCraftError("Operation list invalid")
        for action in actions:
            if not isinstance(action,dict) or action.get("name") not in VERIFIED_EFFECTS:
                raise FilmCraftError("Unsupported creative operation; refusing silent effect omission")
            if not isinstance(action.get("parameters",{}),dict):
                raise FilmCraftError("Effect parameters malformed")
        total+=seconds
    if not 1<=total<=120:raise FilmCraftError("Output timeline exceeds guarded duration")
    return round(total,3)

def apply_operations(m:MCP,clip:int,ops:list[dict],timeline_start:float,total:float,index:int):
    applied=[]
    for action in ops:
        name=action["name"];v=action.get("parameters",{})
        if name in ("color_grade","lumetri"):
            m.cmd("effects.apply",{"clips":[clip],"effect":"lumetri"})
            # FilmCraft's Lumetri numerical controls; fixed conservative treatment
            # is honest and deterministic, not arbitrary model-to-command execution.
            m.cmd("effects.setParam",{"clip":clip,"effect":"lumetri","param":"contrast","value":float(v.get("contrast",12))})
            applied.append("lumetri_contrast")
        elif name in ("blur","gaussian_blur"):
            m.cmd("effects.apply",{"clips":[clip],"effect":"gaussian_blur"})
            m.cmd("effects.setParam",{"clip":clip,"effect":"gaussian_blur","param":"blurriness","value":max(0.,min(10.,float(v.get("blurriness",1.0))))})
            applied.append("gaussian_blur")
        elif name in ("motion","zoom"):
            m.cmd("effects.setParam",{"clip":clip,"effect":"motion","param":"scale",
                "value":max(.6,min(1.6,float(v.get("scale",1.04))))})
            applied.append("motion_scale")
        elif name=="transition":
            if index==0:raise FilmCraftError("Transition requires preceding clip")
            kind=v.get("kind","cross_dissolve")
            if kind not in ("cross_dissolve","film_dissolve","dip_to_black"):
                raise FilmCraftError("Transition style not allowlisted")
            m.cmd("sequence.applyVideoTransition",{"clip":clip,"effect":kind,
                "frames":max(3,min(15,int(v.get("frames",8)))),"edge":"in"})
            applied.append(kind)
        elif name in ("motion_typography","title","caption"):
            title=str(v.get("text","")).strip()
            if not title or len(title)>90:raise FilmCraftError("Grounded title text required")
            m.cmd("graphics.newText",{"text":title,"size":max(25,min(110,int(v.get("size",75)))),
                "seconds":min(float(v.get("seconds",2.6)),total-timeline_start),
                "time":int(timeline_start*TICKS_PER_SECOND),"track":2,
                "position":[70,380]})
            applied.append("filmcraft_text")
        elif name=="audio_gain":
            m.cmd("clip.audioGain",{"clips":[clip],"mode":"adjust",
                "db":max(-12.,min(3.,float(v.get("db",0))))})
            applied.append("source_audio_gain")
        else:raise FilmCraftError("Unsupported creative operation: "+name)
    return applied

def render(*,cli:str,workdir:Path,output:Path,source:Path|None=None,
           cuts:list[dict]|None=None,operations:list[list[dict]]|None=None,
           hook:str="",music:Path|None=None,width:int=1080,height:int=1920,fps:int=30):
    if (width,height) not in ((480,270),(720,1280),(1080,1920)) or fps not in (24,30):
        raise FilmCraftError("FilmCraft export geometry not approved")
    workdir.mkdir(parents=True,exist_ok=True)
    if output.resolve().parent!=workdir.resolve():
        raise FilmCraftError("FilmCraft may export only to isolated job workdir")
    m=MCP(cli,workdir)
    try:
        probe=None;source_id=None
        if source:
            if not source.is_file() or source.stat().st_size<1024:raise FilmCraftError("Private source missing")
            probe=m.cmd("mediaBrowser.probe",{"path":str(source.resolve())})
            info=probe.get("info",{})
            if not info.get("video"):raise FilmCraftError("FilmCraft failed video source probe")
            duration=info.get("duration",0)/TICKS_PER_SECOND
            if not 3<=duration<=480:raise FilmCraftError("Source duration outside owner-beta admission")
        else:
            duration=None
        if cuts is None:cuts=[{"start":0.,"seconds":2.,"source_index":0}]
        if operations is None:operations=[[] for _ in cuts]
        total=validate_edl(cuts,operations,duration)
        m.cmd("file.newSequence",{"name":"MAD_V5_FILMCRAFT_PRIVATE_REVIEW",
            "width":width,"height":height,"fps":fps,"video":2,"audio":2})
        if source:
            m.tool("media_import",{"paths":[str(source.resolve())]})
            source_id=find_item(m.tool("project_inspect",{}),source.name)
        else:
            source_id=m.cmd("file.newColorMatte",{"color":"#18382F","seconds":max(3.,total)})["item"]
        if not isinstance(source_id,int):raise FilmCraftError("FilmCraft media item ID unverified")
        timeline=0.;applied=[];clips=[]
        for i,(cut,op) in enumerate(zip(cuts,operations)):
            params={"item":source_id,"track":"V1","seconds":timeline,
                "sourceIn":{"seconds":float(cut.get("start",0))},
                "duration":{"seconds":float(cut["seconds"])},"audio":bool(source),"video":True,
                "matchSequence":False}
            placed=m.cmd("timeline.place",params)
            ids=placed.get("clips",[])
            if not ids or not isinstance(ids[0],int):
                raise FilmCraftError("FilmCraft did not confirm placed clip ID")
            clips.append(ids[0])
            applied.extend(apply_operations(m,ids[0],op,timeline,total,i))
            timeline+=float(cut["seconds"])
        if hook:
            m.cmd("graphics.newText",{"text":hook[:100],"size":56 if width==480 else 80,
                "seconds":min(2.8,total),"track":2,"time":0,
                "position":[width*.08,height*.20]})
            applied.append("opening_title")
        if music:
            if not music.is_file() or music.stat().st_size<1024:raise FilmCraftError("Approved music file absent")
            m.tool("media_import",{"paths":[str(music.resolve())]})
            music_id=find_item(m.tool("project_inspect",{}),music.name)
            if not isinstance(music_id,int):raise FilmCraftError("Music import not confirmed")
            m.cmd("timeline.place",{"item":music_id,"track":"A2","seconds":0,
                 "duration":{"seconds":total},"video":False,"audio":True,"matchSequence":False})
            applied.append("approved_audio_placed")
        project=workdir/"filmcraft-private.fcproj"
        m.cmd("file.saveAs",{"path":str(project)})
        m.cmd("file.exportMedia",{"path":str(output),"format":"h264","width":width,
            "height":height,"fps":fps,"range":"custom","startSeconds":0,"endSeconds":total,
            "wait":True,"hardwareEncoding":"off","audio":bool(source) or bool(music)},timeout=600)
        if not output.is_file() or output.stat().st_size<1024:raise FilmCraftError("FilmCraft export missing")
        verified=m.cmd("mediaBrowser.probe",{"path":str(output)})
        video=verified.get("info",{}).get("video",{})
        if video.get("width")!=width or video.get("height")!=height or "H.264" not in video.get("codec",""):
            raise FilmCraftError("FilmCraft export codec/geometry verification failed")
        h=hashlib.sha256()
        with output.open("rb") as fd:
            for block in iter(lambda:fd.read(4*1024*1024),b""):h.update(block)
        return {"engine":"FilmCraft","filmcraft_only":True,"rendered":True,
            "ffmpeg_invocations":0,"sha256":h.hexdigest(),"bytes":output.stat().st_size,
            "width":width,"height":height,"fps":fps,"duration_seconds":total,
            "applied_operations":applied,"operations_requested":sum(map(len,operations)),
            "operations_applied":sum(map(len,operations)),
            "operations_unapplied":0,"source_music":"approved_recording" if music else "original_source_or_silence",
            "project":str(project),"output":str(output),"published":False}
    finally:m.close()

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--workdir",required=True)
    p.add_argument("--cli",default=os.getenv("FILMCRAFT_CLI",""))
    p.add_argument("--source")
    p.add_argument("--output")
    p.add_argument("--cuts-json")
    p.add_argument("--operations-json")
    p.add_argument("--hook",default="MOKSHA")
    p.add_argument("--width",type=int,default=480)
    p.add_argument("--height",type=int,default=270)
    p.add_argument("--fps",type=int,default=24)
    a=p.parse_args()
    root=Path(a.workdir).resolve()
    receipt=render(cli=a.cli,workdir=root,source=Path(a.source).resolve() if a.source else None,
        output=(root/(a.output or "filmcraft-v5-private.mp4")),hook=a.hook,
        cuts=json.loads(Path(a.cuts_json).read_text()) if a.cuts_json else None,
        operations=json.loads(Path(a.operations_json).read_text()) if a.operations_json else None,
        width=a.width,height=a.height,fps=a.fps)
    print("MAD_V5_FILMCRAFT_ONLY_RENDER_PASS",json.dumps({k:v for k,v in receipt.items() if k not in ("project","output")}))
    (root/"filmcraft-receipt.json").write_text(json.dumps(receipt,indent=2))
