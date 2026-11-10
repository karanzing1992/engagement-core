# Shaadi M7.1 — private Gemini artistic review

Reuses existing Reel Engine V8's approved Gemini credential in the owner-owned public
engagement-core repository, without exposing private Shaadi game images or credentials.

Trusted workflow: .github/workflows/shaadi-m71-owner-private-art-review.yml
Runner: services/reel-engine/game-art-review/private_runner.py
All requests are limited to owner-created issues beginning with [SHAADI-M71-GEMINI].
GitHub's ephemeral runner generates an X25519 public key. Dell encrypts the three
real, SHA256-pinned gameplay screenshots as per-frame AES-GCM payloads and posts
only ciphertext chunks to the public issue. The runner verifies GitHub owner ID,
run ID, frame integrity, expected source hashes, and format/size bounds.
A single owner-approved free Flash model may inspect the decrypted JPEGs. Its
validated review is encrypted again to a Dell-held reply public key.
The private key to decrypt the report never leaves Dell.

Source screenshot SHA256s: baseline mobile
296d2c2fde135fb8a58d742b5a749a9a90bc29527fa4c49e5a627f5210f54d60;
updated mobile 47152b6229ea25186e5e6ef4d0275681a6e077c806ee1deda5256f655a5f1fce;
updated desktop 53ee0d12857c6384485772d9f3adeb69037630f981b0451d7f509fb385fdc83d.

The hashes of original PNGs are owner-asserted provenance. The runner independently
checks the JPEG ciphertext authenticity and contents. The original private game
source never leaves the game repository. The screenshots do NOT demonstrate actual
movement, animation, FPS, thermal performance or audio quality.

Offline verification:
python3 services/reel-engine/game-art-review/test_private_runner.py
python3 experiments/reel-engine-v4_2/test_gemini_adapter.py

A single real Gemini review is advisory. It does NOT independently certify a
95/100 score, approve release, authorize autonomous changes or replace device QA.
No game/production mutation, public unencrypted media, secret rotation or billing
changes. Owner-scoped action plus encrypted private handoff only.
