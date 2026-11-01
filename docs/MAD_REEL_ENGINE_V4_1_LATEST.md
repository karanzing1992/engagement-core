# MAD Reel Engine V4.1 — Latest usable high-creativity private Reel configuration

**Baseline:** 2026-11-02, Asia/Kolkata  
**Classification:** Latest usable **private-preview** reel pipeline.  
**Certification:** Three actual 24-second 720×1280 H.264/AAC previews technically verified. One render was reproduced with the portable renderer with an identical SHA-256 output. **Not** certified for rights-cleared publication, automatic footage understanding, or real-footage FilmCraft cloud editing.  
**Technical predecessor:** Reel Engine V4 GitHub Actions **Groq → FilmCraft MCP** synthetic cloud certification; V4 remains the historical cloud baseline, V4.1 is the latest usable creative-editing configuration.  
**Unique master registry event:** `[MASTER-STACK-EVENT:MAD-REEL-ENGINE-V4-1-20261102]`.

## 1. Configuration locked for V4.1

| Setting | Value and meaning |
| --- | --- |
| Creative AI | Groq-hosted `openai/gpt-oss-20b` **only** for the final three-concept creative plan |
| Creativity | `temperature=0.9`, high-creativity *tested* setting, not verified provider maximum |
| Output shape | `response_format={"type":"json_object"}`; three concepts in one JSON |
| Token budget | `max_completion_tokens=6500` in the tested 20B concept call |
| Planner objective | Maximum concept, story, shot-order, opening-hook, pacing and emotional-arc freedom *inside brand and factual constraints* |
| Visual grounding | Timecoded observations from the actual 119-second user-uploaded 640×480 Arambol video; editorial source check and corrections performed separately |
| Final creative directions | A: Lake Journey — reflective / B: Rhythmic Shore — kinetic / C: Grounded to Lake — tactile POV |
| Production backend | FFmpeg direct; *not* FilmCraft's public GitHub hosted runner for these footage edits |
| Render | 720×1280 (9:16), 24 fps, libx264 H.264 CRF 25, AAC mono 112 kbps, MP4 faststart |
| Source framing | 4:3 footage retained within cinematic editorial vertical canvas, blurred natural-image backdrop; original vlog subtitle band cropped |
| Audio | Procedurally synthesized instrumental scores (ambient, rhythmic, organic), not third-party copyrighted songs |
| Review gate | FFprobe format/codec/duration verification, full FFmpeg decode and SHA-256 output receipts |

**Important:** A fully generalized brand-RAG + visual-model input stage was **not** implemented in V4.1. The model was supplied with curated brand constraints and manually timecoded source observations. The portable renderer consumes a vetted JSON treatment plan; it **does not call Groq every time it runs**. Any future prompt-to-plan automation must separately add image understanding, safe input access, model invocation and verification.

## 2. Brand policy and creative permission

**Absolute requirements (not negotiable by the AI):** Moksha Wellness is a nature-rooted, intimate, quiet-premium ritual sanctuary. Approved colors: Deep Forest `#18382F`, Soft Ivory `#F9F5EA`, Warm Sand `#E8DCC7`, restrained Brass Gold `#C5A15A`. Prefer editorial serif headlines (EB Garamond / Libre Baskerville family style), clean sans secondary text and sparse meaningful copy. A visual hook must work within 1–1.5 seconds without sound, and no opening full-screen logo is allowed. Preserve real source imagery; do not create false buildings, steam, people or lake facilities. No medical outcome claims, invented guests, invented facility depictions, aggressive selling or generic tourist stock as if Moksha footage. If the official logo is not available, **omit it**; never invent a replacement. Film context must not imply Sweet Water Lake is Moksha property. All outputs remain private previews until rights, people/guest permissions and owner approval are confirmed.

**AI autonomy within these bounds:** Choose a distinct idea for each edit; reorder clips; select emotional arc and opening; write concise overlays; pick movement/cut rhythm, music-feel and restrained color treatment; reject misleading shots; provide three independent options. Groq should not be instructed to produce a fixed two-second test edit. When it suggests a fictional scene or a misleading caption, the footage-grounding gate overrules it.

