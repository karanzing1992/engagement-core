#!/usr/bin/env python3
"""V6 native FilmCraft adapter isolation, rights and effect admission tests."""
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

HERE = Path(__file__).resolve().parent
FILE = HERE.parent.parent / "services" / "reel-engine" / "filmcraft_v6_adapter.py"
SPEC = importlib.util.spec_from_file_location("filmcraft_v6_adapter", FILE)
EDITOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EDITOR)


class FilmCraftV6Tests(unittest.TestCase):
    def test_valid_edl_with_stable_effect_id(self):
        cuts = [{"start": 0, "seconds": 3}]
        ops = [[{"id": "effect1", "name": "title", "parameters": {"text": "Moksha"}}]]
        self.assertEqual(EDITOR.validate_edl(cuts, ops, 10), 3)

    def test_effect_id_omission_duplication_and_unsupported_effect_blocked(self):
        cuts = [{"start": 0, "seconds": 3}]
        base = {"id": "e1", "name": "title", "parameters": {"text": "Moksha"}}
        for actions in ([{"name": "title", "parameters": {"text": "Moksha"}}],
                        [base, base],
                        [{"id": "e1", "name": "imaginary_effect"}]):
            with self.assertRaises(EDITOR.FilmCraftError):
                EDITOR.validate_edl(cuts, [actions], 10)

    def test_reject_guest_source_without_rights_before_editor_start(self):
        with TemporaryDirectory() as folder:
            wd = Path(folder)
            src = wd / "source.mp4"
            src.write_bytes(b"x" * 2048)
            with self.assertRaisesRegex(EDITOR.FilmCraftError, "rights"):
                EDITOR.render(cli="/not/installed/filmcraft", workdir=wd,
                              output=wd / "out.mp4", source=src)
            with self.assertRaisesRegex(EDITOR.FilmCraftError, "SHA256"):
                EDITOR.render(cli="/not/installed/filmcraft", workdir=wd,
                              output=wd / "out.mp4", source=src,
                              source_rights_cleared=True, source_sha256="0"*64)

    def test_fixed_native_stage_emitted_before_rights_rejection(self):
        with TemporaryDirectory() as folder:
            wd=Path(folder)
            src=wd/"source.mp4"
            src.write_bytes(b"x"*2048)
            stages=[]
            with self.assertRaisesRegex(EDITOR.FilmCraftError,"rights"):
                EDITOR.render(cli="/not/installed/filmcraft",workdir=wd,
                              output=wd/"out.mp4",source=src,on_stage=stages.append)
            self.assertEqual(stages,["filmcraft_source_preflight"])

    def test_reject_unverified_music_license_before_editor_start(self):
        with TemporaryDirectory() as folder:
            wd = Path(folder)
            track = wd / "song.wav"
            track.write_bytes(b"x" * 4096)
            with self.assertRaisesRegex(EDITOR.FilmCraftError, "license"):
                EDITOR.render(cli="/not/installed/filmcraft", workdir=wd,
                              output=wd / "out.mp4", music=track)
            fake = {"human_verified": True, "license": "CC BY-NC",
                    "creator": "https://example.org/author",
                    "original_source_url": "https://example.org/song",
                    "original_license_url": "https://example.org/license"}
            with self.assertRaisesRegex(EDITOR.FilmCraftError, "license"):
                EDITOR.render(cli="/not/installed/filmcraft", workdir=wd,
                              output=wd / "out.mp4", music=track, music_rights=fake)

    def test_filmcraft_is_only_renderer_in_source(self):
        source = FILE.read_text(encoding="utf-8")
        self.assertNotIn('subprocess.run(["ffmpeg"', source)
        self.assertNotIn('subprocess.run(["ffprobe"', source)
        self.assertIn('"creative_complete":False', source)
        self.assertIn('"output_verified":False', source)


if __name__ == "__main__":
    unittest.main()
