"""Cover still: one frame of the reel (meta.cover.at, default the title-card beat's start - 0.4 s) at full res.
blender -b <proj>/project/scene.blend -P make_cover.py -- <proj>
"""
import sys, os, json, bpy
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scene"))
from tl import Anchors, fr
proj = os.path.abspath(sys.argv[sys.argv.index("--") + 1])
TL = json.load(open(os.path.join(proj, "project/timeline.json")))
SB = json.load(open(os.path.join(proj, "storyboard.json")))
A = Anchors(TL)
cov = SB["meta"].get("cover", {})
t = A(cov.get("at", "end"), cov.get("beat", SB["beats"][1]["id"]))
f = fr(t)
sc = bpy.context.scene
sc.frame_set(f)
ms = [m for m in sc.timeline_markers if m.frame <= f and m.camera]
sc.camera = max(ms, key=lambda m: m.frame).camera
sc.render.resolution_percentage = 100
sc.eevee.taa_render_samples = 64
sc.render.use_motion_blur = False
os.makedirs(os.path.join(proj, "renders"), exist_ok=True)
sc.render.filepath = os.path.join(proj, "renders", "cover_raw.png")
bpy.ops.render.render(write_still=True)
print("cover raw frame", f)
