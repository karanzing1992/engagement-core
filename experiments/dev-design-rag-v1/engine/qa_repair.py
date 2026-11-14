"""Bounded, receipt-preserving V2.1.1 QA repairs. Never overwrites a rejected page.

Only one route per job is repaired; multi-page failures remain fail closed.
No new concept call or SOP replay; revisions derive from real same-build QA.
"""
import hashlib,json,re,shutil,subprocess
from pathlib import Path
from core import sha,state,treehash,require,write
from cli import qa,ingest_agent
from design_contract import policy_for

def validated_failure(w,page):
    path=w/'reports/browser-qa.json'
    require(path.is_file() and not path.is_symlink(),'QA_FAILURE_REPORT_REQUIRED')
    data=json.loads(path.read_text())
    s=state(w)
    require(data.get('pass') is False and data.get('source_hash')==s['site_sha256']==
            treehash(w/'site'),'QA_FAILURE_BUILD_MISMATCH')
    rows=data.get('rows',[])
    require(len(rows)==4 and {(x.get('page'),x.get('width')) for x in rows}==
            {(page,width) for width in (320,390,768,1440)},'QA_FAILURE_COVERAGE_MISSING')
    require(any(not x.get('pass') for x in rows),'QA_NO_FAILURE_TO_REPAIR')
    images=[x for x in data.get('screenshots',[]) if x.get('page')==page]
    require(len(images)==4,'QA_SCREENSHOT_COVERAGE_MISSING')
    for item in images:
        name=item['name'];f=w/'evidence/screenshots'/name
        require(Path(name).name==name and f.is_file() and not f.is_symlink() and
                sha(f)==item['sha256'],'QA_IMAGE_PROVENANCE_MISMATCH')
    return data

def revision_task(w,original_task):
    p=policy_for(state(w)['project'])
    facts=('Use only '+p['brand']+' and '+p['official_whatsapp']+
           ', actual logo/photo, no unsupported room claims. ') if p else ''
    start='Fix real axe/QA failures using reference.html and qa-feedback.txt; legible contrast and responsive mobile navigation. '
    task=(start+facts+'Preserve original intent: '+original_task[:220])
    require(len(task)<=650,'REPAIR_TASK_BUDGET')
    return task

def run(w,page,original_task,rounds,checkpoint):
    require(type(rounds) is int and 1<=rounds<=2,'REPAIR_BUDGET_LIMIT')
    require(Path(page).name==page and page.endswith('.html') and (w/'site'/page).is_file(),
            'REPAIR_PAGE_NOT_FOUND')
    history=w/'reports/qa-attempts'
    history.mkdir(exist_ok=True)
    ledger={'schema':'bounded-qa-repair-v1','site_baseline_sha256':state(w)['baseline_sha256'],
            'repair_max':rounds,'attempts':[],'artistic_score':None,'release_authorized':False}
    current=page
    for revision in range(1,rounds+1):
        previous=validated_failure(w,current)
        qa_path=w/'reports/browser-qa.json'
        prior_qa=history/('qa-r'+str(revision-1)+'.json')
        if prior_qa.exists():
            require(sha(prior_qa)==sha(qa_path),'REPAIR_HISTORY_COLLISION')
        else:shutil.copy2(qa_path,prior_qa)
        oldagent=w/'reports/accepted-agent.json'
        if oldagent.is_file():
            agent_snapshot=history/('agent-r'+str(revision-1)+'.json')
            if agent_snapshot.exists():
                require(sha(agent_snapshot)==sha(oldagent),'AGENT_HISTORY_COLLISION')
            else:shutil.copy2(oldagent,agent_snapshot)
        destination=Path(page).stem+'-r'+str(revision)+'.html'
        require(not (w/'site'/destination).exists(),'REPAIR_DESTINATION_COLLISION')
        receipt_hash=sha(prior_qa)
        seed=hashlib.sha256((state(w)['job_id']+receipt_hash+destination+'guarded-repair-v2').encode()).hexdigest()[:17]
        task_id='qar-'+seed+'-r'+str(revision)
        notes=revision_task(w,original_task)
        checkpoint('qa_repair:'+str(revision),'RUNNING','bound QA='+receipt_hash[:16]+' target='+destination)
        cmd=['python3',str(Path(__file__).with_name('agent.py')),'--workspace',str(w),
             '--target',destination,'--task',notes,'--task-id',task_id,
             '--reference-page',current]
        out=subprocess.run(cmd,text=True,capture_output=True,timeout=170)
        agent_receipt=w/'tasks'/task_id/'receipt.json'
        if out.returncode!=0 or not agent_receipt.is_file():
            reason='AGENT_REPAIR_FAILED:'+out.stdout[-140:]+out.stderr[-90:]
            checkpoint('qa_repair:'+str(revision),'BLOCKED',reason)
            raise ValueError(reason)
        ingested=ingest_agent(w,agent_receipt)
        entry={'revision':revision,'previous_page':current,'output_page':destination,
               'qa_failure_sha256':receipt_hash,'agent_receipt_sha256':sha(agent_receipt),
               'site_sha256':ingested['site_sha256'],'qa_pass':False}
        ledger['attempts'].append(entry)
        write(w/'reports/qa-repair-evidence.json',ledger)
        try:
            result=qa(w,destination)
        except Exception as e:
            if 'BROWSER_QA_BLOCKED:' not in str(e):
                checkpoint('qa_repair:'+str(revision),'BLOCKED','QA_RUNTIME_FAILURE:'+str(e)[:140])
                raise
            checkpoint('qa_repair:'+str(revision),'FAILED_QA','new page still fails browser check')
            current=destination
            continue
        entry['qa_pass']=True
        entry['new_qa_receipt_sha256']=state(w).get('qa_receipt_sha256')
        ledger['status']='QA_REPAIR_PASS'
        write(w/'reports/qa-repair-evidence.json',ledger)
        checkpoint('qa_repair:'+str(revision),'PASS',result)
        return destination
    ledger['status']='QA_REPAIR_EXHAUSTED'
    write(w/'reports/qa-repair-evidence.json',ledger)
    raise ValueError('QA_REPAIR_EXHAUSTED_AT_'+str(rounds))
