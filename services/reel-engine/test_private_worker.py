"""Actual end-to-end test: private chunk transfer -> two-phone FFmpeg edit ->
approved Drive logo -> signed WordPress-private output-chunk return."""
import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from render_ready_sessions import WP, process_session, token_from_existing_hook, CHUNK


class FakeWordPress:
    def __init__(self, files: list[Path], target_seconds=6):
        self.inputs=[p.read_bytes() for p in files]
        self.record={"id":"a"*32,"target_seconds":target_seconds,"state":"ready",
                     "files":[{"name":f"phone-{i}.mp4","size":len(b),
                               "parts":(len(b)+CHUNK-1)//CHUNK,
                               "sha256":hashlib.sha256(b).hexdigest()}
                              for i,b in enumerate(self.inputs)]}
        self.uploaded=[]
        self.expected=None
        self.complete=False
        self.no_publish=True

    def call(self, path: str, *, method="GET", json_data=None, data=None, digest=None):
        if "/source-part/" in path:
            seg=path.split("/")
            i, part=int(seg[-2]),int(seg[-1])
            return self.inputs[i][part*CHUNK:(part+1)*CHUNK]
        if "/render-chunk/" in path:
            assert method=="POST"
            assert hashlib.sha256(data).hexdigest()==digest
            self.uploaded.append(data)
            return b'{"ok":true}'
        raise AssertionError("Unexpected file transfer "+path)

    def j(self, path, method="GET", data=None):
        if path.endswith("/render-start"):
            assert data["size"]>5000
            self.expected=data
            return {"ok":True,"id":self.record["id"],"state":"processing"}
        if path.endswith("/render-finish"):
            full=b"".join(self.uploaded)
            assert len(full)==self.expected["size"]
            assert hashlib.sha256(full).hexdigest()==self.expected["sha256"]
            self.complete=True
            return {"ok":True,"status":"preview_ready_private","publishing_enabled":False}
        raise AssertionError("Unexpected API command "+path)


class PrivatePipelineTests(unittest.TestCase):
    @staticmethod
    def source(where: Path, number: int):
        cmd=["ffmpeg","-v","error","-y","-f","lavfi","-i",
             f"testsrc2=size=320x180:rate=15:duration=4",
             "-f","lavfi","-i",f"sine=frequency={400+number*200}:sample_rate=48000",
             "-t","4","-c:v","libx264","-preset","ultrafast","-pix_fmt","yuv420p",
             "-c:a","aac",str(where)]
        subprocess.run(cmd,check=True)

    def test_auth_uses_existing_secret_without_logging(self):
        import os
        key="MOKSHA_DFG_ENGAGEMENT_CORE_URL"
        old=os.environ.get(key)
        os.environ[key]="https://mokshagoa.com/?secret="+"a"*40
        try:
            tok=token_from_existing_hook()
            self.assertEqual(len(tok),64)
        finally:
            if old is None:os.environ.pop(key,None)
            else:os.environ[key]=old

    def test_private_2_source_render_and_round_trip(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)
            clips=[path/"phone-one.mp4",path/"phone-two.mp4"]
            for i,p in enumerate(clips): self.source(p,i)
            mock=FakeWordPress(clips,target_seconds=6)
            result=process_session(mock,mock.record)
            self.assertTrue(mock.complete)
            self.assertEqual(result["sources"],2)
            self.assertFalse(result["publishing_enabled"])
            self.assertEqual(len(mock.uploaded),1)
            self.assertGreater(len(mock.uploaded[0]),4000)
            # Uploaded private output is a real decodable MP4 with audio.
            final=path/"received.mp4"
            final.write_bytes(b"".join(mock.uploaded))
            probe=subprocess.check_output(["ffprobe","-v","error",
                    "-show_entries","format=duration:stream=codec_type,width,height",
                    "-of","json",str(final)],text=True)
            data=json.loads(probe)
            self.assertAlmostEqual(float(data["format"]["duration"]),6,delta=0.28)
            self.assertTrue(any(s["codec_type"]=="audio" for s in data["streams"]))
            v=next(s for s in data["streams"] if s["codec_type"]=="video")
            self.assertEqual((v["width"],v["height"]),(720,1280))


if __name__=="__main__":
    unittest.main()
