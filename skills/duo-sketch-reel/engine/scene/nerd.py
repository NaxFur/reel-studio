"""The Nerd: stylised low-poly developer with an IK rig.

Built standing in rest pose, facing +Y (towards the monitor), origin at the floor.
Clothes are skinned (envelope-style weights we compute ourselves); head, face
parts, hands and shoes are rigid bone children so they can be animated directly.
"""
import math, random
import bpy, bmesh
from mathutils import Vector, Matrix, Euler
from mathutils.bvhtree import BVHTree
from util import (bm_box, bm_cyl, bm_sphere, bm_segment, mesh_obj, facet, mat, empty, set_origin,
                  col, merge, parent_keep, emission_mat)

SKIN = (0.74, 0.39, 0.205)
BONES = {
    # name: (head, tail, parent, connect)
    "root": ((0, 0, 0), (0, 0.15, 0), None, False),
    "hips": ((0, 0, 0.93), (0, 0, 1.06), "root", False),
    "spine": ((0, 0, 1.06), (0, -0.005, 1.24), "hips", True),
    "chest": ((0, -0.005, 1.24), (0, -0.01, 1.44), "spine", True),
    "neck": ((0, -0.005, 1.44), (0, 0.0, 1.52), "chest", False),
    "head": ((0, 0.0, 1.52), (0, 0.0, 1.76), "neck", True),
}
for s, x in (("L", 1), ("R", -1)):
    BONES.update({
        f"shoulder.{s}": ((x * 0.04, -0.01, 1.41), (x * 0.185, -0.01, 1.415), "chest", False),
        f"upper_arm.{s}": ((x * 0.205, -0.01, 1.40), (x * 0.235, -0.04, 1.12), f"shoulder.{s}", False),
        f"forearm.{s}": ((x * 0.235, -0.04, 1.12), (x * 0.255, 0.0, 0.875), f"upper_arm.{s}", True),
        f"hand.{s}": ((x * 0.255, 0.0, 0.875), (x * 0.262, 0.004, 0.77), f"forearm.{s}", True),
        f"thigh.{s}": ((x * 0.095, 0.0, 0.93), (x * 0.10, 0.02, 0.50), "hips", False),
        f"shin.{s}": ((x * 0.10, 0.02, 0.50), (x * 0.10, -0.005, 0.085), f"thigh.{s}", True),
        f"foot.{s}": ((x * 0.10, -0.005, 0.085), (x * 0.10, 0.13, 0.02), f"shin.{s}", True),
    })


def seg_dist(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / ab.length_squared))
    return (p - (a + ab * t)).length


def skin(ob, arm, bone_names, power=6.0):
    """Envelope-style weights: inverse distance to bone segments, normalised."""
    mod = ob.modifiers.new("Armature", "ARMATURE")
    mod.object = arm
    groups = {b: ob.vertex_groups.new(name=b) for b in bone_names}
    segs = {b: (Vector(BONES[b][0]), Vector(BONES[b][1])) for b in bone_names}
    for v in ob.data.vertices:
        p = ob.matrix_world @ v.co
        d = {b: seg_dist(p, *segs[b]) for b in bone_names}
        w = {b: 1.0 / (max(dd, 1e-4) ** power) for b, dd in d.items()}
        tot = sum(w.values())
        for b, ww in w.items():
            ww /= tot
            if ww > 0.01:
                groups[b].add([v.index], ww, "REPLACE")
    parent_keep(ob, arm)


def bone_child(ob, arm, bone):
    """Rigid child of a bone that keeps its rest position and its own local transform."""
    bpy.context.view_layer.update()
    b = arm.data.bones[bone]
    ob.parent = arm
    ob.parent_type = "BONE"
    ob.parent_bone = bone
    rest = arm.matrix_world @ b.matrix_local @ Matrix.Translation((0, b.length, 0))
    ob.matrix_parent_inverse = rest.inverted()


