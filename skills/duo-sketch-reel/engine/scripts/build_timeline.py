"""Dialogue edit + master timeline, from storyboard.json and the voice takes.

  build_timeline.py <proj> [--say]

Takes: <proj>/assets/audio/dialogue_raw/<beat id>.mp3|.wav (ElevenLabs, one file per line beat).
--say: free draft voices with macOS `say` (Nerd = Fred, Claude = Daniel) in dialogue_say/, for layout work.

Writes:
  assets/audio/dialogue/<id>.wav    processed clip (48 kHz mono)
  assets/audio/stems/dialogue.wav   full-length dialogue stem
  project/timeline.json             beats (start/end/words) + duration
  project/lipsync.json              per-frame mouth envelopes for nerd / mascot
  project/whisper_check.txt         what whisper heard vs the script (mispronunciation check)
"""
import difflib, json, os, subprocess, sys
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scene"))
from tl import proj_paths, load_sb, FPS

SR = 48000
WHISPER = os.path.expanduser(os.environ.get("WHISPER_MODEL", "~/whisper-models/ggml-medium.en.bin"))
SAY_VOICE = {"nerd": ("Fred", 190), "claude": ("Daniel", 185)}


def load(path):
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(pcm, dtype=np.float32).copy()


def env_db(x, win=0.01):
    n = int(SR * win); m = len(x) // n
    return 20 * np.log10(np.sqrt((x[:m * n].reshape(m, n) ** 2).mean(1)) + 1e-9), win


def voiced_segments(x, thresh=-42, min_gap=0.18):
    db, w = env_db(x)
    segs, start, gap, last = [], None, 0, 0
    for i, on in enumerate(db > thresh):
        if on:
            if start is None: start = i
            gap = 0; last = i
        elif start is not None:
            gap += 1
            if gap * w >= min_gap:
                segs.append((start * w, (last + 1) * w)); start = None
    if start is not None: segs.append((start * w, (last + 1) * w))
    return segs


def trim(x, pre=0.03, post=0.09):
    segs = voiced_segments(x)
    if not segs:
        return x
    a, b = max(0, segs[0][0] - pre), min(len(x) / SR, segs[-1][1] + post)
    y = x[int(a * SR):int(b * SR)].copy()
    f = int(0.008 * SR); y[:f] *= np.linspace(0, 1, f); y[-int(0.03 * SR):] *= np.linspace(1, 0, int(0.03 * SR))
    return y


def tighten(x, max_gap, new_gap, xf=0.012):
    """Shorten silences longer than max_gap to new_gap (short crossfades); never speeds the voice."""
    segs = voiced_segments(x)
    cuts = [(e + new_gap / 2, s - new_gap / 2) for (_, e), (s, _) in zip(segs, segs[1:]) if s - e > max_gap]
    if not cuts:
        return x
    out, pos, n = [], 0, int(xf * SR)
    for a, b in cuts:
        piece = x[pos:int(a * SR)].copy()
        if out: piece[:n] *= np.linspace(0, 1, n)
        piece[-n:] *= np.linspace(1, 0, n)
        out.append(piece); pos = int(b * SR)
    last = x[pos:].copy(); last[:n] *= np.linspace(0, 1, n); out.append(last)
    return np.concatenate(out)


def process(y, gain_db):
    y = sosfilt(butter(2, 85, "highpass", fs=SR, output="sos"), y)
    db, w = env_db(y, 0.005)
    target = -np.maximum(db + 24, 0) * (1 - 1 / 3)            # gentle 3:1 compressor above -24 dB
    sm = np.zeros_like(target); g = 0.0
    for i, t in enumerate(target):
        g += (t - g) * (0.4 if t < g else 0.04); sm[i] = g
    gain = np.repeat(10 ** (sm / 20), int(SR * 0.005))
    gain = np.pad(gain, (0, max(0, len(y) - len(gain))), constant_values=gain[-1])[:len(y)]
    y = y * gain
    seg_db, _ = env_db(y)
    act = seg_db[seg_db > -40]
    rms_db = 10 * np.log10(np.mean(10 ** (act / 10))) if len(act) else -30
    return (y * 10 ** ((-19 - rms_db + gain_db) / 20)).astype(np.float32)


NUM = {"0": "zero", "1": "one", "2": "two", "3": "three", "4": "four", "5": "five", "10": "ten", "100": "onehundred"}


