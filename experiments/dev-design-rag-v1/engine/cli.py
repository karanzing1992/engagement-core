#!/usr/bin/env python3
"""Dell Generic Design RAG V2 autonomous workflow controls; no production deploy."""
import argparse,hashlib,http.server,json,os,socketserver,subprocess,sys,threading
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from core import create,workspace,state,write,treehash,sha,gate,verify_review,require
ROOT=Path(__file__).resolve().parents[1]
def concept(w):
 d=state(w);txt=(w/'evidence/rag-packet.txt').read_text()
 require(hashlib.sha256(txt.encode()).hexdigest()==d['rag_sha256'],'RAG_CHANGED')
 # One bounded concept task, not full-context model conversation.
 data=json.loads((w/'reports/rag-v2.json').read_text())
 layers=data['layers']
 cues=(next(k for k in layers if k.startswith('project/')),
      next(k for k in layers if k.startswith('brand/')),
      'generic/shared',
      next(k for k in layers if k.startswith('type/')))
 limits=(590,510,250,160)
 chunks=[k+'\n'+layers[k]['context'][:n] for k,n in zip(cues,limits)]
 prompt=('Propose TWO distinct UI designs based on CURRENT project and brand rules; pick one. '
  'Give navigation, mobile, interaction, brand and accessible typography recommendations. '
  'Return under 400 words; this is not screenshot/artistic certification.\n'+'\n'.join(chunks))
 require(len(prompt.encode('utf8'))<=2048,'ROUTER_PUBLIC_PROMPT_2048_BYTE_LIMIT')
 # Enforce existing owner-approved model routing SOP, never invent grants.
 approvals=json.loads(Path('/var/lib/generic-linux-automator-exec/matrix-controller/owner-intake-approvals-v1.json').read_text())['approvals']
 project=d['project'].replace('-','_')
 refs=[x['approval_ref'] for x in approvals if x.get('project')==project and x.get('approved_by')=='owner']
 require(bool(refs),'NO_APPROVED_EXTERNAL_MODEL_ENVELOPE_FOR_PROJECT')
 packet={'packet_version':'1.0','department':'development','project_id':project,
  'baseline_sha256':d['baseline_sha256'],'task_id':'GenericUIUXV2Concept'+d['baseline_sha256'][:11]+hashlib.sha256(prompt.encode()).hexdigest()[:9],
  'idempotency_key':'uiux-v2-'+d['baseline_sha256'][:16]+'-'+hashlib.sha256(prompt.encode()).hexdigest()[:10]+'-concept',
  'owner_envelope_ref':refs[-1],
  'data_policy':{'classification':'public','external_transfer_authorized':True,'redaction_verified':True},
  'routing_policy':{'mode':'external','license_decision':'osi_verified',
   'license_receipt_ref':'Existing Dell GPT-OSS Apache-2.0 model license',
   'provider_ids':['groq-oss20'],'model_ids':['openai/gpt-oss-20b']},
  'allowed_paths':[str(w/'evidence')],'input_evidence':[{'type':'V2_RAG_CURRENT_PACKET','sha256':d['rag_sha256']}],
  'qa':{'reviewer_id':'independent-real-screenshot-review','test_refs':['V2 source accuracy','owner artistic >=95','mobile QA'],
   'acceptance':'Proposal only; no production code writes or deployment.'},
  'budget':{'paid_cap':0,'reserved_amount':0,'max_total_attempts':1,
   'max_input_tokens':2000,'max_output_tokens':650},
  'reporting':{'release_mode':'none','allow_publishing':False,'allow_production_deployment':False},
  'forbidden_effects':['deployment','external_messages','production_write','git_push','unbounded_shell','secret_exfiltration']}
 sop=w/'reports/concept-sop.json';write(sop,packet);sop.chmod(0o600)
 command=['python3',str(Path.home()/'.local/share/matrix-dev-router/matrix-route.py'),'run',
 '--slot','groq-oss20','--no-fallback','--profile','coding','--public-input',
 '--task-packet',str(sop),prompt]
 p=subprocess.run(command,text=True,capture_output=True,timeout=92)
 require(p.returncode==0 and len(p.stdout)>320,'MODEL_CONCEPT_FAILED:'+p.stderr[-160:])
 (w/'evidence/concept-router.txt').write_text(p.stdout)
 d['stage_status']['autonomous_concept_and_design']='PASS'
 d['concept_receipt_sha256']=sha(w/'evidence/concept-router.txt')
 write(w/'engine-state.json',d)
 return {'status':'PASS','concept_output_bytes':len(p.stdout),'router':'groq-oss20','artistic_certified':False}
