"""Title treatment on the cover (inside the 3:4 grid crop y 240..1680): meta.cover.line1 / line2 / badge.
  cover_title.py <proj>
"""
import os, sys, json
from PIL import Image, ImageDraw, ImageFont, ImageFilter
proj = os.path.abspath(sys.argv[1])
SB = json.load(open(os.path.join(proj, "storyboard.json")))
cov = SB["meta"].get("cover", {})
AV = os.environ.get("DUO_FONT_DISPLAY", "/System/Library/Fonts/Avenir Next.ttc")
im = Image.open(os.path.join(proj, "renders/cover_raw.png")).convert("RGBA")
W, H = im.size
g = Image.new("L", (1, H))
for y in range(H):
    g.putpixel((0, y), int(205 * max(0, 1 - y / 900) ** 1.4))
grad = Image.new("RGBA", (W, H), (8, 4, 10, 255)); grad.putalpha(g.resize((W, H)))
im = Image.alpha_composite(im, grad)
txt = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(txt)


def fit(t, s, mw):
    while ImageFont.truetype(AV, s, index=8).getlength(t) > mw and s > 30: s -= 2
    return ImageFont.truetype(AV, s, index=8)


d.text((W // 2, 380), cov.get("line1", ""), font=fit(cov.get("line1", ""), 112, 960), fill=(255, 255, 255, 255), anchor="mm", stroke_width=8, stroke_fill=(10, 6, 12, 255))
d.text((W // 2, 510), cov.get("line2", ""), font=fit(cov.get("line2", ""), 132, 980), fill=(255, 122, 26, 255), anchor="mm", stroke_width=8, stroke_fill=(10, 6, 12, 255))
if cov.get("badge"):
    b = Image.new("RGBA", (1060, 190), (0, 0, 0, 0)); bd = ImageDraw.Draw(b)
    f2 = fit(cov["badge"], 80, 860); tw = f2.getlength(cov["badge"])
    bd.rounded_rectangle([530 - tw / 2 - 36, 22, 530 + tw / 2 + 36, 166], 28, fill=(232, 38, 52, 255), outline=(255, 255, 255, 255), width=7)
    bd.text((530, 94), cov["badge"], font=f2, fill=(255, 255, 255, 255), anchor="mm")
    b = b.rotate(-4, resample=Image.BICUBIC, expand=True)
    txt.alpha_composite(b, (W // 2 - b.width // 2, 600))
sh = txt.split()[3].filter(ImageFilter.GaussianBlur(14)).point(lambda v: int(v * 0.6))
s = Image.new("RGBA", (W, H), (0, 0, 0, 0)); s.putalpha(sh)
im = Image.alpha_composite(Image.alpha_composite(im, s), txt)
im.convert("RGB").save(os.path.join(proj, "cover.png"))
im.convert("RGB").crop((0, 240, W, 1680)).resize((240, 320)).save(os.path.join(proj, "renders/cover_grid_thumb.png"))
print("cover.png ok")
