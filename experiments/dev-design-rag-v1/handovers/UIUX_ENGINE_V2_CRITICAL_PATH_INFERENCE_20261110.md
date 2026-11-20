# UI/UX Engine V2 — critical-path inference verification (2026-11-10 IST)

Local isolated Dell review worktree; prior source HEAD 70db96d9873b62285ebe29f6794442dba8880c94. Master Registry #353 is the reference checkpoint, NOT a newly published event.

## New real model diagnostics
- Dell host: i5-8250U (8 logical CPUs), 7.5 GiB RAM; local Ollama 0.40.6. No paid model calls.
- Genuine isolated fixture image: engine_smoke_html-390.jpg, resized to 256x384 max (not a certification-ready full-page representation).
- qwen3-vl:2b-instruct via Ollama HTTP /api/generate; image+single short visible-layout question, num_ctx=4096, num_predict=64, num_thread=6, num_gpu=0. **TIMEOUT after 105.13s**, no model response.
- hf.co/ggml-org/SmolVLM2-256M-Video-Instruct-GGUF:Q4_K_M via same local HTTP API with the real image, num_ctx=2048, num_predict=56, num_thread=6, num_gpu=0. **TIMEOUT after 58.13s**, no model response. This small diagnostic model is not accepted as an independent artistic jury.
- Prior evidence: genuine Qwen3-VL image-pair timed out after about 102s; first larger prompt generated context HTTP 400 before correction.
- No raw observation, visual quality score, independent signature, or approval was obtained. These probes DO NOT satisfy full-resolution, all-route, dual-viewport artistic assessment.
- During Qwen attempt, llama-server consumed ~2.7 GiB resident memory and ~88% one-CPU-equivalent according to ps; thus local image inference throughput is an immediate hardware/CPU constraint, though a specific internal bottleneck is not yet proven.

## Nonnegotiable remaining prerequisites
1. Use authorized zero-cost *capable* independent vision reviewer compute to inspect 6 routes x 2 full-page screenshots and record all raw outputs; accept true score even below 95.
2. Owner-provision a distinct reviewer principal with signing key outside writer's access and protected root-owned trusted-reviewers.json; execute live boundary negative tests.
3. Obtain independently attested raw-derived minimum score >=95, else revise actual design and reassess.
4. Certify real cross-project lifecycle/recovery and all deploy paths against the protected gate; run genuine free remote preview only after gate passes.
5. Safely reconcile the correct GitHub source/review PR, then publish/read back a Master Registry event.

## Operational decision
Keep release and public preview BLOCKED. No scoring fixture substituted, no threshold relaxed, no remote preview, no production mutation, no new paid tool. Existing 60/60 passing tests and prior 12/12 all-route Lighthouse evidence remain preserved without new test claims.
