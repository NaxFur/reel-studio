"""Procedural synth voices and SFX (48 kHz), shared by make_audio.py. From the eps. 1-7 score."""
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve
SR = 48000
rng = np.random.default_rng(7)
def midi(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def db(x):
    return 10 ** (x / 20)


def lp(x, f, o=2):
    return sosfilt(butter(o, min(f, SR * 0.49), "lowpass", fs=SR, output="sos"), x, axis=0)


def hp(x, f, o=2):
    return sosfilt(butter(o, min(f, SR * 0.49), "highpass", fs=SR, output="sos"), x, axis=0)


def bp(x, lo, hi, o=2):
    return sosfilt(butter(o, [min(lo, SR * 0.48), min(hi, SR * 0.49)], "bandpass", fs=SR, output="sos"), x, axis=0)


def add(buf, sig, t, gain=1.0, pan=0.0):
    a = int(t * SR)
    if a >= len(buf) or a + len(sig) <= 0:
        return
    if sig.ndim == 1:
        l = np.cos((pan + 1) * np.pi / 4)
        r = np.sin((pan + 1) * np.pi / 4)
        sig = np.stack([sig * l * 1.414, sig * r * 1.414], 1)
    s0 = max(0, -a)
    a = max(0, a)
    n = min(len(buf) - a, len(sig) - s0)
    buf[a:a + n] += sig[s0:s0 + n] * gain


def env_adsr(n, a=0.005, d=0.3, s=0.0, r=0.05, hold=None):
    t = np.arange(n) / SR
    e = np.minimum(1, t / max(a, 1e-4))
    dec = s + (1 - s) * np.exp(-(t - a).clip(0) / max(d, 1e-4))
    e = np.where(t < a, e, dec)
    if hold is not None:
        rel = (t - hold).clip(0)
        e = e * np.exp(-rel / max(r, 1e-4))
    return e


def reverb(x, secs=1.5, wet=0.22):
    n = int(secs * SR)
    t = np.arange(n) / SR
    ir = np.stack([rng.standard_normal(n), rng.standard_normal(n)], 1) * np.exp(-t / (secs / 5))[:, None]
    ir = lp(ir, 5500)
    ir /= (np.abs(ir).sum(0) ** 0.5 * 4 + 1e-9)
    y = np.stack([fftconvolve(x[:, c], ir[:, c])[:len(x)] for c in range(2)], 1)
    return x * (1 - wet) + y * wet


# ------------------------------------------------------------------ Synthesis Instruments
def epiano(m, dur, vel=0.6):
    f = midi(m)
    n = int((dur + 1.2) * SR)
    t = np.arange(n) / SR
    idx = 1.5 * np.exp(-t / 0.35) + 0.2
    car = np.sin(2 * np.pi * f * t + idx * np.sin(2 * np.pi * f * t)) + 0.22 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t / 0.2)
    e = env_adsr(n, 0.004, 1.0, 0.0, 0.25, hold=dur)
    trem = 1 + 0.06 * np.sin(2 * np.pi * 4.5 * t)
    x = car * e * trem * vel
    l = x
    r = np.roll(x, int(0.005 * SR))
    return np.stack([l, r], 1) * 0.25


def pad(m, dur, vel=0.5, bright=1600):
    f = midi(m)
    n = int((dur + 0.8) * SR)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for k in range(1, 8):
        for det in (-0.15, 0.14):
            x += np.sin(2 * np.pi * f * k * (1 + det / 100) * t + rng.uniform(0, 6)) / k
    x = lp(x, bright)
    e = np.minimum(1, t / 0.35) * np.where(t > dur, np.exp(-(t - dur) / 0.45), 1)
    y = x * e * vel * 0.05
    return np.stack([y, np.roll(y, int(0.010 * SR))], 1)


def bass(m, dur, vel=0.7):
    f = midi(m)
    n = int((dur + 0.2) * SR)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2 * f * t)
    e = env_adsr(n, 0.008, 0.7, 0.6, 0.1, hold=dur)
    return np.tanh(x * 1.2) * e * vel * 0.35


