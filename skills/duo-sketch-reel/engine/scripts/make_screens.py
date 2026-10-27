"""Monitor image sequences (centre 2400x1350, sides 1600x900) from storyboard `screens` states.

  make_screens.py <proj> [frame ...]      (frames given = only those, for stills)

State types (see references/storyboard.md): terminal, menu, card, alert, code, idle, black.
Centre-monitor content is laid out in the column x 600..1820: the only part a close-up (ECU) sees.
Line prefixes colour terminal lines: "> " prompt, "✓ " ok, "✗ " error, "! " warn, "● " claude, "# " dim,
"$ " command, "+ " added, "- " removed. Identical frames are hard links (the cache key holds everything
that changes over time).
"""
import os, sys, random
from PIL import Image, ImageDraw, ImageFont, ImageFilter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scene"))
from tl import proj_paths, load_sb, load_tl, Anchors, screen_states, active, FPS

MONO = os.environ.get("DUO_FONT_MONO", "/System/Library/Fonts/SFNSMono.ttf")
SANS = os.environ.get("DUO_FONT_SANS", "/System/Library/Fonts/SFNS.ttf")
_fc = {}


def font(path, size, var=None):
    k = (path, int(size), var)
    if k not in _fc:
        f = ImageFont.truetype(path, int(size))
        if var:
            try: f.set_variation_by_name(var)
            except Exception: pass
        _fc[k] = f
    return _fc[k]


BG = (12, 12, 16); PANEL = (20, 20, 27); PANEL2 = (28, 28, 38); BORDER = (48, 48, 64)
TXT = (232, 232, 240); DIM = (128, 130, 150)
COL = {"orange": (255, 122, 26), "green": (60, 214, 120), "red": (255, 84, 96), "blue": (96, 170, 255),
       "yellow": (255, 206, 84), "purple": (190, 130, 255), "white": TXT, "dim": DIM}
PREFIX = [("> ", "orange", TXT), ("✓ ", "green", DIM), ("✗ ", "red", (255, 160, 165)), ("! ", "yellow", TXT),
          ("● ", "orange", TXT), ("# ", "dim", DIM), ("$ ", "green", COL["green"]), ("+ ", "green", COL["green"]),
          ("- ", "red", COL["red"])]


def ease(x):
    x = max(0.0, min(1.0, x)); return 1 - (1 - x) ** 3


def out_back(x):
    x = max(0.0, min(1.0, x)); c = 1.70158
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


def mix(a, b, w):
    return tuple(int(a[i] + (b[i] - a[i]) * w) for i in range(3))


class Canvas:
    def __init__(self, w, h, centre):
        self.w, self.h = w, h
        self.k = h / 1350
        self.x0, self.cw = (600, 1220) if centre else (int(90 * w / 1600), int(1420 * w / 1600))


def window(d, cv, title, clock=None):
    w, h = cv.w, cv.h
    d.rectangle([0, 0, w, h], fill=BG)
    bar = int(h * 0.055)
    d.rectangle([0, 0, w, bar], fill=(22, 22, 30))
    d.line([(0, bar), (w, bar)], fill=BORDER, width=2)
    r = bar * 0.22
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        cx = bar * 0.6 + i * bar * 0.55
        d.ellipse([cx - r, bar / 2 - r, cx + r, bar / 2 + r], fill=c)
    d.text((w / 2, bar / 2), title or "", font=font(SANS, bar * 0.42, "Medium"), fill=DIM, anchor="mm")
    if clock:
        d.text((w - bar * 0.5, bar / 2), clock, font=font(MONO, bar * 0.40, "Medium"), fill=DIM, anchor="rm")
    return bar


def split_prefix(line):
    for p, c, rest in PREFIX:
        if line.startswith(p):
            return p, COL[c], line[len(p):], rest
    return "", TXT, line, TXT


def fit(f_path, size, var, text, maxw):
    while size > 20 and font(f_path, size, var).getlength(text) > maxw:
        size -= 2
    return font(f_path, size, var)


