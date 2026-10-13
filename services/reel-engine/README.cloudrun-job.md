# CPU-only Cloud Run Job adapter — staging / review

**PRIVATE PILOT DEPLOYED; FIRST APPROVED MEDIA RENDER NOT YET EXECUTED.** The isolated Mumbai Cloud Run job `reel-engine-cpu-pilot` is registered and idle. Project billing/trial is enabled and Cloud Build succeeded. This draft PR is unmerged. Google sample runtime test #31 and five-second synthetic FFmpeg cloud encoding test #32 have both passed, but durable private GCS export and genuine reviewed footage intake have not been verified.

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

## First private Cloud Run job deployed — verified 13 October 2026

User-provided authenticated Cloud Shell output confirms:
- Google Cloud Build `9baf7f61-6c75-4929-94cc-31c8591f50cf`,
  `STATUS: SUCCESS`, duration `2M1S`.
- Built image `asia-south1-docker.pkg.dev/focused-premise-510518-g6/reel-pilot-images/reel-engine-cpu-pilot:source-v1`.
- `gcloud run jobs deploy` completed successfully for
  `reel-engine-cpu-pilot` in `asia-south1`.
- `gcloud run jobs describe ... --format=value(metadata.name)`
  returned the exact job name.

Independently, authenticated Opera Agent 2 browser readback in Google Cloud
Console confirmed `reel-engine-cpu-pilot` appeared in the Cloud Run Jobs
list with **No executions**, and the job History tab read
**No history for this job yet** (agent jobs #12 and #13).
YAML details (service account, CPU, RAM, environment) were not readable
through the browser and remain **configured by source, not independently
inspected post-deployment**. The Cloud Shell script was executed with
`REEL_PILOT_SUFFIX=pilot2` after both suffixed private bucket names
passed a read-only absence audit. Original existing buckets were preserved.

**Runtime status:** job REGISTERED/DEPLOYED; **not executed**, not
media-tested in Google Cloud and not a public or live social publishing
service. Deployment may consume Google trial credit. Before any first
execution, independently inspect the job's IAM/environment and private GCS
storage, upload human-reviewed genuinely owned/licensed India/Goa video,
SHA-256 checksums and approved evidence, then review the job execution
budget. The unbranded `generic` pilot is mandatory until the actual official
transparent Moksha logo is approved and integrated.

The existing feature branch/PR #50 is still draft and has not been merged
to a monitored default branch. Runtime deployment is independently reported
via Moksha Master **Route B event #28**. Do not register this same runtime
change again as a Route A deployed result without deduplication.

## Post-deployment authenticated browser audit — 13 October 2026

Using the **isolated Opera Agent 2 read-only browser** with Google Cloud's
owner session, the actual Cloud Run Job edit form was read **without saving**:

- Job `reel-engine-cpu-pilot` in `asia-south1`, image
  `asia-south1-docker.pkg.dev/focused-premise-510518-g6/reel-pilot-images/reel-engine-cpu-pilot:source-v1`
- 1 vCPU, **512 MiB**, 1 task, parallelism **1**, 10-minute timeout,
  **0 retries**, manual-only.
- Job Security tab identified **Private reel pilot worker**.
- Job Triggers tab explicitly displayed **This job has no triggers**.
- Job History listed **No history for this job yet**; no execution proven.

The actual Cloud Storage bucket inventory separately verified both
`reel-pilot-source-focused-premise-510518-g6-pilot2` and
`reel-pilot-drafts-focused-premise-510518-g6-pilot2`:
- Region `asia-south1`, Standard class; public access **Not public**,
  **Uniform** access control and Public Access Prevention.
- Actual source Permissions list: **Private reel pilot worker** has
  `Storage Object Viewer` (bucket-level), no extra cross-venture grants.
- Actual output Permissions list: same worker has
  `Storage Object Creator` (bucket-level).
- Both **object inventories were empty** at the observed time.
- Existing original unsuffixed buckets were preserved; no changes
  were made during this audit. Broader project-inherited principals
  remained in the IAM list and were not modified.

Two *private user Library* video candidates were reviewed locally for
technical suitability only:
- `1000051316.mp4`: H.264 720×1280, 69.798s, 20,501,679 bytes,
  SHA256 `398c1b5b16854266e26fcb9874f19589771292982174cb7b47e2cf499949052d`.
- `1000042280.mp4`: H.264 1080×1920, 16.067s, 20,442,820 bytes,
  SHA256 `346a1e32617dc23419be5e546728c2593f4ee85dd7de48dffa3a8b3eafef6047`.
- Combined **40,944,499 bytes**, below current pilot's 48 MiB combined
  input cap. Library copies are **not Google Cloud objects**.

**BLOCKER:** User-uploaded media cannot be described as independently
human-verified Goa/India footage simply because it was found in a
brand library or visually resembles Goa. Exact HTTPS source/location
evidence, rights confirmation, human reviewer, and private GCS intake
are still outstanding. Do NOT create a fabricated provenance manifest,
bypass `geo_policy.py`, upload sources publicly, execute the job against
a missing manifest, or claim the first cloud render succeeded.
The existing job remains registered and idle.

## Cloud Run runtime checkpoint (13 October 2026)

Verified one-shot Google-provided sample job `reel-runtime-sample-20261013`
execution `reel-runtime-sample-20261013-v9dwq`:
- Google Cloud Run in Mumbai `asia-south1`, 1 vCPU, 512 MiB,
  1 task, 120-second timeout, zero retries, dedicated Reel worker.
- Authenticated Console Tasks pane: 1 succeeded, 0 failed, 0 running.
  Task index 0 exited with code 0, actual start 15:21:12 IST and end
  15:21:16 IST. Logs confirm Completed Task #0 and `exit(0)`.
- Exact execution:
  https://console.cloud.google.com/run/jobs/execution/asia-south1/reel-runtime-sample-20261013-v9dwq?project=focused-premise-510518-g6
- Independently registered in the private Supabase Master event inbox
  as published event #31. NOT a verified FFmpeg video render.

A separate isolated `reel-cpu-smoke-20261013` diagnostic job was created
but has never been executed. The Cloud Console custom edit form did not
persist `/usr/bin/ffmpeg` command/argument overrides; readback confirmed
missing values, so execution was deliberately blocked. The isolated Agent 2
Mac worker rejected native keyboard/paste actions with
`Disallowed Agent 2 step`. Do not bypass this permission boundary.

An offline tested fail-closed `run-ffmpeg-smoke.sh` diagnostic has been
prepared in the conversation artifact set. It targets ONLY the isolated
diagnostic job, uses gcloud's official `--command` and `--args`
overrides, validates exact job/image/service account and no prior
execution, and does not touch the production Reel Engine. Its bash syntax
check and both read-only and --run paths **passed against a mock gcloud
client**; real gcloud execution and actual MP4 generation are NOT verified.
The script needs explicitly authorized Cloud Shell execution. Do not
claim the cloud job succeeded until its task exit code and logs are read.

## FFmpeg isolated Cloud Run smoke PASS — 13 October 2026

Authenticated Cloud Shell operator ran the guarded private synthetic FFmpeg diagnostic on the **existing disposable smoke job** `reel-cpu-smoke-20261013`, not on `reel-engine-cpu-pilot`.

- Exact Cloud Run execution: https://console.cloud.google.com/run/jobs/execution/asia-south1/reel-cpu-smoke-20261013-4scrk?project=focused-premise-510518-g6
- Independent browser job #108 read the new execution `reel-cpu-smoke-20261013-4scrk` in Mumbai. Job #109 read **1 succeeded, 0 failed, exit code 0, retries 0** and actual 15:52:54–15:52:59 IST task timing.
- Authenticated browser job #110 read actual FFmpeg logs: input `lavfi testsrc2=size=720x1280:rate=25`, encoder `libx264`, output 9:16 720×1280 H.264/yuv420p MP4 at **25 fps**, **125 frames / 5.00 seconds**, encoded file size approximately **3,870 KiB**, FFmpeg reported **6.44×** throughput, followed by container `exit(0)`.
- The smoke file was saved **only to ephemeral `/tmp/reel-cpu-smoke.mp4` inside the job container** and is not a durable Google Cloud Storage object or an export available for publishing.
- This verifies the container's real CPU/FFmpeg encoding path, **not** a 30-second real-footage render, geographic provenance, source-file ingestion, sustained workload or durable private GCS export.
- Recorded as verified published Moksha Master Route B **Event #32**; exact canonical Google Doc event marker read back once.

**Release gate still pending:** implement and verify least-privilege private GCS artifact export, then intake authenticated/approved original Goa/India footage with source checksums and location/usage evidence, run a single 30-second unbranded render, confirm ffprobe dimensions/duration/audio and video output integrity. Do not create scheduled or public posting until reviewed.

## Private GCS artifact smoke — prepared, not yet run (13 October 2026)

New review-only branch files:
- `gcs_persist_smoke.py` — synthetic 5-second 720×1280/25 fps H.264 MP4, in-container ffprobe, SHA-256, then private GCS MP4+JSON report uploads using **create-only** `if_generation_match=0`. Never generates signed URLs or publishes; the actor has Storage Object Creator on the output bucket.
- `run-private-gcs-smoke.sh` — **defaults to --check**. Requires authorized Cloud Shell. Verifies correct isolated job, pinned image, dedicated service account, single known prior execution `reel-cpu-smoke-20261013-4scrk`, Mumbai output bucket, raw IAM with Public Access Prevention and Uniform Access, absent target names and billing. `--run` only updates the disposable smoke job with exact Python inline payload, reads it back, runs once with 2-minute timeout/zero retries, then independently downloads MP4 and JSON into a temporary Cloud Shell workspace to verify checksum, size, format and duration.
- `test_gcs_persist_smoke.py` — mock-GCS tests with genuine local FFmpeg/ffprobe and intentional no-overwrite failure.

**Validation completed locally:** Python syntax PASS, Bash syntax PASS, 2 real-FFmpeg/mock-GCS unit tests PASS (5 seconds, 125 frames, H.264, 720×1280, ~3.96 MB, checksum checked). The Bash `--check` and `--run` paths both PASS with a mock gcloud client, including post-download SHA-256 and metadata verification. The two original program files were fetched from GitHub and verified byte-identical against the tested local copies before the small `--raw` bucket-metadata flag improvement. Actual **Google Cloud GCS upload has NOT been executed or verified.**

Private output destinations are fixed to:
- `gs://reel-pilot-drafts-focused-premise-510518-g6-pilot2/smoke/cpu-gcs-20261013-01.mp4`
- `gs://reel-pilot-drafts-focused-premise-510518-g6-pilot2/smoke/cpu-gcs-20261013-01.json`

In existing authenticated Cloud Shell (one-time action; `--run` may consume trial credit):

```bash
cd ~/reel-engine-cloud-source/services/reel-engine
git pull --ff-only
python3 -m unittest -v test_gcs_persist_smoke.py
bash -n run-private-gcs-smoke.sh
bash run-private-gcs-smoke.sh --check
bash run-private-gcs-smoke.sh --run
```

**Stop after any failed check or partial execution; no blind retries.** Do not execute the production `reel-engine-cpu-pilot`, alter existing unsuffixed buckets or publish test files. A successful Cloud Shell script execution is not proof until real private GCS objects and download hashes are independently read back; verify in Cloud Run + GCS afterwards. Rollback remains isolated to the disposable smoke job and the two named synthetic objects only; never delete other customer data or original buckets. Reusable functionality remains separated from venture config for future productization.
