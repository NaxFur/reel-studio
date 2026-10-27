"""Overlay frames (1080x1920 RGBA): hook, word-timed subtitles, overlay items, title card; plus captions.srt.

  make_overlay.py <proj> [--variant B] [--out dir] [frame ...]

Overlay items per beat (`overlay` list): chip, keys, panel, stamp (see references/storyboard.md).
Safe zone: x 90..990, y 230..1540 (Instagram UI covers the rest). Subtitles sit at y≈1235.
"""
import os, sys, re
from PIL import Image, ImageDraw, ImageFont, ImageFilter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scene"))
from tl import proj_paths, load_sb, load_tl, Anchors, clean, FPS

W, H = 1080, 1920
AV = os.environ.get("DUO_FONT_DISPLAY", "/System/Library/Fonts/Avenir Next.ttc")
MONO = os.environ.get("DUO_FONT_MONO", "/System/Library/Fonts/SFNSMono.ttf")
EMOJI = os.environ.get("DUO_FONT_EMOJI", "/System/Library/Fonts/Apple Color Emoji.ttc")
WHITE = (255, 255, 255); MASCOT = (255, 150, 95); KEY = (255, 214, 64); ORANGE = (255, 122, 61)
RED = (235, 45, 55); GREEN = (60, 214, 120); INK = (8, 8, 14)
COLS = {"red": RED, "orange": ORANGE, "green": GREEN, "yellow": KEY, "white": WHITE, "blue": (70, 150, 255)}
_f = {}


def av(size, idx=8):
    k = ("av", int(size), idx)
    if k not in _f: _f[k] = ImageFont.truetype(AV, int(size), index=idx)
    return _f[k]


def mono(size, var="Bold"):
    k = ("mono", int(size), var)
    if k not in _f:
        f = ImageFont.truetype(MONO, int(size))
        try: f.set_variation_by_name(var)
        except Exception: pass
        _f[k] = f
    return _f[k]


def emoji(ch, size):
    f = ImageFont.truetype(EMOJI, 160)
    im = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((100, 100), ch, font=f, embedded_color=True, anchor="mm")
    im = im.crop(im.getbbox() or (0, 0, 200, 200))
    return im.resize((int(im.width * size / 160), int(im.height * size / 160)), Image.LANCZOS)


def ease(x):
    x = max(0.0, min(1.0, x)); return 1 - (1 - x) ** 3


def out_back(x):
    x = max(0.0, min(1.0, x)); c = 1.70158
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


def fade(im, a):
    if a >= 1: return im
    im = im.copy(); im.putalpha(im.split()[3].point(lambda v: int(v * max(0, a)))); return im


def shadowed(layer, blur=10, k=0.6):
    sh = layer.split()[3].filter(ImageFilter.GaussianBlur(blur)).point(lambda v: int(v * k))
    s = Image.new("RGBA", layer.size, (0, 0, 0, 0)); s.putalpha(sh)
    return Image.alpha_composite(s, layer)


def fit_av(text, size, maxw, idx=8):
    while size > 24 and av(size, idx).getlength(text) > maxw:
        size -= 2
    return av(size, idx)


# ------------------------------------------------------------------ subtitles
def chunk_words(words, plan=None, max_words=3, max_chars=17):
    if plan:
        out, i = [], 0
        for n in plan:
            out.append(words[i:i + n]); i += n
        return [c for c in out if c]
    out, cur = [], []
    for w in words:
        if cur and (len(cur) >= max_words or len(" ".join(x["w"] for x in cur + [w])) > max_chars):
            out.append(cur); cur = []
        cur.append(w)
        if re.search(r"[.,?!…:;]$", w["w"]):
            out.append(cur); cur = []
    if cur: out.append(cur)
    return out


