#!/usr/bin/env python3
"""Owner-only FFmpeg synthetic source -> private Cloudflare KV -> FFmpeg QA."""
import argparse
import os
import subprocess
from pathlib import Path
import runner


def main(job_id,*,live_models=False,groq_only=False):
 if os.environ.get("GITHUB_EVENT_NAME")!="issues" or os.environ.get("GITHUB_ACTOR")!="karanzing1992":
  raise RuntimeError("Owner-only synthetic QA event required")
 if not runner.GATEWAY.startswith("https://mad-v7-kv-private-beta."):
  raise RuntimeError("Unrecognized private KV test destination")
 work=Path(os.environ["RUNNER_TEMP"])/("mad-v6-seed-"+job_id)
 work.mkdir(mode=0o700,parents=True,exist_ok=True)
 source=work/"test-matte.mp4"
 try:
  subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y",
       "-f","lavfi","-i","testsrc2=size=320x180:rate=24:duration=4",
       "-c:v","libx264","-preset","ultrafast","-crf","34","-pix_fmt","yuv420p",
       "-an",str(source)],check=True,timeout=90)
  if not source.exists() or source.stat().st_size>262144 or source.stat().st_size<1024:
   raise RuntimeError("Synthetic FFmpeg source violates private 256 KiB cap")
  result=runner.call("/internal/v6/jobs/"+job_id+"/seed",runner.token(),
       data=source.read_bytes(),digest=runner.sha(source))
  if result.get("synthetic_only") is not True or result.get("source_sha256")!=runner.sha(source):
   raise RuntimeError("Private QA source verification mismatch")
  print("MAD_V6_SYNTHETIC_SOURCE_SEEDED_TO_KV",job_id)
 finally:
  source.unlink(missing_ok=True)
 if groq_only:
  os.environ["GEMINI_INFERENCE_OWNER_APPROVED"]="false"
  os.environ["GEMINI_PROJECT_FREE_TIER_VERIFIED"]="false"
 runner.run(job_id,fixture=not live_models)

if __name__=="__main__":
 ap=argparse.ArgumentParser();ap.add_argument("--job-id",required=True)
 ap.add_argument("--live-models",action="store_true")
 ap.add_argument("--groq-only",action="store_true")
 args=ap.parse_args();main(args.job_id,live_models=args.live_models or args.groq_only,groq_only=args.groq_only)
