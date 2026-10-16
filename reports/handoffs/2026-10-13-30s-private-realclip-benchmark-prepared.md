# Real-video 30-second CPU benchmark — private technical handoff (13 October 2026)

**State: CODE + LOCAL TEST ONLY. NOT RUN IN GOOGLE CLOUD.** Do not record as a deployed benchmark or publish videos.

## Environment

- GCP `focused-premise-510518-g6`, region `asia-south1`.
- Existing private source/output: `reel-pilot-source-focused-premise-510518-g6-pilot2` and `reel-pilot-drafts-focused-premise-510518-g6-pilot2`.
- Disposable **new** benchmark job name: `reel-cpu-30s-benchmark`, configured for 1 vCPU, 1 GiB RAM, 600s deadline, one task, zero retries, no scheduler; never edit `reel-engine-cpu-pilot`.
- Existing image: `asia-south1-docker.pkg.dev/focused-premise-510518-g6/reel-pilot-images/reel-engine-cpu-pilot:source-v1`.
- Existing least-privilege Reel worker: `reel-pilot-worker@focused-premise-510518-g6.iam.gserviceaccount.com`.

## Source availability / provenance

Connected Google Drive video search and accessible Moksha media folders yielded no accessible source video. **Do not call this a Google Drive test.** Use the user's prior **ChatGPT Library upload** `1000051316.mp4` strictly for private engineering benchmark: 69.797778 seconds, 720×1280, H.264 + audio, 20,501,679 bytes, SHA256 `398c1b5b16854266e26fcb9874f19589771292982174cb7b47e2cf499949052d`. It is **not independently certified as filmed in Goa, cleared for publication, or approved for Moksha branding**.

A separate local conversation artifact (NOT automatically mounted in Google Cloud Shell) contains the user-approved test video and fully checked runnable code:

`reel_cloudrun_30s_benchmark.zip` (20 MB). Archive SHA256 (verified in sandbox): `eb3b80ea2e3aa6803defafd9d88e2d8b4181f784809f7b86f6feb75d96180228`.

## Actual implementation (attached ZIP, not yet landed in GitHub)

- `benchmark_cloudrun_30s.py`: GCS download time, SHA256, ffprobe, standalone 30s video decode-to-null, matching FFmpeg filters/ fades and audio, `libx264` at CRF22 for `veryfast` and `ultrafast`, concat faststart remux, output validation, SHA256 and *private create-only* GCS MP4+JSON uploads. Logs `BENCHMARK_PRESET` and `BENCHMARK_COMPLETE`.
- `run_cloud_30s_benchmark.sh`: `--check` read-only, `--stage` upload source exactly once and SHA-readback, `--run` create and run separate manual-only benchmark job after strict guard checks, `--verify` independently download outputs and compare report bytes/hashes. CLI GCS uploads use `--if-generation-match=0`.
- `test_benchmark_local.py`: real local FFmpeg execution with fake private GCS interface and an overwrite refusal test.
- `README.md`, original source MP4 and local baseline report.

## Measured local validation (not cloud timing)

Real 30-second 720×1280 H.264 with audio rendered twice, checksum-verified against fake GCS. `python -m unittest -v test_benchmark_local.py`: **1 test PASS**, including both encoders, final 750 frames and refusal to overwrite. `bash -n`: PASS. Offline `--check` with simulated gcloud: PASS after handling Google `NOT_FOUND` missing-job error.

Earlier unrestricted local baseline (different process/hardware, not Cloud Run): veryfast 9.200s/~13.1 MB, ultrafast 3.412s/~36.3 MB. Also a prior *single-affinity-CPU proxy* veryfast run ~23.071s. Do **not** use these as Cloud Run metrics.

## Next exact action and gate

Authorized owner must upload the single ZIP into existing Cloud Shell, `unzip`, and run `bash run_cloud_30s_benchmark.sh --check`, then `--stage`, then `--run` exactly once. It may consume billing/trial credits. The browser Agent 2 has only Google Cloud Console, no logged-in Cloud Shell tab, cannot access the uploaded Library MP4 or transfer arbitrary local binary files; restricted native commands remain blocked. Do not circumvent.

Only after `--run` succeeds: inspect exact GCP execution task history and logs, GCS object metadata and hashes, worker timing JSON, source download, decode-only, encode+filter, remux, upload, total worker time, cold-start/queue and GCP billing. Compare speed/size quality before changing production presets. No live execution or Master Route B deployed claim until independently verified.

## Isolation and rollback

Use only isolated `benchmark-inputs/benchmark-lib-1000051316-20261013-01/` source and `benchmarks/benchmark-lib-1000051316-20261013-01/` output prefixes; never overwrite or delete any unrelated object. Do not execute `reel-engine-cpu-pilot`, register scheduling, create a public URL, or publish video. Keep real-source rights audit and publishing approval separate.