def build_sub_events(SB, TL):
    B = {b["id"]: b for b in SB["beats"]}
    ev = []
    for x in TL["beats"]:
        if x["kind"] != "line" or B[x["id"]].get("no_subs"):
            continue
        b = B[x["id"]]
        emph = {clean(e) for e in b.get("emph", [])}
        for ch in chunk_words(x["words"], b.get("chunks")):
            ev.append({"s": ch[0]["start"] - 0.05, "e": None, "ws": ch, "spk": x["speaker"], "bid": x["id"],
                       "emph": emph, "vend": x.get("voice_end", x["end"]), "y": b.get("sub_y", 1235)})
    for i, e in enumerate(ev):
        nxt = ev[i + 1] if i + 1 < len(ev) else None
        same = nxt is not None and nxt["bid"] == e["bid"]
        end = (nxt["s"] - 0.02) if same else e["vend"] + 0.25
        if nxt is not None and not same:
            end = min(end, nxt["s"] - 0.02)
        e["e"] = max(end, e["s"] + 0.35)
    return ev


def draw_sub(img, e, t):
    f = av(76)
    base = MASCOT if e["spk"] == "claude" else WHITE
    hot = (255, 196, 80) if e["spk"] == "claude" else KEY
    space = f.getlength(" ")
    rows, cur, cw = [], [], 0
    for w in e["ws"]:
        wl = f.getlength(w["w"])
        if cur and cw + space + wl > 860:
            rows.append(cur); cur, cw = [], 0
        cur.append((w, wl)); cw += (space if cw else 0) + wl
    if cur: rows.append(cur)
    pop = min(1, (t - e["s"]) / 0.12)
    sc = 0.86 + 0.14 * (1 - (1 - pop) ** 3)
    alpha = min(pop * 1.4, 1) * max(0, min(1, (e["e"] - t) / 0.06))
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    lh, yc = 90, e["y"]
    y0 = yc - (len(rows) - 1) * lh / 2
    lit = 0
    for ri, row in enumerate(rows):
        tot = sum(wl for _, wl in row) + space * (len(row) - 1)
        x = 540 - tot / 2
        for w, wl in row:
            col = hot if clean(w["w"]) in e["emph"] else base
            on = w["start"] - 0.04 <= t
            lit += on
            if not on:
                col = tuple(int(c * 0.5) for c in col)
            d.text((x, y0 + ri * lh), w["w"], font=f, fill=(*col, 255), stroke_width=8, stroke_fill=(*INK, 255), anchor="lm")
            x += wl + space
    comp = shadowed(layer)
    if sc < 0.999:
        small = comp.resize((int(W * sc), int(H * sc)), Image.LANCZOS)
        comp = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        comp.paste(small, (int(540 - 540 * sc), int(yc - yc * sc)))
    img.alpha_composite(fade(comp, alpha))
    return (round(pop, 2), lit, round(alpha, 2))


