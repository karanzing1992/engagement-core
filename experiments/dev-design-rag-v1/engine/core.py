"""Reusable UIUX V2 artifact, provenance and fail-closed release controls."""
import hashlib,json,os,shutil,sys,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from dev_design_rag.core import Registry
from dev_design_rag.knowledge_v2 import build_packet
from attestation import validate as validate_artistic_attestation
from version import ENGINE_VERSION
RUNTIME=Path.home()/'.local/share/dev-design-rag-v1/runtime'
STAGES=('rag_retrieval','autonomous_concept_and_design','autonomous_implementation','actual_render_and_screenshot','independent_artistic_review','technical_qa','isolated_preview','owner_release_approval')
def require(ok,why):
 if not ok:raise ValueError(why)
def write(path,data):
 path.parent.mkdir(parents=True,exist_ok=True)
 tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(data,indent=2,ensure_ascii=False));os.replace(tmp,path)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def treehash(path):
 h=hashlib.sha256()
 for f in sorted(path.rglob('*')):
  if f.is_symlink():raise ValueError('SITE_SYMLINK_FORBIDDEN')
  if f.is_file() and '.git' not in f.parts:
   h.update(f.relative_to(path).as_posix().encode()+b'\0');h.update(bytes.fromhex(sha(f)))
 return h.hexdigest()
def workspace(path):
 w=path.expanduser().resolve()
 require(w.is_dir() and (w/'site').is_dir() and (w/'site').resolve().is_relative_to(w),'INVALID_WORKSPACE')
 return w
def state(w):
 d=json.loads((w/'engine-state.json').read_text())
 require(d.get('version') in ('2.0.0',ENGINE_VERSION) and d.get('execution_mode')=='autonomous_engine_required','INVALID_ENGINE_STATE')
 require(set(d.get('stage_status',{}))==set(STAGES),'INVALID_STAGES')
 return d
def create(path,baseline,project,prompt):
 w=path.expanduser().resolve();base=baseline.expanduser().resolve()
 require(base.is_dir() and not w.exists() and base!=w and base!=Path('/'),'UNSAFE_BASELINE_OR_WORKSPACE')
 packet=build_packet(Registry(RUNTIME),project,prompt)
 require(packet['status']=='READY' and packet['estimated_tokens_upper_bound']<=3000,'V2_CONTEXT_BUDGET_FAIL')
 w.mkdir(parents=True);shutil.copytree(base,w/'site',ignore=shutil.ignore_patterns('.git','node_modules','*.key','*.pem','*.env','.env*'))
 (w/'evidence').mkdir();(w/'reports').mkdir()
 write(w/'reports/rag-v2.json',{k:v for k,v in packet.items() if k!='packet_text'})
 (w/'evidence/rag-packet.txt').write_text(packet['packet_text'])
 src=treehash(w/'site')
 d={'version':ENGINE_VERSION,'job_id':uuid.uuid4().hex,'project':project,'execution_mode':'autonomous_engine_required','baseline_sha256':src,
   'site_sha256':src,'rag_sha256':packet['packet_sha256'],'stage_status':{k:'PASS' if k=='rag_retrieval' else 'PENDING' for k in STAGES},
   'artistic_score':None,'independent_verdict':None,'owner_release_authorized':False,
   'manual_only_build':False,'preview_url':None}
 write(w/'engine-state.json',d)
 return {'status':'PREPARED','workspace':str(w),'baseline_hash':src,'rag_token_estimate':packet['estimated_tokens_upper_bound']}
def verify_review(w,receipt):
 s=state(w)
 r=validate_artistic_attestation(w,receipt,s,sha,treehash)
 accepted=w/'reports/accepted-art-review.json'
 write(accepted,r)
 s['artistic_score']=r['score']
 s['independent_verdict']='APPROVE'
 s['stage_status']['independent_artistic_review']='PASS'
 s['artistic_receipt_sha256']=sha(accepted)
 write(w/'engine-state.json',s)
 return {'status':'PASS','score':r['score'],'site_hash':s['site_sha256']}

