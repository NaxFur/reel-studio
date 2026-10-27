"""Render a frame range of the final animation to PNGs (resumable: skips existing frames).
blender -b project/claude_broke_my_app.blend -P scripts/render_range.py -- outdir start end [samples]
"""
import sys, os, bpy
a = sys.argv[sys.argv.index("--") + 1:]
out, f0, f1 = a[0], int(a[1]), int(a[2])
spp = int(a[3]) if len(a) > 3 else 48
os.makedirs(out, exist_ok=True)
sc = bpy.context.scene
sc.render.resolution_percentage = 100
sc.eevee.taa_render_samples = spp
sc.render.use_motion_blur = True
for f in range(f0, f1 + 1):
    path = os.path.join(out, f"frame_{f:04d}.png")
    if os.path.exists(path) and os.path.getsize(path) > 0:
        continue
    sc.frame_set(f)
    ms = [m for m in sc.timeline_markers if m.frame <= f and m.camera]
    sc.camera = max(ms, key=lambda m: m.frame).camera
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("DONE", f, flush=True)
