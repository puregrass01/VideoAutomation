---
name: video-editing-automation
description: Automate timeline video edits as CapCut drafts via pyCapCut.
version: 0.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [video-editing, capcut, pycapcut, scenedetect, automation]
    related_skills: [youtube-content, songsee]
---

# Video Editing Automation

Automate short-form and long-form timeline video editing by converting reference videos or markdown briefs into a renderer-neutral specification (`spec.json`) and compiling editable project drafts (`CapCut` / `pyCapCut`) for human review, finishing and export in the CapCut GUI.

## When to Use

- Converting editing briefs (`.md`), reference videos, or local templates into timeline sequences
- Generating or inspecting CapCut desktop drafts (`com.lveditor.draft`) via `pyCapCut`
- Analyzing reference video cut boundaries (`PySceneDetect`) and audio beat grids (`librosa`)
- **Don't use for:** generative AI text-to-video synthesis or ASCII/Manim animation (use `ascii-video` or `manim-video`)

## Standing User Preferences (Always-On)

- **No AI Slop or Unrelated Stock Footage**: Strictly forbid AI-generated video clips (e.g., synthetic dashcam, Midjourney/Runway/Kling/InVideo clips) and stock footage unrelated to the subtitle copy. Always use **actual camera footage (`IMG_*.MOV`, real workshop/product shots)** and verify via `vision_analyze` that every scene's visual subject directly matches its subtitle text.
- **Typography (Bold Static Fonts)**: Default Korean text to **Bold** weight using a static `Noto Sans KR Bold` font (`NotoSansKR-Bold-Static.ttf`, instantiated at `wght=700` from `NotoSansKR-VF.ttf` so headless renderers do not fall back to the Thin variable axis or produce Bold variable-font thorn artifacts) and Latin/numeric display text to `NotoSans_Condensed-Bold`. Never apply a Latin-only `Noto Sans` or `Noto Sans Condensed` font file alone to Korean strings without Korean fallback, or Hangul syllables render as missing-glyph boxes (`□`).
- **Text Box Styling (Solid Black Background, No Outline)**: Disable text outlines (`stroke: false` / `null`) and use a **solid black background box** (`cc.TextBackground(color="#000000", style=1, alpha=1.0, round_radius=0.14)` in `pyCapCut`).
- **Finishing Boundary**: Keep the neutral `spec.json` as the single source of truth and output a CapCut draft (`hermes_*`) as the deliverable. Visual review means opening the deployed draft in CapCut; the final MP4 is exported manually from the CapCut GUI.
- **Asset & Template Hygiene**: Never attempt to decrypt encrypted CapCut drafts or copy cloud team-space drafts directly as template originals. Extract only the editing grammar (timing, layout, motion intent) into `spec.json`, and isolate unmatched or Pro (`is_vip`) assets in `needs_review`.

## Procedure

### 1. Reference & Media Analysis
1. Copy source and reference media into an isolated working folder (`구글드라이브다운파일/media/` at the repo root) before analysing it.
2. Detect reference cut boundaries at frame precision via `terminal`:
   ```bash
   py -m scenedetect -i 구글드라이브다운파일/media/reference.mp4 detect-adaptive list-scenes -o work/
   ```
3. Extract BPM and downbeats using `librosa` (`librosa.beat.beat_track`) to build the beat grid (`downbeats_s`).
4. Extract start, middle, and end frames per scene with `ffmpeg -ss <t> -i 구글드라이브다운파일/media/reference.mp4 -frames:v 1 구글드라이브다운파일/frames/<png>`, then inspect text placement and framing with `vision_analyze`.
   - **Completion criterion:** Cut list CSV and BPM/downbeat array exist in `work/`; representative scene PNGs exist in `구글드라이브다운파일/frames/`.

### 2. Neutral Spec (`spec.json`) Compilation
1. Merge timing from `PySceneDetect` / `librosa` (prioritizing measured cut/downbeat timestamps) with copy and structure from the template brief.
2. Store all times in seconds (`float`, 3 decimal places). Normalize text anchors to `[0.0..1.0, 0.0..1.0]`.
3. Match CapCut effects, transitions, and animations by `resource_id` (not localized UI title) against `pyCapCut` metadata enums. Any asset missing from static enums or flagged `is_vip` must be added to the scene's `needs_review` array.
   - **Completion criterion:** `spec.json` validates against `spec.schema.json` with `stroke: null`, `background.enabled: true`, and explicit `needs_review` entries.

### 3. CapCut Draft Compilation (`pyCapCut`)
1. Run pre-flight checks before touching the CapCut drafts folder:
   - Verify `CapCut.exe` is not running (`tasklist /FI "IMAGENAME eq CapCut.exe" /NH /FO CSV`). If running, stage the draft under `work/capcut_stage/` instead.
   - Verify the highest installed CapCut version under `CapCut/Apps/` is `< 10.0`.
2. Write the generation script to `work/<script>.py` and execute via `py` (do not run inside an isolated sandbox interpreter that lacks the editable `pycapcut` package).
3. Post-process `draft_content.json` and `draft_meta_info.json` to restore `canvas_config.ratio` (e.g., `"9:16"`), populate `draft_name`/`draft_fold_path`/`tm_duration`, and inject cached font `{id, path}` into both `materials.texts[].fonts` and `content.styles[].font`.
   - **Completion criterion:** Draft folder `hermes_<name>` contains valid plaintext JSON (`first_byte == b'{'`) with matching durations and font IDs.
4. Open the deployed draft in CapCut and review cuts, framing and captions there; export the MP4 from the CapCut GUI.

See `references/capcut.md` for JSON structures, encryption checks, and font/background payloads.

## Pitfalls

- **Check both root and `Timelines/*/` for encryption:** Inspect the first byte (`{`) of both root `draft_content.json` and every `Timelines/*/draft_content.json` before reading an existing CapCut draft — CapCut 9.2.8+ reads `Timelines/<UUID>/draft_content.json` first, which can be encrypted even when the root `draft_content.json` is plaintext, causing template loaders to silently read a stale snapshot.
- **Ignore `crypto_key_store.dat` as an encryption indicator:** Plaintext local drafts frequently contain `crypto_key_store.dat` while encrypted cloud-downloaded drafts can omit it; only the `{` first-byte check and `draft_virtual_store.json` (`"path": "draft_content.json", "is_encrypted": true`) are reliable.
- **Never write to CapCut drafts while `CapCut.exe` is running:** Concurrent external writes race with CapCut's `.locked` files and `root_meta_info.json` sync.
- **Always attach time units in `pyCapCut`:** Pass `"1.5s"` to `cc.trange()` and `cc.tim("0s")` (never a raw string) to `AudioSegment.add_keyframe()` — unitless strings silently parse as `0µs`, and raw strings in `add_keyframe` write invalid string offsets into JSON.
- **Restore `canvas_config.ratio` after `pyCapCut` save:** `ScriptFile.dumps()` hardcodes `canvas_config.ratio = "original"`, stripping `"9:16"` metadata unless patched in post-processing.
- **Include both `id` and `path` on CapCut text fonts:** Setting `styles[].font` in `materials.texts[].content` without the `id` key crashes CapCut on load.
## Verification

- [ ] The deployed draft opened in CapCut shows cuts at the spec scene boundaries, the spec aspect ratio (16:9 longform / 9:16 shorts) with the frame covered, Korean glyph integrity (no `□` or thorn artifacts), and legible captions (no outline, solid black box)
- [ ] Generated CapCut draft starts with `hermes_`, has `first_byte == b'{'` on all `draft_content.json` files, and preserves `canvas_config.ratio`
