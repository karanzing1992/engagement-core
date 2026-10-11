from __future__ import annotations
import pathlib
import shutil
import subprocess
import tempfile
import unittest
from chunked_ingest import UploadError
from multiclip import assemble_multiclip, validate_timeline, media_info


def ff(*args):
    subprocess.run(['ffmpeg','-v','error','-y',*map(str,args)],check=True,timeout=70)


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg required')
class MultiClipTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=pathlib.Path(self.temp.name)
        self.first=self.root/'a.mp4';self.second=self.root/'b.mp4'
        ff('-f','lavfi','-i','color=c=0x123456:s=180x320:r=12',
           '-t','5.5','-c:v','libx264','-preset','ultrafast','-pix_fmt','yuv420p',self.first)
        ff('-f','lavfi','-i','color=c=0x448854:s=320x180:r=15',
           '-f','lavfi','-i','sine=frequency=280:sample_rate=48000',
           '-t','5.5','-c:v','libx264','-preset','ultrafast',
           '-pix_fmt','yuv420p','-c:a','aac',self.second)
        self.cuts=[{'source_index':0,'start':0,'end':5},
                   {'source_index':1,'start':0,'end':5}]

    def test_two_video_sources_mixed_as_portrait_with_audio(self):
        output=self.root/'finished.mp4'
        r=assemble_multiclip([self.first,self.second],self.cuts,output,self.root/'work',
                             duration=10,width=360,height=640,fps=24)
        self.assertAlmostEqual(r['output_duration'],10,delta=0.12)
        self.assertEqual(r['output_width'],360)
        self.assertTrue(media_info(output)['audio'])
        self.assertEqual(r['audio_source_index'],1)
        self.assertFalse(r['publishing_enabled'])

    def test_rejects_out_of_range_segment(self):
        bad=[self.cuts[0], {'source_index':1,'start':1,'end':6}]
        with self.assertRaisesRegex(UploadError,"past source"):
            validate_timeline([self.first,self.second],bad,duration=10,width=360,height=640,fps=24)

    def test_rejects_unauthorized_content_duration(self):
        with self.assertRaisesRegex(UploadError,"Timeline totals"):
            validate_timeline([self.first,self.second],self.cuts,duration=11,width=360,height=640,fps=24)

    def test_rejects_wrong_source_and_unsafe_resolution(self):
        cuts=[{'source_index':99,'start':0,'end':10}]
        with self.assertRaisesRegex(UploadError,"source index"):
            validate_timeline([self.first,self.second],cuts,duration=10,width=360,height=640,fps=24)
        with self.assertRaises(UploadError):
            validate_timeline([self.first,self.second],self.cuts,duration=10,width=1080,height=1080,fps=30)


if __name__=='__main__':unittest.main()