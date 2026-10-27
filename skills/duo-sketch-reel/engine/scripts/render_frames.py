"""Render chosen frames (stills for layout checks) or every Nth frame (draft).
blender -b <proj>/project/scene.blend -P render_frames.py -- outdir pct samples [--step N | f1 f2 ...]
"""
import sys, os, bpy
a = sys.argv[sys.argv.index("--") + 1:]
out, pct, spp = a[0], int(a[1]), int(a[2])
sc = bpy.context.scene
if "--step" in a:
    frames = list(range(sc.frame_start, sc.frame_end + 1, int(a[a.index("--step") + 1])))
else:
    frames = [int(x) for x in a[3:]]
os.makedirs(out, exist_ok=True)
sc.render.resolution_percentage = pct
sc.eevee.taa_render_samples = spp
sc.render.use_motion_blur = False
for f in frames:
    path = os.path.join(out, f"d_{f:04d}.png")
    if os.path.exists(path):
        continue
    sc.frame_set(f)
    ms = [m for m in sc.timeline_markers if m.frame <= f and m.camera]
    sc.camera = max(ms, key=lambda m: m.frame).camera
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("DONE", f, flush=True)
