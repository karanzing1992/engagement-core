#!/usr/bin/env python3
"""Bounded isolated RAG page regeneration; backups, lock, fail-closed."""
import argparse,fcntl,hashlib,json,os,subprocess,sys
from pathlib import Path
from core import state,treehash,sha,write,require
from site_builder import plan, ROOT as CERT_ROOT
from editorial_contract import check_editorial
from design_contract import validate_html
from cli import ingest_agent
TASKS={
'index.html':('Rebuild truthful Andaz Home with 4+ substantial sections, 180+ words. One original room photo as hero ONLY; no room photo in Food/Explore. Andaz Table section links food.html, navigation all 6 pages. Only verified six-bed dorms, two-bed SHARED dorm, private AC, fresh Indian HOME-STYLE meals Rs180 dine-in Rs220 delivered Arambol free delivery, real WhatsApp and Moksha independent optional partner. NEVER claim WiFi, TV, workspace, chefs, sourced ingredients, balcony, sustainability, tours or extra amenities.'),
'rooms.html':('Rebuild Rooms truthfully: 6-bed non-AC dorm, 6-bed AC dorm, TWO-bed NON-AC SHARED DORM (never private), and private AC rooms with NO guessed bedding. 2+ sections, 115+ words. No WiFi/TV/workspace, balcony, pool, kitchen or unverified facilities. Official logo, all six navigation links, approved CSS/JS, real WhatsApp CTA.'),
'experiences.html':('Rebuild Experiences with 3+ sections, 140+ factual words about relaxed Arambol hostel community, SELF-DIRECTED exploring, Moksha Wellness OPTIONAL INDEPENDENT partner. ONLY original logo image, no fake pool/other photos. No shared kitchen/lounge, nightly gatherings, guided tours, staff services, walk-distance claims. Complete six-page nav, WhatsApp.'),
'food.html':('Rebuild The Andaz Table with 2+ sections, 110+ factual words: fresh Indian home-style meals Rs180 dine-in Rs220 delivery within Arambol with FREE delivery, outside fee quoted on enquiry. ONLY original logo; no meal or bedroom image. NO chefs, locally sourced claims, invented dishes, hours or extra services. Clean expressive typographic pricing, original logo, full six-page nav, official WhatsApp.')
}
def bounded_task(p):
 require(p in TASKS,'UNAPPROVED_REPAIR_PAGE')
 require(40<=len(TASKS[p])<=650,'TASK_BUDGET')
 return TASKS[p]