def qa(w,pages):
 d=state(w)
 require(d['stage_status']['autonomous_implementation']=='PASS','AGENT_IMPLEMENTATION_RECEIPT_REQUIRED')
 require(d['site_sha256']==treehash(w/'site'),'SOURCE_HASH_DRIFT')
 class Handler(http.server.SimpleHTTPRequestHandler):
  def __init__(self,*a,**kw):super().__init__(*a,directory=str(w/'site'),**kw)
  def log_message(self,*a):pass
 with socketserver.TCPServer(('127.0.0.1',0),Handler) as server:
  runner=threading.Thread(target=server.serve_forever,daemon=True);runner.start()
  options={'root':str(w/'site'),'url':'http://127.0.0.1:'+str(server.server_address[1]),
  'source_hash':d['site_sha256'],'screenshots':str(w/'evidence/screenshots'),
  'report':str(w/'reports/browser-qa.json'),'pages':pages.split(',')}
  write(w/'reports/qa-options.json',options)
  env=os.environ.copy()
  env['NODE_PATH']=str(Path.home()/'.local/share/andaz-autonomous-website-pilot-20261106/audit-engine/node_modules')
  p=subprocess.run(['node',str(ROOT/'engine/qa-site.cjs'),str(w/'reports/qa-options.json')],env=env,text=True,capture_output=True,timeout=175)
  server.shutdown()
 require(p.returncode==0,'BROWSER_QA_BLOCKED:'+p.stdout[-250:]+p.stderr[-250:])
 r=json.loads((w/'reports/browser-qa.json').read_text())
 require(r['pass'] and r['source_hash']==d['site_sha256'] and len(r['screenshots'])>=len(pages.split(','))*4,'QA_RECEIPT_INCOMPLETE')
 d['stage_status']['actual_render_and_screenshot']='PASS'
 d['stage_status']['technical_qa']='PENDING'
 d['qa_receipt_sha256']=sha(w/'reports/browser-qa.json')
 write(w/'engine-state.json',d)
 return {'status':'PASS','rows':len(r['rows']),'screenshots':len(r['screenshots']),'sha256':d['site_sha256']}
def performance(w,page):
 from lighthouse import audit
 d=state(w)
 require(d['site_sha256']==treehash(w/'site'),'SOURCE_DRIFT')
 qa_file=w/'reports/browser-qa.json'
 require(qa_file.is_file() and sha(qa_file)==d.get('qa_receipt_sha256'),'QA_RECEIPT_REQUIRED')
 q=json.loads(qa_file.read_text())
 require(q['pass'] and q['source_hash']==d['site_sha256'],'QA_NOT_VERIFIED')
 required=sorted({x['page'] for x in q['screenshots']})
 require(page in required,'LIGHTHOUSE_PAGE_NOT_IN_QA')
 class Handler(http.server.SimpleHTTPRequestHandler):
  def __init__(self,*a,**kw):super().__init__(*a,directory=str(w/'site'),**kw)
  def log_message(self,*z):pass
 with socketserver.TCPServer(('127.0.0.1',0),Handler) as server:
  thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
  results=audit('http://127.0.0.1:'+str(server.server_address[1]),w/'site',w/'reports',page)
  server.shutdown()
 summary_path=w/'reports/lighthouse-summary.json'
 old=json.loads(summary_path.read_text()) if summary_path.is_file() else {}
 if old.get('source_sha256')==d['site_sha256'] and old.get('browser_receipt_sha256')==d['qa_receipt_sha256']:
  pages=old.get('pages',{})
 else:pages={}
 pages[page]=results
 complete=set(pages)==set(required)
 summary={'status':'PASS' if complete else 'PARTIAL','pages':pages,
    'required_pages':required,'source_sha256':d['site_sha256'],
    'browser_receipt_sha256':d['qa_receipt_sha256'],
    'seo_note':'Isolated noindex previews; production SEO assessed separately'}
 write(summary_path,summary)
 d['lighthouse_summary_sha256']=sha(summary_path)
 d['stage_status']['technical_qa']='PASS' if complete else 'PENDING'
 write(w/'engine-state.json',d)
 return {'status':summary['status'],'page':page,'page_scores':results,
         'audited_pages':len(pages),'required_pages':len(required)}
