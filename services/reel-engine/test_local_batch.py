from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from geo_policy import GeoPolicyError
from local_batch import _workspace, setup, run, validate_request


class OfflineBatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "private-reel"
        setup(self.root)
        self.folders = _workspace(self.root)
        self.original = self.folders["approved"] / "synthetic-test.mp4"
        self.original.write_bytes(b"fake-mp4-data-for-manifest-unit-check" * 100)
        self.spec = {
            "schema_version": 1, "job_id": "pilot-20261013", "brand": "generic",
            "source_files": [{"file": self.original.name,
                              "sha256": hashlib.sha256(self.original.read_bytes()).hexdigest()}],
            "config": {
                "brand": "generic", "editorial_region": "Goa",
                "target_seconds": 30, "width": 720, "height": 1280, "fps": 25,
                "source_provenance": [{
                    "origin": "owned", "capture_country": "India", "capture_region": "Goa",
                    "source_url": "https://example.invalid/synthetic-only",
                    "location_evidence_url": "https://example.invalid/synthetic-only",
                    "verification_status": "human_verified",
                    "verified_by": "Synthetic Fixture, Not Real Approval"
                }]
            }
        }
        self.manifest = self.folders["requests"] / "pilot-20261013.json"

    def write_spec(self):
        self.manifest.write_text(json.dumps(self.spec))

    def test_private_manifest_only(self):
        self.write_spec()
        result = run(self.root, self.manifest.name, check_only=True)
        self.assertTrue(result["checked"])
        self.assertFalse(result["published"])

    def test_denies_absolute_source(self):
        self.spec["source_files"][0]["file"] = "/etc/passwd"
        self.write_spec()
        with self.assertRaises(ValueError):
            run(self.root, self.manifest.name, check_only=True)

    def test_denies_parent_traversal(self):
        self.spec["source_files"][0]["file"] = "../secret.mp4"
        self.write_spec()
        with self.assertRaises(ValueError):
            run(self.root, self.manifest.name, check_only=True)

    def test_denies_symlink_input(self):
        linked = self.folders["approved"] / "alias.mp4"
        linked.symlink_to(self.original)
        self.spec["source_files"][0]["file"] = "alias.mp4"
        self.write_spec()
        with self.assertRaises(ValueError):
            run(self.root, self.manifest.name, check_only=True)

    def test_denies_wrong_hash(self):
        self.spec["source_files"][0]["sha256"] = "0" * 64
        self.write_spec()
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            run(self.root, self.manifest.name, check_only=True)

    def test_denies_foreign_footage(self):
        self.spec["config"]["source_provenance"][0]["capture_country"] = "Spain"
        self.write_spec()
        with self.assertRaises(GeoPolicyError):
            run(self.root, self.manifest.name, check_only=True)

    def test_denies_moksha_brand_without_approved_logo(self):
        self.spec["brand"] = "moksha"
        self.spec["config"]["brand"] = "moksha"
        self.write_spec()
        with self.assertRaisesRegex(ValueError, "unbranded"):
            run(self.root, self.manifest.name, check_only=True)

    def test_denies_existing_draft(self):
        self.write_spec()
        (self.folders["drafts"] / "pilot-20261013.mp4").write_bytes(b"existing")
        with self.assertRaises(FileExistsError):
            run(self.root, self.manifest.name, check_only=True)

    def test_denies_duplicate_workspaces(self):
        with self.assertRaises(ValueError):
            setup(self.root)

    def test_denies_override(self):
        self.spec["config"]["regional_override"] = True
        self.write_spec()
        with self.assertRaises(ValueError):
            run(self.root, self.manifest.name, check_only=True)


if __name__ == "__main__":
    unittest.main()
