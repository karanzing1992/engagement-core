"""HTTP-level tests for private chunking and queued multi-clip FFmpeg jobs."""
from __future__ import annotations
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest

os.environ.setdefault("REEL_DATA_ROOT", str(Path(tempfile.gettempdir()) / 'moksha-private-api-tests'))
os.environ['REEL_ENGINE_TOKEN'] = 'fixture-private-token-' + 'a' * 48

# During isolated local testing, the project-wide modules may not be checked out.
# CI runs these tests with the actual geo_policy and verified_logo modules.
import sys, types
try:
    import geo_policy
except ModuleNotFoundError:
    geo_policy = types.ModuleType('geo_policy')
    class GeoPolicyError(ValueError): pass
    def validate_render_config(cfg):
        if cfg.get('editorial_region') not in ('Goa', 'India'):
            raise GeoPolicyError('Wrong region')
        return {'editorial_region':cfg['editorial_region'],'geography_gate':'passed'}
    geo_policy.GeoPolicyError = GeoPolicyError
    geo_policy.validate_render_config = validate_render_config
    sys.modules['geo_policy'] = geo_policy
try:
    import verified_logo
except ModuleNotFoundError:
    verified_logo = types.ModuleType('verified_logo')
    verified_logo.overlay_verified_logo = lambda source, dest, **kw: None
    sys.modules['verified_logo'] = verified_logo

from fastapi import FastAPI
from fastapi.testclient import TestClient
from chunked_ingest import UploadStore
import upload_api
import multi_api


class PrivateApiTests(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.root = Path(self.t.name)
        self.store = UploadStore(self.root / 'uploads', max_file_bytes=300_000_000, chunk_bytes=4096)
        upload_api.STORE = self.store
        multi_api.STORE = self.store
        multi_api.JOBS = self.root / 'jobs'; multi_api.JOBS.mkdir()
        multi_api.VIDEOS = self.root / 'outputs'; multi_api.VIDEOS.mkdir()
        self.app = FastAPI()
        self.app.include_router(upload_api.router)
        self.app.include_router(multi_api.router)
        self.client = TestClient(self.app)
        self.headers = {'Authorization':'Bearer ' + os.environ['REEL_ENGINE_TOKEN']}

    def _upload(self, content: bytes, name: str = 'goa.mp4') -> str:
        digest = hashlib.sha256(content).hexdigest()
        info = self.client.post('/v1/uploads',json={'name':name,'size':len(content),
                'sha256':digest,'mime_type':'video/mp4'},headers=self.headers)
        self.assertEqual(info.status_code, 200, info.text)
        value=info.json(); uid=value['id']
        for i in range(value['total_chunks']):
            piece=content[i*value['chunk_bytes']:(i+1)*value['chunk_bytes']]
            answer=self.client.put(f'/v1/uploads/{uid}/chunks/{i}', content=piece,
                headers={**self.headers,'X-Chunk-SHA256':hashlib.sha256(piece).hexdigest()})
            self.assertEqual(answer.status_code,200,answer.text)
        finish=self.client.post(f'/v1/uploads/{uid}/complete',headers=self.headers)
        self.assertEqual(finish.status_code,200,finish.text)
        return uid

    def _media(self,name:str,with_audio:bool=False) -> Path:
        dest=self.root/name
        cmd=['ffmpeg','-v','error','-y','-f','lavfi','-i',
             'color=c=0x638171:s=180x320:r=12']
        if with_audio:cmd+=['-f','lavfi','-i','sine=frequency=210:sample_rate=44100']
        cmd+=['-t','5.5','-c:v','libx264','-preset','ultrafast','-pix_fmt','yuv420p']
        if with_audio:cmd+=['-c:a','aac']
        cmd.append(str(dest))
        subprocess.run(cmd,check=True,timeout=45)
        return dest

    def test_unauthenticated_requests_are_denied(self):
        self.assertEqual(self.client.post('/v1/uploads',json={}).status_code,401)
        self.assertEqual(self.client.get('/v1/uploads/'+'0'*32).status_code,401)
        self.assertEqual(self.client.post('/v1/render/multi',json={}).status_code,401)
        self.assertEqual(self.client.get('/v1/render/multi/'+'0'*32).status_code,401)
        self.assertEqual(self.client.get('/v1/render/multi/'+'0'*32+'/video').status_code,401)

    def test_weak_missing_server_secret_fails_closed(self):
        old = os.environ.pop('REEL_ENGINE_TOKEN')
        try:
            self.assertEqual(self.client.post('/v1/uploads',json={}).status_code,503)
        finally:
            os.environ['REEL_ENGINE_TOKEN']=old

    def test_chunk_http_resumes_and_requires_digest(self):
        data=b'Goa calm waves'*430
        sha=hashlib.sha256(data).hexdigest()
        st=self.client.post('/v1/uploads',json={'name':'goa.mp4','size':len(data),
               'sha256':sha,'mime_type':'video/mp4'},headers=self.headers).json()
        uid=st['id']; chunk=data[:4096]
        bad=self.client.put(f'/v1/uploads/{uid}/chunks/0',content=chunk,
                headers={**self.headers,'X-Chunk-SHA256':'0'*64})
        self.assertEqual(bad.status_code,422)
        ok=self.client.put(f'/v1/uploads/{uid}/chunks/0',content=chunk,
                headers={**self.headers,'X-Chunk-SHA256':hashlib.sha256(chunk).hexdigest()})
        self.assertEqual(ok.status_code,200)
        again=self.client.put(f'/v1/uploads/{uid}/chunks/0',content=chunk,
                headers={**self.headers,'X-Chunk-SHA256':hashlib.sha256(chunk).hexdigest()})
        self.assertTrue(again.json()['already_received'])
        self.assertEqual(self.client.post(f'/v1/uploads/{uid}/complete',headers=self.headers).status_code,409)
        self.assertEqual(self.client.get(f'/v1/uploads/{uid}',headers=self.headers).json()['received_chunks'],[0])

    def test_multiclip_private_async_render_and_poll(self):
        original0=self._media('clip1.mp4');original1=self._media('clip2.mp4',True)
        ids=[self._upload(original0.read_bytes(),name='clip1.mp4'),
             self._upload(original1.read_bytes(),name='clip2.mp4')]
        evidence={'origin':'owned','capture_country':'India','capture_region':'Goa',
          'source_url':'https://drive.google.com/file/d/example/goa',
          'location_evidence_url':'https://drive.google.com/file/d/example/goa',
          'verification_status':'human_verified','verified_by':'Human tester'}
        body={'asset_ids':ids,'cuts':[{'source_index':0,'start':0,'end':5},
              {'source_index':1,'start':0,'end':5}], 'duration_seconds':10,
              'width':360,'height':640,'fps':24,'config':{'brand':'generic',
              'editorial_region':'Goa','source_provenance':[evidence,evidence]}}
        created=self.client.post('/v1/render/multi',json=body,headers=self.headers)
        self.assertEqual(created.status_code,202,created.text)
        job=created.json()['job_id']
        last=None
        for i in range(60):
            answer=self.client.get(f'/v1/render/multi/{job}',headers=self.headers)
            self.assertEqual(answer.status_code,200)
            last=answer.json()
            if last['status'] in ('completed','failed'):break
            time.sleep(.2)
        self.assertEqual(last['status'],'completed',last)
        self.assertFalse(last['publishing_enabled'])
        self.assertNotIn('request',last)
        result=self.client.get(f'/v1/render/multi/{job}/video',headers=self.headers)
        self.assertEqual(result.status_code,200)
        self.assertGreater(len(result.content),2000)


if __name__ == '__main__':unittest.main()