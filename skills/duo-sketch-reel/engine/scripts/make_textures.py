"""Set textures: night-city bokeh for the window + the sticky note on the monitor bezel (meta.sticky lines).
  make_textures.py <proj>
"""
import os, sys, random
from PIL import Image, ImageDraw, ImageFont, ImageFilter
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scene"))
from tl import proj_paths, load_sb

SANS = os.environ.get("DUO_FONT_SANS", "/System/Library/Fonts/SFNS.ttf")


def font(size, var):
    f = ImageFont.truetype(SANS, size)
    try: f.set_variation_by_name(var)
    except Exception: pass
    return f


def city(out):
    W, H = 1800, 1300
    rnd = random.Random(42)
    img = Image.new("RGB", (W, H)); d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H; d.line([(0, y), (W, y)], fill=(int(4 + 12 * t), int(6 + 18 * t), int(18 + 42 * t)))
    for _ in range(30):
        bw, bx, bh = rnd.randint(60, 180), rnd.randint(-50, W), rnd.randint(250, 850)
        d.rectangle([bx, H - bh, bx + bw, H], fill=(6, 8, 16))
        for wy in range(H - bh + 25, H - 20, 30):
            for wx in range(bx + 12, bx + bw - 12, 22):
                if rnd.random() < 0.18:
                    d.rectangle([wx, wy, wx + 6, wy + 10], fill=rnd.choice([(255, 220, 140), (140, 180, 255), (200, 160, 255)]))
    img = img.filter(ImageFilter.GaussianBlur(10))
    bok = Image.new("RGB", (W, H)); bd = ImageDraw.Draw(bok)
    for _ in range(50):
        r, x, y = rnd.randint(15, 65), rnd.randint(0, W), rnd.randint(int(H * 0.3), H)
        c = rnd.choice([(70, 130, 255), (120, 180, 255), (200, 140, 255), (255, 180, 100)]); k = rnd.uniform(0.18, 0.5)
        bd.ellipse([x - r, y - r, x + r, y + r], fill=tuple(int(v * k) for v in c))
    bok = bok.filter(ImageFilter.GaussianBlur(8))
    img = Image.blend(img, Image.composite(bok, img, bok.convert("L").point(lambda v: 255 if v > 8 else 0)), 0.5)
    img.save(os.path.join(out, "city_bokeh.png"))


def sticky(out, lines):
    img = Image.new("RGBA", (512, 512), (255, 240, 100, 255)); d = ImageDraw.Draw(img)
    sizes = [(52, "Heavy", (30, 30, 30)), (70, "Heavy", (220, 30, 40)), (36, "Medium", (90, 80, 40))]
    y = 170
    for i, ln in enumerate(lines[:3]):
        s, v, c = sizes[min(i, 2)]
        while font(s, v).getlength(ln) > 460 and s > 20: s -= 2
        d.text((256, y), ln, font=font(s, v), fill=c, anchor="mm"); y += 80
    img.save(os.path.join(out, "sticky_note.png"))


if __name__ == "__main__":
    P = proj_paths(sys.argv[1]); SB = load_sb(sys.argv[1])
    out = os.path.join(P["work"], "textures"); os.makedirs(out, exist_ok=True)
    city(out); sticky(out, SB["meta"].get("sticky", ["SHIP IT", "TODAY", "(maybe)"]))
    print("textures ok")
