#!/usr/bin/env python3
"""Isolated V7 auto Commons source validation and true FFmpeg audiovisual E2E."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
sys.path.insert(0,str(HERE.parent/"v7-cinema"))
import ffmpeg_v6_adapter as ffmpeg
import v7_verified_source as source
from ffmpeg_v7_cinema import finish

ORIG="https://commons.wikimedia.org/wiki/File:Fixture_Sunrise.wav"
MEDIA="https://upload.wikimedia.org/wikipedia/commons/b/b1/Fixture_Sunrise.wav"
LIC="https://creativecommons.org/licenses/by/4.0/"

def track(license_name="by"):
    return {"source":"Openverse","id":"a"*32,"title":"Fixture Sunrise",
        "creator":"Test Artist","license":license_name,"license_url":LIC,
        "original_source_page":ORIG,"source_media_url":MEDIA}

def meta(audio:bytes,license_name="CC BY 4.0",artist="Test Artist",restriction=""):
    return {"query":{"pages":{"123":{"title":"File:Fixture Sunrise.wav",
        "imageinfo":[{"mediatype":"AUDIO","mime":"audio/wav","size":len(audio),
          "url":MEDIA,"extmetadata":{
            "LicenseShortName":{"value":license_name},
            "LicenseUrl":{"value":LIC},
            "Artist":{"value":artist},
            "Restrictions":{"value":restriction}}}]}}}}

class FakeResponse:
    def __init__(self,data:bytes,url:str):
        self.raw=data;self.url=url;self.headers={"Content-Length":str(len(data))}
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def read(self,n=-1):return self.raw[:n]
    def geturl(self):return self.url

def server(data:bytes,payload=None,redirect=False):
    doc=json.dumps(payload or meta(data)).encode()
    def respond(req,timeout=20):
        url=req.full_url
        if url.startswith("https://commons.wikimedia.org/w/api.php?"):
            return FakeResponse(doc,url)
        if url==MEDIA:
            return FakeResponse(data,"https://attacker.invalid/redirect" if redirect else url)
        raise AssertionError("unknown URL: "+url)
    return respond

class AutomatedSourceUnit(unittest.TestCase):
    def test_cc_by_has_attribution_and_live_same_licensing(self):
        with tempfile.TemporaryDirectory() as root:
            payload=b"not real audio"*120
            result=source._source_meta(track(),opener=server(payload))
            self.assertEqual(result["license"],"by")
            self.assertEqual(result["creator"],"Test Artist")

    def test_noncommercial_sharealike_conflict_must_block(self):
        for lic in ("CC BY-SA 4.0","CC BY-NC 4.0","All rights reserved"):
            with self.subTest(lic=lic), self.assertRaises(source.AutoLicenseBlocked):
                source._source_meta(track(),opener=server(b"a"*3000,meta(b"a"*3000,lic)))

    def test_disagreement_between_catalog_and_original_blocks(self):
        with self.assertRaises(source.AutoLicenseBlocked):
            source._source_meta(track(license_name="cc0"),opener=server(b"a"*3000))

    def test_missing_creator_or_explicit_source_restriction_blocks(self):
        for payload in (meta(b"a"*3000,artist=""),
                        meta(b"a"*3000,restriction="copyright violation")):
            with self.subTest(payload=payload),self.assertRaises(source.AutoLicenseBlocked):
                source._source_meta(track(),opener=server(b"a"*3000,payload))

    def test_no_arbitrary_redirect_hosts(self):
        with self.assertRaises(source.AutoLicenseBlocked):
            source._source_meta({**track(),"original_source_page":"https://evil.invalid/Track"},opener=server(b"a"*3000))
        with self.assertRaises(source.AutoLicenseBlocked):
            source._source_meta({**track(),"source_media_url":"https://evil.invalid/payload.mp3"},opener=server(b"a"*3000))

    def test_download_redirect_fails_and_leaves_no_music(self):
        with tempfile.TemporaryDirectory() as folder:
            payload=b"a"*4096
            with self.assertRaises(source.AutoLicenseBlocked):
                source.admit(track(),Path(folder),3,opener=server(payload,redirect=True),
                             probe=lambda *a,**k:{"duration":5})
            self.assertEqual(list(Path(folder).iterdir()),[])

    def test_tampered_size_or_short_track_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            payload=b"a"*4096
            with self.assertRaises(source.AutoLicenseBlocked):
                source.admit(track(),Path(folder),8,opener=server(payload),
                             probe=lambda *a,**k:{"duration":3})
            self.assertEqual(list(Path(folder).iterdir()),[])

class RealAudioEndToEnd(unittest.TestCase):
    def test_auto_source_verification_to_ffmpeg_mix_master_audiovideo(self):
        with tempfile.TemporaryDirectory(prefix="v7-auto-source-private-qa-") as td:
            work=Path(td)
            song=work/"fixture.wav";video=work/"source.mp4";out=work/"finished.mp4"
            # Only a temporary test tone, never a released composition.
            subprocess.run(["ffmpeg","-y","-hide_banner","-loglevel","error",
                "-f","lavfi","-i","sine=frequency=390:sample_rate=48000:duration=5",
                "-c:a","pcm_s16le",str(song)],check=True,timeout=45)
            content=song.read_bytes()
            subprocess.run(["ffmpeg","-y","-hide_banner","-loglevel","error",
                "-f","lavfi","-i","testsrc2=size=480x270:rate=24:duration=5",
                "-f","lavfi","-i","sine=frequency=190:sample_rate=48000:duration=5",
                "-c:v","libx264","-preset","ultrafast","-pix_fmt","yuv420p",
                "-c:a","aac","-shortest",str(video)],check=True,timeout=60)
            admission=source.admit(track(),work,3,
                opener=server(content),probe=ffmpeg.probe)
            self.assertTrue(admission["rights"]["automatic_source_verified"])
            self.assertFalse(admission["rights"]["human_verified"])
            self.assertIn("Test Artist",admission["provenance"]["credit_text"])
            self.assertEqual(admission["sha256"],hashlib.sha256(content).hexdigest())
            spec={"workdir":str(work),"source":str(video),"source_sha256":ffmpeg.sha256(video),
                "output":str(out),"width":480,"height":270,"fps":24,
                "template_id":"wellness-cinema","hook":"FIXTURE QA",
                "cuts":[{"start":.2,"seconds":1.4},{"start":2.0,"seconds":1.4}],
                "operations":[[],[]],
                "music":str(admission["path"]),"music_sha256":admission["sha256"],
                "music_rights":admission["rights"],"v7_preset":"clean-editorial",
                "published":False,"owner_approval":False}
            receipt=finish(spec)
            self.assertTrue(receipt["rendered"])
            self.assertTrue(receipt["music_mixed"])
            self.assertTrue(receipt["audio_stream_verified"])
            self.assertTrue(receipt["video_stream_verified"])
            self.assertTrue(receipt["full_decode_passed"])
            self.assertFalse(receipt["published"])
            self.assertEqual(receipt["sha256"],ffmpeg.sha256(out))

if __name__=="__main__":
    unittest.main(verbosity=2)