def run(w,m,epoch=1,tries=3):
 w=w.expanduser().resolve();d=plan(m)
 require(w.is_relative_to(CERT_ROOT) and (w/'site').is_dir(),'ISOLATION_REQUIRED')
 require(d['project']=='andaz-vibe-stay' and 1<=epoch<=20 and 1<=tries<=3,'BOUNDS')
 names=[x['file'] for x in d['pages']]
 require(names==['index.html','rooms.html','experiences.html','food.html','explore.html','contact.html'],'ROUTE_SCOPE')
 with (w/'.full-site.lock').open('a+') as lock:
  try:fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:raise ValueError('ALREADY_RUNNING')
  original_state=state(w)
  require(original_state['site_sha256']==treehash(w/'site'),'SOURCE_HASH_DRIFT')
  failed=[p for p in names if check_editorial((w/'site'/p).read_text(),p,d['project'])['status']!='PASS']
  require(set(failed).issubset(TASKS),'UNSUPPORTED_SCOPE')
  ledger={'schema':'factual-rag-repair-v1','epoch':epoch,'requested':failed,'completed':[],'events':[],
    'status':'RUNNING','original_source':original_state['site_sha256'],'artistic_score':None,'release_authorized':False}
  report=w/'reports'/('factual-repair-epoch'+str(epoch)+'.json')
  require(not report.exists(),'EPOCH_ALREADY_USED');write(report,ledger)
  backups=w/'evidence/factual-source-backups';backups.mkdir(parents=True,exist_ok=True,mode=0o700)
  for page in failed:
   source=w/'site'/page;old=source.read_bytes();old_hash=sha(source)
   backup=backups/(page+'-'+old_hash[:16]+'.bak')
   if backup.exists():require(backup.read_bytes()==old,'BACKUP_COLLISION')
   else:
    with backup.open('xb') as f:f.write(old)
    backup.chmod(0o600)
   ok=False
   for attempt in range(1,tries+1):
    current=state(w)
    require(current['site_sha256']==treehash(w/'site'),'PRE_REPAIR_SOURCE_DRIFT')
    tid='fact-'+hashlib.sha256((current['job_id']+page+str(epoch)+str(attempt)+old_hash).encode()).hexdigest()[:23]
    folder=w/'tasks'/tid;require(not folder.exists(),'TASK_REPLAY')
    source.unlink()
    st=state(w);st['site_sha256']=treehash(w/'site')
    for g in ('actual_render_and_screenshot','technical_qa','independent_artistic_review'):st['stage_status'][g]='PENDING'
    st['artistic_score']=None;write(w/'engine-state.json',st)
    try:
     model='groq-oss120' if page=='experiences.html' else 'groq-oss20'
     cmd=['python3',str(Path(__file__).parent/'agent.py'),'--workspace',str(w),
       '--target',page,'--task',bounded_task(page),'--task-id',tid,'--site-brief',
       '--style-reference','--style-path',d['css_file']]
     process=subprocess.run(cmd,env={**os.environ,'UIUX_GROQ_FREE_ROUTE':model},
          capture_output=True,text=True,timeout=170)
     rec=folder/'receipt.json'
     if process.returncode==0 and rec.exists() and json.loads(rec.read_text()).get('status')=='PASS':
      validate_html(source.read_text(),d['project'],w/'site',page=page)
      require(check_editorial(source.read_text(),page,d['project'])['status']=='PASS','FACTUAL_REPAIR_FAILED')
      ingest_agent(w,rec)
      ledger['completed'].append(page)
      ledger['events'].append({'page':page,'attempt':attempt,'result':'PASS','model':model,'source_sha256':sha(source)})
      ok=True
     else:
      reason=json.loads(rec.read_text()).get('validation_failure') if rec.exists() else 'NO_RECEIPT'
      ledger['events'].append({'page':page,'attempt':attempt,'result':'REJECTED','reason':str(reason)[:130]})
    except Exception as e:ledger['events'].append({'page':page,'attempt':attempt,'result':'BLOCKED','reason':type(e).__name__+':'+str(e)[:110]})
    finally:
     if not ok:
      source.write_bytes(old);write(w/'engine-state.json',current)
     write(report,ledger)
    if ok:break
   if not ok:
    ledger['status']='BLOCKED';ledger['reason']='REGENERATION_EXHAUSTED:'+page
    write(report,ledger);return ledger
  remaining={p:check_editorial((w/'site'/p).read_text(),p,d['project'])['issues'] for p in names}
  ledger['remaining']={p:x for p,x in remaining.items() if x}
  ledger['status']='PASS' if not ledger['remaining'] else 'BLOCKED'
  ledger['final_source_sha256']=treehash(w/'site');write(report,ledger)
  return ledger
if __name__=='__main__':
 ap=argparse.ArgumentParser()
 ap.add_argument('--workspace',type=Path,required=True)
 ap.add_argument('--manifest',type=Path,required=True)
 ap.add_argument('--epoch',type=int,default=1)
 ap.add_argument('--max-attempts',type=int,default=3)
 a=ap.parse_args()
 try:
  result=run(a.workspace,a.manifest,a.epoch,a.max_attempts)
  print(json.dumps({'status':result['status'],'completed':result['completed'],
    'remaining':result.get('remaining'),'reason':result.get('reason'),'release':False}))
  sys.exit(0 if result['status']=='PASS' else 4)
 except Exception as e:
  print(json.dumps({'status':'BLOCKED','error':type(e).__name__+':'+str(e)[:200],'release':False}))
  sys.exit(4)
