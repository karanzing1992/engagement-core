#!/usr/bin/env bash
# CPU-only private Reel Engine Cloud Run Job pilot: no execution, no publishing.
set -euo pipefail
umask 077
PROJECT_ID=focused-premise-510518-g6
REGION=asia-south1
JOB=reel-engine-cpu-pilot
REPO=reel-pilot-images
SA="reel-pilot-worker@${PROJECT_ID}.iam.gserviceaccount.com"
INPUT="reel-pilot-source-${PROJECT_ID}"
OUTPUT="reel-pilot-drafts-${PROJECT_ID}"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/reel-engine-cpu-pilot:source-v1"
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
case "${1:---check}" in
  --check) MODE=check ;;
  --deploy) MODE=deploy ;;
  *) echo 'Usage: bash bootstrap-cloudrun-pilot.sh [--check|--deploy]' >&2; exit 2 ;;
esac
[ "$#" -eq 0 ] || [ "$#" -eq 1 ] || { echo 'Too many arguments' >&2; exit 2; }
command -v gcloud >/dev/null || { echo 'gcloud CLI is required' >&2; exit 3; }
for file in cloudrun_batch.py geo_policy.py multi_renderer.py Dockerfile.cloudrun-job; do
  test -f "$ROOT/$file" || { echo "Missing source $file" >&2; exit 3; }
done
account="$(gcloud auth list --filter='status:ACTIVE' --format='value(account)' | head -n 1)"
test -n "$account" || { echo 'No authenticated Cloud SDK account' >&2; exit 3; }
billing="$(gcloud billing projects describe "$PROJECT_ID" --format='value(billingEnabled)' 2>/dev/null)" || {
  echo 'Cannot verify project billing. Nothing changed.' >&2; exit 4;
}
printf 'Project: %s | Region: %s | Billing enabled: %s\n' "$PROJECT_ID" "$REGION" "$billing"
if [[ "${billing,,}" != true ]]; then
  echo 'Billing not enabled. No cloud resources changed.' >&2; exit 4
fi
if [[ "$MODE" == check ]]; then
  echo 'READ-ONLY PASS; Cloud Build, Artifact Registry and storage use trial credits or accrue charges.'
  printf 'Proposed resources: %s; gs://%s; gs://%s; %s\n' "$REPO" "$INPUT" "$OUTPUT" "$JOB"
  echo 'No changes made; deploy mode never executes or publishes anything.'
  exit 0
fi
if gcloud storage buckets describe "gs://$INPUT" >/dev/null 2>&1 ||
   gcloud storage buckets describe "gs://$OUTPUT" >/dev/null 2>&1; then
  echo 'A private pilot bucket already exists; refusing overwrite/reuse.' >&2; exit 5
fi
# Enabling APIs is a project modification and is only reached in explicit deploy mode.
gcloud services enable --project="$PROJECT_ID" \
  run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com \
  storage.googleapis.com iam.googleapis.com
if gcloud run jobs describe "$JOB" --region="$REGION" --project="$PROJECT_ID" >/dev/null 2>&1; then
  echo 'Pilot job already exists; refusing overwrite.' >&2; exit 5
fi
if ! gcloud artifacts repositories describe "$REPO" --location="$REGION" --project="$PROJECT_ID" >/dev/null 2>&1; then
  gcloud artifacts repositories create "$REPO" --repository-format=docker --location="$REGION" \
    --description='Private CPU-only reel pilot' --project="$PROJECT_ID"
fi
if ! gcloud iam service-accounts describe "$SA" --project="$PROJECT_ID" >/dev/null 2>&1; then
  gcloud iam service-accounts create reel-pilot-worker --project="$PROJECT_ID" \
    --display-name='Private reel pilot worker'
fi
for bucket in "$INPUT" "$OUTPUT"; do
  gcloud storage buckets create "gs://$bucket" --project="$PROJECT_ID" \
    --location="$REGION" --uniform-bucket-level-access --public-access-prevention \
    --soft-delete-duration=0
done
gcloud storage buckets add-iam-policy-binding "gs://$INPUT" \
  --member="serviceAccount:$SA" --role=roles/storage.objectViewer
gcloud storage buckets add-iam-policy-binding "gs://$OUTPUT" \
  --member="serviceAccount:$SA" --role=roles/storage.objectCreator
build_dir="$(mktemp -d)"
trap 'rm -rf -- "$build_dir"' EXIT
cp "$ROOT/Dockerfile.cloudrun-job" "$build_dir/Dockerfile"
cp "$ROOT/cloudrun_batch.py" "$ROOT/geo_policy.py" "$ROOT/multi_renderer.py" "$build_dir/"
echo 'Building image via Cloud Build; charges may apply beyond trial/free tier.'
gcloud builds submit "$build_dir" --tag="$IMAGE" --project="$PROJECT_ID" --region="$REGION" --quiet
gcloud run jobs deploy "$JOB" --project="$PROJECT_ID" --region="$REGION" \
  --image="$IMAGE" --cpu=1 --memory=512Mi --tasks=1 --parallelism=1 \
  --max-retries=0 --task-timeout=600s --service-account="$SA" \
  --set-env-vars="REEL_BATCH_MANIFEST_URI=gs://$INPUT/approved/pilot-0001.json,REEL_BATCH_SOURCE_PREFIX=gs://$INPUT/approved/,REEL_BATCH_OUTPUT_PREFIX=gs://$OUTPUT/drafts/" --quiet
printf 'Pilot job deployed but NOT executed or published: %s\n' "$JOB"
echo 'Next gate: private upload of genuine reviewed Goa/India footage, exact checksums and provenance.'
