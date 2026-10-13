#!/usr/bin/env bash
# Disposable Cloud Run synthetic MP4 -> private GCS smoke; no real content/publishing.
set -euo pipefail
umask 077

PROJECT='focused-premise-510518-g6'
REGION='asia-south1'
JOB='reel-cpu-smoke-20261013'
BASELINE_EXEC='reel-cpu-smoke-20261013-4scrk'
IMAGE="${REGION}-docker.pkg.dev/${PROJECT}/reel-pilot-images/reel-engine-cpu-pilot:source-v1"
WORKER="reel-pilot-worker@${PROJECT}.iam.gserviceaccount.com"
BUCKET="reel-pilot-drafts-${PROJECT}-pilot2"
KEY='smoke/cpu-gcs-20261013-01'
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SOURCE="${ROOT}/gcs_persist_smoke.py"
MODE="${1:---check}"
if [[ $# -gt 1 || ( "$MODE" != '--check' && "$MODE" != '--run' ) ]]; then
  echo 'Usage: bash run-private-gcs-smoke.sh [--check|--run]' >&2; exit 2
fi
for bin in gcloud python3 base64 sha256sum; do
  command -v "$bin" >/dev/null || { echo "Missing dependency: $bin" >&2; exit 2; }
done
[[ -f "$PYTHON_SOURCE" ]] || { echo 'Missing checked-in Python smoke source' >&2; exit 2; }
python3 -m py_compile "$PYTHON_SOURCE"
if ! gcloud auth list --filter='status:ACTIVE' --format='value(account)' | grep -q '@'; then
  echo 'No active Cloud SDK account' >&2; exit 3
fi
billing="$(gcloud billing projects describe "$PROJECT" --format='value(billingEnabled)' 2>/dev/null)" || {
  echo 'Cannot verify billing; do not proceed' >&2; exit 3;
}
[[ "${billing,,}" == true ]] || { echo 'Billing not enabled' >&2; exit 3; }
WORKSPACE="$(mktemp -d)"
trap 'rm -rf -- "$WORKSPACE"' EXIT

gcloud run jobs describe "$JOB" --project="$PROJECT" --region="$REGION" --format=json > "$WORKSPACE/job.json"
gcloud storage buckets describe "gs://$BUCKET" --format=json > "$WORKSPACE/bucket.json"
gcloud run jobs executions list --job="$JOB" --project="$PROJECT" --region="$REGION" --format=json > "$WORKSPACE/executions.json"
python3 - "$WORKSPACE/job.json" "$WORKSPACE/bucket.json" "$WORKSPACE/executions.json" "$JOB" "$IMAGE" "$WORKER" "$BUCKET" "$BASELINE_EXEC" <<'PY'
import json, sys
job_file,bucket_file,exec_file,name,image,worker,bucket,baseline=sys.argv[1:]
with open(job_file,encoding='utf8') as f: job=json.load(f)
with open(bucket_file,encoding='utf8') as f: storage=json.load(f)
with open(exec_file,encoding='utf8') as f: executions=json.load(f)
def values(x,key):
    if isinstance(x,dict):
        for k,v in x.items():
            if k==key: yield v
            yield from values(v,key)
    elif isinstance(x,list):
        for i in x: yield from values(i,key)
assert job.get('metadata',{}).get('name')==name,'WRONG JOB - STOP'
containers=[i for group in values(job,'containers') if isinstance(group,list) for i in group if isinstance(i,dict)]
assert len(containers)==1 and containers[0].get('image')==image,'WRONG IMAGE - STOP'
identities=[str(x) for k in ('serviceAccount','serviceAccountName') for x in values(job,k)]
assert worker in identities,'WRONG SERVICE ACCOUNT - STOP'
assert storage.get('location','').upper()=='ASIA-SOUTH1','BUCKET LOCATION MISMATCH - STOP'
bucket_name=str(storage.get('name','')).removeprefix('gs://')
assert bucket_name==bucket,'WRONG OUTPUT BUCKET - STOP'
config=storage.get('iamConfiguration') or {}
assert config.get('publicAccessPrevention','').lower()=='enforced','BUCKET PAP NOT ENFORCED - STOP'
assert config.get('uniformBucketLevelAccess',{}).get('enabled') is True,'BUCKET NOT UNIFORM - STOP'
if not isinstance(executions,list): raise SystemExit('EXECUTION LIST NOT AVAILABLE - STOP')
names=[]
for e in executions:
    if isinstance(e,dict):
        value=e.get('metadata',{}).get('name') or e.get('name')
        if value: names.append(str(value).rsplit('/',1)[-1])
if sorted(names)!=[baseline]: raise SystemExit('SMOKE JOB NOT SINGLE BASELINE EXECUTION; NO RERUN: '+repr(names))
print('PASS: isolated job/image/worker, Mumbai private bucket and exactly one prior smoke execution')
PY

# No overwrites, including partial prior attempts. Differentiate 404 from auth/transport errors.
for object in "$KEY.mp4" "$KEY.json"; do
  if gcloud storage objects describe "gs://$BUCKET/$object" --format=json > "$WORKSPACE/object.json" 2> "$WORKSPACE/object.err"; then
    echo "FAIL CLOSED: object already exists: gs://$BUCKET/$object" >&2; exit 4
  fi
  if ! grep -Eiq '404|not found|does not exist|matched no objects' "$WORKSPACE/object.err"; then
    echo "FAIL CLOSED: cannot distinguish absent object from denied access: $object" >&2; exit 4
  fi
done

if [[ "$MODE" == '--check' ]]; then
  echo 'READ-ONLY PASS; target objects absent, no Cloud Run or GCS change made.'
  echo "PRIVATE TARGET: gs://$BUCKET/$KEY.mp4"
  echo 'Cloud Run execution and storage can consume trial credit or incur charges.'
  exit 0
fi

# Only source code in this very checkout runs. Keep inline interpreter argument comma-free.
SOURCE_B64="$(base64 < "$PYTHON_SOURCE" | tr -d '\n')"
INLINE="exec(__import__(\"base64\").b64decode(\"${SOURCE_B64}\"))"

gcloud run jobs update "$JOB" \
  --project="$PROJECT" --region="$REGION" \
  --command=python3 --args="-c,${INLINE}" \
  --tasks=1 --parallelism=1 --max-retries=0 --task-timeout=120s \
  --cpu=1 --memory=512Mi --service-account="$WORKER" --quiet

gcloud run jobs describe "$JOB" --project="$PROJECT" --region="$REGION" --format=json > "$WORKSPACE/job-after.json"
python3 - "$WORKSPACE/job-after.json" "$JOB" "$IMAGE" "$WORKER" "$INLINE" <<'PY'
import json,sys
f,name,image,worker,inline=sys.argv[1:]
with open(f,encoding='utf8') as s: data=json.load(s)
def find(x,key):
    if isinstance(x,dict):
        for k,v in x.items():
            if k==key: yield v
            yield from find(v,key)
    elif isinstance(x,list):
        for y in x: yield from find(y,key)
cs=[y for a in find(data,'containers') if isinstance(a,list) for y in a if isinstance(y,dict)]
assert data.get('metadata',{}).get('name')==name,'Job mismatch'
assert len(cs)==1 and cs[0].get('image')==image,'Image mismatch'
assert cs[0].get('command')==['python3'],'Python entrypoint was not saved'
assert cs[0].get('args')==['-c',inline],'Exact private GCS encoder payload was not saved'
assert worker in [str(v) for k in ('serviceAccount','serviceAccountName') for v in find(data,k)],'Worker mismatch'
print('PASS: Cloud Run confirms exact synthetic encoder and private uploader were persisted')
PY

# Race/duplicate guard immediately before execute.
gcloud run jobs executions list --job="$JOB" --project="$PROJECT" --region="$REGION" --format=json > "$WORKSPACE/before-start.json"
python3 - "$WORKSPACE/before-start.json" "$BASELINE_EXEC" <<'PY'
import json,sys
with open(sys.argv[1]) as f: l=json.load(f)
n=[str(x.get('metadata',{}).get('name') or x.get('name','')).rsplit('/',1)[-1] for x in l]
assert n==[sys.argv[2]],'New execution appeared; refusing duplicate'
PY

echo 'Executing exactly one disposable 5-second synthetic encode + private GCS upload.'
gcloud run jobs execute "$JOB" --project="$PROJECT" --region="$REGION" --wait --quiet

# Independent Cloud Shell readback from private objects, not a claim based only on logs.
gcloud storage cp "gs://$BUCKET/$KEY.mp4" "$WORKSPACE/downloaded.mp4" --quiet
gcloud storage cp "gs://$BUCKET/$KEY.json" "$WORKSPACE/report.json" --quiet
python3 - "$WORKSPACE/downloaded.mp4" "$WORKSPACE/report.json" "$BUCKET" "$KEY" <<'PY'
import hashlib,json,sys
from pathlib import Path
video,report_file,bucket,key=sys.argv[1:]
data=Path(video).read_bytes(); actual=hashlib.sha256(data).hexdigest()
report=json.loads(Path(report_file).read_text(encoding='utf8'))
assert report.get('video_uri')==f'gs://{bucket}/{key}.mp4','Wrong GCS URI'
assert report.get('sha256')==actual,'SHA256 mismatch after private GCS download'
assert report.get('bytes')==len(data),'Storage size mismatch'
assert report.get('codec')=='h264' and report.get('width')==720 and report.get('height')==1280,'Wrong video format'
assert report.get('frames')==125 and abs(float(report.get('duration_seconds',0))-5.0)<0.05,'Wrong duration'
assert report.get('published') is False and report.get('no_real_footage') is True,'Privacy/footage scope mismatch'
print('VERIFIED PRIVATE GCS MP4 PASS: 5s, 720x1280, 25fps, SHA256='+actual+', bytes='+str(len(data)))
print('Saved private: '+report['video_uri'])
PY
if command -v ffprobe >/dev/null; then
  ffprobe -v error -show_entries format=duration,size:stream=codec_name,width,height,r_frame_rate,nb_frames \
    -of json "$WORKSPACE/downloaded.mp4"
fi
echo 'No public URL, publishing action, or production Reel Engine execution was performed.'
