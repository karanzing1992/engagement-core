"""Isolated synthetic tests of autonomous job locking, recovery and fail-closed gates.
No remote model calls, no deployment, no production data.
"""
import argparse,fcntl,hashlib,json,shutil,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent))
import orchestrator
from core import gate,write,treehash
SOURCE=Path.home()/'.local/share/dev-design-rag-v1/certification/uiux-v2-andaz-fixture-20261110'

class AutonomousRecovery(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.w=Path(self.temp.name)/'fixture';self.w.mkdir();shutil.copytree(SOURCE/'site',self.w/'site')
  self.s=json.loads((SOURCE/'engine-state.json').read_text())
  self.s['site_sha256']=treehash(self.w/'site')
  write(self.w/'engine-state.json',self.s)
  self.args=argparse.Namespace(workspace=self.w,baseline=None,project=None,prompt=None,
   target='engine-smoke.html',task='isolated test',pages='',vision_model='qwen3-vl:2b-instruct',vision_timeout=1)
 def test_01_concurrent_lock_fail_closed(self):
  with (self.w/'.orchestrator.lock').open('a+') as locked:
   fcntl.flock(locked.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
   with self.assertRaisesRegex(orchestrator.Blocked,'JOB_ALREADY_RUNNING'):
    orchestrator.runner(self.args)
  self.assertEqual(self.s['site_sha256'],treehash(self.w/'site'))
 def test_02_forged_crashed_agent_receipt_rejected(self):
  self.s['stage_status']['autonomous_implementation']='PENDING';write(self.w/'engine-state.json',self.s)
  seed='uiuxv2-'+hashlib.sha256((self.s['baseline_sha256']+self.args.target+self.args.task).encode()).hexdigest()[:15]
  task=self.w/'tasks'/(seed+'-a1');task.mkdir(parents=True)
  write(task/'receipt.json',{'status':'PASS','output_site_sha256':'f'*64})
  with self.assertRaisesRegex(orchestrator.Blocked,'AGENT_RECEIPT_SITE_HASH_MISMATCH'):
   orchestrator.runner(self.args)
  log=json.loads((self.w/'reports/orchestration.json').read_text())
  self.assertEqual(log['state'],'BLOCKED')
  self.assertEqual(self.s['site_sha256'],treehash(self.w/'site'))
 def test_03_transient_retry_capped_at_two(self):
  self.s['stage_status']['autonomous_concept_and_design']='PENDING'
  write(self.w/'engine-state.json',self.s)
  with patch.object(orchestrator,'concept',side_effect=ValueError('429 THROTTLE')) as stub:
   with patch.object(orchestrator.time,'sleep',return_value=None):
    with self.assertRaisesRegex(orchestrator.Blocked,'429 THROTTLE'):
     orchestrator.runner(self.args)
  self.assertEqual(stub.call_count,2)
  log=json.loads((self.w/'reports/orchestration.json').read_text())
  self.assertEqual([x['status'] for x in log['events']],['RUNNING','RETRY','RUNNING','BLOCKED'])
 def test_04_missing_evidence_denies_preview(self):
  r=gate(self.w,'preview')
  self.assertEqual(r['status'],'BLOCKED')
  self.assertFalse(r['production_release_allowed'])
  self.assertIn('INDEPENDENT_ARTISTIC_RECEIPT_MISSING',r['missing'])
if __name__=='__main__':unittest.main(verbosity=2)
