"""Layout check: composite 3D stills + overlay at chosen times into one contact sheet.
  stills.py <proj> [--times 1.2,3.4 ...] [--pct 40] [--spp 16]
Default times: each beat's end - 0.25 s (where payoffs sit, see the anchor rule) and the first frame.
Writes <proj>/renders/stills/sheet.jpg (and the single composites).
"""
import os, sys, json, subprocess
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scene"))
from tl import proj_paths, load_tl, fr

BLENDER = os.environ.get("BLENDER", "/Applications/Blender.app/Contents/MacOS/Blender")
a = sys.argv[1:]
proj = os.path.abspath(a[0]); P = proj_paths(proj); TL = load_tl(proj)
pct = int(a[a.index("--pct") + 1]) if "--pct" in a else 40
spp = int(a[a.index("--spp") + 1]) if "--spp" in a else 16
if "--times" in a:
    times = [float(x) for x in a[a.index("--times") + 1].split(",")]
else:
    times = [0.0] + [max(b["start"] + 0.05, b["end"] - 0.25) for b in TL["beats"]]
frames = sorted({min(TL["frames"], fr(t)) for t in times})
out = os.path.join(proj, "renders", "stills"); os.makedirs(out, exist_ok=True)
for f in frames:
    p = os.path.join(out, f"d_{f:04d}.png")
    if os.path.exists(p): os.remove(p)
subprocess.run([BLENDER, "-b", "--factory-startup", os.path.join(P["work"], "scene.blend"), "-P", os.path.join(HERE, "render_frames.py"),
                "--", out, str(pct), str(spp)] + [str(f) for f in frames], check=True, capture_output=True)
py = sys.executable
subprocess.run([py, os.path.join(HERE, "make_overlay.py"), proj, "--out", os.path.join(out, "ov")] + [str(f) for f in frames], check=True)
tiles = []
for f in frames:
    im = Image.open(os.path.join(out, f"d_{f:04d}.png")).convert("RGBA").resize((1080, 1920))
    ov = Image.open(os.path.join(out, "ov", f"ov_{f:04d}.png")).convert("RGBA")
    c = Image.alpha_composite(im, ov).convert("RGB")
    c.save(os.path.join(out, f"c_{f:04d}.jpg"), quality=85)
    th = c.resize((270, 480)); ImageDraw.Draw(th).text((8, 8), f"{(f - 1) / 30:.2f}s", fill=(255, 255, 0))
    tiles.append(th)
cols = 6
rows = (len(tiles) + cols - 1) // cols
sheet = Image.new("RGB", (cols * 270, rows * 480), (0, 0, 0))
for i, t in enumerate(tiles):
    sheet.paste(t, ((i % cols) * 270, (i // cols) * 480))
sheet.save(os.path.join(out, "sheet.jpg"), quality=82)
print("sheet:", os.path.join(out, "sheet.jpg"), len(frames), "frames")
