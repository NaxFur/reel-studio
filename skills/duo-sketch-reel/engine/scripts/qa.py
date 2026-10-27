"""QA gate for a finished episode -> <proj>/qa/report.md (publish.py refuses anything with blocking items).
  qa.py <proj>
"""
import json, os, re, subprocess, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scene"))
from tl import load_sb, load_tl

proj = os.path.abspath(sys.argv[1])
SB, TL = load_sb(proj), load_tl(proj)
meta = SB["meta"]
block, warn, info = [], [], []
mp4 = os.path.join(proj, "final.mp4")


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


if not os.path.exists(mp4):
    block.append("final.mp4 missing")
else:
    pr = json.loads(run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", mp4]).stdout)
    v = next(s for s in pr["streams"] if s["codec_type"] == "video")
    dur = float(pr["format"]["duration"])
    info.append(f"video {v['width']}x{v['height']} {v['r_frame_rate']} {v['codec_name']}, {dur:.2f} s")
    if (v["width"], v["height"]) != (1080, 1920): block.append("not 1080x1920")
    if v["r_frame_rate"] != "30/1": block.append("not 30 fps")
    if not any(s["codec_type"] == "audio" for s in pr["streams"]): block.append("no audio stream")
    if abs(dur - TL["duration"]) > 0.2: block.append(f"duration {dur:.2f} != timeline {TL['duration']:.2f}")
    if dur > 90: block.append("longer than 90 s")
    elif dur > 60: warn.append("longer than 60 s: retention drops, aim for 30-45 s")
    e = run(["ffmpeg", "-hide_banner", "-i", mp4, "-af", "ebur128=peak=true", "-f", "null", "-"]).stderr
    s = e[e.rfind("Summary:"):]
    I = float(re.search(r"I:\s+(-?[\d.]+) LUFS", s).group(1)); tp = float(re.search(r"Peak:\s+(-?[\d.]+) dBFS", s).group(1))
    info.append(f"loudness {I:.1f} LUFS, true peak {tp:.1f} dBTP")
    if not -15.5 <= I <= -12.5: block.append(f"loudness {I:.1f} LUFS (target -14)")
    if tp > -0.9: block.append(f"true peak {tp:.1f} dBTP")
    bd = run(["ffmpeg", "-hide_banner", "-i", mp4, "-vf", "blackdetect=d=0.15:pix_th=0.06", "-an", "-f", "null", "-"]).stderr
    blacks = re.findall(r"black_start:([\d.]+)", bd)
    if blacks: block.append(f"black frames at {', '.join(blacks)} s")
if TL.get("draft_voice"):
    block.append("timeline built from the free `say` draft voices: rebuild with the real takes")
wc = os.path.join(proj, "project/whisper_check.txt")
if os.path.exists(wc):
    for ln in open(wc):
        m = re.match(r"(\S+) ([\d.]+)  script:", ln)
        if m and float(m.group(2)) < 0.72:
            warn.append(f"{m.group(1)}: whisper match {m.group(2)} - listen for a mispronunciation")
for k in ("series", "cta_keyword", "caption", "hashtags", "resources"):
    if not meta.get(k): block.append(f"meta.{k} missing")
kw = meta.get("cta_keyword", "")
if kw and not re.fullmatch(r"[A-Z0-9]+", kw): block.append("cta_keyword must be one word in capitals")
if re.search(r"\bcomment\b", meta.get("caption", ""), re.I): block.append("caption has its own 'Comment X' line: publish.py adds it")
if not meta.get("resources", {}).get("main_link"): block.append("meta.resources.main_link missing")
if not os.path.exists(os.path.join(proj, "cover.png")): block.append("cover.png missing")
if not os.path.exists(os.path.join(proj, "research.md")): block.append("research.md missing (every fact needs a source)")
first = TL["beats"][0]
first_line = next((b for b in TL["beats"] if b["kind"] == "line"), None)
if first_line and first_line["voice_start"] > 1.0:
    warn.append(f"first word at {first_line['voice_start']:.2f} s: speak within the first second")
gaps = [b2["start"] - b1["end"] for b1, b2 in zip(TL["beats"], TL["beats"][1:])]
if any(g > 0.9 for g in gaps): warn.append("a silent gap longer than 0.9 s between beats")
os.makedirs(os.path.join(proj, "qa"), exist_ok=True)
rep = [f"# QA {os.path.basename(proj)}", "", "## Info"] + [f"- {x}" for x in info] + ["", "## Warnings"] + \
      ([f"- {x}" for x in warn] or ["- none"]) + ["", "## Blocking"] + ([f"- {x}" for x in block] or ["- none"]) + [""]
open(os.path.join(proj, "qa/report.md"), "w").write("\n".join(rep))
print("\n".join(rep))
sys.exit(1 if block else 0)
