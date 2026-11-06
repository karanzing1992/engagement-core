#!/usr/bin/env python3
"""Owner-only signed GitHub synthetic FilmCraft -> Cloudflare KV -> FilmCraft smoke."""
import argparse
import os
from pathlib import Path
import runner
import filmcraft_v6_adapter as filmcraft

def main(job_id,*,live_models=False):
 if os.environ.get("GITHUB_EVENT_NAME")!="issues" or os.environ.get("GITHUB_ACTOR")!="karanzing1992":
  raise RuntimeError("Owner-only synthetic QA event required")
 if not runner.GATEWAY.startswith("https://mad-v6-kv-private-beta."):
  raise RuntimeError("Unrecognized private KV test destination")
 work=Path(os.environ["RUNNER_TEMP"])/("mad-v6-seed-"+job_id)
 work.mkdir(mode=0o700,parents=True,exist_ok=True)
 source=work/"test-matte.mp4"
 try:
  receipt=filmcraft.render(cli=os.environ["FILMCRAFT_CLI"],workdir=work,output=source,
    cuts=[{"start":0.,"seconds":4.,"source_index":0}],operations=[[]],
    hook="SYNTHETIC QA - NOT A GUEST",width=480,height=270,fps=24)
  if receipt.get("filmcraft_only") is not True or receipt.get("ffmpeg_invocations")!=0:
   raise RuntimeError("Native FilmCraft synthetic source not verified")
  if source.stat().st_size>262144:
   raise RuntimeError("Synthetic source exceeds private QA 256 KiB safety cap")
  result=runner.call("/internal/v6/jobs/"+job_id+"/seed",runner.token(),
       data=source.read_bytes(),digest=runner.sha(source))
  if result.get("synthetic_only") is not True or result.get("source_sha256")!=runner.sha(source):
   raise RuntimeError("Private QA source verification mismatch")
  print("MAD_V6_SYNTHETIC_SOURCE_SEEDED_TO_KV",job_id)
 finally:
  source.unlink(missing_ok=True)
 runner.run(job_id,fixture=not live_models)

if __name__=="__main__":
 ap=argparse.ArgumentParser();ap.add_argument("--job-id",required=True)
 ap.add_argument("--live-models",action="store_true")
 args=ap.parse_args();main(args.job_id,live_models=args.live_models)