# ------------------------------------------------------------------ templates (each returns key parts)
def terminal(img, cv, st, lt, A):
    d = ImageDraw.Draw(img)
    bar = window(d, cv, st.get("title", "claude — ~/app"), st.get("clock"))
    k = cv.k * st.get("scale", 1.0)
    fs, lh = 62 * k, 92 * k
    lines = st.get("lines", [])
    reveal = st.get("_reveal")
    keyp = []
    y = bar + 80 * k + st.get("y0", 0) * cv.k
    typed_i = st.get("type_line", len(lines) - 1 if st.get("typed") else -1)
    for i, ln in enumerate(lines):
        if reveal and lt < reveal[i]:
            break
        a = ease((lt - reveal[i]) / 0.10) if reveal else 1.0
        keyp.append(round(a, 2))
        p, pc, rest, rc = split_prefix(ln)
        if i == typed_i:
            t0 = reveal[i] if reveal else st.get("type_delay", 0.15)
            n = int(max(0, lt - t0) * st.get("cps", 24))
            rest = rest[:n] + ("▋" if n < len(rest) or int(lt * 2.2) % 2 == 0 else "")
            keyp.append(min(n, len(rest) + 1)); keyp.append(int(lt * 2.2) % 2)
        f = fit(MONO, fs, "Medium", p + rest, cv.cw)
        fb = font(MONO, f.size, "Bold")
        x = cv.x0
        if p:
            d.text((x, y), p, font=fb, fill=mix(BG, pc, a), anchor="lm"); x += fb.getlength(p)
        d.text((x, y), rest, font=f, fill=mix(BG, rc, a), anchor="lm")
        y += lh
    pr = st.get("progress")
    if pr:
        frac = pr.get("from", 0) + (pr.get("to", 1) - pr.get("from", 0)) * ease((lt - pr.get("delay", 0)) / pr.get("dur", 1.0))
        col = COL[pr.get("color", "orange")] if frac < 0.999 else COL["green"]
        bw, bh = cv.cw * 0.68, 50 * k
        d.rounded_rectangle([cv.x0, y + 10 * k, cv.x0 + bw, y + 10 * k + bh], int(bh // 2), fill=(40, 40, 52))
        d.rounded_rectangle([cv.x0, y + 10 * k, cv.x0 + max(bh, bw * frac), y + 10 * k + bh], int(bh // 2), fill=col)
        lab = pr.get("label", "{pct}%").replace("{pct}", str(int(frac * 100)))
        d.text((cv.x0 + bw + 30 * k, y + 35 * k), lab, font=font(MONO, 54 * k, "Medium"), fill=DIM, anchor="lm")
        y += 110 * k
        keyp.append(round(frac, 3))
    big = st.get("big")
    if big:
        tb = A(big.get("at"), st["_beat"]) - st["_t0"] if big.get("at") else 0.0
        if lt >= tb:
            a = ease((lt - tb) / 0.12)
            sc = 1 + 0.25 * (1 - out_back((lt - tb) / 0.3))
            f = fit(MONO, 92 * k * sc, "Bold", big["text"], cv.cw)
            d.text((cv.x0, y + 70 * k), big["text"], font=f, fill=mix(BG, COL[big.get("color", "green")], a), anchor="lm")
            if big.get("sub"):
                d.text((cv.x0, y + 170 * k), big["sub"], font=font(MONO, 56 * k, "Medium"), fill=mix(BG, DIM, a), anchor="lm")
            keyp.append(round(min(lt - tb, 0.31), 2))
    return keyp


def menu(img, cv, st, lt, A):
    """A TUI picker (e.g. a rewind menu): rows, a moving highlight, optional second-level action list."""
    d = ImageDraw.Draw(img)
    bar = window(d, cv, st.get("title", "claude"), st.get("clock"))
    k = cv.k * st.get("scale", 1.0)
    y = bar + 70 * k
    d.text((cv.x0, y), st.get("header", ""), font=font(MONO, 58 * k, "Bold"), fill=COL["orange"], anchor="lm")
    y += 100 * k
    sel = 0
    for s in st.get("_sel", []):
        if lt >= s[0]:
            sel = s[1]
    stage2 = st.get("_sub_t") is not None and lt >= st["_sub_t"]
    items = st["sub"]["items"] if stage2 else st.get("items", [])
    if stage2:
        sel = 0
        for s in st.get("_sub_sel", []):
            if lt >= s[0]:
                sel = s[1]
        d.text((cv.x0, y - 10 * k), st["sub"].get("header", ""), font=font(MONO, 50 * k, "Medium"), fill=DIM, anchor="lm")
        y += 80 * k
    f = font(MONO, 60 * k, "Medium")
    rh = 96 * k
    for i, it in enumerate(items):
        on = i == sel
        if on:
            d.rounded_rectangle([cv.x0 - 24 * k, y - rh / 2 + 6 * k, cv.x0 + cv.cw, y + rh / 2 - 6 * k], int(16 * k),
                                fill=(52, 34, 20), outline=COL["orange"], width=max(2, int(4 * k)))
        d.text((cv.x0, y), ("❯ " if on else "  ") + it, font=fit(MONO, 60 * k, "Medium", "❯ " + it, cv.cw - 30 * k),
               fill=TXT if on else DIM, anchor="lm")
        y += rh
    if st.get("hint"):
        d.text((cv.x0, cv.h - 80 * k), st["hint"], font=font(MONO, 46 * k, "Medium"), fill=DIM, anchor="lm")
    done = st.get("_done_t") is not None and lt >= st["_done_t"]
    if done:
        a = ease((lt - st["_done_t"]) / 0.12)
        d.rectangle([0, bar, cv.w, cv.h], fill=mix(BG, BG, 1))
        f2 = fit(MONO, 100 * k, "Bold", st["done"]["text"], cv.cw)
        d.text((cv.x0, cv.h * 0.45), st["done"]["text"], font=f2, fill=mix(BG, COL[st["done"].get("color", "green")], a), anchor="lm")
        if st["done"].get("sub"):
            d.text((cv.x0, cv.h * 0.45 + 120 * k), st["done"]["sub"], font=font(MONO, 58 * k, "Medium"), fill=mix(BG, DIM, a), anchor="lm")
        return ["done", round(min(lt - st["_done_t"], 0.13), 2)]
    return [sel, stage2]


def card(img, cv, st, lt, A):
    k = cv.k
    acc = COL[st.get("accent", "orange")]
    base = Image.new("RGB", (cv.w, cv.h), BG)
    d = ImageDraw.Draw(base)
    m = 70 * k
    d.rounded_rectangle([m, m, cv.w - m, cv.h - m], int(40 * k), fill=PANEL, outline=acc, width=max(3, int(7 * k)))
    x = max(cv.x0, m + 60 * k) if cv.w > 2000 else m + 60 * k
    cw = cv.cw if cv.w > 2000 else cv.w - 2 * (m + 60 * k)
    y = m + 110 * k
    if st.get("kicker"):
        f = font(SANS, 58 * k, "Heavy")
        tw = f.getlength(st["kicker"])
        d.rounded_rectangle([x, y - 50 * k, x + tw + 60 * k, y + 50 * k], int(50 * k), fill=acc)
        d.text((x + 30 * k, y), st["kicker"], font=f, fill=(18, 12, 8), anchor="lm")
        y += 150 * k
    if st.get("title"):
        f = fit(SANS, 130 * k, "Heavy", st["title"], cw)
        d.text((x, y), st["title"], font=f, fill=TXT, anchor="lm"); y += 150 * k
    if st.get("sub"):
        f = fit(SANS, 66 * k, "Semibold", st["sub"], cw)
        d.text((x, y), st["sub"], font=f, fill=DIM, anchor="lm"); y += 110 * k
    for ln in st.get("lines", []):
        p, pc, rest, rc = split_prefix(ln)
        f = fit(MONO, 60 * k, "Medium", p + rest, cw)
        d.text((x, y), p + rest, font=f, fill=pc if p else TXT, anchor="lm"); y += 90 * k
    if not st.get("slam", True):
        img.paste(base); return []
    a = ease(lt / 0.10)
    sc = 1.0 + 0.18 * (1 - out_back(lt / 0.32))
    if sc > 1.0005:
        cw2, ch2 = int(cv.w * sc), int(cv.h * sc)
        big = base.resize((cw2, ch2), Image.LANCZOS)
        base = Image.new("RGB", (cv.w, cv.h), BG)
        base.paste(big, ((cv.w - cw2) // 2, (cv.h - ch2) // 2))
    if a < 1:
        base = Image.blend(Image.new("RGB", (cv.w, cv.h), BG), base, a)
    img.paste(base)
    return [round(min(lt, 0.33), 2)]


def alert(img, cv, st, lt, A):
    d = ImageDraw.Draw(img)
    k = cv.k
    acc = COL[st.get("color", "red")]
    flash = 0.5 + 0.5 * (1 if int(lt * 4) % 2 == 0 else 0) if st.get("flash", True) else 1
    d.rectangle([0, 0, cv.w, cv.h], fill=mix(BG, acc, 0.10 + 0.10 * flash))
    d.rectangle([0, 0, cv.w, int(40 * k)], fill=acc); d.rectangle([0, cv.h - int(40 * k), cv.w, cv.h], fill=acc)
    cx = cv.x0 + cv.cw / 2 if cv.w > 2000 else cv.w / 2
    d.text((cx, cv.h * 0.36), st.get("icon", "✗"), font=font(SANS, 260 * k, "Heavy"), fill=acc, anchor="mm")
    f = fit(SANS, 120 * k, "Heavy", st.get("title", ""), cv.cw)
    d.text((cx, cv.h * 0.60), st.get("title", ""), font=f, fill=TXT, anchor="mm")
    if st.get("sub"):
        f = fit(MONO, 60 * k, "Medium", st["sub"], cv.cw)
        d.text((cx, cv.h * 0.74), st["sub"], font=f, fill=(235, 200, 205), anchor="mm")
    return [int(lt * 4) % 2 if st.get("flash", True) else 0]


def code(img, cv, st, lt, A):
    d = ImageDraw.Draw(img)
    bar = window(d, cv, st.get("file", "app.py"))
    k = cv.k
    y = bar + 70 * k
    hl = set(st.get("hl", []))
    for i, ln in enumerate(st.get("lines", [])):
        if i in hl:
            d.rectangle([cv.x0 - 30 * k, y - 40 * k, cv.x0 + cv.cw, y + 40 * k], fill=(60, 40, 18))
        d.text((cv.x0 - 10 * k, y), f"{i + 1:>2}", font=font(MONO, 40 * k), fill=(80, 82, 100), anchor="rm")
        p, pc, rest, rc = split_prefix(ln)
        d.text((cv.x0 + 20 * k, y), ln, font=fit(MONO, 54 * k, "Medium", ln, cv.cw - 30 * k), fill=pc if p else TXT, anchor="lm")
        y += 80 * k
    return []


def idle(img, cv, st, lt, A):
    d = ImageDraw.Draw(img)
    bar = window(d, cv, st.get("title", "main.py"))
    rnd = random.Random(st.get("seed", 3))
    k = cv.k
    scroll = int(lt * st.get("scroll", 0) * 46 * k * 1.5)
    y = bar + 50 * k - scroll % int(46 * k * 1.5)
    rows = int((cv.h - bar) / (46 * k * 1.5)) + 2
    off = scroll // int(46 * k * 1.5)
    for i in range(rows):
        r2 = random.Random(st.get("seed", 3) * 1000 + i + off)
        x = cv.x0 * 0.2 + r2.choice([0, 0, 1, 2]) * 60 * k
        for _ in range(r2.randint(1, 4)):
            w = r2.randint(60, 300) * k
            c = r2.choice([TXT, DIM, COL["blue"], COL["purple"], COL["green"], COL["yellow"]])
            d.rounded_rectangle([x, y - 13 * k, x + w, y + 13 * k], int(8 * k), fill=tuple(int(v * 0.7) for v in c))
            x += w + 26 * k
        y += 46 * k * 1.5
    return [off, int(scroll % int(46 * k * 1.5))] if st.get("scroll") else []


def black(img, cv, st, lt, A):
    ImageDraw.Draw(img).rectangle([0, 0, cv.w, cv.h], fill=(4, 4, 6)); return []


T = {"terminal": terminal, "menu": menu, "card": card, "alert": alert, "code": code, "idle": idle, "black": black}


def prepare(states, A):
    """Resolve the anchors inside each state into local seconds."""
    for t0, st in states:
        st["_t0"] = t0
        b = st["_beat"]
        if st.get("reveal"):
            st["_reveal"] = [A(r, b) - t0 for r in st["reveal"]]
        if st.get("sel"):
            st["_sel"] = [(A(s["at"], b) - t0, s["i"]) for s in st["sel"]]
        if st.get("sub"):
            st["_sub_t"] = A(st["sub"]["at"], b) - t0
            st["_sub_sel"] = [(A(s["at"], b) - t0, s["i"]) for s in st["sub"].get("sel", [])]
        if st.get("done"):
            st["_done_t"] = A(st["done"]["at"], b) - t0


def render_state(states, t, cv, A, default):
    cur = active(states, t)
    t0, st, idx = cur if cur else (0.0, default, -1)
    img = Image.new("RGB", (cv.w, cv.h), BG)
    keyp = T[st.get("type", "idle")](img, cv, st, t - t0, A)
    return img, (idx, tuple(keyp))


def main():
    proj = sys.argv[1]
    only = [int(a) for a in sys.argv[2:]]
    P = proj_paths(proj)
    SB, TL = load_sb(proj), load_tl(proj)
    A = Anchors(TL)
    NF = TL["frames"]
    mons = [("center", "screen", "screen", Canvas(2400, 1350, True), {"type": "idle", "title": "main.py", "seed": 5}),
            ("left", "screen_left", "screen_left", Canvas(1600, 900, False), {"type": "idle", "title": "notes.md", "seed": 3}),
            ("right", "screen_right", "screen_right", Canvas(1600, 900, False), {"type": "idle", "title": "server.log", "seed": 8, "scroll": 1})]
    for mon, sub, name, cv, default in mons:
        out = os.path.join(P["work"], sub)
        os.makedirs(out, exist_ok=True)
        states = screen_states(SB, A, mon)
        prepare(states, A)
        dflt = dict(SB["meta"].get("screen_default", {}).get(mon, default), _beat=SB["beats"][0]["id"], _t0=0.0)
        last = (None, None)
        for f in (only or range(1, NF + 1)):
            t = (f - 1) / FPS
            p = os.path.join(out, f"{name}_{f:04d}.jpg")
            img, key = render_state(states, t, cv, A, dflt)
            if os.path.exists(p):
                os.remove(p)
            if key == last[0] and not only:
                os.link(last[1], p)
            else:
                img.save(p, quality=92)
                last = (key, p)
    print("screens:", len(only) or NF, "frames")


if __name__ == "__main__":
    main()
