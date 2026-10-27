"""Shared helpers for building the scene procedurally with bpy/bmesh."""
import math, random
import bpy, bmesh
from mathutils import Vector, Matrix, Euler

FPS = 30


def col(name, parent=None):
    c = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    p = parent or bpy.context.scene.collection
    if c.name not in [x.name for x in p.children]:
        p.children.link(c)
    return c


def link(obj, collection):
    for c in obj.users_collection:
        c.objects.unlink(obj)
    collection.objects.link(obj)
    return obj


def mesh_obj(name, bm, collection, mat=None, smooth=False):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = smooth
    ob = bpy.data.objects.new(name, me)
    collection.objects.link(ob)
    if mat:
        if isinstance(mat, (list, tuple)):
            for m in mat: me.materials.append(m)
        else:
            me.materials.append(mat)
    return ob


def bm_box(sx, sy, sz, center=(0, 0, 0), bevel=0.0, segs=1):
    """Box of full size (sx,sy,sz) centred at center, optional bevel."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(sx, sy, sz), verts=bm.verts)
    if bevel > 0:
        bmesh.ops.bevel(bm, geom=bm.edges[:] + bm.verts[:], offset=bevel, segments=segs, affect="EDGES", profile=0.5)
    bmesh.ops.translate(bm, vec=Vector(center), verts=bm.verts)
    return bm


def bm_cyl(r1, r2, depth, center=(0, 0, 0), segs=8, axis="Z", cap=True):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=cap, cap_tris=False, segments=segs, radius1=r1, radius2=r2, depth=depth)
    if axis == "X":
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(90), 3, "Y"))
    elif axis == "Y":
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(90), 3, "X"))
    bmesh.ops.translate(bm, vec=Vector(center), verts=bm.verts)
    return bm


def bm_sphere(r, center=(0, 0, 0), u=12, v=8, scale=(1, 1, 1), ico=0):
    bm = bmesh.new()
    if ico:
        bmesh.ops.create_icosphere(bm, subdivisions=ico, radius=r)
    else:
        bmesh.ops.create_uvsphere(bm, u_segments=u, v_segments=v, radius=r)
    bmesh.ops.scale(bm, vec=scale, verts=bm.verts)
    bmesh.ops.translate(bm, vec=Vector(center), verts=bm.verts)
    return bm


def bm_segment(p0, p1, r0, r1, segs=6):
    """Tapered prism between two points (limb pieces)."""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    bm = bm_cyl(r0, r1, d.length, segs=segs)
    # cone is centred at origin along Z: move so base at origin, then orient
    bmesh.ops.translate(bm, vec=(0, 0, d.length / 2), verts=bm.verts)
    rot = Vector((0, 0, 1)).rotation_difference(d.normalized()).to_matrix()
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=rot)
    bmesh.ops.translate(bm, vec=p0, verts=bm.verts)
    return bm


def merge(*bms):
    out = bmesh.new()
    for b in bms:
        me = bpy.data.meshes.new("_tmp")
        b.to_mesh(me); b.free()
        out.from_mesh(me)
        bpy.data.meshes.remove(me)
    return out


def facet(bm, amount=0.0, seed=0, triangulate=True, subdiv=0):
    """Low-poly faceted look: optional subdivision, triangulation, jitter."""
    rnd = random.Random(seed)
    for _ in range(subdiv):
        bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=1, use_grid_fill=True)
    if triangulate:
        bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method="BEAUTY", ngon_method="BEAUTY")
    if amount > 0:
        bm.normal_update()
        for v in bm.verts:
            n = v.normal
            v.co += n * rnd.uniform(-amount, amount) + Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1))) * amount * 0.35
    return bm


def mat(name, color, rough=0.5, metal=0.0, emit=None, emit_strength=0.0, spec=0.5, coat=0.0, sheen=0.0, alpha=1.0, transmission=0.0):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    for key in ("Specular IOR Level", "Specular"):
        if key in b.inputs:
            b.inputs[key].default_value = spec; break
    if coat and "Coat Weight" in b.inputs:
        b.inputs["Coat Weight"].default_value = coat
        b.inputs["Coat Roughness"].default_value = 0.15
    if sheen and "Sheen Weight" in b.inputs:
        b.inputs["Sheen Weight"].default_value = sheen
    if emit is not None:
        b.inputs["Emission Color"].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = emit_strength
    if transmission and "Transmission Weight" in b.inputs:
        b.inputs["Transmission Weight"].default_value = transmission
    if alpha < 1:
        b.inputs["Alpha"].default_value = alpha
        try:
            m.surface_render_method = "BLENDED"
        except Exception:
            pass
    m.diffuse_color = (*color, 1)
    return m


def emission_mat(name, color, strength):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*color, 1)
    em.inputs["Strength"].default_value = strength
    nt.links.new(em.outputs[0], out.inputs[0])
    return m


def empty(name, loc, collection, size=0.05, parent=None, kind="PLAIN_AXES"):
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = kind
    e.empty_display_size = size
    e.location = loc
    collection.objects.link(e)
    if parent:
        e.parent = parent
    return e


def set_origin(ob, point):
    """Move object origin to world point without moving geometry."""
    point = Vector(point)
    offset = point - ob.location
    ob.data.transform(Matrix.Translation(-offset), shape_keys=bool(ob.data.shape_keys))
    ob.location = point


def sec(t):
    return t * FPS + 1


def key(ob, path, value, t, index=-1, interp=None):
    """Keyframe a property at time t (seconds)."""
    if index >= 0:
        getattr(ob, path)[index] = value
    else:
        setattr(ob, path, value)
    ob.keyframe_insert(data_path=path, index=index, frame=sec(t))
    if interp:
        fc_set_interp(ob, path, sec(t), interp)


def fc_set_interp(idblock, path, frame, interp):
    ad = idblock.animation_data
    if not ad or not ad.action:
        return
    for fc in fcurves_of(ad.action):
        if fc.data_path == path:
            for kp in fc.keyframe_points:
                if abs(kp.co[0] - frame) < 0.01:
                    kp.interpolation = interp


def fcurves_of(action):
    """Blender 4.4+/5.x layered actions keep fcurves in channelbags."""
    if hasattr(action, "fcurves") and len(getattr(action, "fcurves", [])):
        return list(action.fcurves)
    out = []
    for layer in getattr(action, "layers", []):
        for strip in layer.strips:
            for cb in getattr(strip, "channelbags", []):
                out.extend(cb.fcurves)
    return out


def ease(a, b, x):
    x = max(0.0, min(1.0, x))
    x = x * x * (3 - 2 * x)
    return a + (b - a) * x


def parent_keep(child, parent):
    """Parent without moving the child (like Ctrl+P > Keep Transform at rest)."""
    bpy.context.view_layer.update()
    child.parent = parent
    child.matrix_parent_inverse = parent.matrix_world.inverted()
    return child
