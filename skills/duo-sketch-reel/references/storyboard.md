# storyboard.json

Working example: `viral_videos/2026-10-25_claude_undo/storyboard.json`.

```jsonc
{
 "meta": {
  "series": "duo", "title": "...", "language": "en",
  "cta_keyword": "UNDO",                 // one word, capitals, unique in the last 7 days (DM workflow)
  "caption": "...", "hashtags": ["#claudecode", ...],   // no "Comment X" line
  "hook": {"text": "LINE 1\nLINE 2", "badge": "RED BADGE", "badge_color": "red", "until": "L01.end",
           "variant_b": {"text": "...", "badge": "..."}},          // final_b.mp4 for an A/B test
  "title_card": {"line1": "ESC + ESC", "line2": "= UNDO", "cta_tail": " for the cheat sheet"},
  "cover": {"beat": "L04", "at": "wend:twice", "line1": "...", "line2": "...", "badge": "..."},
  "sticky": ["3 lines", "on the", "sticky note"],
  "light": "alarm",                      // starting light preset
  "claude_spot": "desk", "claude_eyes": "flat",
  "nerd_start": {"face": "panic", "pose": "recoil", "hands": ["cheek", "cheek"], "look": "screen"},
  "screen_default": {"center": {...}, "left": {...}, "right": {...}},   // monitor states before any beat sets one
  "music": [{"at": 0, "style": "tense"}, {"at": "L04.start", "style": "none", "stop": "tape"}, ...],
  "music_db": -20,
  "resources": {"title", "summary", "main_link", "links": [{label,url}], "steps": [{title,text,code}], "notes": []}
 },
 "beats": [ ... ]
}
```

## Beats
Placed one after the other. A **line** beat has `speaker` (`nerd` | `claude`), `text` (what the subtitles
show; words are matched to the take), `tts` (sent to ElevenLabs, with audio tags). A **hold** beat has
`hold` seconds (silent action, title card, loop shot).

| key | meaning |
|---|---|
| `id` | `L01`… for lines, anything for holds (`B05`, `TITLE`, `END`) |
| `gap` | silence before the beat (default 0.22 for lines, 0 for holds); comedy timing lives here |
| `tail` | extra seconds after a line |
| `tighten` | `[max_gap, new_gap]` shortens long pauses inside a take (default `[0.45, 0.30]`), `null` = off |
| `word_fix` | `{"3": 1.80}` word index → start (s from clip start) when whisper drifts |
| `shot` | camera at the beat start (cut 0.10 s before a line: `cut_lead`) |
| `cuts` | `[{"at": anchor, "shot": ...}]` extra cuts inside the beat |
| `nerd`, `claude` | acting keys (below) |
| `screens` | `{"center"|"left"|"right": [state, ...]}` monitor states (below) |
| `overlay` | overlay items (below) |
| `sfx`, `light` | sound effects / light presets at anchors |
| `emph` | words shown in yellow in the subtitles |
| `chunks` | subtitle chunk sizes, e.g. `[2, 3]` (default: ≤ 3 words, break on punctuation) |
| `sub_y` | subtitle centre y (default 1235; 1480 over a monitor close-up) |
| `no_subs`, `title` | hide subtitles / this hold is the title card |
| `sources` | URLs for this beat (listed on the guide page) |

## Anchors (every `at`, `until`)
`start`, `end`, `w:<prefix>` (start of the first word starting with prefix), `w:<prefix>#2`,
`wend:<prefix>`, `L05.w:restore` (another beat), plus offsets: `w:git-0.25`, `end+0.1`, or a number.
**Payoffs (stamps, keys, ticks) go 0.2-0.3 s before the word they illustrate, never on the last word.**

## Shots (`"shot": "name"` or `{"name", "punch": [{"at", "amt": 1.15}], "tgt_off": [x,y,z], "pos_off", "lens", "static", "shake"}`)
| name | what it sees |
|---|---|
| `ecu_center` | extreme close-up of the centre monitor (hook / loop); content in the lower 60 %, hook text above |
| `monitor_ecu` | close-up of the centre monitor, slightly wider (menus, demos); set `sub_y: 1480` |
| `ots_nerd` | over the Nerd's left shoulder onto the monitors (typing, pressing keys) |
| `nerd_mcu` / `nerd_cu` | Nerd from the front, medium / tight (reactions). `tgt_off [0,0,0.16]` pushes the face below the hook |
| `claude_cu` | Claude on the desk, 3/4 front (Claude must face `cheat` or the camera) |
| `claude_lens` / `claude_lens_close` | Claude at the desk **edge** facing the lens (lessons, the tip, the twist) |
| `wide_monitors`, `left_mon`, `right_mon`, `center_push` | listicles over 3 monitors |
| `two_shot` | both characters (check framing in stills before relying on it) |
| `title` | under the title card |
`punch` = a fast zoom-in on a word (pattern interrupt; 1-2 per video, on the key words).