# ------------------------------------------------------------------ hook / items / title
def draw_hook(img, hook, t, end, variant):
    hk = dict(hook, **(hook.get("variant_b", {}) if variant == "B" else {}))
    out = min(1, (end - t) / 0.15)
    sc = 1.0 + 0.05 * max(0.0, 1 - t / 0.25) * (1 if t > 0 else 0)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    y = 330
    for i, line in enumerate(hk["text"].split("\n")):
        f = fit_av(line, 88 * sc, 900)
        d.text((540, y), line, font=f, fill=WHITE, anchor="mm", stroke_width=9, stroke_fill=(*INK, 255))
        y += 100
    if hk.get("badge"):
        b = Image.new("RGBA", (1040, 200), (0, 0, 0, 0))
        bd = ImageDraw.Draw(b)
        f = fit_av(hk["badge"], 80 * sc, 800)
        tw = f.getlength(hk["badge"])
        col = COLS.get(hk.get("badge_color", "red"), RED)
        bd.rounded_rectangle([520 - tw / 2 - 36, 24, 520 + tw / 2 + 36, 172], 28, fill=(*col, 255), outline=WHITE, width=7)
        bd.text((520, 98), hk["badge"], font=f, fill=WHITE, anchor="mm")
        b = b.rotate(-3.0, resample=Image.BICUBIC, expand=True)
        layer.alpha_composite(b, (540 - b.width // 2, y - 30))
    img.alpha_composite(fade(shadowed(layer, 14), out))
    return (round(min(t, 0.26), 2), round(out, 2))


def pill(text, size, fg, bg, outline=None):
    f = av(size)
    tw = f.getlength(text)
    im = Image.new("RGBA", (int(tw + size * 1.6), int(size * 1.9)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, im.width - 1, im.height - 1], im.height // 2, fill=bg, outline=outline, width=5 if outline else 0)
    d.text((im.width / 2, im.height / 2), text, font=f, fill=fg, anchor="mm")
    return im


def keycap(label, pressed):
    w, h = 300, 260
    im = Image.new("RGBA", (w + 20, h + 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    dy = 18 if pressed else 0
    d.rounded_rectangle([10, 30, w + 10, h + 30], 46, fill=(120, 120, 135, 255))
    d.rounded_rectangle([10, 10 + dy, w + 10, h + 10 + dy - 18], 46, fill=(250, 250, 252, 255), outline=(20, 20, 26, 255), width=6)
    d.text((w / 2 + 10, h / 2 + dy - 2), label, font=fit_av(label, 96, w - 40), fill=(20, 20, 26, 255), anchor="mm")
    return im


def draw_item(img, it, t, A):
    typ = it["type"]
    t0, t1 = it["_t0"], it["_t1"]
    a = ease((t - t0) / 0.12) * min(1, max(0, (t1 - t) / 0.12))
    lt = t - t0
    if typ == "chip":
        im = pill(it["text"], it.get("size", 54), WHITE, (*COLS.get(it.get("color", "orange"), ORANGE), 255), WHITE)
        sc = 0.7 + 0.3 * out_back(lt / 0.25)
        im = im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))), Image.LANCZOS)
        img.alpha_composite(fade(shadowed(im, 8), a), (540 - im.width // 2, it.get("y", 290) - im.height // 2))
        return (round(min(lt, 0.26), 2), round(a, 2))
    if typ == "keys":
        ats = it["_keys_t"]
        n = len(it["keys"])
        gap = 40
        total = n * 320 + (n - 1) * (gap + 70)
        x = 540 - total / 2
        y = it.get("y", 560)
        st = []
        d = ImageDraw.Draw(img)
        for i, lab in enumerate(it["keys"]):
            if t < ats[i]:
                st.append(0); x += 320 + gap + 70; continue
            kt = t - ats[i]
            pressed = kt < 0.12
            sc = 0.6 + 0.4 * out_back(kt / 0.22)
            cap = keycap(lab, pressed)
            cap = cap.resize((int(cap.width * sc), int(cap.height * sc)), Image.LANCZOS)
            img.alpha_composite(fade(shadowed(cap, 10), a), (int(x + 160 - cap.width / 2), int(y - cap.height / 2)))
            st.append((round(min(kt, 0.23), 2), pressed))
            if i < n - 1 and t >= ats[i + 1]:
                d.text((x + 320 + gap / 2 + 35, y), "+", font=av(110), fill=(255, 255, 255, int(255 * a)), anchor="mm",
                       stroke_width=7, stroke_fill=(*INK, int(255 * a)))
            x += 320 + gap + 70
        return (tuple(st), round(a, 2))
    if typ == "panel":
        rows = it["items"]
        top, pw = it.get("y", 240), 920
        ph = 130 + 120 * len(rows)
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        x0 = 540 - pw / 2
        d.rounded_rectangle([x0, top, x0 + pw, top + ph], 34, fill=(16, 16, 22, 235), outline=(*ORANGE, 255), width=5)
        d.text((540, top + 66), it["title"], font=fit_av(it["title"], 56, pw - 80), fill=(*ORANGE, 255), anchor="mm")
        st = []
        for i, r in enumerate(rows):
            on = t >= r["_t"]
            y = top + 160 + i * 120
            k = ease((t - r["_t"]) / 0.15) if on else 0
            dim = 0.35 + 0.65 * k
            cx = x0 + 70
            d.ellipse([cx - 30, y - 30, cx + 30, y + 30], fill=(*(GREEN if on else (70, 70, 84)), 255))
            if on:                                   # Avenir has no check glyph: draw it
                d.line([(cx - 14, y + 1), (cx - 4, y + 12), (cx + 15, y - 11)], fill=(*INK, 255), width=8, joint="curve")
            else:
                d.text((cx, y), str(i + 1), font=av(40), fill=(*WHITE, 255), anchor="mm")
            col = tuple(int(c * dim) for c in WHITE)
            d.text((x0 + 125, y - (18 if r.get("sub") else 0)), r["text"], font=fit_av(r["text"], 52, pw - 160), fill=(*col, 255), anchor="lm")
            if r.get("sub"):
                d.text((x0 + 125, y + 30), r["sub"], font=mono(32, "Medium"), fill=(*tuple(int(c * dim) for c in (150, 152, 172)), 255), anchor="lm")
            st.append(round(k, 2))
        sc = 0.92 + 0.08 * ease(lt / 0.2)
        comp = shadowed(layer, 12)
        if sc < 0.999:
            small = comp.resize((int(W * sc), int(H * sc)), Image.LANCZOS)
            comp = Image.new("RGBA", (W, H), (0, 0, 0, 0)); comp.paste(small, (int(540 - 540 * sc), int(top - top * sc)))
        img.alpha_composite(fade(comp, a))
        return (tuple(st), round(min(lt, 0.21), 2), round(a, 2))
    if typ == "stamp":
        col = COLS.get(it.get("color", "green"), GREEN)
        im = Image.new("RGBA", (1000, 260), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        f = fit_av(it["text"], 110, 860)
        tw = f.getlength(it["text"])
        d.rounded_rectangle([500 - tw / 2 - 40, 20, 500 + tw / 2 + 40, 240], 30, fill=(*col, 240), outline=WHITE, width=8)
        d.text((500, 130), it["text"], font=f, fill=WHITE, anchor="mm")
        im = im.rotate(it.get("rot", -6), resample=Image.BICUBIC, expand=True)
        sc = 1.6 - 0.6 * out_back(lt / 0.22)
        im = im.resize((int(im.width * sc), int(im.height * sc)), Image.LANCZOS)
        img.alpha_composite(fade(shadowed(im, 12), a), (540 - im.width // 2, it.get("y", 780) - im.height // 2))
        return (round(min(lt, 0.23), 2), round(a, 2))
    raise KeyError(typ)


def draw_title(img, tc, t, t0, t1):
    lt = t - t0
    a = ease(lt / 0.12) * min(1, (t1 - t) / 0.08)
    layer = Image.new("RGBA", (W, H), (10, 8, 14, int(236 * a)))
    d = ImageDraw.Draw(layer)
    s1 = 1 + 0.2 * (1 - out_back(lt / 0.3))
    f1 = fit_av(tc["line1"], 120 * s1, 940)
    d.text((540, 760), tc["line1"], font=f1, fill=(*WHITE, int(255 * a)), anchor="mm", stroke_width=8, stroke_fill=(*INK, int(255 * a)))
    if lt > 0.25:
        a2 = ease((lt - 0.25) / 0.15) * a
        s2 = 1 + 0.25 * (1 - out_back((lt - 0.25) / 0.3))
        f2 = fit_av(tc["line2"], 132 * s2, 960)
        d.text((540, 905), tc["line2"], font=f2, fill=(*ORANGE, int(255 * a2)), anchor="mm", stroke_width=8, stroke_fill=(*INK, int(255 * a2)))
    if lt > 0.7 and tc.get("cta"):
        a3 = ease((lt - 0.7) / 0.25) * a
        pre, kw, post = tc["cta"]
        f = av(46)
        e_im = emoji("👇", 48)
        tw = f.getlength(pre) + f.getlength(kw) + f.getlength(post) + 14 + e_im.width
        y = 1180 + 24 * (1 - a3)
        d.rounded_rectangle([540 - tw / 2 - 42, y - 54, 540 + tw / 2 + 42, y + 54], 54, fill=(255, 255, 255, int(245 * a3)),
                            outline=(*ORANGE, int(255 * a3)), width=4)
        x = 540 - tw / 2
        for part, c in ((pre, (14, 16, 24)), (kw, ORANGE), (post, (14, 16, 24))):
            d.text((x, y), part, font=f, fill=(*c, int(255 * a3)), anchor="lm"); x += f.getlength(part)
        layer.alpha_composite(fade(e_im, a3), (int(x + 14), int(y - e_im.height / 2)))
    img.alpha_composite(layer)
    return (round(min(lt, 1.0), 2), round(a, 2))


def srt_time(x):
    h, r = divmod(max(0, x), 3600); m, s = divmod(r, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int(round((s - int(s)) * 1000)) % 1000:03d}"


def main():
    args = sys.argv[1:]
    proj = args[0]
    variant = args[args.index("--variant") + 1].upper() if "--variant" in args else "A"
    P = proj_paths(proj)
    out = args[args.index("--out") + 1] if "--out" in args else os.path.join(P["work"], "overlay" if variant == "A" else "overlay_b")
    only = [int(a) for a in args[1:] if a.isdigit()]
    os.makedirs(out, exist_ok=True)
    SB, TL = load_sb(proj), load_tl(proj)
    A = Anchors(TL)
    NF = TL["frames"]
    meta = SB["meta"]
    hook_end = A(meta["hook"].get("until", 2.4), SB["beats"][0]["id"])
    subs = build_sub_events(SB, TL)
    items = []
    titles = []
    TB = {x["id"]: x for x in TL["beats"]}
    for b in SB["beats"]:
        if b.get("title"):
            titles.append((TB[b["id"]]["start"], TB[b["id"]]["end"]))
        for it in b.get("overlay", []) or []:
            it = dict(it)
            it["_t0"] = A(it.get("at"), b["id"])
            it["_t1"] = A(it.get("until", "end"), b["id"])
            if it["type"] == "keys":
                ats = it.get("key_at") or [it.get("at")] * len(it["keys"])
                it["_keys_t"] = [A(x, b["id"]) for x in ats]
            if it["type"] == "panel":
                for r in it["items"]:
                    r["_t"] = A(r.get("at", it.get("at")), b["id"])
            items.append(it)
    tc = meta.get("title_card", {})
    if tc.get("cta") is None:
        kw = meta["cta_keyword"]
        tc["cta"] = ["Comment ", kw, " " + tc.get("cta_tail", "for the cheat sheet")]

    last_key, last_path = None, None
    for f in (only or range(1, NF + 1)):
        t = (f - 1) / FPS
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        key = []
        in_title = next(((a, b) for a, b in titles if a <= t < b), None)
        if in_title:
            key.append(("T", draw_title(img, tc, t, *in_title)))
        else:
            for i, it in enumerate(items):
                if it["_t0"] <= t < it["_t1"]:
                    key.append((i, draw_item(img, it, t, A)))
            for i, e in enumerate(subs):
                if e["s"] <= t < e["e"]:
                    key.append(("s", i, draw_sub(img, e, t)))
        if t < hook_end:
            key.append(("h", draw_hook(img, meta["hook"], t, hook_end, variant)))
        key = tuple(key)
        p = os.path.join(out, f"ov_{f:04d}.png")
        if os.path.exists(p):
            os.remove(p)
        if key == last_key and last_path and not only:
            os.link(last_path, p)
        else:
            img.save(p, compress_level=1)
            last_key, last_path = key, p

    if not only:
        with open(os.path.join(proj, "captions.srt"), "w") as fh:
            lines = [x for x in TL["beats"] if x["kind"] == "line"]
            for i, x in enumerate(lines, 1):
                end = x["voice_end"] + 0.25
                if i < len(lines):
                    end = min(end, lines[i]["voice_start"] - 0.05)
                fh.write(f"{i}\n{srt_time(x['voice_start'])} --> {srt_time(end)}\n{x['text']}\n\n")
    print(f"overlay: {len(only) or NF} frames, variant {variant}, {len(subs)} subtitle chunks, {len(items)} items")


if __name__ == "__main__":
    main()
