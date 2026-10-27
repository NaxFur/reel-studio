"""Master: gain to -14 LUFS integrated + look-ahead true-peak limiter (4x oversampled) at -1.5 dBTP.
Loudness is measured with ffmpeg's EBU R128 meter so the target matches what platforms read."""
import os, re, subprocess, sys
import numpy as np, soundfile as sf
from scipy.signal import resample_poly
from scipy.ndimage import minimum_filter1d, uniform_filter1d

ROOT = os.path.abspath(sys.argv[1])   # master_audio.py <proj>
SRC, DST = f"{ROOT}/assets/audio/mix_premaster.wav", f"{ROOT}/assets/audio/master.wav"
TARGET_I, CEIL_TP = -14.0, -1.6


def measure(path):
    out = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    summ = out[out.rfind("Summary:"):]
    i = float(re.search(r"I:\s+(-?[\d.]+) LUFS", summ).group(1))
    tp = float(re.search(r"Peak:\s+(-?[\d.]+) dBFS", summ).group(1))
    return i, tp


def limit(x, ceil_db, sr, look=0.0015, rel=0.08):
    up = resample_poly(x, 4, 1, axis=0)
    peak = np.abs(up).max(1).reshape(-1, 4).max(1)[:len(x)]           # true-peak estimate per sample
    ceil = 10 ** (ceil_db / 20)
    g = np.minimum(1.0, ceil / np.maximum(peak, 1e-9))
    n = int(look * sr)
    g = minimum_filter1d(g, size=2 * n + 1)                              # look-ahead: hold the reduction around peaks
    a = np.exp(-1 / (rel * sr)); out = np.empty_like(g); cur = 1.0
    for i, v in enumerate(g):                                            # instant attack, smooth release
        cur = v if v < cur else v + (cur - v) * a
        out[i] = cur
    out = np.minimum(uniform_filter1d(out, size=n + 1), g)              # smooth, but never above the needed reduction
    return x * out[:, None]


x, sr = sf.read(SRC)
i0, tp0 = measure(SRC)
gain = 10 ** ((TARGET_I - i0) / 20)
y = x * gain
for it in range(4):
    y = limit(y, CEIL_TP, sr)
    sf.write(DST, y.astype(np.float32), sr, subtype="PCM_24")
    i1, tp1 = measure(DST)
    print(f"pass {it}: I={i1:.2f} LUFS TP={tp1:.2f} dBTP")
    if abs(i1 - TARGET_I) < 0.25 and tp1 <= -1.0:
        break
    y = y * 10 ** ((TARGET_I - i1) / 20)
print(f"premaster I={i0:.2f} TP={tp0:.2f} -> master I={i1:.2f} TP={tp1:.2f}")