def norm(txt):
    out = []
    for tok in txt.replace("-", " ").replace("/", " slash ").split():
        k = "".join(ch for ch in tok.lower() if ch.isalnum())
        out.append(NUM.get(k, k))
    return "".join(out)


def whisper_words(path, dur):
    tmp = path[:-4] + "_16k.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", path, "-ar", "16000", "-ac", "1", tmp], check=True)
    subprocess.run(["whisper-cli", "-m", WHISPER, "-f", tmp, "-ml", "1", "-sow", "-ocsv", "-of", tmp[:-4], "-np"],
                   capture_output=True, text=True)
    rows = open(tmp[:-4] + ".csv").read().strip().splitlines()[1:] if os.path.exists(tmp[:-4] + ".csv") else []
    for p in (tmp, tmp[:-4] + ".csv"):
        if os.path.exists(p): os.remove(p)
    out = []
    for row in rows:
        parts = row.split(",", 2)
        if len(parts) == 3:
            t = parts[2].strip().strip('"').strip()
            if t:
                out.append({"w": t, "start": int(parts[0]) / 1000, "end": int(parts[1]) / 1000})
    return out


def align(text, ws, y, dur, fixes):
    """Whisper tokens -> the script's own words (character alignment), word starts snapped out of silences."""
    disp = text.split()
    if not ws:
        step = dur / max(1, len(disp))
        return [{"w": d, "start": i * step, "end": (i + 1) * step} for i, d in enumerate(disp)]
    chars, ct = [], []
    for w in ws:
        n = norm(w["w"])
        for i, ch in enumerate(n):
            chars.append(ch); ct.append(w["start"] + (w["end"] - w["start"]) * i / max(1, len(n)))
    dchars, owner = [], []
    for j, dw in enumerate(disp):
        for ch in norm(dw):
            dchars.append(ch); owner.append(j)
    sm = difflib.SequenceMatcher(None, "".join(dchars), "".join(chars), autojunk=False)
    t_of = [None] * len(dchars)
    for blk in sm.get_matching_blocks():
        for k in range(blk.size):
            t_of[blk.a + k] = ct[blk.b + k]
    starts = [None] * len(disp)
    for i, j in enumerate(owner):
        if t_of[i] is not None and starts[j] is None:
            starts[j] = t_of[i]
    known = [(j, s) for j, s in enumerate(starts) if s is not None]
    for j in range(len(disp)):
        if starts[j] is None:
            prv = max((k for k in known if k[0] < j), default=(-1, ws[0]["start"]), key=lambda k: k[0])
            nxt = min((k for k in known if k[0] > j), default=(len(disp), ws[-1]["end"]), key=lambda k: k[0])
            starts[j] = prv[1] + (nxt[1] - prv[1]) * (j - prv[0]) / (nxt[0] - prv[0])
    segs = voiced_segments(y)
    for j in range(len(disp)):
        for (a, b), nx in zip(segs, segs[1:] + [(1e9, 1e9)]):
            if b <= starts[j] < nx[0]:
                starts[j] = nx[0]; break
    for j, t in (fixes or {}).items():
        starts[int(j)] = float(t)
    for j in range(1, len(disp)):
        starts[j] = max(starts[j], starts[j - 1] + 0.06)
    out = []
    for j, dw in enumerate(disp):
        end = starts[j + 1] if j + 1 < len(disp) else min(dur, segs[-1][1] if segs else dur)
        inside = [e for s, e in segs if s <= starts[j] + 0.05 and e >= starts[j]]
        if inside: end = min(end, inside[0])
        out.append({"w": dw, "start": starts[j], "end": max(end, starts[j] + 0.05)})
    return out