def gate(w,phase='preview'):
 s=state(w);bad=[]
 try:
  if s['site_sha256']!=treehash(w/'site'):bad.append('SOURCE_HASH_DRIFT')
 except Exception:bad.append('UNSAFE_OR_UNREADABLE_SITE')
 for stage in STAGES[:6]:
  if s['stage_status'].get(stage)!='PASS':bad.append('MISSING:'+stage)
 qp=w/'reports/browser-qa.json';pages=set()
 if not qp.is_file():bad.append('QA_RECEIPT_MISSING')
 else:
  try:
   q=json.loads(qp.read_text())
   shots=q['screenshots'];pages={x['page'] for x in shots}
   pairs={(x['page'],x['width']) for x in shots}
   if (q.get('pass') is not True or q.get('source_hash')!=s['site_sha256'] or
       sha(qp)!=s.get('qa_receipt_sha256') or len(pairs)!=len(shots) or
       not pages or any((p,width) not in pairs for p in pages for width in (320,390,768,1440))):
    bad.append('QA_EVIDENCE_WRONG_BUILD_OR_INCOMPLETE')
  except Exception:bad.append('QA_EVIDENCE_UNREADABLE')
 lh=w/'reports/lighthouse-summary.json'
 if not lh.is_file():bad.append('LIGHTHOUSE_ROUTE_COVERAGE_MISSING')
 else:
  try:
   summary=json.loads(lh.read_text())
   if (sha(lh)!=s.get('lighthouse_summary_sha256') or
       summary.get('source_sha256')!=s['site_sha256'] or
       summary.get('browser_receipt_sha256')!=s.get('qa_receipt_sha256')):
    bad.append('LIGHTHOUSE_EVIDENCE_WRONG_BUILD')
   measured=summary.get('pages',{})
   if not pages or set(measured)!=pages:bad.append('LIGHTHOUSE_ROUTE_COVERAGE_INCOMPLETE')
   for page in pages:
    modes=measured.get(page,{})
    for mode in ('mobile','desktop'):
     entry=modes.get(mode)
     if not isinstance(entry,dict):
      bad.append('LIGHTHOUSE_MISSING:'+page+':'+mode);continue
     target=w/'reports'/('lighthouse-'+page.replace('.html','')+'-'+mode+'.json')
     if not target.is_file() or sha(target)!=entry.get('report_sha256'):
      bad.append('LIGHTHOUSE_RAW_REPORT_MISMATCH:'+page+':'+mode);continue
     scores=entry.get('scores',{})
     try:
      raw=json.loads(target.read_text())
      for field in ('requestedUrl','finalUrl'):
       url=raw.get(field,'')
       if not (isinstance(url,str) and url.startswith('http://127.0.0.1:') and url.split('?',1)[0].endswith('/'+page)):
        bad.append('LIGHTHOUSE_WRONG_ROUTE:'+page+':'+mode+':'+field)
      if not raw.get('fetchTime') or not raw.get('lighthouseVersion'):
       bad.append('LIGHTHOUSE_PROVENANCE_MISSING:'+page+':'+mode)
      raw_scores={name:round(v['score']*100) for name,v in raw.get('categories',{}).items() if type(v.get('score')) in (int,float)}
      for name in ('performance','accessibility','best-practices'):
       if scores.get(name)!=raw_scores.get(name):
        bad.append('LIGHTHOUSE_RAW_SCORE_MISMATCH:'+page+':'+mode+':'+name)
     except Exception:bad.append('LIGHTHOUSE_RAW_REPORT_UNREADABLE:'+page+':'+mode)
     for name,minimum in (('performance',90),('accessibility',95),('best-practices',90)):
      v=scores.get(name)
      if type(v) not in (int,float) or v<minimum:
       bad.append('LIGHTHOUSE_THRESHOLD:'+page+':'+mode+':'+name)
  except Exception:bad.append('LIGHTHOUSE_EVIDENCE_UNREADABLE')
 review=w/'reports/accepted-art-review.json'
 if not review.is_file() or sha(review)!=s.get('artistic_receipt_sha256'):
  bad.append('INDEPENDENT_ARTISTIC_RECEIPT_MISSING')
 else:
  try:
   data=validate_artistic_attestation(w,review,s,sha,treehash)
   if data['score']!=s.get('artistic_score') or s.get('independent_verdict')!='APPROVE':
    bad.append('ARTISTIC_STATE_MISMATCH')
  except Exception as e:bad.append('ARTISTIC_ATTESTATION_INVALID:'+str(e)[:85])
 score=s.get('artistic_score')
 if type(score) not in (int,float) or score<95 or s.get('independent_verdict')!='APPROVE':
  bad.append('ARTISTIC_95_NOT_APPROVED')
 if s.get('manual_only_build'):bad.append('AUTONOMOUS_CODE_REQUIRED')
 if phase=='release':bad.append('OWNER_RELEASE_AUTHORITY_EXTERNAL_ONLY')
 return {'status':'BLOCKED' if bad else 'PASS','phase':phase,'missing':bad,
  'site_sha256':s['site_sha256'],'production_release_allowed':False}
