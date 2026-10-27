# Lessons (eps. 1-7 + the first data-driven episode)

- The hook text covers the top 25 % of the frame: in Nerd close-ups during the hook add
  `"tgt_off": [0, 0, 0.16]` so his face sits under it.
- Hands `head` reads as relaxed ("hands behind the head"); for panic use `cheek` (Home-Alone scream).
- A payoff anchored on the beat's last word appears too late (the cut follows): anchor 0.2-0.3 s earlier.
  The stills sample each beat's end - 0.25 s exactly to catch this.
- Avenir (overlay) has no ✓ ⚠ → glyphs and SF Mono (monitors) has no ⏪: they render as boxes.
- Claude close-ups: keep stamps/chips away from y 600-800 (its eyes).
- ElevenLabs eleven_v4 ≈ 1 credit per character of `tts` (tags included): an 11-line episode ≈ 700.
- whisper glues/mishears words; if two models agree on a mispronunciation the take is wrong: phonetic
  spelling fixes it ("Ree-motion"). `project/whisper_check.txt` lists script vs heard with a ratio.
- Rig: Claude's stub arms are short; "pointing" is a forward/up slide of the arm, not a rotation.
- EEVEE 1080x1920 with motion blur: 16 samples ≈ 10 s/frame per worker (3 workers ≈ 3.2 s/frame overall, eps. 1-7 used 16 too); 48 samples is 3x slower (≈ 4 h per reel) for no visible gain.
- Overlay/screen frames are hard-linked when identical: everything that changes over time must be in
  the cache key (each template returns its key parts).
- The free `say` draft timeline is shorter than the real takes (≈ 20 %): re-check stills after the takes.
