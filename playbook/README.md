# The playbook

What we learned making sketch reels for [@thedebugduo](https://www.instagram.com/thedebugduo/), with our
own numbers. Small account, small sample: read these as directions, not laws.

## 1. What our own data says

Instagram API insights for our first 17 reels (read 26 Oct 2026):

| | orange-robot sketches (7) | 60 s pixel-art tutorials (9) |
|---|---|---|
| median views | **1,797** | 1,142 |
| watched on average | **16.6 s of ~40 s (47%)** | 8.5 s of ~60 s (14%) |
| likes per reach | **3.9%** | 1.2% |

- Our only breakout before this repo was a sketch: "I pushed .env to GitHub", 9,446 views, about 7× our
  median.
- Its sequel, made with this repo's pipeline, had 2,760 views and 18 s average watch (44% of 41 s) after
  11 hours, about 2× our median.
- **The weak spot everywhere is shares.** We stayed under 1% shares per reach. A share is a viewer
  sending the reel to someone: write the punchline so it's obvious who they'd send it to.

## 2. What the sketches that do numbers have in common

From reading the top skits in the "you and your AI" niche (patterns only, never copy anyone's jokes):

1. **The joke is about the viewer.** Their own behaviour with their AI: not reading what it wrote,
   asking it to "make it scale", being proud of debugging alone, shouting in caps lock. Nobody learns a
   feature from the joke.
2. **The AI is a character.** Deadpan, a little passive-aggressive, always right, always gets the last
   line. The human is the one who's wrong.
3. **Line one is the human, first person, talking to the AI.** "Okay. Deleted the commit. We're safe."
4. **Very specific numbers inside the story**: a time, a count, a bill ("attempt twelve", "thirty seconds
   ago"). They are story details, not claims.
5. **The ending flips the opening** and the last frame cuts back into the first, so the replay is free.
6. **Short, first-person captions**, lowercase, one emoji: "told claude to fix the button 13 times. it was
   fixed the whole time 🫠". Not a wall of instructions.

## 3. Structure (30-40 s)

| time | beat |
|---|---|
| 0-3 s | Nerd's pain. Frame 1 is already the disaster (red screen or panic face) + 2-line hook text + a badge with an open question |
| 3-10 s | Claude's dry one-liner, the Nerd escalates (two or three rounds) |
| 10-20 s | the reveal / the tip in ≤ 5 words, shown working on the monitor |
| 20-28 s | the tip as a 3-point panel (the save), then the twist: "why didn't you say so?" → deadpan answer |
| 28-31 s | title card: the tip as a formula + "Comment KEYWORD" |
| 31-36 s | stinger: the Nerd repeats the mistake → cut to frame 1 |

Pace: a cut every 1.5-3 s, never hold a shot more than 4 s, subtitles always on (≤ 3 words per chunk),
the music changes on every story turn. Details: [`retention.md`](../skills/duo-sketch-reel/references/retention.md).

## 4. Rules we don't break

- **Every fact is sourced.** A `research.md` per episode with URL and date. The story can be fiction; the
  tip can't. If you can't verify it, it doesn't go in.
- **One idea per reel.** Two tips = two reels.
- **No tutorial in a costume.** If half the lines are instructions, it's a tutorial and retention drops.
  One tip line, one panel, done.
- **Free draft first.** Fix the layout with system voices and stills before paying for a single credit.
- **Five hashtags max.** Instagram limited captions to five hashtags in December 2025
  ([Social Media Today](https://www.socialmediatoday.com/news/instagram-implements-new-limits-on-hashtag-use/808309/)).

## 5. The comment-to-DM funnel

Each reel ends with "Comment KEYWORD", and a small automation replies with a DM (the link plus a
step-by-step guide page). It turns viewers into comments (a signal for the algorithm) and into people who
have actually used the tip. Keep the keyword one word, in capitals, and different from your recent reels.
This repo doesn't include our automation: it depends on your Instagram app and tokens. Use Instagram's
own tools or an approved partner, and never automate likes, follows or cold DMs: that breaks Instagram's
Terms.

## 6. A starter idea bank

Verify each tip in official docs before you use it.

- Claude Code: `/rewind` and checkpoints, plan mode, `CLAUDE.md` memory, `/compact`, `--continue`, hooks,
  custom slash commands, subagents, permission modes.
- Git: `git reflog`, `git bisect`, `git stash -u`, `git commit --fixup`, `.gitignore` after a leak
  (`git rm --cached`).
- Dev servers and tooling: ports that move, hard refresh vs cache, "works on my machine" env vars.
- Security: secrets in a pushed `.env` (rotate first), `npm audit`, prompt injection in a README the agent reads.
