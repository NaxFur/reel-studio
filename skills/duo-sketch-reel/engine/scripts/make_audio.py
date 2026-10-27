"""Procedural score + sound design from the storyboard, ducked under the dialogue (no credits spent).

  make_audio.py <proj>

Music: meta.music = [{"at": anchor, "style": "tense|groove|lofi|drone|resolve|none", "stop": "tape"}], each cue
plays until the next one. SFX: explicit per-beat `sfx` items plus automatic ones (typing, taps, clicks, hops,
walks, key caps, stamps, panel ticks, card slams, cut whooshes). Writes stems + assets/audio/mix_premaster.wav;
master_audio.py brings it to -14 LUFS / -1.6 dBTP.
"""
import os, sys
import numpy as np, soundfile as sf

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scene"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tl import proj_paths, load_sb, load_tl, Anchors, screen_states
from synth import *  # noqa: F401,F403  (SR, add, db, lp, pad, epiano, bass, kick, snare, hat, ...)

proj = sys.argv[1]
P = proj_paths(proj)
SB, TL = load_sb(proj), load_tl(proj)
A = Anchors(TL)
DUR = TL["duration"]
N = int(DUR * SR)
B0 = SB["beats"][0]["id"]


def seg_buf(d):
    return np.zeros((int((d + 2.5) * SR), 2))


def cut_tail(x, d, tau=0.04):
    c = int(d * SR)
    if c < len(x):
        x[c:] *= np.exp(-np.arange(len(x) - c) / (tau * SR))[:, None]
    return x


def m_tense(d):
    """Panic bed: pulsing low minor drone + ticking 8ths at 120 BPM, rising filter."""
    x = seg_buf(d)
    for m in (33, 40, 45):
        add(x, pad(m, d + 0.3, 0.55, 700), 0.0)
    beat = 0.5
    k = 0
    while k * beat / 2 < d:
        add(x, hat(), k * beat / 2, db(-12 if k % 2 == 0 else -17), pan=0.25)
        if k % 4 == 0:
            add(x, kick(), k * beat / 2, db(-6))
        k += 1
    add(x, np.stack([riser(min(d, 2.5))] * 2, 1) * 0.35, max(0, d - min(d, 2.5)))
    return cut_tail(x, d)


