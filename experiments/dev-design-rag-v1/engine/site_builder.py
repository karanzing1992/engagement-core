#!/usr/bin/env python3
"""Manifest-driven autonomous full-site builder; no production deploy."""
import argparse,fcntl,hashlib,json,re,shutil,subprocess,sys,time
from pathlib import Path
from core import create,state,sha,treehash,write,require,gate,verify_review
from cli import concept,ingest_agent,qa,performance
from qa_repair import run as llm_qa_repair
from contrast_repair import candidate as contrast_candidate,run as contrast_repair
from reviewer import review
from design_contract import validate_html,policy_for
from multipage_contract import layout_preflight
ENGINE=Path(__file__).resolve().parent
ROOT=Path.home()/'.local/share/dev-design-rag-v1/certification'
def plan(path):
 require(path.is_file() and not path.is_symlink() and path.stat().st_size<128000,'SAFE_PLAN_REQUIRED')
 d=json.loads(path.read_text());pages=d['pages']
 require(1<=len(pages)<=64 and policy_for(d['project']) is not None,'OWNER_VERIFIED_PROJECT_AND_SITEMAP_REQUIRED')
 d['css_file']=d.get('css_file','assets/v9-main.css' if d['project']=='andaz-vibe-stay' else 'assets/site.css')
 require(bool(re.fullmatch(r'assets/[a-z][a-z0-9-]{2,60}\.css',d['css_file'])),'UNSAFE_CSS_TARGET')
 require(any(p['file']=='index.html' for p in pages),'HOMEPAGE_REQUIRED')
 require(len(set(p['file'] for p in pages))==len(pages),'DUPLICATE_ROUTE')
 for p in pages:
  require(bool(re.fullmatch(r'[a-z0-9][a-z0-9-]{2,64}\.html',p['file'])),'UNSAFE_PAGE')
  require(40<=len(p['task'])<=650,'PAGE_TASK_BUDGET')
 require(100<len(d['full_brief'])<12000 and len(d['brand_prompt'])<800,'BRAND_BRIEF_INVALID')
 require(100<len(d['css_task'])<=650,'CSS_TASK_INVALID')
 return d
