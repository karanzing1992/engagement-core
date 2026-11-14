# Generic Design RAG 2.1.0 + Engine 2.1.0 — complete reproducible source

Local verified commit: `878d2086db5bedf60368615f8f95ea95e6630080` (separate Dell worktree, original 2.0 preserved).
**Archive SHA256:** `27a414ad169132cb48418ddf220c2be55dbb9a7d7090f53ee034f079e1753efb`.
**Format:** 7 contiguous base64 fragments totaling 99,332 characters, representing a 74,497-byte tar.gz containing **47 source files** (all Python engine, RAG, tests, generic+brand reference markdown, manifests, requirements, docs). No screenshot, API key, system home directory, runtime database or production data.

To reconstruct locally from this source directory:

```bash
cat full-source-v21.tar.gz.b64.part* | base64 --decode > full-source-v21.tar.gz
echo '27a414ad169132cb48418ddf220c2be55dbb9a7d7090f53ee034f079e1753efb  full-source-v21.tar.gz' | sha256sum --check -
tar -tzf full-source-v21.tar.gz  # inspect paths; unpack only in an isolated workspace
```

Partial human-readable changed modules are also in the PR source tree. The archive provides unchanged baseline dependencies absent from the draft PR, without registering a new runtime. GitHub Actions Gemini private review was authenticated and reached 10 of 12 image calls, then stopped at HTTP 429. Advisory feedback/signed 95 quality/release remain blocked. This is **source backup only**, not a deployed package.

Source archive fragments contain only text base64 source bytes; unlike the 14 separate screenshot ciphertext blobs, source fragments are intentionally committed and accessible on the branch.
