#!/usr/bin/env python3
"""Bounded autonomous OpenCode output-only agent. Protected Dell free-plan route."""
import argparse,hashlib,json,os,re,shutil,signal,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from core import workspace,state,treehash,write,require,RUNTIME
from design_contract import writer_context,validate_html,policy_for
from editorial_contract import check_editorial
def normalize_trusted_script_defer(text):
 """Narrow deterministic repair, never permits a different JS asset or inline JS."""
 if len(re.findall(r'<script\b',text,re.I)) != 1:
  return text,False
 pattern=r'<script\s+src=(["\'])assets/site\.js\1\s*></script\s*>'
 revised,count=re.subn(pattern,'<script src="assets/site.js" defer></script>',text,count=1,flags=re.I)
 return revised,bool(count)

def run():
 p=argparse.ArgumentParser()
 for name in ('workspace','target','task','task-id'):p.add_argument('--'+name,required=True)
 p.add_argument('--reference-page',default=None)
 p.add_argument('--site-brief',action='store_true')
 p.add_argument('--style-reference',action='store_true')
 p.add_argument('--style-path',default='assets/v9-main.css')
 a=p.parse_args();w=workspace(Path(a.workspace));s=state(w)
 require(s['stage_status']['autonomous_concept_and_design']=='PASS','DESIGN_NOT_APPROVED_FOR_CODING')
 require(s['site_sha256']==treehash(w/'site'),'SOURCE_HASH_DRIFT')
 require(re.fullmatch(r'[a-z0-9_-]{3,45}',a.task_id),'BAD_TASK_ID')
 require(re.fullmatch(r'(assets/)?[a-z0-9][a-z0-9_.-]{2,95}\.(css|js|html)',a.target),'UNSAFE_OUTPUT_FILE')
 require(not (w/'site'/a.target).exists(),'EXISTING_OUTPUT_PROTECTED')
 require(len(a.task)<=650,'TASK_BUDGET_TOO_LARGE')
 t=w/'tasks'/a.task_id;require(not t.exists(),'TASK_ALREADY_EXECUTED');t.mkdir(parents=True)
 ctx=(w/'evidence/rag-packet.txt').read_text()
 require(hashlib.sha256(ctx.encode()).hexdigest()==s['rag_sha256'],'RAG_CONTEXT_DRIFT')
 facts=writer_context(ctx,s['project'])
 # Keep owner's verified project facts before secondary general knowledge.
 # Free Groq 120b TPM=8000; bound each model input without diluting policy checks.
 (t/'knowledge.txt').write_text(facts[:1050])
 if a.target=='contact.html' and s['project']=='andaz-vibe-stay':
  # Historical V6 RAG snippets previously contaminated Contact output with unrelated countries.
  # RAG integrity verified above; page-scoped context contains only approved owner facts.
  (t/'knowledge.txt').write_text(
   'OWNER-VERIFIED ANDAZ VIBE STAY ARAMBOL CONTACT FACTS ONLY.\n'
   'Address: Temple Road, Arambol, Goa 403524, India. Phone: +91 89995 41081. '
   'WhatsApp: https://wa.me/918999541081. Map: https://maps.app.goo.gl/CrzfATU3QnmNoMZcA. '
   'Check-in 1 PM; checkout 11 AM. Genuine logo assets/andaz-official-cropped.webp. '
   'Shared stylesheet assets/v9-fresh.css. Only JS assets/site.js with defer. '
   'Pages index.html rooms.html experiences.html food.html explore.html contact.html. '
   'Contact form exact IDs: booking-form,guest-name,room-type,guests,checkin,checkout,form-error; '
   'select options: Non-AC six-bed dorm, AC six-bed dorm, Two-bed non-AC dorm, Private AC room. '
   'Consent checkbox required. WhatsApp redirect done by trusted JS. '
   'Never invent other locations, phone numbers, room names, prices, photos or domains.\n')
 if s['project']=='andaz-vibe-stay':
  verified=('\nOWNER-VERIFIED FACTS ONLY: Andaz Vibe Stay in Arambol, Goa. '
   'Rooms are six-bed non-AC dorm, six-bed AC dorm, two-bed NON-AC SHARED DORM (not private), and private AC rooms; '
   'do not guess private room bed layouts. Only one verified bedroom photo, for room or stay contexts. '
   'The Andaz Table serves fresh Indian HOMESTYLE meals: Rs 180 dine-in, Rs 220 delivered inside Arambol with no delivery charge; '
   'outside Arambol minimal additional delivery fee by enquiry. Moksha Wellness is an optional independent partner. '
   'Official WhatsApp https://wa.me/918999541081 and official map https://maps.app.goo.gl/CrzfATU3QnmNoMZcA. '
   'NOT VERIFIED: Wi-Fi, TV, workstation, shared kitchens, common lounges, balconies, pool, breakfast, '
   'chefs, locally sourced ingredients, sustainability credentials, organized tours, special staff services. '
   'NEVER claim unverified facts or use the bedroom photo as a food, pool or destination image.\n')
  (t/'knowledge.txt').write_text((t/'knowledge.txt').read_text()+verified)
 extra=''
 if a.site_brief:
  src=w/'evidence/full-site-brief.txt'
  require(src.is_file() and not src.is_symlink() and 100<=src.stat().st_size<=12000,'SITE_BRIEF_MISSING_OR_UNSAFE')
  full=src.read_text()
  intro=full[:650]
  if a.target=='contact.html':
   intro='Andaz Vibe Stay Arambol, Goa; official WhatsApp https://wa.me/918999541081; six-page responsive editorial hostel. Only original logo, verified contact facts and approved shared CSS. No other property/brand.'
  anchor='Explore requires' if a.target.startswith('explore') else (
         'Contact form must' if a.target.startswith('contact') else (
         'Rooms:' if a.target.startswith('rooms') else (
         'Experiences:' if a.target.startswith('experiences') else '')))
  additional=''
  if anchor and anchor in full:
   offset=full.index(anchor)
   additional=full[offset:offset+(360 if a.target=='contact.html' else 550)]
  (t/'site-brief.txt').write_text((intro+'\n'+additional)[:1250])
  earlier=(t/'knowledge.txt').read_text()
  (t/'knowledge.txt').write_text(earlier+'\nAPPROVED SITE BRIEF: '+intro+'\nPAGE FACTS: '+additional)
  extra+=' Verified page facts are included in knowledge.txt.'
 if a.style_reference:
  require(bool(re.fullmatch(r'assets/[a-z][a-z0-9-]{2,60}\.css',a.style_path)),'UNSAFE_STYLE_PATH')
  src=w/'site'/a.style_path
  require(src.is_file() and not src.is_symlink() and src.stat().st_size<=30000,'STYLE_REFERENCE_MISSING')
  (t/'design.css').write_text(src.read_text()[:650])
  css_classes=list(dict.fromkeys(re.findall(r'\.([a-zA-Z][a-zA-Z0-9_-]+)',src.read_text())))
  earlier=(t/'knowledge.txt').read_text()
  (t/'knowledge.txt').write_text(earlier+'\nSHARED CSS CLASS HINTS: '+', '.join(css_classes[:30])+'; link '+a.style_path+' and preserve the shared design.')
  extra+=' CSS and style hints are in knowledge.txt; link '+a.style_path+'.'

 if a.reference_page:
  require(Path(a.reference_page).name==a.reference_page and a.reference_page.endswith('.html'),'INVALID_REPAIR_REFERENCE')
  old=w/'site'/a.reference_page
  require(old.is_file() and not old.is_symlink(),'REPAIR_REFERENCE_MISSING')
  qpath=w/'reports/browser-qa.json'
  require(qpath.is_file() and not qpath.is_symlink(),'FAILED_QA_REQUIRED')
  qa=json.loads(qpath.read_text())
  rows=[row for row in qa.get('rows',[]) if row.get('page')==a.reference_page]
  require(qa.get('pass') is False and len(rows)==4 and
    {row['width'] for row in rows}=={320,390,768,1440} and
    qa.get('source_hash')==s['site_sha256'] and
    all(row.get('pass') is False for row in rows),'BOUND_FAILURE_QA_REQUIRED')
  (t/'reference.html').write_bytes(old.read_bytes())
  (t/'qa-feedback.txt').write_text('WCAG defects from real browser: '+
    '; '.join(str(row['width'])+'px='+','.join(item.get('id','?') for item in row.get('axe',[]))+
     ' targets='+','.join(z.get('selector','')+':'+z.get('failure_summary','')[:110] for item in row.get('axe',[]) for z in item.get('targets',[])[:2])+
     ' '+','.join(str(err)[:80] for err in row.get('errors',[])) for row in rows))

 name=Path(a.target).name
 policy=policy_for(s['project'])
 must=(' REQUIRED HTML: include EXACT visible link <a href=\"'+policy['official_whatsapp']+'\">WhatsApp enquiry</a> before main content; official logo; required navigation; viewport meta; approved trusted <script src="assets/site.js" defer></script>; one main and h1. Grounded facts ONLY: NO suites, balconies, luxury, guided walks, sunrise yoga, pool, sea views or global fusion. Room photo alt EXACT Andaz room interior; bedroom imagery ONLY Home/Rooms. ' if a.target.endswith('.html') and policy else '')
 if a.target in ('experiences.html','food.html','explore.html','contact.html') and policy:
  must+=' Use ONLY official logo img; NO other images, URLs or external assets. Design with CSS typography and genuine words. '
 prompt=('Read '+str(t/'knowledge.txt')+' briefly. WRITE exactly one file to ABSOLUTE PATH '+str(t/name)+
 ' using your actual WRITE tool. Read knowledge.txt ONCE for all owner facts. Do not open other references. '+
 ('Repair from reference.html and qa-feedback.txt; keep approved brand, eliminate ALL axe issues. ' if a.reference_page else '')+
 extra+must+' Task: '+a.task+
 '. Shared editorial components must have CSS selectors. Hero images need bounded aspect ratio, object-fit cover and responsive height. Do not write other files or publish.')
 require(len(prompt)<(2100 if a.reference_page else 1900),'PROMPT_BUDGET')
 R=Path.home()/'.local/share/matrix-dev-router';policy=json.loads((R/'policy.json').read_text())
 require(policy.get('paid_inference_allowed') is False and policy.get('groq_free_plan_owner_confirmed'),'FREE_ROUTE_REQUIRED')
 route=os.environ.get('UIUX_GROQ_FREE_ROUTE','groq-oss120')
 require(route in ('groq-oss120','groq-oss20'),'UNAPPROVED_FREE_MODEL_ROUTE')
 slot=next((x for x in policy['connections'] if x['id']==route and x['enabled'] and x.get('provider')=='groq'),None)
 require(slot is not None,'FREE_MODEL_UNAVAILABLE')
 key=R/'secrets'/(slot['credential_ref']+'.key')
 require(key.is_file() and key.stat().st_mode&0o077==0,'SECRET_PERMISSIONS')
 H=Path(os.environ.get('UIUX_OPENCODE_HOME',str(RUNTIME/'opencode-home')))
 config=H/'.config/opencode/opencode.json';require(config.is_file(),'MODEL_CONFIG_MISSING')
 taskconfig=t/'opencode-config.json'
 config_data=json.loads(config.read_text())
 # External directory tools may access only sandbox-bound taskdir at filesystem layer.
 config_data.setdefault('permission',{})['external_directory']='allow'
 taskconfig.write_text(json.dumps(config_data))
 taskconfig.chmod(0o600)
 env={'PATH':'/usr/local/bin:/usr/bin:/bin','LANG':'C.UTF-8','HOME':str(H),
 'XDG_CONFIG_HOME':str(H/'.config'),'XDG_DATA_HOME':str(H/'.local/share'),
 'XDG_STATE_HOME':str(H/'.local/state'),'XDG_CACHE_HOME':str(H/'.cache'),
 'OPENCODE_CONFIG':str(taskconfig),'OPENCODE_CONFIG_DIR':str(config.parent),
 'OPENCODE_DISABLE_AUTOUPDATE':'1','GROQ_API_KEY':key.read_text().strip()}
 cmd=['bwrap','--die-with-parent','--new-session']
 for root in ('/usr','/bin','/lib','/lib64','/etc','/usr/local','/run/systemd/resolve'):
  cmd+=['--ro-bind',root,root]
 cmd+=['--ro-bind','/opt/business-house-matrix/toolchain/node_modules/opencode-ai/bin/opencode.exe','/opencode',
 '--bind',str(H),str(H),'--bind',str(t),str(t),'--proc','/proc','--dev-bind','/dev','/dev',
 '--tmpfs','/tmp','--chdir',str(t),'/opencode','run','--pure','--auto','--format','json',
 '--model','groq/'+slot['model'],prompt]
 started=time.monotonic();settled=None
 with (t/'events.ndjson').open('w') as out,(t/'stderr.log').open('w') as err:
  proc=subprocess.Popen(cmd,env=env,stdout=out,stderr=err,start_new_session=True)
  while proc.poll() is None:
   f=t/name
   if f.is_file() and f.stat().st_size>=200:
    if settled is None:settled=time.monotonic()
    elif time.monotonic()-settled>=3:os.killpg(proc.pid,signal.SIGTERM);break
   if time.monotonic()-started>140:os.killpg(proc.pid,signal.SIGTERM);break
   time.sleep(1)
  try:exitcode=proc.wait(timeout=5)
  except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);exitcode=proc.wait()
 f=t/name;tools=[]
 for line in (t/'events.ndjson').read_text(errors='replace').splitlines():
  try:
   x=json.loads(line)
   if x.get('type')=='tool_use':tools.append((x.get('part') or {}).get('tool'))
  except Exception:pass
 success=f.is_file() and 200<=f.stat().st_size<=30000 and any(x in ('write','edit','apply_patch') for x in tools)
 deterministic_repairs=[]
 if success:
  data=f.read_text(errors='replace')
  if a.target.endswith('.html'):
   fixed,changed=normalize_trusted_script_defer(data)
   if changed:
    (t/'model-original.html').write_text(data)
    f.write_text(fixed)
    deterministic_repairs.append({'kind':'TRUSTED_SCRIPT_DEFER_INSERTED',
      'original_sha256':hashlib.sha256(data.encode()).hexdigest(),
      'normalized_sha256':hashlib.sha256(fixed.encode()).hexdigest()})
  if a.target.endswith('.css') and data.count('{')!=data.count('}'):success=False
 validation=None;invalid_reason=None
 if success and a.target.endswith('.html'):
  try:
   validation=validate_html(f.read_text(encoding='utf-8'),s['project'],w/'site',page=a.target)
   editorial=check_editorial(f.read_text(encoding='utf-8'),a.target,s['project'])
   if editorial['status']!='PASS':raise ValueError('EDITORIAL_GATE:'+','.join(editorial['issues']))
  except Exception as e:
   invalid_reason=type(e).__name__+':'+str(e)[:140]
   success=False
 if success:
  target=w/'site'/a.target;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,target)
 receipt={'status':'PASS' if success else 'BLOCKED','agent':'opencode','task_id':a.task_id,
 'target':a.target,'tool_file_write_verified':bool(success),'tool_types':tools[-8:],
 'baseline_sha256':s['baseline_sha256'],'output_site_sha256':treehash(w/'site'),
 'task_source':'bounded_v2_rag','prompt_token_budget':1700,'code_files_written':1 if success else 0,
 'semantic_validation':validation,'validation_failure':invalid_reason,
 'deterministic_repairs':deterministic_repairs,
 'exit_code':exitcode,'elapsed_sec':round(time.monotonic()-started,2),'production_writes':False}
 write(t/'receipt.json',receipt);return receipt
if __name__=='__main__':
 try:
  r=run();print(json.dumps(r,indent=2));sys.exit(0 if r['status']=='PASS' else 4)
 except Exception as e:
  print(json.dumps({'status':'BLOCKED','reason':type(e).__name__+':'+str(e)[:220]}));sys.exit(5)
