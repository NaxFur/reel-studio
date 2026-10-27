"""Storyboard + timeline helpers shared by every step (plain Python, also imported inside Blender).

Anchors (any time field in storyboard.json):
  "start" | "end"                    this beat's start / end
  "w:restore"  "w:three#2"           start of the (n-th) word in this beat that begins with the prefix
  "wend:restore"                     end of that word
  "L05" | "L05.end" | "L05.w:escape" another beat
  any of the above + "+0.2" / "-0.15"  offset in seconds
  a number                           absolute seconds
"""
import json, math, os, re

FPS = 30


def fr(t):
    return int(math.ceil(t * FPS - 1e-6)) + 1


def tm(f):
    return (f - 1) / FPS


def proj_paths(proj):
    proj = os.path.abspath(proj)
    return {
        "proj": proj,
        "sb": os.path.join(proj, "storyboard.json"),
        "tl": os.path.join(proj, "project", "timeline.json"),
        "lip": os.path.join(proj, "project", "lipsync.json"),
        "work": os.path.join(proj, "project"),
    }


def load_sb(proj):
    return json.load(open(proj_paths(proj)["sb"]))


def load_tl(proj):
    return json.load(open(proj_paths(proj)["tl"]))


def clean(w):
    return re.sub(r"[^a-z0-9']", "", w.lower().replace("’", "'"))


_OFF = re.compile(r"^(.*?)([+-]\d+(?:\.\d+)?)$")


class Anchors:
    def __init__(self, TL):
        self.TL = TL
        self.B = {b["id"]: b for b in TL["beats"]}

    def word(self, bid, prefix, n=1, end=False):
        b = self.B[bid]
        hits = [w for w in b.get("words", []) if clean(w["w"]).startswith(clean(prefix))]
        if not hits:
            raise KeyError(f"no word starting with '{prefix}' in {bid}: {[w['w'] for w in b.get('words', [])]}")
        w = hits[min(n, len(hits)) - 1]
        return w["end"] if end else w["start"]

    def __call__(self, spec, ctx=None, default=None):
        if spec is None:
            spec = default if default is not None else "start"
        if isinstance(spec, (int, float)):
            return float(spec)
        s = str(spec).strip()
        off = 0.0
        m = _OFF.match(s)
        if m and m.group(1) and not re.fullmatch(r"[\d.]+[eE]", m.group(1)):  # "1e-3" is a number, "w:rotate-0.2" an offset
            s, off = m.group(1), float(m.group(2))
        bid = ctx
        if "." in s and s.split(".")[0] in self.B:
            bid, s = s.split(".", 1)
        elif s in self.B:
            bid, s = s, "start"
        if bid is None:
            raise KeyError(f"anchor '{spec}' needs a beat")
        b = self.B[bid]
        if s == "start":
            t = b["start"]
        elif s == "end":
            t = b["end"]
        elif s in ("vstart", "vend"):
            t = b.get("voice_" + s[1:], b[s[1:]])
        elif s.startswith(("w:", "wend:")):
            kind, rest = s.split(":", 1)
            n = 1
            if "#" in rest:
                rest, n = rest.split("#"); n = int(n)
            t = self.word(bid, rest, n, end=(kind == "wend"))
        else:
            raise KeyError(f"bad anchor '{spec}' in {bid}")
        return t + off


def beat_items(SB, key):
    """Yield (beat_id, item) for every item of list `key` in every beat."""
    for b in SB["beats"]:
        for it in b.get(key, []) or []:
            yield b["id"], it


def screen_states(SB, A, monitor):
    """Sorted [(t, state)] for one monitor ('center' | 'left' | 'right')."""
    out = []
    for b in SB["beats"]:
        for st in (b.get("screens", {}) or {}).get(monitor, []) or []:
            out.append((A(st.get("at"), b["id"]), dict(st, _beat=b["id"])))
    out.sort(key=lambda x: x[0])
    return out


def active(states, t):
    cur = None
    for i, (t0, st) in enumerate(states):
        if t0 <= t:
            cur = (t0, st, i)
        else:
            break
    return cur
