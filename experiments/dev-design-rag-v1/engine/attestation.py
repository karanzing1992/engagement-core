"""Independent reviewer verification. Signing is external to the code-writing principal.

Production trust roots must be provisioned by the owner as root-owned files.
This module has no signing operation or reviewer private key access.
"""
import base64
import hashlib
import json
import os
import stat
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

TRUST_FILE = Path('/etc/moksha-uiux-v2/trusted-reviewers.json')

def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()

def must(condition, code):
    if not condition:
        raise ValueError(code)

def _trust():
    p = TRUST_FILE
    for node in (p.parent, p):
        must(node.exists() and not node.is_symlink(), 'REVIEW_TRUST_ROOT_MISSING_OR_SYMLINK')
        s = node.stat()
        must(s.st_uid == 0 and not (s.st_mode & 0o022), 'REVIEW_TRUST_ROOT_NOT_OWNER_PROTECTED')
    must(p.is_file() and p.stat().st_size < 65536, 'REVIEW_TRUST_ROOT_INVALID')
    policy = json.loads(p.read_text())
    must(policy.get('version') == 1 and isinstance(policy.get('keys'), dict), 'REVIEW_TRUST_POLICY_INVALID')
    return policy['keys']

def validate(w, receipt, state, sha, treehash):
    must(state['site_sha256'] == treehash(w/'site'), 'SOURCE_CHANGED')
    r = json.loads(receipt.read_text())
    must(isinstance(r, dict), 'REVIEW_INVALID')
    keys = _trust()
    identity = r.get('reviewer_id')
    key_id = r.get('key_id')
    key = keys.get(key_id)
    must(isinstance(key, dict) and key.get('reviewer_id') == identity and key.get('enabled') is True,
         'UNTRUSTED_REVIEWER_IDENTITY')
    must(r.get('reviewer_kind') == 'independent_service' and r.get('model') in key.get('models', []),
         'REVIEWER_NOT_INDEPENDENT_OR_MODEL_NOT_ALLOWED')
    must(r.get('signature_scheme') == 'Ed25519', 'REVIEW_SIGNATURE_SCHEME_INVALID')
    signed = {k:v for k,v in r.items() if k != 'signature'}
    try:
        pub = Ed25519PublicKey.from_public_bytes(base64.b64decode(key['public_key'],validate=True))
        sig = base64.b64decode(r['signature'], validate=True)
        pub.verify(sig, canonical(signed))
    except Exception as e:
        raise ValueError('REVIEW_SIGNATURE_INVALID') from e
    must(r.get('job_id') and r['job_id'] == state.get('job_id'), 'REVIEW_JOB_BINDING_MISMATCH')
    must(r.get('project_id') and r['project_id'] == state.get('project'), 'REVIEW_PROJECT_BINDING_MISMATCH')
    must(r.get('site_sha256') == state['site_sha256'], 'REVIEW_BUILD_MISMATCH')
    must(r.get('qa_receipt_sha256') == state.get('qa_receipt_sha256'), 'REVIEW_QA_BINDING_MISMATCH')
    must(r.get('assessment_method') == 'actual_screenshots' and r.get('evidence_source') == 'independent_visual_model',
         'REVIEW_PROVENANCE_MISSING')
    qa = json.loads((w/'reports/browser-qa.json').read_text())
    must(qa.get('pass') is True and sha(w/'reports/browser-qa.json') == state.get('qa_receipt_sha256'),
         'REVIEW_QA_RECEIPT_DRIFT')
    expected = {(x['page'], x['width']):x for x in qa['screenshots']}
    must(len(expected) == len(qa['screenshots']) and len(expected) > 0, 'REVIEW_QA_DUPLICATE_OR_EMPTY')
    recorded = r.get('screenshots')
    must(isinstance(recorded,list) and len(recorded)==len(expected),'REVIEW_SCREENSHOT_SET_MISMATCH')
    found = {}
    for x in recorded:
        must(isinstance(x,dict),'REVIEW_SCREENSHOT_FORMAT_INVALID')
        key_pair = (x.get('page'),x.get('width'))
        must(key_pair in expected and key_pair not in found,'REVIEW_SCREENSHOT_SET_MISMATCH')
        original=expected[key_pair]
        must(x == original,'REVIEW_SCREENSHOT_RECEIPT_MISMATCH')
        name=x['name']
        must(Path(name).name == name and name not in ('','.','..'),'UNSAFE_SCREENSHOT_NAME')
        path=w/'evidence/screenshots'/name
        must(path.is_file() and not path.is_symlink() and sha(path)==x['sha256'],
             'REVIEW_SCREENSHOT_HASH_MISMATCH')
        found[key_pair]=x['sha256']
    must(set(found)==set(expected),'REVIEW_SCREENSHOT_SET_MISMATCH')
    pages={x['page'] for x in qa['screenshots']}
    required={(page,width) for page in pages for width in (390,1440)}
    must(required.issubset(expected),'REVIEW_REQUIRED_CAPTURE_MISSING')
    reviewed=r.get('reviewed_screenshots')
    must(isinstance(reviewed,list) and
         {(x.get('page'),x.get('width')) for x in reviewed}==required and len(reviewed)==len(required),
         'REVIEW_FULL_SCREEN_COVERAGE_MISSING')
    for x in reviewed:
        k=(x['page'],x['width'])
        must(x.get('name')==expected[k]['name'] and x.get('sha256')==expected[k]['sha256'],
             'REVIEW_REVIEWED_SHOT_MISMATCH')
    raw=r.get('raw_model_outputs')
    must(isinstance(raw,list) and len(raw)==len(pages),'REVIEW_RAW_MODEL_OUTPUT_MISSING')
    must(hashlib.sha256('\n'.join(x.get('raw','') for x in raw).encode()).hexdigest()==r.get('model_response_sha256'),
         'REVIEW_RAW_RESPONSE_HASH_MISMATCH')
    observed=[]; seen=set()
    for x in raw:
        page=x.get('page')
        must(page in pages and page not in seen,'REVIEW_PAGE_DUPLICATED_OR_MISSING')
        seen.add(page)
        try:parsed=json.loads(x['raw'])
        except (ValueError,TypeError):raise ValueError('REVIEW_RAW_RESPONSE_UNPARSEABLE')
        score=parsed.get('score')
        must(type(score) in (int,float) and 0<=score<=100, 'REVIEW_RAW_SCORE_INVALID')
        must(isinstance(parsed.get('issues'),list) and all(isinstance(v,str) for v in parsed['issues']),
             'REVIEW_RAW_FINDINGS_MISSING')
        must(len(str(parsed.get('visual_evidence','')).strip())>=12,'REVIEW_VISIBLE_EVIDENCE_MISSING')
        observed.append(score)
    must(seen==pages,'REVIEW_PAGE_COVERAGE_MISSING')
    score=r.get('score')
    must(type(score) in (int,float) and score==min(observed),'REVIEW_SCORE_NOT_RAW_DERIVED')
    must(r.get('verdict')==('APPROVE' if score>=95 else 'REVISE'),'REVIEW_VERDICT_INCONSISTENT')
    must(r.get('scope_complete') is True,'REVIEW_PARTIAL_SCOPE')
    must(r.get('signed_or_verifiable_receipt') is True,'REVIEW_ATTESTATION_REQUIRED')
    must(r.get('issues') is not None,'REVIEW_ISSUES_REQUIRED')
    must(score>=95 and r['verdict']=='APPROVE','REVIEW_BELOW_THRESHOLD')
    return r