def ingest_agent(w,receipt):
 d=state(w);r=json.loads(receipt.read_text())
 require(d['stage_status']['autonomous_concept_and_design']=='PASS','DESIGN_STAGE_REQUIRED')
 require(r.get('agent')=='opencode' and r.get('status')=='PASS' and r.get('tool_file_write_verified') is True,'AGENT_PROVENANCE_REQUIRED')
 require(r.get('baseline_sha256')==d['baseline_sha256'],'WRONG_BASELINE')
 require(r.get('output_site_sha256')==treehash(w/'site'),'WRONG_OUTPUT_HASH')
 require(r.get('task_source')=='bounded_v2_rag' and r.get('prompt_token_budget',99999)<=3000,'BAD_AGENT_CONTEXT')
 require(r.get('code_files_written',0)>=1,'NO_ACTUAL_CODE_WRITE')
 d['stage_status']['autonomous_implementation']='PASS'
 d['site_sha256']=r['output_site_sha256'];d['agent_receipt_sha256']=sha(receipt)
 write(w/'reports/accepted-agent.json',r);write(w/'engine-state.json',d)
 return {'status':'PASS','actual_agent_files_written':r['code_files_written'],'site_sha256':d['site_sha256']}
def main():
 ap=argparse.ArgumentParser();sub=ap.add_subparsers(dest='command',required=True)
 for name in ('prepare','concept','accept-agent','qa','lighthouse','accept-art','gate','status'):
  x=sub.add_parser(name);x.add_argument('--workspace',type=Path,required=True)
  if name=='prepare':
   x.add_argument('--baseline',type=Path,required=True);x.add_argument('--project',required=True);x.add_argument('--prompt',required=True)
  if name in ('accept-agent','accept-art'):x.add_argument('--receipt',type=Path,required=True)
  if name=='lighthouse':x.add_argument('--page',default='index.html')
  if name=='qa':x.add_argument('--pages',default='index.html,rooms.html,experiences.html,explore.html,contact.html')
  if name=='gate':x.add_argument('--phase',choices=['preview','release'],default='preview')
 a=ap.parse_args()
 try:
  if a.command=='prepare':o=create(a.workspace,a.baseline,a.project,a.prompt)
  else:
   w=workspace(a.workspace)
   o={'concept':lambda:concept(w),'accept-agent':lambda:ingest_agent(w,a.receipt),
      'qa':lambda:qa(w,a.pages),'lighthouse':lambda:performance(w,a.page),'accept-art':lambda:verify_review(w,a.receipt),
      'gate':lambda:gate(w,a.phase),'status':lambda:state(w)}[a.command]()
  print(json.dumps(o,indent=2))
  return 0 if o.get('status')!='BLOCKED' else 4
 except Exception as e:
  print(json.dumps({'status':'BLOCKED','step':a.command,'reason':type(e).__name__+': '+str(e)[:350]}));return 5
if __name__=='__main__':sys.exit(main())
