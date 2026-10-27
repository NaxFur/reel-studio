---
name: duo-sketch-reel
description: Make a 9:16 comedy-sketch reel (30-45 s, English) with two 3D characters - the Nerd (spiky hair, glasses, hoodie) and Claude, the small orange low-poly robot on his desk - rendered in Blender from one storyboard.json. The Nerd has a real dev/AI pain, Claude answers deadpan and slips in one verified tip, then a twist and a loop back to frame 1. Runs research with sources, script, free `say` draft, layout stills, ElevenLabs takes, whisper check, final EEVEE render, cover and QA. Use for "make a Nerd + Claude sketch", "duo reel", "new episode", "sketch reel about X", "video con l'omino arancione".
---

# Duo sketch reel (Nerd + Claude)

A 3D sketch where the Nerd panics and Claude (the orange robot) answers deadpan. Everything is
procedural Blender: the set, both rigs, acting, lights, cameras, monitors, overlay, score and SFX are built
from **one file per episode, `storyboard.json`**. A new episode is data, not code. No image or video
generation anywhere.

An episode is a folder: `<anything>/<YYYY-MM-DD>_<slug>/` with `storyboard.json` and `research.md`. The
pipeline writes everything else into it (`assets/`, `project/`, `renders/`, `final.mp4`, `cover.png`, `qa/`).
Two finished episodes live in `examples/` of the repo: copy one to start.

## Workflow (in order, don't skip)

1. **Topic** (5 min). One relatable dev/AI pain and ONE tip a developer can use today. The joke is about
   what the viewer does with their AI, not about a tool. Rules and the idea bank: `references/retention.md`.
2. **Research** → `research.md`: every fact on screen / in the voice / caption with URL + date checked,
   primary sources (official docs, README, source code). A separate "Fiction" section for the sketch's
   invented story bits (times, counts, names). Drop what you can't verify and say so.
3. **Script + storyboard** → `storyboard.json` (copy an example and rewrite it). Schema and vocabulary:
   `references/storyboard.md`. Target 30-40 s, 10-14 lines, first word ≤ 0.5 s, a cut every 1.5-3 s,
   Nerd opens, Claude closes, the last frame cuts back into the first.
4. **Free draft** (macOS): `pipeline.sh <episode> --say stills` (system voices, no credits). Look at
   `renders/stills/sheet.jpg` (one frame per beat end). Fix framing/overlay collisions, re-run.
   Not on macOS? Skip `--say`: record or generate the takes first (step 5), then run `stills`.
5. **Voices.** One audio file per line at `assets/audio/dialogue_raw/<beat id>.mp3` (`L01.mp3`, ...).
   The reference episodes use ElevenLabs `eleven_v4` with two library voices - Nerd = "Quinn - Soft Nerd Boy",
   Claude = "Sarcastic Nigel" - and audio tags in each beat's `tts` (e.g. `[deadpan] It was ugly.`).
   With the ElevenLabs connector in Claude: estimate one line first (≈ 1 credit per character incl. tags),
   then one generation per line, and download each take from its `content_url`. An 11-14 line episode is
   ≈ 700-900 credits. Your own recordings work too: same file names.
6. **Real build + stills**: `pipeline.sh <episode> stills`. `project/whisper_check.txt` lists script vs heard
   per line (ratio < 0.8 = listen to it). Takes are longer than the `say` draft: check the sheet again.
7. **Final**: `pipeline.sh <episode> final` (16 samples, 3 workers ≈ 3 s per frame on an M-series Mac: a
   38 s reel ≈ 1 h; run it in the background). It renders `final.mp4`, the B-hook variant `final_b.mp4`,
   `cover.png`, and runs `qa.py` → `qa/report.md` (must say Blocking: none).

## Hard rules
- Characters: don't redesign the Nerd or Claude (`engine/scene/nerd.py`, `mascot.py`). Claude has no
  mouth: it "talks" with body squash, bounces, eyes and arms.
- A sketch may invent its story (that's comedy), never a product feature, number, benchmark or quote.
- Payoffs (stamps, keys, ticks) go 0.2-0.3 s before the word they illustrate, never on the last word.
- Free draft before paid voices; stills before the final render.

## Files
- `pipeline.sh <episode> [--say] [build|stills|draft|final]`
- `engine/scene/` Blender side: `build_scene.py` (entry), `animate.py` (acting/lights/cameras from the
  storyboard), `env.py` set, `nerd.py`, `mascot.py`, `lights.py`, `tl.py` (anchors, shared with scripts).
- `engine/scripts/`: `build_timeline.py` (takes → timeline + whisper words + lipsync), `make_screens.py`
  (monitor templates), `make_overlay.py` (hook, subtitles, items, title card, captions.srt),
  `make_audio.py` + `synth.py` (score/SFX), `master_audio.py` (-14 LUFS), `stills.py`, `draft.sh`,
  `render_final.sh`, `encode.sh`, `make_cover.py`, `cover_title.py`, `qa.py`, `make_textures.py`.
- Tools and paths (environment variables, macOS defaults): `BLENDER` (Blender 5.x binary),
  `DUO_PYTHON` (a Python with numpy, scipy, soundfile, pillow; default `~/.venvs/duo-reel/bin/python`),
  `WHISPER_MODEL` (whisper.cpp model, default `~/whisper-models/ggml-medium.en.bin`), `whisper-cli` and
  `ffmpeg` on PATH, fonts `DUO_FONT_DISPLAY` / `DUO_FONT_MONO` / `DUO_FONT_SANS` / `DUO_FONT_EMOJI`.
- `references/storyboard.md` (schema, every preset), `references/retention.md` (hook/structure/topics),
  `references/lessons.md` (things that went wrong once).
