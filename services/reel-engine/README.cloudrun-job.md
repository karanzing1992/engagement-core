# CPU-only Cloud Run Job adapter — staging / review

**NOT DEPLOYED.** No billing, paid service, Cloud API, build, GCS bucket, Cloud Run job or schedule was activated.

## Purpose / isolation

A private one-shot adapter for the existing Reel Engine v0.5, reusing the
existing multi_renderer.render_multiple and geo_policy.validate_render_config.
It does not replace the FastAPI engine or bypass the WordPress approval gate.
Generic, unbranded 30-second draft renders only. Moksha output remains blocked
until a separately verified, genuine transparent official logo is available.
The older black-backed asset is not an approved substitute.

The worker reads private GCS footage and writes a private MP4 and JSON report.
No social publishing, public URL, video server, automation schedule, LLM
provider, GPU, external credentials or customer/guest data.

## Environment variables

REEL_BATCH_MANIFEST_URI=gs://YOUR_BUCKET/approved/pilot-0001.json

REEL_BATCH_SOURCE_PREFIX=gs://YOUR_BUCKET/approved/

REEL_BATCH_OUTPUT_PREFIX=gs://YOUR_BUCKET/drafts/

The input manifest must contain:
- schema_version: 1, brand: generic, unique job_id (8–50 chars, lowercase/dashes)
- source_objects: list of 1–4 objects, each with a gs:// URI and exact SHA-256
- config: existing geography-reviewed config, brand generic, editorial_region Goa
  or India, one human-verified source_provenance record per clip,
  target_seconds=30, width=720, height=1280, fps=25

Provenance must be genuinely verified by an editor. Inventing an editor's
review or location evidence is forbidden. Malformed / missing metadata fails
before rendering. All source inputs must stay under the designated prefix.
The 48 MiB TOTAL source cap is an intentionally small first pilot. Large
231 MB footage is unsupported without rebenchmarking and more memory.

Outputs: gs://YOUR_BUCKET/drafts/JOB_ID.mp4 and JOB_ID.json, always private.
Uploads use create-only preconditions to prevent silent replacement.

## Image and cost gates

Dockerfile.cloudrun-job: Python 3.12 slim + FFmpeg; pinned
google-cloud-storage v3.17.0. No HTTP listener or persistent container.

Proposed settings:
- Project: focused-premise-510518-g6
- Region: asia-south1 (Mumbai)
- Name: reel-engine-cpu-pilot
- 1 vCPU, 512 MiB RAM, 1 task, parallelism 1, no retries
- Task timeout 600 seconds, manual execution only
- Dedicated service account: Storage Object Viewer on approved inputs;
  Storage Object Creator on private output storage (scope minimally)
- No GPU, no always-on instance, no public access
- Cloud Billing budget alerts before execution; alerts are NOT a spending cap

DO NOT DEPLOY until the project billing status, identity permissions and
costs have been verified and the operator explicitly authorizes paid cloud
resources. The live Cloud Run Jobs page is accessible but the billing page
was inconclusive, so billing is UNVERIFIED as of 2026-10-13. Cloud Run Jobs
have a monthly free tier aggregated per billing account. Cloud Build, Artifact
Registry, GCS and egress can each incur separate costs.

Example proposed gcloud job configuration only (not executed):

    gcloud run jobs deploy reel-engine-cpu-pilot \
      --project=focused-premise-510518-g6 \
      --region=asia-south1 \
      --image=asia-south1-docker.pkg.dev/PROJECT/REPO/IMAGE:PINNED_TAG \
      --cpu=1 --memory=512Mi --tasks=1 --parallelism=1 \
      --max-retries=0 --task-timeout=600s \
      --service-account=DEDICATED_SERVICE_ACCOUNT_EMAIL \
      --set-env-vars=REEL_BATCH_MANIFEST_URI=gs://YOUR_BUCKET/approved/pilot-0001.json,REEL_BATCH_SOURCE_PREFIX=gs://YOUR_BUCKET/approved/,REEL_BATCH_OUTPUT_PREFIX=gs://YOUR_BUCKET/drafts/

Run local structural checks:

    cd services/reel-engine
    python3 -m unittest -v test_cloudrun_batch.py test_geo_policy.py
    python3 -m py_compile cloudrun_batch.py

The tests are NOT cloud execution or real-media FFmpeg validation.
Before release run build, vulnerability scan, checksum-driven video smoke
test and output-quality review. For rollback discard this feature branch
before deployment; after deployment delete only the approved pilot job,
image, private pilot objects and scoped permissions. Agent 1, Agent 2,
other customer data and existing Reel Engine API remain untouched.