def run(a):
 d=plan(a.manifest);w=a.workspace.expanduser().resolve()
 require(w.is_relative_to(ROOT),'ISOLATED_ROOT_REQUIRED')
 if not (w/'engine-state.json').exists():create(w,a.baseline,d['project'],d['brand_prompt'])
 require(w.is_dir() and (w/'site').is_dir(),'WORKSPACE_INVALID')
 with (w/'.full-site.lock').open('a+') as lf:
  try:fcntl.flock(lf.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:raise ValueError('ALREADY_RUNNING')
  brief=w/'evidence/full-site-brief.txt'
  if brief.exists():require(brief.read_text()==d['full_brief'],'BRIEF_CHANGED')
  else:brief.write_text(d['full_brief'])
  log=w/'reports/full-site-ledger.json'
  if log.exists():
   x=json.loads(log.read_text());require(x['manifest_sha256']==sha(a.manifest),'PLAN_CHANGED')
  else:
   x={'schema':'autonomous-full-site-v1','manifest_sha256':sha(a.manifest),
      'pages_planned':[p['file'] for p in d['pages']],'completed':[],
      'events':[],'status':'RUNNING','artistic_score':None,
      'production_release_allowed':False};write(log,x)
  def event(stage,status,msg=''):
   x['events'].append({'stage':stage,'status':status,'message':str(msg)[:240],'at':int(time.time())})
   x['status']='BLOCKED' if status=='BLOCKED' else 'RUNNING'
   write(log,x)
  if state(w)['stage_status']['autonomous_concept_and_design']!='PASS':
   event('concept','START');event('concept','PASS',concept(w))
  else:event('concept','REUSED')
  def build(target,task,style):
   if target in x['completed']:
    require((w/'site'/target).is_file(),'LOST_COMMITTED_OUTPUT')
    event(target,'REUSED');return
   require(not (w/'site'/target).exists(),'EXISTING_OUTPUT_PROTECTED')
   for attempt in range(1,17):
    tid='multi-'+hashlib.sha256((state(w)['job_id']+target+task+str(attempt)).encode()).hexdigest()[:22]
    receipt=w/'tasks'/tid/'receipt.json'
    if (w/'tasks'/tid).exists():
     if not receipt.exists() or json.loads(receipt.read_text()).get('status')!='PASS':
      event(target,'PREVIOUS_ATTEMPT_REJECTED',tid);continue
     require(json.loads(receipt.read_text())['output_site_sha256']==treehash(w/'site'),'REPLAY_DRIFT')
    else:
     cmd=['python3',str(ENGINE/'agent.py'),'--workspace',str(w),'--target',target,
          '--task',task,'--task-id',tid,'--site-brief']
     if style:cmd.extend(['--style-reference','--style-path',d['css_file']])
     event(target,'START',tid)
     p=subprocess.run(cmd,capture_output=True,text=True,timeout=170)
     if p.returncode!=0 or not receipt.exists():
      event(target,'ATTEMPT_FAILED',p.stdout[-180:]+p.stderr[-70:]);continue
     r=json.loads(receipt.read_text())
     if r.get('status')!='PASS':
      event(target,'ATTEMPT_REJECTED',r.get('validation_failure'));continue
    result=ingest_agent(w,receipt)
    if target.endswith('.html'):
     validate_html((w/'site'/target).read_text(),d['project'],w/'site',page=target)
    x['completed'].append(target);event(target,'PASS',result);return
   event(target,'BLOCKED','bounded agent retries exhausted')
   raise ValueError('AGENT_GENERATION_BLOCKED:'+target)
  build(d['css_file'],d['css_task'],False)
  for item in d['pages']:build(item['file'],item['task'],True)
  names=[p['file'] for p in d['pages']]
  design=layout_preflight(w/'site',names,d['css_file'])
  write(w/'reports/multipage-design-preflight.json',design)
  event('multipage-design-preflight',design['status'],','.join(design['issues'])[:220])
  require(design['status']=='PASS','MULTIPAGE_DESIGN_PREFLIGHT_BLOCKED')
  event('full-browser-axe','START',names)
  try:event('full-browser-axe','PASS',qa(w,','.join(names)))
  except Exception as e:
   full=w/'reports/browser-qa.json'
   require(full.is_file(),'QA_FAILURE_RECEIPT_MISSING')
   report=json.loads(full.read_text())
   require(not report.get('missing_links'),'BROKEN_INTERNAL_LINKS')
   bad=sorted({row['page'] for row in report['rows'] if not row['pass']})
   require(bad and len(bad)<=len(names),'BAD_QA_COVERAGE')
   event('full-browser-axe','REPAIR_REQUIRED',bad)
   for file in bad:
    event('qa-repair:'+file,'START')
    try:qa(w,file)
    except Exception as single_error:
     try:contrast_candidate(w,file)
     except ValueError:
      original=next(p['task'] for p in d['pages'] if p['file']==file)
      improved=llm_qa_repair(w,file,original,2,event)
     else:improved=contrast_repair(w,file,event)
     source=w/'site'/improved
     destination=w/'site'/file
     require(source.is_file() and destination.is_file(),'REPAIR_ARTIFACT_MISSING')
     history=w/'evidence'/('source-'+file+'-'+sha(destination)[:14])
     require(not history.exists(),'REVISION_REPLAY_COLLISION')
     shutil.copy2(destination,history)
     shutil.copy2(source,destination)
     s=state(w);s['site_sha256']=treehash(w/'site')
     s['stage_status']['actual_render_and_screenshot']='PENDING'
     s['stage_status']['technical_qa']='PENDING'
     s['stage_status']['independent_artistic_review']='PENDING'
     s['artistic_score']=None
     write(w/'engine-state.json',s)
     event('qa-repair:'+file,'PROMOTED_ISOLATED',improved)
    else:event('qa-repair:'+file,'NOT_REPRODUCIBLE',str(e))
   event('full-browser-axe:retested','START')
   event('full-browser-axe:retested','PASS',qa(w,','.join(names)))
  for name in names:
   event('lighthouse:'+name,'START')
   try:event('lighthouse:'+name,'PASS',performance(w,name))
   except Exception as e:
    event('lighthouse:'+name,'BLOCKED',str(e));raise
  try:event('independent-review','EVIDENCE_ONLY',review(w,0,a.vision_model,a.vision_timeout))
  except Exception as e:
   event('independent-review','BLOCKED',str(e));raise
  signed=w/'reports/independent-signed-review.json'
  require(signed.is_file(),'INDEPENDENT_SIGNED_ART_REQUIRED')
  verify_review(w,signed)
  passed=gate(w,'preview')
  require(passed['status']=='PASS','PREVIEW_BLOCKED')
  x['status']='PREFLIGHT_PASS';write(log,x)
  return {'status':'PREFLIGHT_PASS','routes':names,'production':False}
if __name__=='__main__':
 ap=argparse.ArgumentParser()
 ap.add_argument('--workspace',required=True,type=Path)
 ap.add_argument('--manifest',required=True,type=Path)
 ap.add_argument('--baseline',type=Path)
 ap.add_argument('--vision-model',default='qwen3-vl:2b-instruct')
 ap.add_argument('--vision-timeout',type=int,default=100)
 ap.add_argument('--status',action='store_true')
 a=ap.parse_args()
 if a.status:
  f=a.workspace/'reports/full-site-ledger.json'
  print(f.read_text() if f.exists() else '{"status":"NOT_STARTED"}')
 else:
  try:print(json.dumps(run(a),indent=2))
  except Exception as e:
   print(json.dumps({'status':'BLOCKED','reason':type(e).__name__+':'+str(e)[:250]}))
   sys.exit(4)
