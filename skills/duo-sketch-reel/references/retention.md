# Retention formula (what every episode must do)

Goal: the viewer stops on frame 1, never finds a moment to leave, and has a reason to comment, save and
follow. Platform facts we rely on are general (Instagram ranks on watch time, rewatches, shares, saves);
we don't promise numbers.

## The 0-3 s hook (three layers at once)
1. **Visual**: frame 1 is already the disaster - a face in panic (Nerd, `panic` + hands `cheek`) or a red
   screen ECU with readable text. Never a black frame, a logo or an empty room. Frame 1 is also the thumbnail.
2. **Text**: `meta.hook` - 2 short lines + a red badge, visible from frame 1, no fade-in. A claim from
   the story ("CLAUDE REWROTE MY WHOLE APP.") + an open question badge ("3 HOURS GONE?").
3. **Voice**: the first word within 0.5 s, emotional (panic, disbelief), no intro, no "hey guys".

## Structure (30-40 s, 9-12 lines)
| time | beat | purpose |
|---|---|---|
| 0-3 s | Nerd's pain, in panic | hook (relatable: every dev lived it) |
| 3-8 s | Claude's dry one-liner + Nerd's despair | conflict, character comedy, open loop |
| 8-11 s | Claude: the tip in ≤ 4 words ("Press Escape. Twice.") | the promise |
| 11-17 s | the tip shown working on the monitor (close-up), keys on screen | proof, rewatch value |
| 17-24 s | how/why in one sentence + overlay panel (save-worthy) + the honest limit | saves, trust |
| 24-30 s | twist: Nerd suspects Claude, Claude's deadpan punchline | laugh = shares |
| 30-33 s | title card: the tip as a formula + "Comment KEYWORD for the cheat sheet" | comments (DM) |
| 33-38 s | stinger: Nerd repeats the mistake → cut to frame 1 | loop = rewatch |

## Pace
- A cut every 1.5-3 s; never hold one shot more than 4 s (use `punch` or a cut inside long lines).
- Gaps 0.1-0.25 s between lines; a longer pause (0.3-0.4) only right before a punchline.
- Subtitles always on, ≤ 3 words per chunk, key words yellow.
- Music changes on story turns (tense → stop → groove → drone → resolve → lofi → tense for the loop).
- Something moves every second: Claude bounces on stressed words, the Nerd reacts with face+pose+hands.

## Comment / follow drivers
- Title card keyword (DM workflow sends the guide). The guide page must be genuinely useful.
- One mildly debatable line in the caption or the punchline ("It was ugly.") invites replies.
- Series consistency: same set, same two characters, same ending loop → people follow for the next one.

## Topics (one tip per episode)
Good: a hidden feature / shortcut / command of a tool devs use daily, a safety lesson with a fix, a common
mistake with a 10-second fix, "X vs Y" with a clear verdict. The tip must be verifiable in official docs
and usable today. Pain first, tool second.

Idea bank (verify each before use; skip what you've already posted):
- Claude Code: plan mode, `/rewind` ✔ (2026-10-25), CLAUDE.md memory, `/compact`, `--continue`/`--resume`,
  hooks, custom slash commands / skills, subagents, permission modes.
- Git: `git reflog` (undo almost anything), `git bisect`, `git stash -u`, `git commit --fixup`, `.gitignore`
  after the leak (`git rm --cached`).
- Security: secrets in `.env` committed, `npm audit`, prompt injection in a README the agent reads.
- Terminal: `Ctrl+R`, `!!`, `cd -`; VS Code multi-cursor; Chrome DevTools "copy as fetch".
- Founder lessons (eps. 1-7 style): validate first, distribution > building, charge more.

Avoid: piracy/abuse/ToS evasion, politics, NSFW, inflated-star repos, anything you can't source.

## Before the final render, ask
- Would I stop on frame 1 with the sound off? (text + face readable at 360x640)
- Is there any 4-second stretch where nothing new happens?
- Is the tip stated before 12 s and shown working?
- Does the last frame cut cleanly into the first?
