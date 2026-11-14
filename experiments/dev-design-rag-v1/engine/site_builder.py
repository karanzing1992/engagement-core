#!/usr/bin/env python3
"""Manifest-driven autonomous full-site builder; no production deploy."""
import argparse,fcntl,hashlib,json,re,shutil,subprocess,sys,time
from pathlib import Path
from core import create,state,sha,treehash,write,require,gate,verify_review
from cli import concept,ingest_agent,qa,performance,functional
from qa_repair import run as llm_qa_repair
from contrast_repair import candidate as contrast_candidate,run as contrast_repair
from reviewer import review
from performance_repair import improve_image_dimensions
from design_contract import validate_html,policy_for
from multipage_contract import layout_preflight
from editorial_contract import check_editorial
from layout_repair import repair as safe_layout_repair
from shared_contrast_repair import repair as safe_shared_contrast_repair
from vision_bridge import prepare as prepare_private_vision_review
from interactive_contract import inspect_explore,repair as safe_interactive_repair,ensure_hidden_css,stabilize_explore_layout
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
def approved_free_model_for_task(target,recovery_epoch):
  '''Deterministic bounded model selection after verified model-path failures.'''
  if target=='experiences.html' and recovery_epoch>=2:return 'groq-oss120'
  if target=='contact.html' or (recovery_epoch and target.endswith('.html')):return 'groq-oss20'
  return None

