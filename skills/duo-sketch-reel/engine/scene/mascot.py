"""The orange faceted AI mascot. Local front = -Y; origin = floor contact centre."""
import math
import bpy, bmesh
from mathutils import Vector
from util import bm_box, mesh_obj, facet, mat, empty, set_origin, col, merge, parent_keep

# body proportions follow the character sheet: wide brick, square eyes, side stubs, 4 legs
BODY_W, BODY_D, BODY_H, LEG_H = 0.20, 0.125, 0.128, 0.034


def build(parent_col):
    c = col("Mascot", parent_col)
    orange = mat("M_Mascot_Orange", (0.83, 0.15, 0.036), rough=0.38, coat=0.35, spec=0.55, sheen=0.15)
    orange_dark = mat("M_Mascot_Orange_Under", (0.62, 0.09, 0.03), rough=0.45, coat=0.2)
    eye_m = mat("M_Mascot_Eye", (0.008, 0.008, 0.01), rough=0.12, coat=0.7, spec=0.8)

    root = empty("Mascot_Root", (0, 0, 0), c, size=0.12, kind="ARROWS")

    # body: bevelled brick -> subdivided -> triangulated -> jittered = gem-like facets
    bm = bm_box(BODY_W, BODY_D, BODY_H, center=(0, 0, LEG_H + BODY_H / 2), bevel=0.02, segs=2)
    facet(bm, amount=0.0022, seed=7, subdiv=1)
    body = mesh_obj("Mascot_Body", bm, c, orange)
    set_origin(body, (0, 0, LEG_H))
    parent_keep(body, root)

    # eyes: glossy black bevelled bricks on the front face; origin low so "half-lid" squashes from the top
    eyes = []
    for side, x in (("L", 0.047), ("R", -0.047)):
        bm = bm_box(0.026, 0.012, 0.032, center=(x, -BODY_D / 2 - 0.001, LEG_H + BODY_H * 0.60), bevel=0.003, segs=1)
        e = mesh_obj(f"Mascot_Eye.{side}", bm, c, eye_m)
        set_origin(e, (x, -BODY_D / 2, LEG_H + BODY_H * 0.60 - 0.010))
        parent_keep(e, body)
        eyes.append(e)

    # side arms: short faceted stubs, pivot at the shoulder on the body side
    arms = []
    for side, s in (("L", 1), ("R", -1)):
        cx = s * (BODY_W / 2 + 0.022)
        bm = bm_box(0.05, 0.062, 0.046, center=(cx, -0.004, LEG_H + BODY_H * 0.47), bevel=0.009, segs=1)
        facet(bm, amount=0.0015, seed=11 + s)
        a = mesh_obj(f"Mascot_Arm.{side}", bm, c, orange)
        set_origin(a, (s * (BODY_W / 2 - 0.004), -0.004, LEG_H + BODY_H * 0.47))
        parent_keep(a, body)
        arms.append(a)

    # four legs in a row (like the sheet), pivot at the top so they can step
    legs = []
    for i, x in enumerate((-0.072, -0.031, 0.031, 0.072)):
        bm = bm_box(0.029, 0.072, LEG_H + 0.012, center=(x, 0.0, (LEG_H + 0.012) / 2), bevel=0.005, segs=1)
        facet(bm, amount=0.001, seed=20 + i)
        lg = mesh_obj(f"Mascot_Leg.{i}", bm, c, orange)
        set_origin(lg, (x, 0.0, LEG_H))
        parent_keep(lg, root)
        legs.append(lg)

    return {"root": root, "body": body, "eyes": eyes, "arms": arms, "legs": legs}
