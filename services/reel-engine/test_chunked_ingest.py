from __future__ import annotations
import hashlib
import os
from pathlib import Path
import tempfile
import unittest

from chunked_ingest import UploadError, UploadStore


class ChunkedIngestTests(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.root = Path(self.t.name)
        self.store = UploadStore(self.root, max_file_bytes=20000, chunk_bytes=4096)
        self.content = b"Goa sunshine\0" * 830
        self.digest = hashlib.sha256(self.content).hexdigest()

    def _begin(self):
        return self.store.begin(name="morning-goa.mp4", size=len(self.content),
                                sha256=self.digest, mime_type="video/mp4")

    def _write(self, upload_id, idx, data, checksum=True):
        path = self.root / f"temp{idx}.tmp"
        path.write_bytes(data)
        return self.store.accept_chunk(upload_id, idx, path,
                hashlib.sha256(data).hexdigest() if checksum else "0" * 64)

    def test_all_chunks_out_of_order_resumable_with_idempotent_retry(self):
        sess = self._begin()
        upload_id = sess["id"]
        pieces = [self.content[i:i+4096] for i in range(0,len(self.content),4096)]
        for idx in reversed(range(len(pieces))):
            self._write(upload_id, idx, pieces[idx])
        self.assertEqual(sorted(self.store.status(upload_id)["received_chunks"]), list(range(len(pieces))))
        self.assertTrue(self._write(upload_id, 0, pieces[0])["already_received"])
        finish = self.store.complete(upload_id)
        self.assertEqual(finish["sha256"], self.digest)
        self.assertTrue(self.store.complete(upload_id)["already_complete"])
        self.assertEqual(self.store.resolve(upload_id).read_bytes(), self.content)

    def test_missing_chunk_blocks_commit(self):
        sess = self._begin()
        with self.assertRaisesRegex(UploadError, "missing chunks"):
            self.store.complete(sess["id"])

    def test_corrupt_checksum_fails_closed(self):
        sess = self._begin()
        with self.assertRaisesRegex(UploadError, "Chunk SHA-256 mismatch"):
            self._write(sess["id"], 0, self.content[:4096], False)
        self.assertEqual(self.store.status(sess["id"])["received_chunks"], [])

    def test_conflicting_duplicate_chunk_rejected(self):
        sess = self._begin()
        self._write(sess["id"], 0, self.content[:4096])
        with self.assertRaisesRegex(UploadError, "Conflicting"):
            self._write(sess["id"], 0, b"A"*4096)

    def test_modified_chunks_block_full_checksum(self):
        sess = self._begin()
        pieces = [self.content[i:i+4096] for i in range(0,len(self.content),4096)]
        for i, content in enumerate(pieces):
            self._write(sess["id"],i,(b"A"*len(content)) if i==0 else content)
        with self.assertRaisesRegex(UploadError, "Final file size or SHA-256 mismatch"):
            self.store.complete(sess["id"])
        self.assertFalse(self.store.status(sess["id"])["complete"])

    def test_traversal_and_large_file_rejected(self):
        with self.assertRaises(UploadError):
            self.store.begin(name="../../bad.mp4", size=5,sha256=self.digest,mime_type="video/mp4")
        with self.assertRaises(UploadError):
            self.store.begin(name="good.mp4",size=20001,sha256=self.digest,mime_type="video/mp4")

    def test_commit_size_and_chunk_boundary_enforced(self):
        sess = self._begin()
        with self.assertRaisesRegex(UploadError, "expected 4096"):
            self._write(sess["id"],0,b"abc")

    def test_expired_metadata_not_accepted(self):
        sess = self._begin()
        folder = self.root/'sessions'/sess['id']
        import json, time
        m=json.loads((folder/'metadata.json').read_text());m['created_at']=time.time()-49*3600
        (folder/'metadata.json').write_text(json.dumps(m))
        with self.assertRaisesRegex(UploadError,"expired"):
            self.store.status(sess['id'])
        self.assertEqual(self.store.clean_expired()['expired_sessions_removed'],1)


if __name__=="__main__":unittest.main()