def m_groove(d, bpm=96):
    x = seg_buf(d)
    beat = 60 / bpm
    prog = [(41, 56, 60, 63), (37, 53, 56, 60), (39, 55, 58, 63), (36, 52, 55, 60)]
    for b in range(int(d / beat) + 1):
        t0 = b * beat
        sw = 0.06 * beat
        if b % 4 in (0, 2): add(x, kick(), t0, db(-3))
        if b % 4 == 2: add(x, kick(), t0 + beat * 0.5 + sw, db(-7))
        if b % 4 in (1, 3): add(x, snare(), t0, db(-6))
        add(x, hat(), t0, db(-14), pan=0.3)
        add(x, hat(b % 8 == 7), t0 + beat * 0.5 + sw, db(-17), pan=0.3)
        if b % 4 == 0:
            ch = prog[(b // 4) % 4]
            add(x, bass(ch[0], beat * 3.6, 0.75), t0)
            for m in ch[1:]:
                add(x, epiano(m, beat * 3.4, 0.22), t0 + 0.02)
    return cut_tail(reverb(x, 0.9, 0.12) * 0.85, d, 0.03)


def m_lofi(d):
    x = seg_buf(d)
    chords = [(41, 53, 56, 60, 63, 67), (37, 49, 53, 56, 60, 65)]
    tt, k = 0.0, 0
    while tt < d:
        ch = chords[k % 2]
        for m in ch: add(x, pad(m, 2.5, 0.42, 1100), tt)
        for j, m in enumerate(ch[2:]): add(x, epiano(m + 12, 0.6, 0.18), tt + 0.15 + j * 0.42)
        tt += 2.5; k += 1
    tl_ = np.arange(len(x)) / SR
    x *= (1 + 0.04 * np.sin(2 * np.pi * 0.7 * tl_))[:, None]
    return cut_tail(reverb(lp(x, 2400), 1.3, 0.22) * 0.75, d)


def m_drone(d):
    x = seg_buf(d)
    for m in (29, 36, 41):
        add(x, pad(m, d + 0.2, 0.6, 500), 0.0)
    return cut_tail(x * 0.8, d, 0.08)


def m_resolve(d):
    x = seg_buf(d)
    for m in (32, 44, 56, 60, 63, 68, 72):
        add(x, pad(m, d - 0.1, 0.8, 3000), 0.0)
    for j, m in enumerate((68, 72, 75, 80)):
        add(x, epiano(m, 1.2, 0.35), 0.05 + j * 0.11)
    add(x, np.stack([sub_hit()] * 2, 1) * 0.8, 0.0)
    return cut_tail(reverb(x, 1.6, 0.25), d, 0.05)


STYLES = {"tense": m_tense, "groove": m_groove, "lofi": m_lofi, "drone": m_drone, "resolve": m_resolve}

mus = np.zeros((N + SR * 3, 2))
sfx = np.zeros((N + SR * 3, 2))
cues = sorted([(A(c.get("at"), B0), c) for c in SB["meta"].get("music", [])], key=lambda c: c[0])
for i, (t0, c) in enumerate(cues):
    t1 = cues[i + 1][0] if i + 1 < len(cues) else DUR
    if c.get("stop") == "tape":
        add(sfx, np.stack([tape_stop()] * 2, 1), t0 - 0.05, db(-12))
    if c["style"] in STYLES and t1 - t0 > 0.05:
        add(mus, STYLES[c["style"]](t1 - t0) * db(c.get("gain_db", 0)), t0)
music = mus[:N]
fade = np.ones(N); fe = int((DUR - 0.05) * SR); fade[fe:] = np.linspace(1, 0, N - fe)
music *= fade[:, None]

# duck the music under the dialogue
dia, _ = sf.read(os.path.join(proj, "assets/audio/stems/dialogue.wav"))
dia = dia[:N] if len(dia) >= N else np.pad(dia, (0, N - len(dia)))
win = int(0.02 * SR)
envd = np.sqrt(np.convolve(dia ** 2, np.ones(win) / win, "same"))
active_ = (20 * np.log10(envd + 1e-9) > -38).astype(float)
g = np.zeros(N); cur = 0.0
att, rel = 1 - np.exp(-1 / (0.04 * SR)), 1 - np.exp(-1 / (0.35 * SR))
for i in range(0, N, 48):
    tgt = active_[i]
    cur += (tgt - cur) * (1 - (1 - (att if tgt > cur else rel)) ** 48)
    g[i:i + 48] = cur
menv = np.sqrt(np.convolve((music ** 2).mean(1), np.ones(win) / win, "same"))
sounding = 20 * np.log10(menv + 1e-9) > -60
if sounding.any():
    music *= db(SB["meta"].get("music_db", -20.0)) / (np.sqrt((music[sounding] ** 2).mean()) + 1e-9)
music = music * (db(-12.0) * g + (1 - g))[:, None]

# ------------------------------------------------------------------ SFX
FX = {"click": (mouse_click, -13), "key": (key_clack, -11), "enter": (enter_thunk, -9), "chime": (chime, -10),
      "tick": (tick, -12), "whoosh": (whoosh, -15), "slam": (lambda: slam(False), -10), "slam_big": (lambda: slam(True), -7),
      "buzz": (buzz, -12), "twitch": (twitch_tick, -15), "hop": (hop_step, -12), "sub": (lambda: np.stack([sub_hit(1.6, 50)] * 2, 1), -6),
      "tape_stop": (lambda: np.stack([tape_stop()] * 2, 1), -12)}


def fx(name, t, gain=0.0, pan=0.0):
    if name == "typing":
        return
    fn, base = FX[name]
    add(sfx, fn(), t, db(base + gain), pan=pan)


for b in SB["beats"]:
    bid = b["id"]
    for s in b.get("sfx", []) or []:
        t = A(s.get("at"), bid)
        if s["type"] == "typing":
            tt, t1 = t, A(s.get("until"), bid) if s.get("until") else t + s.get("dur", 1.0)
            while tt < t1:
                add(sfx, key_clack(rng.uniform(0.7, 1.0)), tt, db(-13 + s.get("gain", 0)), pan=rng.uniform(-0.2, 0.2))
                tt += rng.uniform(0.06, 0.1)
        elif s["type"] == "riser":
            add(sfx, np.stack([riser(s.get("dur", 1.0))] * 2, 1) * 0.5, t, db(s.get("gain", 0)))
        elif s["type"] == "twitch":
            for k in range(7):
                add(sfx, twitch_tick(), t + k * 0.09, db(-16 - k), pan=0.2)
        else:
            fx(s["type"], t, s.get("gain", 0), s.get("pan", 0))
    for it in b.get("nerd", []) or []:
        t = A(it.get("at"), bid)
        if it.get("do") == "type" and not it.get("silent"):
            t1 = A(it["until"], bid) if "until" in it else t + 1.0
            tt = t + 0.12
            while tt < t1 - 0.06:
                add(sfx, key_clack(rng.uniform(0.7, 1.0)), tt, db(-14), pan=rng.uniform(-0.2, 0.2)); tt += rng.uniform(0.06, 0.1)
        elif it.get("do") in ("tap", "tap_r"):
            fx("key", t, 2)
        elif it.get("do") == "click":
            fx("click", t, 0, -0.3)
    for it in b.get("claude", []) or []:
        t = A(it.get("at"), bid)
        if it.get("do") == "hop":
            fx("whoosh", t, -2, 0.25); fx("hop", t + it.get("dur", 0.30), 0, 0.25)
        elif it.get("do") == "walk":
            for k in range(int(it.get("dur", 0.6) / 0.14)):
                fx("hop", t + 0.1 + k * 0.14, -7, 0.3)
        elif it.get("do") == "twitch":
            for k in range(7):
                add(sfx, twitch_tick(), t + k * 0.09, db(-16 - k), pan=0.2)
    for it in b.get("overlay", []) or []:
        t = A(it.get("at"), bid)
        if it["type"] == "keys":
            for x in (it.get("key_at") or [it.get("at")] * len(it["keys"])):
                tk = A(x, bid); fx("key", tk, 3); fx("tick", tk + 0.02, -4)
        elif it["type"] == "stamp":
            fx("slam_big", t, 0); fx("chime", t + 0.04, -4)
        elif it["type"] == "panel":
            for r in it["items"]:
                fx("tick", A(r.get("at", it.get("at")), bid), 0)
        elif it["type"] == "chip":
            fx("tick", t, -3)
    for c in b.get("cuts", []) or []:
        if isinstance(c.get("shot"), dict) and c["shot"].get("whoosh"):
            fx("whoosh", A(c.get("at"), bid) - 0.18, -4)
for mon in ("center", "left", "right"):
    for t0, st in screen_states(SB, A, mon):
        if st.get("type") == "card" and st.get("slam", True):
            fx("whoosh", t0 - 0.26, 0, 0); fx("slam", t0, 0)
        if st.get("type") == "alert":
            fx("buzz", t0, 0)
sfx = sfx[:N]

t_arr = np.arange(N) / SR
amb = (np.sin(2 * np.pi * 120 * t_arr) * 0.12 + np.sin(2 * np.pi * 240 * t_arr) * 0.04)[:, None] + lp(rng.standard_normal((N, 2)), 600) * 0.5
amb *= db(-48.0) / (np.sqrt((amb ** 2).mean()) + 1e-9)
amb *= fade[:, None]

mix = np.stack([dia, dia], 1) + music + sfx + amb
peak = np.abs(mix).max()
if peak > 0.98:
    mix *= 0.98 / peak
st_dir = os.path.join(proj, "assets/audio/stems")
for name, x in (("music", music), ("sfx", sfx), ("ambience", amb)):
    sf.write(os.path.join(st_dir, f"{name}.wav"), x.astype(np.float32), SR, subtype="PCM_24")
sf.write(os.path.join(proj, "assets/audio/mix_premaster.wav"), mix.astype(np.float32), SR, subtype="PCM_24")
rms = lambda x: 20 * np.log10(np.sqrt((x ** 2).mean()) + 1e-9)
print(f"audio: dialogue {rms(dia):.1f} dB, music {rms(music):.1f} dB, sfx {rms(sfx):.1f} dB, peak {20 * np.log10(np.abs(mix).max()):.1f} dBFS")