def loft(rings, segs=10, cap_bottom=True, cap_top=False):
    """rings: list of (z, rx, ry, cy) ellipses -> closed tube mesh."""
    bm = bmesh.new()
    loops = []
    for z, rx, ry, cy in rings:
        loop = []
        for i in range(segs):
            a = 2 * math.pi * i / segs + math.pi / segs
            loop.append(bm.verts.new((rx * math.cos(a), cy + ry * math.sin(a), z)))
        loops.append(loop)
    for l0, l1 in zip(loops, loops[1:]):
        for i in range(segs):
            bm.faces.new((l0[i], l0[(i + 1) % segs], l1[(i + 1) % segs], l1[i]))
    if cap_bottom:
        bm.faces.new(list(reversed(loops[0])))
    if cap_top:
        bm.faces.new(loops[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def tube(points, radii, segs=7, cap=True):
    """Tube through 3D points (limbs). radii per point."""
    bm = bmesh.new()
    pts = [Vector(p) for p in points]
    loops = []
    for i, (p, r) in enumerate(zip(pts, radii)):
        d = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        q = Vector((0, 0, 1)).rotation_difference(d)
        loop = []
        for k in range(segs):
            a = 2 * math.pi * k / segs
            loop.append(bm.verts.new(p + q @ Vector((r * math.cos(a), r * math.sin(a), 0))))
        loops.append(loop)
    for l0, l1 in zip(loops, loops[1:]):
        for k in range(segs):
            bm.faces.new((l0[k], l0[(k + 1) % segs], l1[(k + 1) % segs], l1[k]))
    if cap:
        bm.faces.new(list(reversed(loops[0])))
        bm.faces.new(loops[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def build(parent_col):
    c = col("Nerd", parent_col)
    rnd = random.Random(3)
    skin_m = mat("M_Skin", SKIN, rough=0.5, sheen=0.15, spec=0.35)
    hair_m = mat("M_Hair", (0.014, 0.010, 0.012), rough=0.5, spec=0.5, sheen=0.4)
    hood_m = mat("M_Hoodie", (0.017, 0.017, 0.021), rough=0.8, sheen=0.12, spec=0.35)
    hood_rib = mat("M_Hoodie_Rib", (0.011, 0.011, 0.014), rough=0.9, sheen=0.1, spec=0.3)
    string_m = mat("M_Drawstring", (0.25, 0.25, 0.27), rough=0.7)
    pants_m = mat("M_Pants", (0.012, 0.012, 0.015), rough=0.8, sheen=0.1)
    shoe_m = mat("M_Shoe", (0.02, 0.02, 0.025), rough=0.6, coat=0.1)
    sole_m = mat("M_Sole", (0.78, 0.77, 0.74), rough=0.55)
    glass_m = mat("M_Glasses", (0.003, 0.003, 0.004), rough=0.28, coat=0.15, spec=0.45)
    eye_m = mat("M_Eye", (0.022, 0.011, 0.007), rough=0.08, coat=1.0, spec=0.9)
    hl_m = emission_mat("M_EyeHighlight", (1, 1, 1), 3.0)
    brow_m = mat("M_Brow", (0.012, 0.009, 0.01), rough=0.6)
    mouth_m = mat("M_Mouth", (0.09, 0.012, 0.012), rough=0.6, spec=0.2)

    # ---------------- armature ----------------
    ad = bpy.data.armatures.new("Nerd_Rig")
    arm = bpy.data.objects.new("Nerd_Rig", ad)
    c.objects.link(arm)
    ad.display_type = "STICK"
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    eb = {}
    for name, (h, t, par, con) in BONES.items():
        b = ad.edit_bones.new(name)
        b.head, b.tail = h, t
        b.roll = 0
        eb[name] = b
    for name, (h, t, par, con) in BONES.items():
        if par:
            eb[name].parent = eb[par]
            eb[name].use_connect = con
    bpy.ops.object.mode_set(mode="OBJECT")
    for pb in arm.pose.bones:
        pb.rotation_mode = "XYZ"

    # ---------------- head ----------------
    bm = bm_sphere(1.0, u=14, v=10)
    for v in bm.verts:
        x, y, z = v.co
        x *= 0.104; y *= 0.112; z *= 0.135
        if z < 0:  # jaw taper + chin
            k = (-z / 0.135)
            x *= 1 - 0.38 * k ** 1.6
            y *= 1 - 0.18 * k ** 2
            if y > 0: y += 0.010 * k
        if y > 0 and z > 0.02:  # flatter forehead
            y *= 0.93
        if abs(x) > 0.07 and -0.04 < z < 0.05:  # cheekbone plane
            x *= 0.985
        v.co = Vector((x, y + 0.012, z + 1.625))
    facet(bm, amount=0.0012, seed=5)
    head = mesh_obj("Nerd_Head", bm, c, skin_m)
    head_parts = [head]

    # ears, nose
    for s in (1, -1):
        bm = bm_sphere(0.028, center=(s * 0.103, -0.004, 1.618), u=6, v=4, scale=(0.45, 0.8, 1.0))
        facet(bm)
        head_parts.append(mesh_obj(f"Nerd_Ear.{'L' if s > 0 else 'R'}", bm, c, skin_m))
    bm = bmesh.new()
    tip = bm.verts.new((0, 0.137, 1.590))
    b1 = bm.verts.new((0.016, 0.112, 1.582)); b2 = bm.verts.new((-0.016, 0.112, 1.582)); b3 = bm.verts.new((0, 0.115, 1.625))
    bm.faces.new((tip, b1, b3)); bm.faces.new((tip, b3, b2)); bm.faces.new((tip, b2, b1)); bm.faces.new((b1, b2, b3))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    head_parts.append(mesh_obj("Nerd_Nose", bm, c, skin_m))

    # BVH of the head to stick face features on the surface
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    bvh = BVHTree.FromObject(head, deps)

    def surf_y(x, z, off=0.0):
        hit = bvh.ray_cast(Vector((x, 0.5, z)), Vector((0, -1, 0)))
        return (hit[0].y if hit[0] else 0.11) + off

    # eyes (dark glossy ovals) + highlight
    eyes = []
    for side, s in (("L", 1), ("R", -1)):
        x, z = s * 0.041, 1.612
        y = surf_y(x, z, -0.004)
        bm = bm_sphere(1.0, center=(0, 0, 0), u=10, v=6, scale=(0.0125, 0.007, 0.0165))
        e = mesh_obj(f"Nerd_Eye.{side}", bm, c, eye_m, smooth=True)
        e.location = (x, y + 0.002, z)
        bm = bm_sphere(0.0038, center=(0, 0, 0), u=6, v=4)
        h = mesh_obj(f"Nerd_EyeHL.{side}", bm, c, hl_m, smooth=True)
        h.location = (x + s * -0.004 + 0.0, y + 0.0085, z + 0.006)
        parent_keep(h, e)
        eyes.append(e)

    # eyebrows: thick angular bars that follow the forehead
    brows = []
    for side, s in (("L", 1), ("R", -1)):
        pts = [(s * 0.019, 1.654), (s * 0.044, 1.659), (s * 0.067, 1.651)]
        p3 = [(x, surf_y(x, z, 0.0042), z) for x, z in pts]
        bm = tube(p3, [0.0052, 0.0058, 0.0036], segs=4)
        br = mesh_obj(f"Nerd_Brow.{side}", bm, c, brow_m)
        set_origin(br, (s * 0.044, surf_y(s * 0.044, 1.656, 0.003), 1.656))
        brows.append(br)

    # mouth: small disk projected on the face, shape keys for lip sync / expression
    RINGS = (1.0, 0.7, 0.4, 0.0)   # concentric rings so the filled mouth hugs the curved face

    def mouth_shape(kind):
        out = []
        n = 16
        for r in RINGS:
            for i in range(n if r > 0 else 1):
                a = 2 * math.pi * i / n
                cx, cz = math.cos(a) * r, math.sin(a) * r
                w, h = 0.024, 0.0022
                if kind == "Open": h = 0.017
                if kind == "Wide": w, h = 0.030, 0.006
                if kind == "Smile": w, h = 0.027, 0.003
                if kind == "Frown": w, h = 0.022, 0.0025
                if kind == "O": w, h = 0.012, 0.013
                x, z = w * cx, h * cz
                if kind == "Smile": z += 0.010 * ((cx / max(r, 1e-6)) ** 2 * r if r > 0 else 0) - 0.003
                if kind == "Frown": z -= 0.007 * ((cx / max(r, 1e-6)) ** 2 * r if r > 0 else 0) - 0.002
                if kind == "Open" and cz > 0: z *= 0.55   # upper lip moves less than the jaw
                out.append((x, 1.553 + z))
        return [(x, surf_y(x, z, 0.0016), z) for x, z in out]

    bm = bmesh.new()
    vs = [bm.verts.new(p) for p in mouth_shape("Basis")]
    n = 16
    for ri in range(len(RINGS) - 2):
        a0, a1 = ri * n, (ri + 1) * n
        for i in range(n):
            bm.faces.new((vs[a0 + i], vs[a0 + (i + 1) % n], vs[a1 + (i + 1) % n], vs[a1 + i]))
    c_ = vs[-1]; a0 = (len(RINGS) - 2) * n
    for i in range(n):
        bm.faces.new((vs[a0 + i], vs[a0 + (i + 1) % n], c_))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    for f_ in bm.faces:
        if f_.normal.y < 0: f_.normal_flip()
    mouth = mesh_obj("Nerd_Mouth", bm, c, mouth_m, smooth=True)
    mouth.shape_key_add(name="Basis")
    for k in ("Open", "Wide", "Smile", "Frown", "O"):
        sk = mouth.shape_key_add(name=k, from_mix=False)
        sk.value = 0.0
        sk.slider_min, sk.slider_max = 0.0, 1.0
        for i, p in enumerate(mouth_shape(k)):
            sk.data[i].co = p
    set_origin(mouth, (0, surf_y(0, 1.553), 1.553))

    # glasses: rectangular black frames + faint reflective lenses
    gl = []
    fy = 0.124
    for s in (1, -1):
        cx, cz, w, h, t = s * 0.043, 1.613, 0.058, 0.043, 0.0055
        gl += [bm_box(w + t, t, t, center=(cx, fy, cz + h / 2)), bm_box(w + t, t, t * 1.2, center=(cx, fy, cz - h / 2)),
               bm_box(t, t, h, center=(cx - w / 2, fy, cz)), bm_box(t, t, h, center=(cx + w / 2, fy, cz)),
               bm_box(0.0045, 0.11, 0.006, center=(s * 0.103, fy - 0.058, cz + 0.014))]
    gl.append(bm_box(0.03, 0.005, 0.006, center=(0, fy, 1.622)))
    glasses = mesh_obj("Nerd_Glasses", merge(*gl), c, glass_m)
    lens_m = mat("M_Lens", (0.01, 0.012, 0.016), rough=0.05, spec=0.6, alpha=0.05)
    lenses = mesh_obj("Nerd_Lenses", merge(bm_box(0.057, 0.0015, 0.042, center=(0.043, fy - 0.001, 1.613)),
                                           bm_box(0.057, 0.0015, 0.042, center=(-0.043, fy - 0.001, 1.613))), c, lens_m)

    # hair: cap + many faceted spikes, swept back and up, fringe over forehead
    bm = bm_sphere(1.0, u=14, v=10)
    hl = lambda y: 0.05 + (0.30 * y if y > 0 else 0.62 * y)   # hairline height per direction
    kill = [v for v in bm.verts if v.co.z < hl(v.co.y)]
    for v in bm.verts:
        x, y, z = v.co
        v.co = Vector((x * 0.112, y * 0.121 + 0.008, z * 0.142 + 1.632))
    bmesh.ops.delete(bm, geom=kill, context="VERTS")
    parts = [bm]
    spikes = []
    while len(spikes) < 48:
        th = rnd.uniform(0, 2 * math.pi)
        ph = rnd.uniform(0.0, 1.75)
        d = Vector((math.sin(ph) * math.cos(th), math.sin(ph) * math.sin(th), math.cos(ph)))
        if d.z < hl(d.y) + 0.12 or (d.y > 0.45 and d.z < 0.62):
            continue
        spikes.append(d)
    for k, (x, z, dy, dz) in enumerate([(-0.05, 1.70, 0.65, -0.55), (-0.012, 1.712, 0.7, -0.5), (0.03, 1.705, 0.68, -0.6),
                                         (0.066, 1.69, 0.55, -0.6), (-0.082, 1.684, 0.45, -0.55)]):
        spikes.append(("fringe", Vector((x, 0.086, z)), Vector((x * 1.6, dy, dz)).normalized()))
    for sp in spikes:
        if isinstance(sp, tuple):
            _, base, d = sp
            ln, r = rnd.uniform(0.045, 0.065), rnd.uniform(0.020, 0.028)
        else:
            d = (sp + Vector((0, -0.32, 0.30))).normalized()
            base = Vector((sp.x * 0.108, sp.y * 0.117 + 0.008, sp.z * 0.137 + 1.632))
            ln, r = rnd.uniform(0.06, 0.115), rnd.uniform(0.026, 0.042)
        b = bm_cyl(r, 0.0, ln, segs=4)
        bmesh.ops.translate(b, vec=(0, 0, ln / 2), verts=b.verts)
        bmesh.ops.rotate(b, verts=b.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(rnd.uniform(0, 1.5), 3, "Z"))
        bmesh.ops.rotate(b, verts=b.verts, cent=(0, 0, 0), matrix=Vector((0, 0, 1)).rotation_difference(d).to_matrix())
        bmesh.ops.translate(b, vec=base - d * 0.012, verts=b.verts)
        parts.append(b)
    hb = merge(*parts)
    facet(hb, amount=0.002, seed=9)
    hair = mesh_obj("Nerd_Hair", hb, c, hair_m)

    for ob in head_parts + [glasses, lenses, hair, mouth] + eyes + brows:
        bone_child(ob, arm, "head")

    # neck
    neck = mesh_obj("Nerd_Neck", bm_cyl(0.043, 0.04, 0.12, center=(0, 0.0, 1.49), segs=8), c, skin_m)
    bone_child(neck, arm, "neck")

    # ---------------- hoodie ----------------
    rings = [(0.885, 0.168, 0.115, 0.005), (0.92, 0.172, 0.118, 0.006), (1.02, 0.176, 0.122, 0.008),
             (1.16, 0.182, 0.126, 0.006), (1.30, 0.200, 0.128, 0.0), (1.385, 0.212, 0.12, -0.006),
             (1.43, 0.19, 0.105, -0.01), (1.465, 0.11, 0.085, -0.012), (1.475, 0.06, 0.06, -0.01)]
    bm = loft(rings, segs=12, cap_bottom=True, cap_top=True)
    facet(bm, amount=0.0025, seed=12)
    torso = mesh_obj("Nerd_Hoodie", bm, c, hood_m)
    skin(torso, arm, ["hips", "spine", "chest", "neck"], power=5)
    # hood bunched behind the neck + front details
    bm = bm_sphere(1.0, u=10, v=6)
    kill = [v for v in bm.verts if v.co.y > 0.35]
    for v in bm.verts:
        v.co = Vector((v.co.x * 0.125, v.co.y * 0.07 - 0.09, v.co.z * 0.065 + 1.455))
    bmesh.ops.delete(bm, geom=kill, context="VERTS")
    facet(bm, amount=0.003, seed=13)
    hood = mesh_obj("Nerd_Hood", bm, c, hood_m)
    bits = [bm_box(0.17, 0.022, 0.10, center=(0, 0.128, 1.0), bevel=0.01, segs=1)]  # kangaroo pocket
    for s in (1, -1):
        bits.append(bm_segment((s * 0.032, 0.124, 1.43), (s * 0.036, 0.137, 1.29), 0.0035, 0.0035, segs=5))
        bits.append(bm_sphere(0.006, center=(s * 0.036, 0.137, 1.285), u=6, v=4))
    det = mesh_obj("Nerd_HoodieDetails", merge(*bits[:1]), c, hood_rib)
    strings = mesh_obj("Nerd_Drawstrings", merge(*bits[1:]), c, string_m)
    for ob in (hood, det, strings):
        skin(ob, arm, ["spine", "chest", "neck"], power=5)

    # sleeves (skinned through shoulder/elbow), cuffs, hands
    hands = {}
    for s, x in (("L", 1), ("R", -1)):
        sh, el, wr = Vector(BONES[f"upper_arm.{s}"][0]), Vector(BONES[f"forearm.{s}"][0]), Vector(BONES[f"hand.{s}"][0])
        pts = [sh + Vector((x * -0.012, 0, 0.012)), sh.lerp(el, 0.25), sh.lerp(el, 0.6), el, el.lerp(wr, 0.55), wr + (wr - el).normalized() * -0.025]
        rad = [0.060, 0.060, 0.057, 0.052, 0.050, 0.047]
        bm = tube(pts, rad, segs=8)
        facet(bm, amount=0.002, seed=20 + x)
        sl = mesh_obj(f"Nerd_Sleeve.{s}", bm, c, hood_m)
        skin(sl, arm, [f"upper_arm.{s}", f"forearm.{s}"], power=9)
        cuff = mesh_obj(f"Nerd_Cuff.{s}", tube([wr + (wr - el).normalized() * -0.035, wr + (wr - el).normalized() * 0.002],
                                                [0.046, 0.044], segs=8), c, hood_rib)
        skin(cuff, arm, [f"forearm.{s}"])
        # mitten hand + thumb, palm facing the body (−x on the left side)
        # palm + four slightly splayed fingers + thumb (palm faces the body in rest pose)
        hc = wr + Vector((x * 0.004, 0.002, -0.036))
        parts_h = [bm_box(0.030, 0.076, 0.062, center=hc, bevel=0.011, segs=1)]
        for k, (fy, ln) in enumerate(((0.026, 0.040), (0.009, 0.046), (-0.009, 0.044), (-0.026, 0.036))):
            top = hc + Vector((x * -0.002, fy, -0.028))
            tip = top + Vector((x * -0.004, fy * 0.12, -ln))
            parts_h.append(bm_segment(top, tip, 0.0085, 0.0072, segs=5))
        parts_h.append(bm_segment(hc + Vector((x * -0.006, 0.03, 0.012)), hc + Vector((x * -0.014, 0.060, -0.022)), 0.0105, 0.008, segs=5))
        hm = merge(*parts_h)
        facet(hm, amount=0.0012, seed=30 + x)
        hand = mesh_obj(f"Nerd_Hand.{s}", hm, c, skin_m)
        bone_child(hand, arm, f"hand.{s}")
        hands[s] = hand

    # ---------------- legs ----------------
    bm = bm_box(0.33, 0.21, 0.13, center=(0, 0.0, 0.905), bevel=0.04, segs=2)
    facet(bm, amount=0.002, seed=40)
    pelvis = mesh_obj("Nerd_PantsHips", bm, c, pants_m)
    skin(pelvis, arm, ["hips", "thigh.L", "thigh.R"], power=4)
    for s, x in (("L", 1), ("R", -1)):
        hp, kn, an = Vector(BONES[f"thigh.{s}"][0]), Vector(BONES[f"shin.{s}"][0]), Vector(BONES[f"foot.{s}"][0])
        pts = [hp + Vector((0, 0, 0.03)), hp.lerp(kn, 0.5), kn, kn.lerp(an, 0.55), an + Vector((0, 0, 0.03)), an + Vector((0, 0, 0.0))]
        bm = tube(pts, [0.085, 0.075, 0.064, 0.058, 0.055, 0.052], segs=8)
        facet(bm, amount=0.002, seed=50 + x)
        lg = mesh_obj(f"Nerd_PantLeg.{s}", bm, c, pants_m)
        skin(lg, arm, [f"thigh.{s}", f"shin.{s}"], power=6)
        sole = bm_box(0.10, 0.29, 0.032, center=(x * 0.10, 0.065, 0.016), bevel=0.012, segs=1)
        upper = bm_box(0.092, 0.25, 0.075, center=(x * 0.10, 0.05, 0.068), bevel=0.028, segs=2)
        facet(upper, amount=0.0015, seed=60 + x)
        shoe = mesh_obj(f"Nerd_Shoe.{s}", merge(upper), c, shoe_m)
        sol = mesh_obj(f"Nerd_Sole.{s}", merge(sole), c, sole_m)
        lace = mesh_obj(f"Nerd_Laces.{s}", merge(*[bm_box(0.05, 0.008, 0.006, center=(x * 0.10, 0.08 + i * 0.022, 0.105 - i * 0.004)) for i in range(4)]), c, sole_m)
        for ob in (shoe, sol, lace):
            bone_child(ob, arm, f"foot.{s}")

    return {"arm": arm, "eyes": eyes, "brows": brows, "mouth": mouth, "hands": hands, "head": head,
            "glasses": glasses, "lenses": lenses, "hair": hair}


def setup_ik(arm, c):
    """IK targets for hands and feet, with poles. Returns dict of controls."""
    ctr = {}
    pole_angles = {}
    for s, x in (("L", 1), ("R", -1)):
        wr = Vector(BONES[f"hand.{s}"][0])
        ht = empty(f"IK_hand.{s}", wr, c, 0.04, kind="CUBE")
        hp = empty(f"Pole_elbow.{s}", (x * 0.55, -0.45, 1.05), c, 0.03, kind="SPHERE")
        an = Vector(BONES[f"foot.{s}"][0])
        ft = empty(f"IK_foot.{s}", an, c, 0.04, kind="CUBE")
        kp = empty(f"Pole_knee.{s}", (x * 0.14, 0.7, 0.5), c, 0.03, kind="SPHERE")
        pb = arm.pose.bones[f"forearm.{s}"]
        ik = pb.constraints.new("IK"); ik.target = ht; ik.pole_target = hp; ik.chain_count = 2
        cr = arm.pose.bones[f"hand.{s}"].constraints.new("COPY_ROTATION"); cr.target = ht
        pb = arm.pose.bones[f"shin.{s}"]
        ik2 = pb.constraints.new("IK"); ik2.target = ft; ik2.pole_target = kp; ik2.chain_count = 2
        cr2 = arm.pose.bones[f"foot.{s}"].constraints.new("COPY_ROTATION"); cr2.target = ft
        ctr.update({f"hand.{s}": ht, f"elbow.{s}": hp, f"foot.{s}": ft, f"knee.{s}": kp})
        # the targets carry rest orientation of the end bones so "identity" = rest pose
        ht.rotation_mode = ft.rotation_mode = "QUATERNION"
        ht.rotation_quaternion = arm.data.bones[f"hand.{s}"].matrix_local.to_quaternion()
        ft.rotation_quaternion = arm.data.bones[f"foot.{s}"].matrix_local.to_quaternion()
    # pick pole angles that put the elbow/knee on the pole side (depends on bone roll)
    for s in ("L", "R"):
        for bone, pole, mid in ((f"forearm.{s}", ctr[f"elbow.{s}"], f"upper_arm.{s}"), (f"shin.{s}", ctr[f"knee.{s}"], f"thigh.{s}")):
            con = arm.pose.bones[bone].constraints[0]
            tgt = con.target
            keep = tgt.location.copy()
            tgt.location = keep + (Vector((0, 0.18, 0.22)) if "forearm" in bone else Vector((0, 0.25, 0.3)))
            best = None
            for ang in (0, 90, -90, 180):
                con.pole_angle = math.radians(ang)
                bpy.context.view_layer.update()
                tail = arm.matrix_world @ arm.pose.bones[mid].tail
                dd = (tail - pole.matrix_world.translation).length
                if best is None or dd < best[0]:
                    best = (dd, ang)
            con.pole_angle = math.radians(best[1])
            pole_angles[bone] = best[1]
            tgt.location = keep
    return ctr, pole_angles


def hand_rot(arm, side, desired):
    """Quaternion for an IK hand target so the hand mesh is rotated by `desired` (world) from rest."""
    rest = arm.data.bones[f"hand.{side}"].matrix_local.to_quaternion()
    return desired @ rest
