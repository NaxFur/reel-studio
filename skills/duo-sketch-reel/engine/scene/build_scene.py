"""Builds the set, both characters, the acting, lights and cameras of one episode, then saves the .blend.

blender -b --factory-startup -P engine/scene/build_scene.py -- <proj> [--no-anim]
Reads <proj>/storyboard.json, <proj>/project/{timeline,lipsync}.json; screens from <proj>/project/screen*/.
Writes <proj>/project/scene.blend.
"""
import sys, os, json, math, importlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy
from mathutils import Matrix
import util, env, nerd, mascot, lights, tl
for m in (util, env, nerd, mascot, lights, tl):
    importlib.reload(m)

args = sys.argv[sys.argv.index("--") + 1:]
PROJ = os.path.abspath(args[0])
P = tl.proj_paths(PROJ)
TL = json.load(open(P["tl"]))
SB = json.load(open(P["sb"]))
lip = json.load(open(P["lip"]))

for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob, do_unlink=True)
for coll in list(bpy.data.collections):
    bpy.data.collections.remove(coll)
scene = bpy.context.scene
scene.frame_start, scene.frame_end = 1, TL["frames"]
scene.render.fps = 30

root_c = util.col("DuoReel")
F = env.build(root_c, os.path.join(P["work"], "screen"), TL["frames"])
N = nerd.build(root_c)
ctr, poles = nerd.setup_ik(N["arm"], util.col("Nerd"))
M = mascot.build(root_c)
L = lights.build(root_c, F)
lights.render_settings(scene)

# default placement: Nerd seated in the chair (same rig as eps. 1-7)
arm = N["arm"]
chair = F["chair_root"]
util.parent_keep(arm, chair)
arm.location = (0, -0.31, -0.405)
for s, x in (("L", 1), ("R", -1)):
    util.parent_keep(ctr[f"foot.{s}"], chair)
    util.parent_keep(ctr[f"knee.{s}"], chair)
    ctr[f"foot.{s}"].location = (x * 0.13, 0.12, 0.085)
    ctr[f"knee.{s}"].location = (x * 0.16, 0.9, 0.62)
    ctr[f"elbow.{s}"].location = (x * 0.65, -0.55, 0.70)
    ctr[f"hand.{s}"].location = (x * 0.105 - 0.02, 0.055, 0.805)
for s, ang in (("L", -90), ("R", 90)):
    desired = (Matrix.Rotation(math.radians(ang), 4, "Y") @ Matrix.Rotation(math.radians(90), 4, "X")).to_quaternion()
    ctr[f"hand.{s}"].rotation_quaternion = nerd.hand_rot(arm, s, desired)
M["root"].location = (0.33, 0.16, env.DESK_Z)
M["root"].rotation_euler = (0, 0, math.radians(200))
scene["poles"] = json.dumps(poles)
scene.camera = None
bpy.context.view_layer.update()

if "--no-anim" not in args:
    import animate
    importlib.reload(animate)
    animate.run(scene, TL, SB, F, N, ctr, M, L, lip)

out = os.path.join(P["work"], "scene.blend")
bpy.ops.wm.save_as_mainfile(filepath=out, compress=True)
print("SAVED", out)
