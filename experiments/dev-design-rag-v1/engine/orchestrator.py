#!/usr/bin/env python3
"""Bounded, resumable, single-job UI/UX V2 orchestration. Never approves production."""
import argparse,fcntl,hashlib,json,subprocess,sys,time
from pathlib import Path
from core import create,gate,sha,state,workspace,verify_review,write,require,treehash
from cli import concept,qa,performance,ingest_agent
from reviewer import review as visual_review

TRANSIENT=('429','503','RATE_LIMIT','THROTTLE','TIMEOUT','MODEL_UNAVAILABLE')
class Blocked(Exception):pass

def runner(args):
    w=args.workspace.expanduser().resolve()
    if not (w/'engine-state.json').is_file():
        require(args.baseline and args.project and args.prompt,'NEW_JOB_REQUIRES_BASELINE_PROJECT_PROMPT')
        create(w,args.baseline,args.project,args.prompt)
    w=workspace(w)
    lockfile=w/'.orchestrator.lock'
    with lockfile.open('a+') as lock:
        try:fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise Blocked('JOB_ALREADY_RUNNING')
        ledger=w/'reports/orchestration.json'
        old=json.loads(ledger.read_text()) if ledger.is_file() else {}
        s=state(w)
        if old.get('job_id') not in (None,s.get('job_id')):raise Blocked('JOB_ID_COLLISION')
        events=old.get('events',[])
        def checkpoint(stage,status,detail):
            entry={'stage':stage,'status':status,'at':int(time.time()),'detail':str(detail)[:250]}
            events.append(entry)
            write(ledger,{'job_id':s.get('job_id'),'state':status,'last_stage':stage,
                'site_sha256':state(w)['site_sha256'],'events':events[-100:]})
        def execute(stage,action,done):
            if done():
                checkpoint(stage,'REUSED','same persisted stage receipt')
                return
            for attempt in range(1,3):
                checkpoint(stage,'RUNNING','attempt='+str(attempt))
                try:
                    result=action()
                    checkpoint(stage,'PASS',result)
                    return
                except Exception as e:
                    message=type(e).__name__+':'+str(e)
                    if attempt==2 or not any(code in message.upper() for code in TRANSIENT):
                        checkpoint(stage,'BLOCKED',message)
                        raise Blocked(stage+':'+message) from e
                    checkpoint(stage,'RETRY',message)
                    time.sleep(attempt*2)
        execute('concept',lambda:concept(w),lambda:state(w)['stage_status']['autonomous_concept_and_design']=='PASS')
        task_seed='uiuxv2-'+hashlib.sha256((state(w)['baseline_sha256']+args.target+args.task).encode()).hexdigest()[:15]
        def agent_step():
            for attempt in (1,2):
                taskid=task_seed+'-a'+str(attempt)
                task=w/'tasks'/taskid
                receipt=task/'receipt.json'
                if receipt.is_file():
                    r=json.loads(receipt.read_text())
                    if r.get('status')!='PASS':
                        continue
                    require(r.get('output_site_sha256')==treehash(w/'site'),
                            'AGENT_RECEIPT_SITE_HASH_MISMATCH')
                    return ingest_agent(w,receipt)
                if task.exists():
                    # Preserve crashed attempt evidence; never overwrite or erase it.
                    continue
                cmd=['python3',str(Path(__file__).with_name('agent.py')),'--workspace',str(w),
                     '--target',args.target,'--task',args.task,'--task-id',taskid]
                result=subprocess.run(cmd,text=True,capture_output=True,timeout=170)
                if result.returncode!=0:
                    raise ValueError('AUTONOMOUS_AGENT_FAILED:'+result.stdout[-180:]+result.stderr[-100:])
                require(receipt.is_file(),'AGENT_RECEIPT_MISSING')
                return ingest_agent(w,receipt)
            raise ValueError('BOUNDED_AGENT_ATTEMPTS_EXHAUSTED')
        execute('implementation',agent_step,lambda:state(w)['stage_status']['autonomous_implementation']=='PASS')
        pages=args.pages.split(',') if args.pages else [p.name for p in sorted((w/'site').glob('*.html'))]
        pages=[p.strip() for p in pages if p.strip()]
        require(pages and all(Path(p).name==p and p.endswith('.html') for p in pages),
                'ROUTE_LIST_INVALID')
        execute('browser_qa',lambda:qa(w,','.join(pages)),lambda:state(w)['stage_status']['actual_render_and_screenshot']=='PASS')
        summary=w/'reports/lighthouse-summary.json'
        for page in pages:
            def done_page():
                if not summary.is_file():return False
                old=json.loads(summary.read_text())
                return (old.get('source_sha256')==state(w)['site_sha256'] and
                        old.get('browser_receipt_sha256')==state(w).get('qa_receipt_sha256') and
                        page in old.get('pages',{}))
            execute('lighthouse:'+page,lambda page=page:performance(w,page),done_page)
        # V2.1: optional one-image-at-a-time Gemini advisory intake.
        # Its source and screenshot hashes are verified, but it is NEVER a signature,
        # a quality score, or an authorization to bypass the independent reviewer.
        advisory=getattr(args,'vision_feedback_file',None)
        if advisory:
            from vision_feedback_v21 import intake
            try:
                staged=intake(w,Path(advisory))
                checkpoint('vision_advisory','ADVISORY_ONLY_NOT_CERTIFIED',staged)
            except Exception as e:
                checkpoint('vision_advisory','BLOCKED',str(e))
                raise Blocked('VISION_ADVISORY_REJECTED:'+str(e)) from e
        # Reviewer cannot attest itself; a separate owner-provisioned service signs the receipt.
        if state(w)['stage_status']['independent_artistic_review']!='PASS':
            if not advisory:
                try:
                    result=visual_review(w,0,args.vision_model,args.vision_timeout)
                    checkpoint('vision_evidence','EVIDENCE_ONLY',result)
                except Exception as e:
                    checkpoint('vision_evidence','BLOCKED',str(e))
                    raise Blocked('VISION_REVIEW_UNAVAILABLE:'+str(e)) from e
            else:
                checkpoint('vision_evidence','ADVISORY_ONLY','12 real screenshot reviews; independent signature still required')
            external=w/'reports/independent-signed-review.json'
            if external.is_file():
                execute('independent_artistic_attestation',
                        lambda:verify_review(w,external),
                        lambda:state(w)['stage_status']['independent_artistic_review']=='PASS')
            else:raise Blocked('INDEPENDENT_SIGNED_REVIEW_REQUIRED')
        result=gate(w,'preview')
        if result['status']!='PASS':
            checkpoint('preview_gate','BLOCKED',result['missing'])
            raise Blocked('PREVIEW_GATE_NOT_PASSED')
        checkpoint('preview_gate','PASS','all receipts checked; preview deployment separate')
        return {'status':'PREFLIGHT_PASS','job_id':s.get('job_id'),
                'preview_deployed':False,'production_release_allowed':False}
if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--workspace',required=True,type=Path)
    p.add_argument('--baseline',type=Path)
    p.add_argument('--project')
    p.add_argument('--prompt')
    p.add_argument('--target',default='engine-smoke.html')
    p.add_argument('--task',default='Create a responsive visual design QA smoke screen consistent with approved RAG.')
    p.add_argument('--pages',default='')
    p.add_argument('--vision-model',default='qwen3-vl:2b-instruct')
    p.add_argument('--vision-timeout',type=int,default=110)
    p.add_argument('--vision-feedback-file',type=Path,default=None)
    p.add_argument('--status',action='store_true')
    a=p.parse_args()
    try:
        if a.status:
            w=workspace(a.workspace)
            ledger=w/'reports/orchestration.json'
            data={'status':'READ_ONLY','state':state(w),
                  'orchestration':json.loads(ledger.read_text()) if ledger.is_file() else None,
                  'preview_gate':gate(w,'preview')}
        else:data=runner(a)
        print(json.dumps(data,indent=2))
    except Exception as e:
        print(json.dumps({'status':'BLOCKED','reason':type(e).__name__+':'+str(e)[:300]}))
        sys.exit(4)
