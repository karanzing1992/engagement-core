# Billing-disabled fallback — private local Reel worker

**Staged source only, not yet installed on the operator's Mac.**

Google Cloud project focused-premise-510518-g6 was reported by the operator as
having **disabled billing** on 13 October 2026. The authenticated Opera Agent 2
Cloud Billing page did not show a definitive linkage state; operator report is
not independent console verification. Cloud Run Jobs requires active billing,
even within the free tier. Never turn billing on, enable APIs, deploy a job,
or create GCS buckets as part of this fallback.

This local CPU-only worker reuses existing multi_renderer.py (FFmpeg) and
geo_policy.py. It does not send the video to Supabase, Google Cloud, GitHub,
or third-party publishing services. It does not integrate with or alter the
Opera Agent 2 native host. Agent 1 and Agent 2 remain untouched.

### Prerequisites

- Checkout of reviewed branch feat/reel-cloudrun-cpu-batch on the Mac.
- Python 3.10+ and local FFmpeg/ffprobe binaries already installed.
- Enough disk space for sources, normalized segments and MP4 outputs.
- Manually approved rights/location/provenance evidence per source clip.

No public inbound listener, scheduler, auto-publisher, credentials or
customer/guest data. The Mac must be running for a render to execute.

### Workspace and invocation

From services/reel-engine (no new Python packages required for local mode):

    python3 local_batch.py --workspace "$HOME/.moksha-reel-local" --init

This creates four distinct private directories:
approved/ for reviewed original videos, requests/ for manifest JSON,
work/ for FFmpeg intermediates and drafts/ for output MP4/JSON.

Copy ONLY locally verified video footage under approved/; manifest JSON goes
under requests/. It must use this structure with real SHA-256 and editor evidence:

    {
      "schema_version": 1,
      "job_id": "pilot-20261013",
      "brand": "generic",
      "source_files": [
        {"file": "approved-clip.mp4", "sha256": "REPLACE_WITH_REAL_SHA256"}
      ],
      "config": {
        "brand": "generic", "editorial_region": "Goa",
        "target_seconds": 30, "width": 720, "height": 1280, "fps": 25,
        "source_provenance": [
          {
            "origin": "owned",
            "capture_country": "India",
            "capture_region": "Goa",
            "source_url": "REPLACE_WITH_REAL_HTTPS_SOURCE",
            "location_evidence_url": "REPLACE_WITH_REAL_HTTPS_PROOF",
            "verification_status": "REQUIRES_ACTUAL_HUMAN_REVIEW",
            "verified_by": "REPLACE_WITH_REAL_REVIEWER"
          }
        ]
      }
    }

This sample intentionally fails without real review and real SHA-256.

    python3 local_batch.py --workspace "$HOME/.moksha-reel-local" \
      --manifest pilot-20261013.json --check

After validation and only for approved clips:

    python3 local_batch.py --workspace "$HOME/.moksha-reel-local" \
      --manifest pilot-20261013.json

Outputs appear only in private drafts/. This is a **generic unbranded** draft
pilot pending approved transparent Moksha logo integration.

### Security and quality gates

- Restrict all file names to basenames; reject symlink inputs and path escape.
- Fail on duplicate source, wrong SHA-256, unreviewed geography, brand mismatch,
  reused job ID and existing output. Total source cap 48 MiB for initial pilot.
- Private created directories (0700), output video/report (0600); no public URLs.
- One job ID runs once, no automatic retries/overwrites. Failure may leave
  private work/ diagnostics; manually inspect before removing them.
- FFmpeg 30-second output and memory usage must be checked with actual
  approved footage before unattended operation.
- Existing local FFmpeg smoke test used synthetic footage; provenance in unit
  test fixtures is synthetic **only**, never a claim of location validation.

Unit-test target for this new local adapter:

    python3 -m unittest -v test_local_batch.py

Do not claim this command has been run until the actual checkout has been
tested. GitHub PR #50 remains draft and unmerged.

### Future automation

An independently reviewed automation scheduler could later feed approved
manifest filenames to this runner via a scoped job queue, without granting
the Opera browser worker general shell execution privileges. Never reuse
Google session cookies or Agent 1 credentials for local file access.