## Nerd keys (`"nerd": [{at, ...}]`)
- `face`: neutral, attentive, surprised, panic, exhausted, sad, confused, amazed, relief, suspicious, angry, ecstatic, smug
- `look`: screen, mascot (follows Claude), nerd_lens, keyboard, left, right, up, down, or `[x,y,z]`; `look_off`
- `pose`: upright, slump, lean_in, lean_back, tilt, amazed, recoil, hunch
- `hands`: `[left, right]` from lap, desk, type, face (chin on hand), head, cheek (Home-Alone scream), point, shrug, mouse (right only); `null` keeps one
- `gaze`: lens | none (eyes to camera)
- `do`: type (`until`), tap / tap_r (one key), click, shake (head no)
- durations: `fdur` `ldur` `pdur` `hdur` (0.01 = snap, for cuts that must match)

## Claude actions (`"claude": [{at, do, ...}]`)
turn (`to`: nerd, cheat, lens, center, left, right, keyboard), point (`to`, `arm` L|R, `until`), hop (`to`
spot), walk (`to`: desk | edge | kb, `face`), bounce (`amt`), arms_up, self (points at itself), lean,
eyes (`to`: flat, open, wide, squint, closed), twitch, shake (no), nod. Spots: `desk` (next to the Nerd),
`edge` (front-right edge, for `claude_lens`), `kb` (by the keyboard). Walk to `edge` while the camera is on
the Nerd, then cut to `claude_lens`.

## Monitor states (`screens`)
Each state shows from its `at` until the next state on that monitor.
- `terminal`: `title`, `lines` (prefixes colour them: `> ` prompt, `✓ ` ok, `✗ ` error, `! ` warn, `● ` claude,
  `# ` dim, `$ ` command, `+ `/`- ` diff), `typed` (types the last line; `cps`, `type_delay`), `reveal`
  (anchor per line), `progress` {from,to,dur,label,color}, `big` {text,color,sub,at}, `scale`, `y0`
- `menu`: `header`, `items`, `sel` [{at,i}], `sub` {at, header, items, sel}, `done` {at, text, sub}, `hint`, `scale`
- `card`: `kicker`, `title`, `sub`, `lines`, `accent`, `slam` · `alert`: `title`, `sub`, `icon`, `color`, `flash`
- `code`: `file`, `lines`, `hl` · `idle`: `title`, `seed`, `scroll` · `black`
Centre-monitor text lives in x 600..1820 (what a close-up sees). Fonts: SF Mono; no emoji/⏪ on monitors.

## Overlay items
- `chip` {text, color, y} pill · `keys` {keys: ["ESC","ESC"], key_at: [anchors], y} keycaps that press
- `panel` {title, items: [{text, sub, at}], y} checklist that ticks · `stamp` {text, color, y, rot}
All have `at`/`until`. Avenir has no ✓ → ⚠ ✗ glyphs: write words (the panel draws its own check marks).
Keep items out of the face: in Claude close-ups the eyes sit at y≈650-750.

## Lights (`"light": [{at, preset, dur}]`)
normal, alarm (red, disaster), green (fixed), gold (reveal), spot (warm key on Claude's lesson), dim (suspense).

## Music (`meta.music`)
tense (disaster), groove (the fix / the list), lofi (chill / stinger), drone (suspicion), resolve (title
card), none. `"stop": "tape"` = tape-stop SFX on the change (comedic beat drop).

## Auto SFX
typing, taps, clicks, Claude hops/walks, keycaps, stamps, panel ticks, chips, card slams, alerts. Extra:
`sfx` types click, key, typing (`until`), enter, chime, tick, whoosh, slam, slam_big, buzz, twitch, hop,
sub, tape_stop, riser (`dur`).
