"""Sample consented source frames with native FilmCraft only, no FFmpeg."""
import base64,hashlib
from pathlib import Path
from filmcraft_v6_adapter import MCP,find_item,TICKS_PER_SECOND,FilmCraftError

def extract(cli,workdir,source,duration,*,count=3,consent=False,source_sha256=""):
 if consent is not True:raise FilmCraftError("Gemini visual consent missing")
 if not 1<=count<=3 or not 3<=duration<=480:raise FilmCraftError("Invalid native frame sampling")
 p=Path(source).resolve();w=Path(workdir).resolve()
 if p.parent!=w or hashlib.sha256(p.read_bytes()).hexdigest()!=source_sha256:
  raise FilmCraftError("Private source checksum mismatch")
 m=MCP(cli,w);result=[];total=0
 try:
  m.tool("media_import",{"paths":[str(p)]})
  item=find_item(m.tool("project_inspect",{}),p.name)
  if not isinstance(item,int):raise FilmCraftError("FilmCraft source import missing")
  for i in range(count):
   t=min(duration-.05,duration*(i+.5)/count)
   output=w/("v6-source-frame-%02d.jpg"%i)
   m.cmd("file.exportFrame",{"target":"source","item":item,"time":int(t*TICKS_PER_SECOND),
          "format":"jpeg","depth":8,"path":str(output)})
   data=output.read_bytes()
   if not data.startswith(bytes.fromhex("ffd8")) or not data.endswith(bytes.fromhex("ffd9")):
    raise FilmCraftError("Native source JPEG invalid")
   total+=len(data)
   if total>3*1024*1024:raise FilmCraftError("Frame payload exceeds privacy and request cap")
   result.append({"time_seconds":round(t,3),"mime_type":"image/jpeg",
     "data":base64.b64encode(data).decode(),"sha256":hashlib.sha256(data).hexdigest(),"bytes":len(data)})
   output.unlink()
  return result
 finally:
  for x in w.glob("v6-source-frame-*.jpg"):x.unlink(missing_ok=True)
  m.close()
