"""Offline real-FFmpeg + mock-GCS safety tests; no cloud calls."""
import importlib.util
import json
import shutil
import sys
import types
import unittest
from unittest.mock import patch
from pathlib import Path

# The real Cloud Run image includes pinned google-cloud-storage; stub it locally.
client_module = types.ModuleType('google')
cloud_module = types.ModuleType('google.cloud')
storage_module = types.ModuleType('google.cloud.storage')
cloud_module.storage = storage_module
client_module.cloud = cloud_module
sys.modules.setdefault('google', client_module)
sys.modules.setdefault('google.cloud', cloud_module)
sys.modules.setdefault('google.cloud.storage', storage_module)

here = Path(__file__).parent
spec = importlib.util.spec_from_file_location('gcs_persist_smoke', here / 'gcs_persist_smoke.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class FakeBlob:
    def __init__(self, key, objects):
        self.key = key
        self.objects = objects
        self.metadata = {}
    def upload_from_filename(self, filename, *, content_type, if_generation_match):
        assert if_generation_match == 0 and content_type == 'video/mp4'
        assert self.key not in self.objects
        self.objects[self.key] = (Path(filename).read_bytes(), self.metadata)
    def upload_from_string(self, text, *, content_type, if_generation_match):
        assert if_generation_match == 0 and content_type == 'application/json'
        assert self.key not in self.objects
        self.objects[self.key] = (text.encode(), None)

class FakeBucket:
    def __init__(self, objects): self.objects = objects
    def blob(self, key): return FakeBlob(key, self.objects)

class FakeClient:
    def __init__(self): self.objects = {}
    def bucket(self, bucket):
        assert bucket == module.BUCKET
        return FakeBucket(self.objects)

class PersistentExportTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),
                         'FFmpeg/ffprobe not installed in Cloud Shell; live Cloud Run FFmpeg test already passed')
    def test_real_ffmpeg_and_mock_private_bucket(self):
        fake=FakeClient()
        report=module.render_and_upload(client=fake)
        self.assertEqual(report['frames'],125)
        self.assertAlmostEqual(report['duration_seconds'],5,delta=.05)
        self.assertEqual(report['codec'],'h264')
        self.assertFalse(report['published'])
        self.assertEqual(set(fake.objects),{module.VIDEO_KEY,module.REPORT_KEY})
        data, metadata =fake.objects[module.VIDEO_KEY]
        self.assertEqual(metadata['sha256'],report['sha256'])
        self.assertEqual(report['bytes'],len(data))
        metadata_report=json.loads(fake.objects[module.REPORT_KEY][0])
        self.assertEqual(metadata_report['sha256'], report['sha256'])
        with self.assertRaises(AssertionError):
            module.render_and_upload(client=fake)
    def test_private_gcs_export_contract_without_local_ffmpeg(self):
        # Cloud Shell need not have FFmpeg: the Cloud Run image contains it.
        # This test still validates GCS create-only uploads, metadata and checksum.
        fake=FakeClient()
        def fake_encoder(argv):
            self.assertEqual(argv[0], 'ffmpeg')
            self.assertIn('testsrc2=size=720x1280:rate=25', argv)
            Path(argv[-1]).write_bytes(b'fixture-only-not-a-real-video')
            return ''
        fake_probe={
            'codec':'h264', 'width':720, 'height':1280,
            'fps':25, 'frames':125, 'duration_seconds':5.0,
            'bytes':len(b'fixture-only-not-a-real-video'),
        }
        with patch.object(module, 'verify_video', return_value=fake_probe) as probe:
            report=module.render_and_upload(client=fake, command_runner=fake_encoder)
            self.assertEqual(probe.call_count,1)
        self.assertEqual(report['sha256'], __import__('hashlib').sha256(
            b'fixture-only-not-a-real-video').hexdigest())
        self.assertEqual(set(fake.objects), {module.VIDEO_KEY, module.REPORT_KEY})
        video, metadata=fake.objects[module.VIDEO_KEY]
        self.assertEqual(len(video), report['bytes'])
        self.assertEqual(metadata['published'], 'false')
        self.assertEqual(metadata['content-approval'], 'smoke-only')
        self.assertFalse(report['published'])
        self.assertFalse(report['public'])
        self.assertTrue(report['no_real_footage'])
        with patch.object(module, 'verify_video', return_value=fake_probe):
            with self.assertRaises(AssertionError, msg='Existing objects must not be overwritten'):
                module.render_and_upload(client=fake, command_runner=fake_encoder)

    def test_distinct_output_keys(self):
        self.assertNotEqual(module.VIDEO_KEY,module.REPORT_KEY)
        self.assertTrue(module.VIDEO_KEY.startswith('smoke/'))
        self.assertTrue(module.REPORT_KEY.endswith('.json'))

if __name__=='__main__': unittest.main()