def lighthouse_with_recovery(w,names,project,event):
 """Two bounded Lighthouse passes, one raw-evidence-bound repair, no gate bypass."""
 for recovery_round in range(2):
  failed_page=None;failed_error=None
  for name in names:
   event('lighthouse:'+name,'START',{'recovery_round':recovery_round})
   try:event('lighthouse:'+name,'PASS',performance(w,name))
   except Exception as exc:
    failed_page=name;failed_error=exc
    event('lighthouse:'+name,'REPAIR_REQUIRED' if recovery_round==0 else 'BLOCKED',str(exc))
    break
  if failed_page is None:return {'status':'PASS','passes':recovery_round+1}
  if recovery_round>=1:raise failed_error
  event('lighthouse:bounded-repair','START',failed_page)
  try:repaired=improve_image_dimensions(w,failed_page)
  except Exception as repair_error:
   event('lighthouse:bounded-repair','BLOCKED',type(repair_error).__name__+': '+str(repair_error)[:130])
   raise failed_error from repair_error
  event('lighthouse:bounded-repair','PATCHED_REQUIRES_RETEST',repaired)
  event('full-browser-axe:performance-repair','START')
  event('full-browser-axe:performance-repair','PASS',qa(w,','.join(names)))
  if project=='andaz-vibe-stay':
   event('functional-e2e:performance-repair','PASS',functional(w))
 raise ValueError('UNREACHABLE_LIGHTHOUSE_RECOVERY_STATE')

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
   for attempt in range(1,7 if a.recovery_epoch else 17):
    tid='multi-'+hashlib.sha256((state(w)['job_id']+target+task+str(attempt)+':recovery:'+str(a.recovery_epoch)).encode()).hexdigest()[:22]
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
     env=None
     selected_free_model=approved_free_model_for_task(target,a.recovery_epoch)
     if selected_free_model:
      # Explicit owner-verified free model only; no paid inference and never bypass QA.
      import os
      env={**os.environ,'UIUX_GROQ_FREE_ROUTE':selected_free_model}
     p=subprocess.run(cmd,capture_output=True,text=True,timeout=170,env=env)
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
  factual={page:check_editorial((w/'site'/page).read_text(),page,d['project']) for page in names}
  write(w/'reports/full-site-factual-preflight.json',{'pages':factual,'artistic_score':None,'signed_release':False})
  problems={page:result['issues'] for page,result in factual.items() if result['status']!='PASS'}
  event('full-site-factual-preflight','BLOCKED' if problems else 'PASS',json.dumps(problems)[:220])
  require(not problems,'FACTUAL_GROUNDING_GATE_BLOCKED:'+json.dumps(problems)[:150])
  design=layout_preflight(w/'site',names,d['css_file'])
  write(w/'reports/multipage-design-preflight.json',design)
  event('multipage-design-preflight',design['status'],','.join(design['issues'])[:220])
  if design['status']!='PASS':
   event('layout-repair','START','Bounded allowlisted CSS only; no artistic certification')
   repair_receipt=safe_layout_repair(w,d['css_file'],design)
   repaired=layout_preflight(w/'site',names,d['css_file'])
   require(repaired['status']=='PASS','LAYOUT_REPAIR_VERIFICATION_FAILED:'+','.join(repaired['issues'])[:120])
   write(w/'reports/multipage-design-preflight.json',repaired)
   st=state(w)
   st['site_sha256']=treehash(w/'site')
   for k in ('actual_render_and_screenshot','technical_qa','independent_artistic_review'):
    st['stage_status'][k]='PENDING'
   st['artistic_score']=None
   write(w/'engine-state.json',st)
   event('layout-repair','PASS',repair_receipt['repairs'])
   design=repaired
  require(design['status']=='PASS','MULTIPAGE_DESIGN_PREFLIGHT_BLOCKED')
  if 'explore.html' in names:
   runtime=inspect_explore((w/'site/explore.html').read_text())
   if runtime['status']!='PASS':
    event('interactive-source-contract','REPAIR_REQUIRED',runtime['missing'])
    fixed=safe_interactive_repair(w)
    event('interactive-source-contract','PASS',fixed['changes'])
   require(inspect_explore((w/'site/explore.html').read_text())['status']=='PASS','INTERACTIVE_JS_CONTRACT_BLOCKED')
   visibility=ensure_hidden_css(w,d['css_file'])
   event('native-hidden-visibility',visibility['status'],'browser functional E2E still required')
   stabilized=stabilize_explore_layout(w)
   event('explore-first-paint-stability',stabilized['status'],'Lighthouse CLS retest required')
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
   shared_fixed=False
   try:
    receipt=safe_shared_contrast_repair(w,names,d['css_file'])
   except ValueError as shared_error:
    event('shared-wcag-contrast','NOT_APPLICABLE',str(shared_error)[:120])
   else:
    event('shared-wcag-contrast','PATCHED_REQUIRES_QA',receipt)
    event('full-browser-axe:shared-contrast-retested','PASS',qa(w,','.join(names)))
    shared_fixed=True
   if not shared_fixed:
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
  if d['project']=='andaz-vibe-stay':
   event('functional-e2e','START','synthetic WhatsApp intercept; no real send')
   try:event('functional-e2e','PASS',functional(w))
   except Exception as e:
    event('functional-e2e','BLOCKED',str(e));raise
  event('lighthouse-recovery-flow','START')
  event('lighthouse-recovery-flow','PASS',lighthouse_with_recovery(w,names,d['project'],event))
  signed=w/'reports/independent-signed-review.json'
  if signed.is_file():
   event('independent-review','SIGNED_RECEIPT_PRESENT','verifying external independent signature')
  else:
   # Owner trust is a mandatory prerequisite for certification.
   # Do not repeatedly time out the local model if no valid signature could be accepted.
   from attestation import _trust
   try:_trust()
   except ValueError as trust_error:
    try:
     handoff=prepare_private_vision_review(w)
     event('private-vision-handoff','PREPARED_LOCAL_ONLY',handoff)
    except Exception as handoff_error:
     event('private-vision-handoff','BLOCKED',str(handoff_error)[:160])
    event('independent-review','BLOCKED','OWNER_TRUST_REQUIRED:'+str(trust_error))
    raise
   try:event('independent-review','EVIDENCE_ONLY',review(w,0,a.vision_model,a.vision_timeout))
   except Exception as e:
    try:
     handoff=prepare_private_vision_review(w)
     event('private-vision-handoff','PREPARED_LOCAL_ONLY',handoff)
    except Exception as handoff_error:
     event('private-vision-handoff','BLOCKED',str(handoff_error)[:160])
    event('independent-review','BLOCKED',str(e));raise
  require(signed.is_file() and not signed.is_symlink(),'INDEPENDENT_SIGNED_ART_REQUIRED')
  verify_review(w,signed)
  passed=gate(w,'preview')
  require(passed['status']=='PASS','PREVIEW_BLOCKED')
  x['status']='PREFLIGHT_PASS';write(log,x)
  return {'status':'PREFLIGHT_PASS','routes':names,'production':False}