def main():
    proj = sys.argv[1]
    say = "--say" in sys.argv
    P = proj_paths(proj)
    SB = load_sb(proj)
    raw = os.path.join(proj, "assets/audio", "dialogue_say" if say else "dialogue_raw")
    out_d = os.path.join(proj, "assets/audio/dialogue"); stems = os.path.join(proj, "assets/audio/stems")
    for d in (raw, out_d, stems, P["work"]):
        os.makedirs(d, exist_ok=True)

    clips = {}
    for b in SB["beats"]:
        if "text" not in b:
            continue
        src = next((os.path.join(raw, b["id"] + e) for e in (".mp3", ".wav", ".aiff") if os.path.exists(os.path.join(raw, b["id"] + e))), None)
        if src is None and say:
            v, rate = SAY_VOICE[b["speaker"]]
            src = os.path.join(raw, b["id"] + ".aiff")
            subprocess.run(["say", "-v", v, "-r", str(rate), "-o", src, b["text"]], check=True)
        if src is None:
            sys.exit(f"missing take for {b['id']} in {raw}")
        y = trim(load(src))
        tg = b.get("tighten", [0.45, 0.30])
        if tg:
            y = tighten(y, *tg)
        clips[b["id"]] = process(y, b.get("gain_db", -0.5 if b["speaker"] == "nerd" else 0.0))

    beats, t = [], 0.0
    for b in SB["beats"]:
        if b["id"] in clips:
            st = t + b.get("gap", 0.22)
            d = len(clips[b["id"]]) / SR
            en = st + d + b.get("tail", 0.0)
        else:
            st = t + b.get("gap", 0.0)
            en = st + float(b.get("hold", 1.0))
        beats.append({"id": b["id"], "kind": "line" if b["id"] in clips else "hold", "speaker": b.get("speaker"),
                      "text": b.get("text"), "start": round(st, 3), "end": round(en, 3)})
        t = en
    total = t
    BT = {x["id"]: x for x in beats}

    stem = np.zeros(int(total * SR) + SR, dtype=np.float32)
    report = []
    for b in SB["beats"]:
        if b["id"] not in clips:
            continue
        y = clips[b["id"]]
        path = os.path.join(out_d, b["id"] + ".wav")
        sf.write(path, y, SR, subtype="PCM_24")
        a = int(BT[b["id"]]["start"] * SR)
        stem[a:a + len(y)] += y
        d = len(y) / SR
        ws = whisper_words(path, d)
        heard = " ".join(w["w"] for w in ws)
        ratio = difflib.SequenceMatcher(None, norm(b["text"]), norm(heard)).ratio()
        report.append(f"{b['id']} {ratio:.2f}  script: {b['text']}\n      heard:  {heard}")
        al = align(b["text"], ws, y, d, b.get("word_fix"))
        segs = voiced_segments(y)
        x = BT[b["id"]]
        x["voice_start"] = round(x["start"] + (segs[0][0] if segs else 0), 3)
        x["voice_end"] = round(x["start"] + (segs[-1][1] if segs else d), 3)
        x["words"] = [{"w": w["w"], "start": round(x["start"] + w["start"], 3), "end": round(x["start"] + w["end"], 3)} for w in al]
    sf.write(os.path.join(stems, "dialogue.wav"), stem[:int(total * SR)], SR, subtype="PCM_24")
    open(os.path.join(P["work"], "whisper_check.txt"), "w").write("\n".join(report) + "\n")

    nf = int(round(total * FPS))
    TL = {"fps": FPS, "duration": round(total, 3), "frames": nf, "draft_voice": say, "beats": beats}
    json.dump(TL, open(P["tl"], "w"), indent=1)

    lip = {"nerd": {"open": [0.0] * nf, "wide": [0.0] * nf}, "mascot": {"open": [0.0] * nf, "wide": [0.0] * nf}}
    hop = SR // FPS
    for x in beats:
        if x["id"] not in clips:
            continue
        y, who = clips[x["id"]], ("nerd" if x["speaker"] == "nerd" else "mascot")
        a = int(round(x["start"] * FPS))
        for i in range(0, len(y) - hop, hop):
            seg = y[i:i + hop * 2]
            o = float(np.clip((20 * np.log10(np.sqrt((seg ** 2).mean()) + 1e-9) + 42) / 26, 0, 1))
            spec = np.abs(np.fft.rfft(seg * np.hanning(len(seg))))
            f = np.fft.rfftfreq(len(seg), 1 / SR)
            wd = float(np.clip(((spec * f).sum() / (spec.sum() + 1e-9) - 900) / 2200, 0, 1)) * o
            fi = a + i // hop
            if 0 <= fi < nf:
                lip[who]["open"][fi] = max(lip[who]["open"][fi], round(o, 3))
                lip[who]["wide"][fi] = max(lip[who]["wide"][fi], round(wd, 3))
    json.dump(lip, open(P["lip"], "w"))
    print("\n".join(report))
    print(f"TOTAL {total:.2f} s, {nf} frames{' (say draft)' if say else ''}")
    for x in beats:
        print(f"  {x['id']:7s} {x['kind']:4s} {x['start']:6.2f}-{x['end']:6.2f}  {x.get('text') or ''}")


if __name__ == "__main__":
    main()
