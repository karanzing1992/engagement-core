#!/usr/bin/env python3
"""GitHub Actions -> Cloudflare D1 authenticated synthetic V5 job runner. No guest files."""
from __future__ import annotations
import argparse,json,os,re,sys,urllib.parse,urllib.request
from pathlib import Path

AUDIENCE="mad-v5-cloudflare-bridge/v1"
ENDPOINT="https://mad-reel-v5-oidc-bridge.karanbizweb360.workers.dev"
REPO="karanzing1992/engagement-core"

def token():
    uri=os.environ.get("ACTIONS_ID_TOKEN_REQUEST_URL","")
    bearer=os.environ.get("ACTIONS_ID_TOKEN_REQUEST_TOKEN","")
    if not uri.startswith("https://") or not bearer:raise RuntimeError("OIDC identity missing")
    sep="&" if "?" in uri else "?"
    url=uri+sep+"audience="+urllib.parse.quote(AUDIENCE,safe="")
    req=urllib.request.Request(url,headers={"Authorization":"Bearer "+bearer,"Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=12) as res:data=json.loads(res.read(16384))
    value=data.get("value","")
    if not isinstance(value,str) or len(value.split("."))!=3:raise RuntimeError("Invalid GitHub ID token")
    return value

def call(action,data):
    if action not in ("enqueue","claim","complete","status"):raise ValueError("Unknown operation")
    base=os.environ.get("MAD_V5_CF_BRIDGE_URL",ENDPOINT)
    p=urllib.parse.urlsplit(base)
    if p.scheme!="https" or p.netloc!=urllib.parse.urlsplit(ENDPOINT).netloc or p.path not in ("","/") or p.query or p.fragment:
        raise RuntimeError("Cloudflare bridge URL must match owner-pinned host")
    req=urllib.request.Request(base.rstrip("/")+"/bridge/v1/"+action,method="POST",
        data=json.dumps(data,separators=(",",":")).encode(),headers={
        "Authorization":"Bearer "+token(),"Content-Type":"application/json","Accept":"application/json",
        "User-Agent":"MAD-V5-GitHub-OIDC-Bridge/1"})
    try:
        with urllib.request.urlopen(req,timeout=35) as res:return json.loads(res.read(8192))
    except urllib.error.HTTPError as exc:
        if exc.code==401:
            import base64,sys
            stage=exc.headers.get('x-mad-oidc-stage','unknown')
            if re.fullmatch(r'[a-z0-9_]{1,64}',stage):print('CLOUDFLARE_OIDC_VERIFY_STAGE '+stage,file=sys.stderr)
            claims={}
            try:
                signed=token()
                parts=signed.split(".")
                t=parts[1]
                claims=json.loads(base64.urlsafe_b64decode(t+"==="))
                header=json.loads(base64.urlsafe_b64decode(parts[0]+"==="))
            except (ValueError,KeyError,IndexError):pass
            expected="karanzing1992/engagement-core/.github/workflows/mad-v5-cloudflare-bridge.yml@refs/heads/main"
            checks={
              "issuer":claims.get("iss")=="https://token.actions.githubusercontent.com",
              "audience":claims.get("aud")==AUDIENCE,
              "repository":claims.get("repository")==REPO,
              "repository_id":str(claims.get("repository_id"))=="1403281267",
              "repository_owner_id":str(claims.get("repository_owner_id"))=="30191163",
              "ref":claims.get("ref")=="refs/heads/main",
              "workflow_ref":claims.get("workflow_ref")==expected,
              "github_hosted":claims.get("runner_environment")=="github-hosted",
              "owner_actor":str(claims.get("actor_id"))=="30191163",
              "event_is_issue":claims.get("event_name")=="issues",
              "nbf_present":isinstance(claims.get("nbf"),int),
              "run_id_present":bool(claims.get("run_id"))
            }
            try:
                import time
                now=int(time.time())
                checks.update({
                  "jwt_length_ok":len(signed)<8500,
                  "header_rs256":header.get("alg")=="RS256",
                  "header_kid_regex":bool(re.fullmatch(r"[A-Za-z0-9_.-]{1,128}",str(header.get("kid","")))),
                  "iat_valid":isinstance(claims.get("iat"),int) and now-1200<=claims["iat"]<=now+30,
                  "nbf_valid":isinstance(claims.get("nbf"),int) and claims["nbf"]<=now+30,
                  "exp_future":isinstance(claims.get("exp"),int) and claims["exp"]>now,
                  "ttl_lte_1200":isinstance(claims.get("exp"),int) and isinstance(claims.get("iat"),int) and claims["exp"]-claims["iat"]<=1200
                })
                reqjwks=urllib.request.Request("https://token.actions.githubusercontent.com/.well-known/jwks",headers={"Accept":"application/json"})
                with urllib.request.urlopen(reqjwks,timeout=12) as jr:
                    keys=json.loads(jr.read(32768)).get("keys",[])
                checks["public_jwks_kid_found"]=any(x.get("kid")==header.get("kid") and x.get("kty")=="RSA" for x in keys)
            except Exception:
                checks["extended_diagnostic_unavailable"]=True
            print("GITHUB_OIDC_NONSECRET_CLAIM_CHECKS "+json.dumps(checks,sort_keys=True),file=sys.stderr)
        raise

def parse_issue(path):
    event=json.loads(path.read_text(encoding="utf-8"))
    repo=event.get("repository",{});issue=event.get("issue",{})
    if repo.get("full_name")!=REPO or issue.get("user",{}).get("login")!=repo.get("owner",{}).get("login") or issue.get("state")!="open":
        raise ValueError("Owner-only open issue required")
    if not str(issue.get("title","")).startswith("[MAD-V5-CF] "):raise ValueError("Title gate failed")
    data=json.loads(issue.get("body","") or "{}")
    if not isinstance(data,dict) or set(data)!={"schema_version","project_id","mode","profile","prompt"} or data.get("schema_version")!=1:
        raise ValueError("Exact synthetic payload required")
    if data.get("project_id")!="moksha_wellness" or data.get("mode") not in ("fixture","live","multimodal") or data.get("profile") not in ("synthetic_test","instagram_reel"):
        raise ValueError("Invalid project or profile")
    prompt=data.get("prompt")
    if not isinstance(prompt,str) or not 12<=len(prompt)<=600 or re.search(r"https?://|data:[^ ]+;base64|github_pat_|ghp_",prompt,re.I):
        raise ValueError("No links/media/secrets accepted")
    return {"issue_number":int(issue["number"]),"project_id":data["project_id"],"mode":data["mode"],
            "profile":data["profile"],"prompt":prompt}

def output(name,value):
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"],"a",encoding="utf-8") as f:f.write(f"{name}={value}\n")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("action",choices=("enqueue","claim","complete"))
    p.add_argument("--event",type=Path);p.add_argument("--claim-file",type=Path)
    p.add_argument("--receipt",type=Path);p.add_argument("--render-outcome",choices=("success","failure","skipped"))
    a=p.parse_args()
    if a.action=="enqueue":
        d=parse_issue(a.event);result=call("enqueue",d)
        if result.get("job_id")!=f"madcf-{d['issue_number']}":raise RuntimeError("Unexpected queue response")
        print("CLOUDFLARE_SYNTHETIC_ENQUEUE_ACK",result["job_id"],bool(result.get("queued")))
    elif a.action=="claim":
        result=call("claim",{});job=result.get("job")
        if not job:output("has_job","0");print("CLOUDFLARE_BRIDGE_QUEUE_IDLE");return
        if not str(job.get("job_id","")).startswith("madcf-") or job.get("project_id")!="moksha_wellness":
            raise RuntimeError("Queue job identity mismatch")
        if job.get("mode") not in ("fixture","live","multimodal") or job.get("profile") not in ("synthetic_test","instagram_reel"):
            raise RuntimeError("Unexpected remote mode/profile")
        a.claim_file.parent.mkdir(parents=True,exist_ok=True)
        a.claim_file.write_text(json.dumps(job),encoding="utf-8");a.claim_file.chmod(0o600)
        output("has_job","1");print("CLOUDFLARE_BRIDGE_JOB_CLAIMED",job["job_id"],job["mode"])
    else:
        job=json.loads(a.claim_file.read_text(encoding="utf-8"))
        passed=a.render_outcome=="success" and a.receipt and a.receipt.exists()
        sha=None
        if passed:
            d=json.loads(a.receipt.read_text(encoding="utf-8"))
            passed=d.get("status")=="SYNTHETIC_TECHNICAL_CERTIFICATION_ONLY" and d.get("video",{}).get("decoded") is True and d.get("real_footage_certified") is False and not d.get("published")
            sha=d.get("video",{}).get("sha256") if passed else None
        result=call("complete",{"job_id":job["job_id"],"claim_id":job["claim_id"],
          "status":"passed" if passed else "failed",**({"sha256":sha} if passed else {})})
        if result.get("accepted") is not True:raise RuntimeError("Cloudflare rejected completion lease")
        print("CLOUDFLARE_V5_REMOTE_SYNTHETIC_RESULT",job["job_id"],"PASS" if passed else "FAIL")
        if not passed:sys.exit(4)

if __name__=="__main__":main()
