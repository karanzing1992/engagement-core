from __future__ import annotations

import io
import hashlib
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
from verified_logo import (
    BYTES, DRIVE_ID, MIRROR, SHA256, VerificationError,
    resolve_verified_logo, overlay_verified_logo,
)

ROOT = Path(__file__).resolve().parents[2]
LOGO_FILE = ROOT / "assets" / "brand" / "moksha-logo-source.jpg"
ORIGINAL = LOGO_FILE.read_bytes()


class FakeOpener:
    def __init__(self, *, wordpress=True, wordpress_image=True, corrupt_wp=False, invalid_manifest=False):
        self.wordpress = wordpress
        self.wordpress_image = wordpress_image
        self.corrupt_wp = corrupt_wp
        self.invalid_manifest = invalid_manifest
        self.visits = []

    def open(self, request, timeout=20):
        u = request.full_url
        self.visits.append(u)
        if "/wp-json/wp-control/v1/brand-assets/" in u:
            if not self.wordpress:
                raise OSError("WordPress temporary outage")
            manifest = {
                "ready": True, "brand": "moksha", "role": "official_full_logo",
                "drive_file_id": DRIVE_ID, "approved_sha256": SHA256,
                "variant": "original_gold_on_black", "allow_ai_recreation": False,
                "width": 737, "height": 681,
                "placement": "reel", "asset_url": "https://mokshagoa.com/wp-content/uploads/official.jpg",
            }
            if self.invalid_manifest:
                manifest["drive_file_id"] = "unapproved-drive-id"
            return io.BytesIO(__import__("json").dumps(manifest).encode())
        if "wp-content/uploads" in u:
            if not self.wordpress_image:
                raise OSError("Public logo CDN unavailable")
            return io.BytesIO(ORIGINAL[:-1] + b"\x00" if self.corrupt_wp else ORIGINAL)
        if u == MIRROR:
            return io.BytesIO(ORIGINAL)
        raise AssertionError("Unexpected untrusted URL: " + u)


class ResolverTests(unittest.TestCase):
    def test_pinned_original_integrity(self):
        self.assertEqual(len(ORIGINAL), BYTES)
        self.assertEqual(hashlib.sha256(ORIGINAL).hexdigest(), SHA256)

    def test_immutable_git_mirror_without_wordpress_auth(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"approved.jpg"
            fake=FakeOpener()
            info=resolve_verified_logo(p, opener=fake)
            self.assertEqual(info["source"],"approved_immutable_git_mirror")
            self.assertEqual(p.read_bytes(),ORIGINAL)
            self.assertEqual(fake.visits,[MIRROR])

    def test_preferred_wordpress_with_valid_manifest(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"approved.jpg"
            fake=FakeOpener()
            info=resolve_verified_logo(p,wp_token="a"*64,opener=fake)
            self.assertEqual(info["source"],"wordpress_verified")
            self.assertEqual(len(fake.visits),2)

    def test_wp_image_unreachable_uses_same_master_mirror(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"approved.jpg"
            fake=FakeOpener(wordpress_image=False)
            info=resolve_verified_logo(p,wp_token="a"*64,opener=fake)
            self.assertEqual(info["source"],"approved_immutable_git_mirror")
            self.assertEqual(p.read_bytes(),ORIGINAL)

    def test_wp_image_tampered_is_rejected_then_mirror_used(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"approved.jpg"
            fake=FakeOpener(corrupt_wp=True)
            info=resolve_verified_logo(p,wp_token="a"*64,opener=fake)
            self.assertEqual(info["source"],"approved_immutable_git_mirror")
            self.assertEqual(p.read_bytes(),ORIGINAL)

    def test_invalid_drive_manifest_never_falls_back(self):
        with tempfile.TemporaryDirectory() as d:
            fake=FakeOpener(invalid_manifest=True)
            with self.assertRaises(VerificationError):
                resolve_verified_logo(Path(d)/"approved.jpg",wp_token="a"*64,opener=fake)
            self.assertEqual(len(fake.visits),1)

    def test_corrupt_local_cache_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"approved.jpg"
            path.write_bytes(b"BAD")
            with self.assertRaises(VerificationError):
                resolve_verified_logo(path,opener=FakeOpener())

    def test_wrong_brands_and_outputs_refused(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"approved.jpg"
            for brand,placement in (("andaz","reel"),("moksha","ai-generated-transparent-mark")):
                with self.assertRaises(VerificationError):
                    resolve_verified_logo(p,brand=brand,placement=placement,opener=FakeOpener())

    def test_existing_verified_cache_survives_outage(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"approved.jpg"
            p.write_bytes(ORIGINAL)
            info=resolve_verified_logo(p,opener=FakeOpener(wordpress=False))
            self.assertEqual(info["source"],"previously_verified_cache")

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),"FFmpeg missing")
    def test_logo_overlay_on_short_private_video(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            source=root/"source.mp4"
            output=root/"branded.mp4"
            subprocess.run(["ffmpeg","-v","error","-y","-f","lavfi","-i","color=c=black:s=540x960:r=15",
                    "-f","lavfi","-i","sine=frequency=350:sample_rate=48000", "-t","3.5",
                    "-c:v","libx264","-preset","ultrafast","-pix_fmt","yuv420p","-c:a","aac",str(source)],check=True)
            cache=root/"approved"
            cache.mkdir()
            (cache/"moksha-approved-master.jpg").write_bytes(ORIGINAL)
            report=overlay_verified_logo(source,output,cache_dir=cache)
            self.assertGreater(output.stat().st_size,4000)
            self.assertGreaterEqual(report["applied_start_seconds"],1.5)
            self.assertFalse(report["publishing_enabled"])


if __name__ == "__main__":
    unittest.main(verbosity=2)