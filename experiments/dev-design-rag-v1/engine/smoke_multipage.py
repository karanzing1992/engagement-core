#!/usr/bin/env python3
"""Isolated deterministic full-route smoke. Does not claim LLM or artistic certification."""
import hashlib,http.server,json,os,socketserver,subprocess,sys,tempfile,threading
from pathlib import Path
from multipage_contract import layout_preflight
from core import write,sha
ROOT=Path(__file__).resolve().parent
PAGES=['index.html','rooms.html','experiences.html','food.html','explore.html','contact.html']
CSS='''*{box-sizing:border-box} :root{--ink:#273241;--paper:#fcf7ee;--sea:#267b85}
body{font:16px/1.5 system-ui,sans-serif;color:var(--ink);background:var(--paper);margin:0}
.container{max-width:1100px;margin:auto;padding:1.5rem}.site-header{background:white;padding:.5rem}
.nav-list{display:flex;gap:1rem;flex-wrap:wrap;list-style:none;padding:0}
a{color:#075273}.hero{padding:2rem 0}.hero img{width:100%;max-height:32rem;object-fit:cover}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:1rem}
.card{border:1px solid #777;padding:1.4rem}.btn{background:#074e66;color:white;padding:.7rem;display:inline-block}
@media(max-width:767px){.container{padding:1rem}.grid{grid-template-columns:1fr}.nav-list{gap:.6rem}}'''+'/* original fixtures; not an actual product design */'*36
def main():
 with tempfile.TemporaryDirectory(prefix='uiux-multipage-smoke-') as td:
  w=Path(td);site=w/'site';(site/'assets').mkdir(parents=True)
  (site/'assets/site.css').write_text(CSS)
  for page in PAGES:
   nav=''.join('<li><a href="'+x+'">'+x.replace('.html','').title()+'</a></li>' for x in PAGES)
   html='<!doctype html><html lang="en"><head><meta name="viewport" content="width=device-width, initial-scale=1"><title>Smoke Fixture</title><link rel="stylesheet" href="assets/site.css"></head><body><header class="site-header"><nav aria-label="Main"><ul class="nav-list">'+nav+'</ul></nav></header><main class="container"><h1>Multi-page smoke: '+page+'</h1><section class="hero"><h2>Page layout</h2><p>Deterministic local fixture, not a brand website or artistic evaluation.</p></section><section class="grid"><article class="card"><h2>Accessible content</h2><a href="index.html" class="btn">Home</a></article></section></main></body></html>'
   (site/page).write_text(html)
  v=layout_preflight(site,PAGES,'assets/site.css')
  if v['status']!='PASS':raise ValueError('SMOKE_DESIGN_PREFLIGHT_FAILED:'+str(v))
  class Handler(http.server.SimpleHTTPRequestHandler):
   def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(site),**kwargs)
   def log_message(self,*args):pass
  class Server(socketserver.TCPServer):allow_reuse_address=True
  with Server(('127.0.0.1',0),Handler) as server:
   th=threading.Thread(target=server.serve_forever,daemon=True);th.start()
   opt={'root':str(site),'url':'http://127.0.0.1:'+str(server.server_address[1]),
     'source_hash':hashlib.sha256(CSS.encode()).hexdigest(),'screenshots':str(w/'screenshots'),
     'report':str(w/'browser-qa.json'),'pages':PAGES,'widths':[320,390,768,1440]}
   write(w/'qa-options.json',opt)
   env=os.environ.copy();env['NODE_PATH']=str(Path.home()/'.local/share/andaz-autonomous-website-pilot-20261106/audit-engine/node_modules')
   p=subprocess.run(['node',str(ROOT/'qa-site.cjs'),str(w/'qa-options.json')],env=env,text=True,capture_output=True,timeout=120)
   server.shutdown()
   r=json.loads((w/'browser-qa.json').read_text())
  report={'schema':'uiux-v2.1.4-multipage-smoke-v1','fixture_only':True,
    'agent_inference_tested':False,'real_browser_and_axe':True,'pages':len(PAGES),
    'browser_cases':len(r['rows']),'failed_cases':r['failed'],'missing_links':r['missing_links'],
    'layout_gate':v['status'],'qa_pass':r['pass'],'exit_code':p.returncode,
    'artistic_score':None,'production_approved':False}
  out=Path.home()/'.local/share/dev-design-rag-v1/certification/uiux-v2.1.4-multipage-fixture-smoke-20261112.json'
  write(out,report)
  print(json.dumps(report,indent=2),flush=True)
  return 0 if r['pass'] and p.returncode==0 and len(r['rows'])==24 else 4
if __name__=='__main__':sys.exit(main())
