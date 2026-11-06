#!/usr/bin/env python3
"""V6 open music library legal/provenance regression tests (no media or API)."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from audio_library_v6 import AudioBlocked, admit, discover, resolve_audio

TRACK = {
    "source": "Openverse", "id": "3f5a1e49-973c-4082-b165-18967dd4ee25",
    "title": "Verified acoustic example", "creator": "Test artist",
    "license": "by",
    "license_url": "https://creativecommons.org/licenses/by/4.0/",
    "original_source_page": "https://example.org/creator/test-audio",
}
EVIDENCE = {
    "reviewer_confirmed_rights": True,
    "track_id": TRACK["id"], "license_url": TRACK["license_url"],
    "original_source_page": TRACK["original_source_page"],
    "source_license_proof_url": "https://example.org/creator/test-audio/rights",
    "reviewed_by": "Authorized reviewer", "reviewed_on": "2026-11-06",
    "attribution_approved": True,
}


class OpenLibraryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "licensed.wav"
        self.path.write_bytes(b"synthetic-not-an-audio-track" * 128)
        self.sha = hashlib.sha256(self.path.read_bytes()).hexdigest()

    def test_source_ambience_does_not_silently_claim_music(self):
        d = resolve_audio("source_ambience_only")
        self.assertFalse(d["licensed_track"])
        self.assertFalse(d["music_required"])

    def test_approved_license_and_sha_only_admit_to_native_editor(self):
        result = admit(TRACK, EVIDENCE, self.path, self.sha)
        self.assertEqual(result["filmcraft_rights"]["license"], "CC BY")
        self.assertEqual(result["filmcraft_rights"]["creator_name"], "Test artist")
        self.assertTrue(result["filmcraft_native_audio_mix_required"])
        self.assertFalse(result["ffmpeg_fallback"])
        self.assertTrue(result["credits"]["attribution_required"])

    def test_missing_requested_music_blocks_render(self):
        with self.assertRaises(AudioBlocked):
            resolve_audio("licensed_music")

    def test_unapproved_rights_block(self):
        with self.assertRaises(AudioBlocked):
            admit(TRACK, {**EVIDENCE, "reviewer_confirmed_rights": False}, self.path, self.sha)

    def test_missing_attribution_blocks(self):
        with self.assertRaises(AudioBlocked):
            admit(TRACK, {**EVIDENCE, "attribution_approved": False}, self.path, self.sha)

    def test_wrong_license_source_blocks(self):
        with self.assertRaises(AudioBlocked):
            admit(TRACK, {**EVIDENCE, "license_url": "https://other.example/rights"}, self.path, self.sha)

    def test_checksum_mismatch_blocks(self):
        with self.assertRaises(AudioBlocked):
            admit(TRACK, EVIDENCE, self.path, "0" * 64)

    def test_excluded_nc_license_blocks(self):
        with self.assertRaises(AudioBlocked):
            admit({**TRACK, "license": "by-nc"}, EVIDENCE, self.path, self.sha)

    def test_no_symlink_audio(self):
        path = Path(self.tmp.name) / "link.wav"
        path.symlink_to(self.path)
        with self.assertRaises(AudioBlocked):
            admit(TRACK, EVIDENCE, path, self.sha)

    def test_reused_library_catalog_returns_unverified_candidates(self):
        with patch("audio_library_v6.library") as lib:
            lib.return_value.search.return_value = {
                "provider": "openverse", "candidates": [TRACK]}
            found = discover("gentle instrumental")
        self.assertFalse(found["rights_verified"])
        self.assertEqual(found["candidates"][0]["creator"], "Test artist")

    def test_audio_extension_required(self):
        renamed = Path(self.tmp.name) / "sound.bin"
        renamed.write_bytes(self.path.read_bytes())
        with self.assertRaises(AudioBlocked):
            admit(TRACK, EVIDENCE, renamed, self.sha)


if __name__ == "__main__":
    unittest.main()
