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

## Offline validation — 13 October 2026

The checked-in cloudrun_batch.py was reproduced locally and its Git blob
SHA-1 was confirmed byte-for-byte against GitHub:
fd22ce0568ba04084e46f9a7e14caa223e8332e3.

Eight local unit tests passed (private URI/path guards, valid pilot manifest,
unbranded restriction, wrong bucket, synthetic foreign-location rejection,
geographic override blocking and target geometry). The test fixture and
geo_policy / multi_renderer helpers were locally reconstructed for the offline
environment rather than obtained as a full exact checkout, so this is
**not** a claim that GitHub Actions, the full repository test suite or a
container build passed.

A full end-to-end offline adapter smoke test with simulated private GCS
Client/Bucket/Blob and **real FFmpeg** also passed using two generated 15-second
synthetic clips. It created a private 720x1280, 25-fps, 750-frame MP4 with
audio, duration 30.043984 seconds and size 6,657,321 bytes, plus a private
JSON result. The test emitted no public URL and performed no real Google
Cloud API requests. Synthetic provenance strings were used **only in the
mock test**, not as proof of eligible real Goa footage.

No cloud billing, API enablement, Google Cloud IAM, Cloud Run, Artifact
Registry, Cloud Build, GCS bucket, production video or brand assets were
modified. Agent 2's Google Cloud Billing page was checked through an
authenticated read-only browser task but displayed a navigation shell only;
billing account linkage is still **UNVERIFIED**. This is a hard block on
deployment and on any paid service creation.

The future Cloud Run 512-MiB memory size remains unbenchmarked under Cloud
Run: local test process peak is not a substitute for whole-container peak
memory or input-size stress testing.

## Google Cloud trial and guarded bootstrap — 13 October 2026

Agent 2 read back an authenticated Cloud Console free-trial banner on
project `focused-premise-510518-g6` displaying ₹28,796.63 credit and
90 days remaining at the observed time. This **does not** independently
prove the Cloud Billing API's `billingEnabled: true`; a check in the
bootstrap script is mandatory. Cloud Run Jobs page was readable but
showed no jobs; its Create Job CTA said it would enable the Admin API.

New source script: `bootstrap-cloudrun-pilot.sh` in this feature branch.
Default `--check` only reads Cloud SDK account/billing. Explicit
`--deploy` enables scoped APIs, creates separate nonpublic Mumbai
source/output buckets, a dedicated service account and Artifact
Registry, builds the CPU image, and registers **one manual-only**
Cloud Run Job. It does NOT execute/render/publish or upgrade the
trial to a paid account. The build and storage can consume trial
credit; hard-spend limits are not implied by budget alerts or credits.
Read the script before execution. No Cloud Shell commands have been
executed yet; no cloud project resource change is verified.
Use `bash -n bootstrap-cloudrun-pilot.sh` as a local syntax check;
the standalone bootstrap syntax has been validated offline.

**Artifact distinction:** A separate ~9KB convenience ZIP of the
offline-tested batch source and bootstrap was assembled as a chat
download. Its `geo_policy.py` and `multi_renderer.py` are from the
verified offline test snapshot and not byte-identical to this PR's
latest versions. Review or replace them with the exact branch source
before promoting the ZIP to production. Cloud Build, integration,
memory sizing and actual footage rights remain release gates.

## Cloud Billing preflight from Cloud Shell — 13 October 2026

The operator executed the source ZIP's **read-only** `bash bootstrap-cloudrun-pilot.sh --check`
in their authenticated Google Cloud Shell, and returned the exact CLI result:

    Project: focused-premise-510518-g6 | Region: asia-south1 | Billing enabled: True
    READ-ONLY PASS; Cloud Build, Artifact Registry and storage use trial credits or accrue charges.
    No changes made; deploy mode never executes or publishes anything.

This is **operator-supplied gcloud evidence** of billing enabled (not a
separately retrieved Cloud Billing API response in this session). The Cloud
trial banner was independently observed through Opera Agent 2 earlier.
Billing enabled is permission to prepare a deployment, not proof that the
relevant APIs, build service account permissions, image or job exist.

**Critical source-parity requirement:** the earlier chat ZIP
`reel-engine-cloudrun-cpu-pilot.zip` had locally reconstructed
`geo_policy.py` and `multi_renderer.py`, and does NOT match this PR's
current Git blobs. Do not deploy from that ZIP. Use a fresh checkout of this
feature branch in Cloud Shell, and run the bootstrap script from
`services/reel-engine/`. Before actual resource creation run Python unit
tests and shell syntax checks. The script's `--deploy` action is not known
to have been run, and no job has been verified created. On a Cloud Build
permission failure, stop and diagnose the build identity; do not grant
Owner/Editor, bypass IAM checks or use Agent 1 credentials.

For the checked-out source, run read-only:

    python3 -m unittest -v test_cloudrun_batch.py test_geo_policy.py
    bash -n bootstrap-cloudrun-pilot.sh
    bash bootstrap-cloudrun-pilot.sh --check

Only a separately chosen explicit `--deploy` enters the creation path.
It may consume Google trial credit and will activate APIs, create private
buckets, an Artifact Registry repository, dedicated service account, build a
CPU image, and register one manual job. It does not execute a render.

## Deployment preflight block: existing bucket name (13 October 2026)

Cloud Shell `bootstrap-cloudrun-pilot.sh --deploy` returned:
`A private pilot bucket already exists; refusing overwrite/reuse.`
Its collision guard executed **before** any API enabling, registry
build, IAM write, bucket creation or job deployment. This failed invocation
made no GCP configuration change.

**Fix in draft PR:** the existing `--check` had tested billing but not
bucket collisions. Added read-only `audit-cloudrun-pilot.py` (verifies
project number, lists project-owned buckets, describes each requested name
without exposing IAM identities) and reuses this audit for **both**
`--check` and `--deploy`. A collision or unknown ownership fails closed.
Optionally set `REEL_PILOT_SUFFIX` to a fresh 4–10-character lowercase
alphanumeric namespace **only after reviewing the audit**; this creates new
source/draft bucket names, not reuse/deletion of existing buckets. Any new
buckets may consume trial credit or accrue storage charges.

Read-only recovery from the existing feature-branch checkout:

    git pull --ff-only
    python3 -m py_compile audit-cloudrun-pilot.py
    bash -n bootstrap-cloudrun-pilot.sh
    bash bootstrap-cloudrun-pilot.sh --check

**Do not** run `--deploy` until collision ownership is known and the
new proposed names pass the audit. Never delete existing buckets or loosen
permissions to bypass a safety check. No new deploy has occurred; source
is still a draft PR, not a main-branch release.
