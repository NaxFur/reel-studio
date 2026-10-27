# AGENTS.md: set up reel-studio and make the first reel

You are a coding agent (Claude Code, Codex or similar) helping a user make Nerd + Claude sketch reels with
this repo. Follow these steps in order. Talk to the user in their language; everything inside the videos
is English.

## 0. Ground rules
- Ask before installing anything big: Blender (~400 MB) and the whisper model (~1.5 GB).
- Never write an API key or token into a file in this repo. Voices come from the ElevenLabs connector, or
  the user's own recordings, or (for drafts) macOS `say`.
- Every fact that ends up in a video needs a source in that episode's `research.md`. The story may be
  fiction; tips, numbers and features may not.
- Don't post anything anywhere. The repo makes video files; the user publishes them.

## 1. Check the machine
- macOS on Apple silicon is the tested platform. On Linux, tell the user it is untested: they will need to
  set `BLENDER`, `DUO_FONT_*` and skip `--say` drafts (see `skills/duo-sketch-reel/SKILL.md`, "Files").
- Need: Blender 5.x (developed on 5.4), `ffmpeg`, `whisper-cli` (whisper.cpp), Python 3.
- With Homebrew, after the user says yes:
  ```bash
  brew install ffmpeg whisper-cpp
  brew install --cask blender
  ```

## 2. Install
```bash
./setup/install.sh --model
```
It checks the tools, creates `~/.venvs/duo-reel` (numpy, scipy, soundfile, pillow), downloads the
whisper model to `~/whisper-models/` and links the skill into `~/.claude/skills/duo-sketch-reel`. Fix every
line marked `--` and re-run until it prints "Ready".

## 3. Prove it works (free, about 5 minutes)
```bash
skills/duo-sketch-reel/pipeline.sh examples/env-rotate --say stills
```
Open `examples/env-rotate/renders/stills/sheet.jpg` and show it to the user: one frame per beat of the
example episode. If a step fails, read the error, fix the cause and re-run; don't skip steps.

## 4. Make the user's first episode
Ask the user for one dev/AI pain they know well. Then follow `skills/duo-sketch-reel/SKILL.md` exactly:
research → `storyboard.json` (copy an example into a new folder `episodes/<YYYY-MM-DD>_<slug>/`) → free
draft + stills → fix the layout → voices → real stills → final render (≈ 1 hour, run it in the
background) → QA must say "Blocking: none".

Read `playbook/README.md` before writing the script: the joke is about what the viewer does with their
AI, Claude is a deadpan character, one tip, 30-40 seconds, the last frame loops into the first.

## 5. Finish
Tell the user where `final.mp4`, `final_b.mp4` (A/B hook) and `cover.png` are, how long it is, what the
voices cost, and that QA passed. Suggest a caption in the playbook's style (one lowercase first-person
line, ≤ 5 hashtags).