def resume_artistic_only(w):
  '''Finish independent reviewer certification without re-running generation or Lighthouse.'''
  w=w.expanduser().resolve()
  require(w.is_relative_to(ROOT) and (w/'site').is_dir(),'ISOLATED_ROOT_REQUIRED')
  with (w/'.full-site.lock').open('a+') as lock:
   try:fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
   except BlockingIOError:raise ValueError('ALREADY_RUNNING')
   s=state(w)
   require(s['site_sha256']==treehash(w/'site'),'SOURCE_HASH_DRIFT')
   required=('rag_retrieval','autonomous_concept_and_design','autonomous_implementation',
        'actual_render_and_screenshot','technical_qa')
   require(all(s['stage_status'][k]=='PASS' for k in required),'TECHNICAL_PREFLIGHT_REQUIRED')
   qa_path=w/'reports/browser-qa.json'
   require(qa_path.is_file() and sha(qa_path)==s.get('qa_receipt_sha256'),'QA_RECEIPT_DRIFT')
   qa_data=json.loads(qa_path.read_text())
   require(qa_data.get('pass') is True and qa_data.get('source_hash')==s['site_sha256'],
           'QA_SOURCE_MISMATCH')
   lh=w/'reports/lighthouse-summary.json'
   require(lh.is_file() and sha(lh)==s.get('lighthouse_summary_sha256'),'LIGHTHOUSE_RECEIPT_DRIFT')
   summary=json.loads(lh.read_text())
   pages={r['page'] for r in qa_data['screenshots']}
   require(summary.get('status')=='PASS' and set(summary.get('pages',{}))==pages and
      summary.get('source_sha256')==s['site_sha256'] and
      summary.get('browser_receipt_sha256')==s['qa_receipt_sha256'],
      'LIGHTHOUSE_TECHNICAL_GATE_REQUIRED')
   receipt=w/'reports/independent-signed-review.json'
   require(receipt.is_file() and not receipt.is_symlink(),'EXTERNAL_INDEPENDENT_SIGNED_RECEIPT_MISSING')
   from attestation import _trust
   _trust()
   reviewed=verify_review(w,receipt)
   result=gate(w,'preview')
   require(result['status']=='PASS','PREVIEW_ARTISTIC_GATE_BLOCKED')
   return {'status':'PREFLIGHT_PASS','artistic_score':reviewed['score'],
     'pages':sorted(pages),'production_release_allowed':False}

if __name__=='__main__':
 ap=argparse.ArgumentParser()
 ap.add_argument('--workspace',required=True,type=Path)
 ap.add_argument('--manifest',required=True,type=Path)
 ap.add_argument('--baseline',type=Path)
 ap.add_argument('--vision-model',default='qwen3-vl:2b-instruct')
 ap.add_argument('--vision-timeout',type=int,default=100)
 ap.add_argument('--recovery-epoch',type=int,default=0)
 ap.add_argument('--status',action='store_true')
 ap.add_argument('--resume-artistic',action='store_true')
 a=ap.parse_args()
 if a.resume_artistic:
  try:print(json.dumps(resume_artistic_only(a.workspace),indent=2))
  except Exception as e:
   print(json.dumps({'status':'BLOCKED','reason':type(e).__name__+':'+str(e)[:240]}));sys.exit(4)
 elif a.status:
  f=a.workspace/'reports/full-site-ledger.json'
  print(f.read_text() if f.exists() else '{"status":"NOT_STARTED"}')
 else:
  try:print(json.dumps(run(a),indent=2))
  except Exception as e:
   print(json.dumps({'status':'BLOCKED','reason':type(e).__name__+':'+str(e)[:250]}))
   sys.exit(4)