def riser(dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    out = np.zeros(n)
    for i in range(0, n, 2400):
        fc = 300 + 7000 * (i / n) ** 2
        seg = noise[i:i + 2400]
        out[i:i + 2400] = bp(seg, fc * 0.7, min(fc * 1.4, 20000), 1)
    tone = np.sin(2 * np.pi * np.cumsum(180 + 720 * (t / dur) ** 2) / SR) * 0.3
    return (out + tone) * (t / dur) ** 2 * 0.35


def hop_step():
    """Soft mascot footstep on desk."""
    n = int(0.12 * SR)
    t = np.arange(n) / SR
    thud = np.sin(2 * np.pi * 180 * t) * np.exp(-t / 0.03) * 0.5
    tap = lp(rng.standard_normal(n), 2000) * np.exp(-t / 0.015) * 0.3
    return thud + tap


# ------------------------------------------------------------------ SFX / drum generators
def mouse_click():
    n = int(0.04 * SR)
    t = np.arange(n) / SR
    tick = hp(rng.standard_normal(n), 3500) * np.exp(-t / 0.003) * 0.7
    body = bp(rng.standard_normal(n), 800, 2400) * np.exp(-t / 0.012) * 0.5
    return tick + body


def key_clack(v=1.0):
    n = int(0.05 * SR)
    t = np.arange(n) / SR
    f = rng.uniform(1800, 3200)
    c = bp(rng.standard_normal(n), f * 0.6, f * 1.4) * np.exp(-t / 0.006)
    thock = np.sin(2 * np.pi * rng.uniform(260, 340) * t) * np.exp(-t / 0.012) * 0.5
    return (c + thock) * 0.55 * v


def enter_thunk():
    n = int(0.12 * SR)
    t = np.arange(n) / SR
    return (np.sin(2 * np.pi * 150 * t) * np.exp(-t / 0.03) + bp(rng.standard_normal(n), 900, 3000) * np.exp(-t / 0.01) * 0.6) * 0.8


def chime(base=1318.5):
    n = int(0.9 * SR)
    t = np.arange(n) / SR
    tone = (np.sin(2 * np.pi * base * t) * np.exp(-t / 0.22) * 0.5 +
            np.sin(2 * np.pi * base * 1.26 * t) * np.exp(-t / 0.26) * 0.4 +
            np.sin(2 * np.pi * base * 1.5 * t) * np.exp(-t / 0.32) * 0.35)
    return tone + hp(rng.standard_normal(n), 6000) * np.exp(-t / 0.04) * 0.12


def tick():
    n = int(0.18 * SR)
    t = np.arange(n) / SR
    return (np.sin(2 * np.pi * 1760 * t) * np.exp(-t / 0.05) * 0.5 + np.sin(2 * np.pi * 2637 * t) * np.exp(-t / 0.035) * 0.3
            + hp(rng.standard_normal(n), 5000) * np.exp(-t / 0.003) * 0.3)


def whoosh(dur=0.32):
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    noise = rng.standard_normal(n)
    for i in range(0, n, 1200):
        fc = 500 + 5000 * (i / n) ** 1.5
        out[i:i + 1200] = bp(noise[i:i + 1200], fc * 0.6, min(fc * 1.6, 20000), 1)
    return out * np.sin(np.pi * t / dur) ** 2 * 0.6


def slam(big=False):
    n = int((0.9 if big else 0.5) * SR)
    t = np.arange(n) / SR
    f = (70 if big else 90) * np.exp(-t / 0.08) + (38 if big else 50)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / (0.35 if big else 0.18))
    crack = bp(rng.standard_normal(n), 1500, 7000) * np.exp(-t / 0.02) * 0.5
    return np.tanh((body + crack) * 1.6) * (0.9 if big else 0.7)


def kick():
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    f = 110 * np.exp(-t / 0.04) + 46
    return np.tanh(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.16) * 1.4) * 0.8


def snare():
    n = int(0.25 * SR)
    t = np.arange(n) / SR
    return (bp(rng.standard_normal(n), 1200, 6500) * np.exp(-t / 0.06) * 0.6 + np.sin(2 * np.pi * 190 * t) * np.exp(-t / 0.04) * 0.4) * 0.7


def hat(open_=False):
    n = int((0.18 if open_ else 0.05) * SR)
    t = np.arange(n) / SR
    return hp(rng.standard_normal(n), 7000) * np.exp(-t / (0.05 if open_ else 0.012)) * 0.35


def buzz():
    """'Computer says no' descending double bleep for ETA: 14 hours."""
    out = []
    for f0, d in ((520, 0.16), (390, 0.34)):
        n = int(d * SR)
        t = np.arange(n) / SR
        x = np.sign(np.sin(2 * np.pi * f0 * t)) * 0.25 + np.sin(2 * np.pi * f0 * t) * 0.3
        x = lp(x, 2500) * np.minimum(1, t / 0.005) * np.exp(-(t / d) * 1.2)
        out += [x, np.zeros(int(0.04 * SR))]
    return np.concatenate(out) * 0.8


def twitch_tick():
    n = int(0.03 * SR)
    t = np.arange(n) / SR
    return np.sin(2 * np.pi * 2400 * t) * np.exp(-t / 0.006) * 0.4


def tape_stop(src_len=0.5):
    """Short pitch-falling 'tape stop' blip used as the beat stops."""
    n = int(src_len * SR)
    t = np.arange(n) / SR
    f = 180 * (1 - t / src_len) ** 2 + 30
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * (1 - t / src_len) * 0.5


def sub_hit(d=1.2, f0=55):
    n = int(d * SR)
    t = np.arange(n) / SR
    return np.sin(2 * np.pi * (f0 * np.exp(-t / 0.2) + 36) * t) * np.exp(-t / 0.45) * 0.9


