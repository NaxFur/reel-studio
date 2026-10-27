# reel-studio

[![License: MIT](https://img.shields.io/badge/license-MIT-orange.svg)](LICENSE)
[![Made with Blender](https://img.shields.io/badge/made%20with-Blender-e87d0d.svg)](https://www.blender.org/)
[![Claude Code skill](https://img.shields.io/badge/Claude%20Code-skill-d97757.svg)](skills/duo-sketch-reel/SKILL.md)
[![GitHub stars](https://img.shields.io/github/stars/NaxFur/reel-studio?style=social)](https://github.com/NaxFur/reel-studio/stargazers)

**Make the orange-robot sketch reels you've seen on Instagram.** One `storyboard.json` in, a finished
9:16 reel out: two 3D characters, acting, cameras, monitors, subtitles, music, SFX, cover and a QA report.
Everything is procedural Blender driven by an AI coding agent. No AI image or video generation.

<p align="center">
  <img src="docs/img/env-rotate.gif" width="300" alt="The Nerd and Claude in the .env episode">
  &nbsp;&nbsp;
  <img src="docs/img/env-rotate-cover.png" width="300" alt="Cover of the .env episode">
</p>

This is the exact setup behind [@thedebugduo](https://www.instagram.com/thedebugduo/): the Nerd panics,
Claude (the orange robot on his desk) answers deadpan, slips in one real tip, and the last frame loops
back into the first. Watch the [".env" episode](https://www.instagram.com/reel/De-JRqviF1z/) made with
this repo.

⭐ **If this saves you a week of Blender work, star the repo.** It's how we know to keep publishing.

**Contents:** [Install with one prompt](#install-with-one-prompt) ·
[What's inside](#whats-inside) · [How a reel gets made](#how-a-reel-gets-made) ·
[Manual install](#manual-install) · [Costs](#costs-honestly) · [Make them perform](#make-them-perform) ·
[Troubleshooting](#troubleshooting) · [License](#license-and-credits)

---

## Install with one prompt

Paste this into **Claude Code** (or any coding agent that can run terminal commands, like OpenAI Codex CLI):

```text
Clone https://github.com/NaxFur/reel-studio, read its AGENTS.md and follow it step by step:
install what's missing (ask me before big downloads), render the example's free draft stills
and show them to me, then help me make my first Nerd + Claude episode.
```

The agent checks your Mac, installs Blender, ffmpeg and whisper.cpp with your OK, runs the installer,
proves the pipeline works on the example episode, then asks you for a topic and makes your first reel.
Everything it follows is in [`AGENTS.md`](AGENTS.md).

> **ChatGPT in the browser can't do this part**: rendering needs Blender running on your own computer.
> Use an agent that works in your terminal (Claude Code, Codex CLI…). A chat assistant can still help
> you write the `storyboard.json`.

## What's inside

| | |
|---|---|
| [`skills/duo-sketch-reel/`](skills/duo-sketch-reel/) | The Claude Code skill: the Blender engine (set, both rigs, acting, lights, cameras, monitors), overlay, synthesized score and SFX, whisper alignment, render, cover and QA. |
| [`examples/`](examples/) | Two finished episodes: [`env-rotate`](examples/env-rotate/) (leaked `.env` → rotate the key) and [`caps-lock`](examples/caps-lock/) (the fix is on another port). Each has its `storyboard.json` and a `research.md` with every fact sourced. |
| [`playbook/`](playbook/) | What we learned growing the account: hooks, structure, retention numbers from our own reels, captions, and the comment-to-DM funnel. |
| [`AGENTS.md`](AGENTS.md) | Step-by-step instructions for your coding agent: install, prove it works, make the first episode. |
| [`setup/`](setup/) | `install.sh` checks the tools, makes the Python environment and installs the skill. |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Show us your reels, report bugs, add presets. |

## How a reel gets made

```
idea ─► research.md (sources) ─► storyboard.json (lines, shots, acting, screens, overlay)
     ─► free draft with macOS voices ─► stills at every beat end (fix the layout for free)
     ─► voice takes (ElevenLabs or your own mic) ─► whisper check
     ─► Blender EEVEE render ─► final.mp4 + final_b.mp4 (A/B hook) + cover.png + qa/report.md
```

A new episode is **data, not code**: lines, camera shots (`nerd_cu`, `claude_lens`, `monitor_ecu`…),
the Nerd's face/pose/hands, Claude's bounces and walks, what each monitor shows, overlay chips,
panels and stamps, lights and music changes. The schema is in
[`references/storyboard.md`](skills/duo-sketch-reel/references/storyboard.md).

<p align="center"><img src="docs/img/env-rotate-beats.jpg" width="640" alt="One still per beat of the .env episode"></p>

## Manual install

**Requirements:** macOS on Apple silicon (tested), [Blender](https://www.blender.org/download/) 5.x
(developed on 5.4), `ffmpeg`, [whisper.cpp](https://github.com/ggerganov/whisper.cpp) (`whisper-cli`),
Python 3 and [Claude Code](https://claude.com/claude-code). Linux is untested: point the environment
variables at your Blender binary and fonts (see the skill's "Files" section); the free `say` draft is
macOS only.

```bash
brew install ffmpeg whisper-cpp
brew install --cask blender
git clone https://github.com/NaxFur/reel-studio.git
cd reel-studio
./setup/install.sh --model      # checks tools, creates ~/.venvs/duo-reel, downloads the whisper model, links the skill
```

Render the example's layout stills (free, no voices needed on macOS):

```bash
skills/duo-sketch-reel/pipeline.sh examples/env-rotate --say stills
open examples/env-rotate/renders/stills/sheet.jpg
```

Then open Claude Code anywhere and ask:

> Make a Nerd + Claude sketch about forgetting to save the file before testing.

Claude follows the skill: researches the tip, writes the script and storyboard, runs the free draft,
checks the stills, generates the voices, renders and runs QA.

## Costs, honestly

- **Voices:** ≈ 1 ElevenLabs credit per character. Our 13-line episodes cost 745-839 credits. Record
  yourself and it's free.
- **Render:** ≈ 3 s per frame with 3 Blender workers on an M-series Mac: a 40 s reel takes about an hour.
- Everything else (music, SFX, overlay, captions, cover) is generated locally.

## Make them perform

Read the [playbook](playbook/README.md) before your first episode. Short version: the joke is about
**what the viewer does with their AI**, Claude is a character (not a teacher), one tip per episode,
30-40 seconds, and the last frame loops into the first.

For captions, hooks and the rest of the Instagram side we use
[instagram-agent-skill](https://github.com/Jakeschincariol/instagram-agent-skill) (MIT, not part of this repo).

## Troubleshooting

| Symptom | Fix |
|---|---|
| A frame in the stills is completely black | A camera `shake` on a close-up can push the camera through the set: remove it, keep `punch`. |
| Squares instead of ✓ ⚠ → in the overlay | The overlay font has no such glyphs: write words, the panel draws its own check marks. |
| A sticker or stamp appears after the word it illustrates | Anchor it 0.2-0.3 s earlier: `"at": "w:word-0.25"`. |
| `whisper_check.txt` ratio below 0.8 | Listen to the take. If two whisper models hear the same wrong word, re-record or regenerate that line; spell tricky words phonetically in `tts`. |
| A take says a word twice | Trim the file at the silence between them (`ffmpeg -af atrim=0:<seconds>`), no need to pay for a new take. |
| Stills look fine but the real build moved things | Real takes are ≈ 20% longer than `say` drafts: always re-check the stills after adding voices. |

More in [`references/lessons.md`](skills/duo-sketch-reel/references/lessons.md).

## License and credits

Code: [MIT](LICENSE). The Nerd and the orange robot are drawn in code in this repo; use them, remix them,
make your own characters.

Not affiliated with or endorsed by Anthropic. "Claude" is a trademark of Anthropic, PBC; the robot is a
fan character in a comedy series. Blender is a trademark of the Blender Foundation.

Made by [@thedebugduo](https://www.instagram.com/thedebugduo/). New episode every day; follow to see
what the repo makes next.