Policy sources (read in current session):
- [Moksha Brand Identity & Experience Handbook](https://docs.google.com/document/d/1H8tn9czlujeKer2olfbJuAyaPxrKwGnDgPIKJOARC9Q/edit)
- [Moksha Social Golden Rules](https://docs.google.com/document/d/1BgCQcK6k4byjGI3x8V01iXWPL5yFKNIEmJ4WxiklEbk/edit)
- [Moksha Creative Direction & Photo Finishing Handbook](https://docs.google.com/document/d/1Ihtl3Sr1f_Ojkrc7NrrgkXLWF8Z9dx8pf9zxcrpw1qA/edit)

## 3. Actual produced evidence

All edits use the **same** user-supplied 119-second 640×480 4:3 Sweet Water Lake / Arambol vlog video, with a distinct 24-second shot-order narrative. They are private previews. Filenames and hashes are verified from their bytes:

| Cut | Treatment | Reference MP4 SHA-256 | Exact bytes | Technical QA |
| --- | --- | --- | ---: | --- |
| A | Lake Journey: reflective travel / water storytelling | `4708a7f412598a6cd520ca801d77c78391ca8982a189fe871f40f4628d2907bc` | 5,164,762 | Pass |
| B | Rhythmic Shore: instruments and market energy → lake | `0ff0a639c0f0196f48d2761cdafa5134164d12fb96710bcfee4356902bb7b57d` | 5,579,770 | Pass |
| C | Grounded to Lake: rocks → trail → lake reveal | `7aff5efd2a4c2796d9eeee06d8c70912424a9ff244f4752efc3bdf843ccb6ebd` | 5,548,403 | Pass |

Recorded artifacts: `Reel_Engine_V4_Groq20B_{A,B,C}_*_PREVIEW.mp4`, individual `v4_{A,B,C}_receipt.json`, original WAV soundtracks and QA contact sheet in conversation workspace `/mnt/data/reel_engine_v4_3versions`. The original preview ZIP is `/mnt/data/Reel_Engine_V4_Groq20B_Three_Instagram_Previews.zip`. These paths are conversation-local, **not** hosted publicly in GitHub or Google Drive.

**Portable runner verification:** The new local-source V4.1 `render_three.py` script was compiled, dry-run validated against the source, and executed for Version B. It generated the original MP4 SHA-256 exactly (`0ff0a639c0f0196f48d2761cdafa5134164d12fb96710bcfee4356902bb7b57d`). This verifies portability for that tested source and environment, not every arbitrary video aspect ratio.

## 4. How to use V4.1

Use a machine with **Python 3 + numpy + FFmpeg/FFprobe** and available fonts. Keep footage outside public repositories. Download the portable renderer and machine-readable configuration from the GitHub repo and place them in the same directory.

```bash
python3 -m pip install numpy
python3 render_three.py \
  --source '/private/approved/video.mp4' \
  --output-dir '/private/reel-previews' \
  --config reel_engine_v4_1_config.json \
  --dry-run

# After reviewing source suitability, rights and timecoded shot plan:
python3 render_three.py \
  --source '/private/approved/video.mp4' \
  --output-dir '/private/reel-previews' \
  --config reel_engine_v4_1_config.json
```

**Caution:** The included source clip timecodes and FFmpeg frame/crop geometry are tuned to the demonstrated 119-second 640×480 source. Update the creative treatment segments, durations and crop layout for any new footage, or they may be wrong. `--only A`, `--only B`, `--only C` can run one treatment. No source footage is uploaded to GitHub. Groq planning happens separately using the recorded V4.1 prompt/config; `render_three.py` executes the fixed plan. The `GROQ_API_KEY` GitHub Actions secret is required by the separate V4 cloud synthetic workflow, **not** by this local FFmpeg renderer.

## 5. Architecture and component ownership

1. **MAD Manager / GPT supervising brain:** brief, evidence provenance, brand RAG integration (future), approval and task receipts. It remains the policy owner.
2. **Groq GPT-OSS 20B high-creativity editorial planner:** generates three distinct ideas from the full creative brief, Moksha's controlling brand rules and timecoded source evidence; set temperature 0.9.
3. **Footage QA / human and future vision model:** compare selected clip timecodes, remove unsupported scenes/captions, check people and copyright/consent and avoid misleading location assumptions.
4. **Portable FFmpeg editor:** consume structured, vetted segment list; compose 9:16 frame with real footage, restrained typography and original procedural audio.
5. **Technical QA:** MP4 dimensions, frame rate, audio codec, full decode and checksum.
6. **Owner creative/rights gate:** approve or request new cut; do not auto-publish.

**Separation from Reel Engine V4:** The V4 GitHub Actions pipeline demonstrated 2 seconds of synthetic video with live Groq plan + FilmCraft MCP + FFmpeg technical output. The **V4.1 three real-footage previews were generated with Groq 20B planning plus FFmpeg local execution**, not with the GitHub Actions FilmCraft cloud runner. We must not claim that FilmCraft was end-to-end tested on these real-footage cuts.

## 6. Acceptance and limitations

**Passed:** actual three distinct 24-second vertical previews from supplied footage; Groq GPT-OSS 20B at temperature 0.9 provided the plans; local FFmpeg exported each video; original procedural audio; technical validation and SHA-256 receipts; rerun of B from portable config matched its original SHA-256.

**Not passed / not claimed:** source clip ownership, commercial reuse/license, recognizable people consent, owner artistic satisfaction, caption and graphic-device manual review, real 1080×1920 quality or professional-grade cinematic grading, fully autonomous shot selection, live RAG-backed planning, FilmCraft cloud rendering of these three outputs, authenticated social publication, production resilience or consumer/plugin synchronization. This is a **usable private-preview engine**, not a publish-certified one.

## 7. Master version and rollback rules

**Version register:** V4 = previous synthetic cloud execution certification; **V4.1 = latest usable creative private-preview configuration** (newest). Do not overwrite V4 audit evidence or call V4.1 a complete M3/M4 milestone. Moksha Fire & Ice M3 remains PARTIAL/HOLD. Social posting remains separately owner-authorized. Mac thermal guards, Firefox sessions, and host-tunnel identity restrictions must not be disabled.

**Rollback:** Revert only V4.1 configuration/docs/portable renderer; leave V4 GitHub Actions runner, its Groq secret, all WordPress/Metricool services, and Mac MAD Manager intact. Never commit raw videos or the Groq key into public GitHub.

**Next scope:** V4.2 — model-driven frame/shot analysis, live brand handbook retrieval, iterative 3-treatment selection, truly automatic raw-footage-safe edits, private cloud-source ingestion and rights-cleared 1080×1920 quality gates. Focus on creative quality and source-grounding before adding arbitrary effects.