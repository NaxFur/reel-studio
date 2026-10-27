"""Developer bedroom-office set. Desk faces +Y wall; the Nerd sits at y≈-0.32 facing +Y."""
import math, random, os
import bpy, bmesh
from mathutils import Vector, Matrix
from util import bm_box, bm_cyl, bm_sphere, bm_segment, mesh_obj, facet, mat, emission_mat, empty, col, merge, set_origin, parent_keep

DESK_Z = 0.75
MON_C = Vector((0.0, 0.47, 1.105))
SCREEN_W, SCREEN_H = 0.70, 0.39375
SIDE_W, SIDE_H, SIDE_YAW = 0.50, 0.28125, math.radians(30)
SIDE_C = {"left": Vector((-0.585, 0.335, 1.07)), "right": Vector((0.585, 0.335, 1.07))}


def screen_material(seq_dir, nframes, name="M_Screen", first_file="screen_0001.jpg", img_name="ScreenSeq", strength=1.35):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    tex = nt.nodes.new("ShaderNodeTexImage")
    first = os.path.join(seq_dir, first_file)
    img = bpy.data.images.load(first, check_existing=True) if os.path.exists(first) else bpy.data.images.new(img_name + "_placeholder", 64, 36)
    if os.path.exists(first):
        img.source = "SEQUENCE"
        tex.image_user.frame_duration = nframes
        tex.image_user.frame_start = 1
        tex.image_user.frame_offset = 0
        tex.image_user.use_auto_refresh = True
    img.name = img_name
    tex.image = img
    tex.interpolation = "Cubic"
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Strength"].default_value = strength
    nt.links.new(tex.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs[0], out.inputs[0])
    m["screen_emission"] = em.name
    return m, img



def still_screen_material(name, path, strength=1.2):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    tex = nt.nodes.new("ShaderNodeTexImage")
    if os.path.exists(path):
        tex.image = bpy.data.images.load(path, check_existing=True)
    tex.interpolation = "Cubic"
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Strength"].default_value = strength
    nt.links.new(tex.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs[0], out.inputs[0])
    m["screen_emission"] = em.name
    return m


def side_monitor(c, name, center, yaw, w, h, screen_m, body_m):
    """Monitor built around its screen centre (screen in local XZ, facing local -Y), then placed and turned."""
    cz = center[2]
    neck_top, neck_bot = cz - h / 2 + 0.06, DESK_Z
    parts = [bm_box(w + 0.02, 0.02, h + 0.02, center=(0, 0.011, 0), bevel=0.004),
             bm_box(w * 0.7, 0.045, h * 0.6, center=(0, 0.04, -0.01), bevel=0.015),
             bm_box(0.04, 0.03, neck_top - neck_bot, center=(0, 0.07, (neck_top + neck_bot) / 2 - cz)),
             bm_box(0.20, 0.16, 0.012, center=(0, 0.06, DESK_Z + 0.006 - cz), bevel=0.004)]
    body = mesh_obj(name + "_Body", merge(*parts), c, body_m)
    bm = bmesh.new()
    hw, hh = w / 2, h / 2
    vs = [bm.verts.new((x, -0.0005, z)) for x, z in ((-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh))]
    f = bm.faces.new(vs)
    uv = bm.loops.layers.uv.new()
    for loop, (u, v) in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
        loop[uv].uv = (u, v)
    f.normal_update()
    if f.normal.y > 0:
        f.normal_flip()
    scr = mesh_obj(name + "_Screen", bm, c, screen_m)
    for ob in (body, scr):
        ob.location = center
        ob.rotation_euler = (0, 0, yaw)
    return scr


def text_obj(name, body, size, loc, rot, mat_, c, extrude=0.0, align="CENTER", font=None):
    cu = bpy.data.curves.new(name, "FONT")
    cu.body = body
    cu.size = size
    cu.extrude = extrude
    cu.align_x = align
    cu.align_y = "CENTER"
    if font and os.path.exists(font):
        cu.font = bpy.data.fonts.load(font, check_existing=True)
    ob = bpy.data.objects.new(name, cu)
    ob.location = loc
    ob.rotation_euler = rot
    c.objects.link(ob)
    cu.materials.append(mat_)
    return ob


def build(parent_col, seq_dir, nframes):
    c = col("Set", parent_col)
    rnd = random.Random(1)
    F = {}

    floor_m = mat("M_Floor", (0.035, 0.024, 0.018), rough=0.32, spec=0.5)
    wall_m = mat("M_Wall", (0.020, 0.022, 0.040), rough=0.85)
    wood_m = mat("M_DeskWood", (0.055, 0.028, 0.016), rough=0.38, coat=0.25)
    metal_m = mat("M_BlackMetal", (0.01, 0.01, 0.012), rough=0.35, metal=0.8)
    plastic_m = mat("M_DarkPlastic", (0.015, 0.015, 0.018), rough=0.4)
    key_m = mat("M_Keycap", (0.03, 0.03, 0.036), rough=0.45)
    mat_m = mat("M_DeskMat", (0.012, 0.012, 0.016), rough=0.95)
    hex_m = mat("M_Hex", (0.035, 0.03, 0.06), rough=0.9, sheen=0.4)
    book_ms = [mat(f"M_Book{i}", col_, rough=0.7) for i, col_ in enumerate(
        [(0.25, 0.04, 0.05), (0.04, 0.10, 0.25), (0.20, 0.17, 0.12), (0.05, 0.16, 0.10), (0.30, 0.20, 0.02), (0.08, 0.05, 0.15)])]

    # floor + walls
    F["floor"] = mesh_obj("Floor", bm_box(7, 7, 0.02, center=(0, -1.0, -0.01)), c, floor_m)
    F["wall_back"] = mesh_obj("Wall_Back", bm_box(7, 0.05, 3.2, center=(0, 0.78, 1.6)), c, wall_m)
    F["wall_left"] = mesh_obj("Wall_Left", bm_box(0.05, 4.5, 3.2, center=(-1.55, -1.4, 1.6)), c, wall_m)
    F["wall_rear"] = mesh_obj("Wall_Rear", bm_box(7, 0.05, 3.2, center=(0, -2.6, 1.6)), c, wall_m)
    rug_m = mat("M_Rug", (0.03, 0.028, 0.045), rough=1.0, sheen=0.6)
    F["rug"] = mesh_obj("Rug", bm_cyl(1.0, 1.0, 0.012, center=(0, -0.45, 0.006), segs=24), c, rug_m)

    # desk
    F["desk_top"] = mesh_obj("Desk_Top", bm_box(1.60, 0.76, 0.035, center=(0, 0.27, DESK_Z - 0.0175), bevel=0.006), c, wood_m)
    legs = []
    for x in (-0.76, 0.76):
        legs.append(bm_box(0.05, 0.62, 0.03, center=(x, 0.27, 0.015)))
        legs.append(bm_box(0.05, 0.05, DESK_Z - 0.035, center=(x, 0.27, (DESK_Z - 0.035) / 2)))
    legs.append(bm_box(1.5, 0.03, 0.05, center=(0, 0.55, DESK_Z - 0.06)))
    mesh_obj("Desk_Frame", merge(*legs), c, metal_m)
    mesh_obj("Desk_Mat", bm_box(0.86, 0.36, 0.003, center=(0.02, 0.12, DESK_Z + 0.0015), bevel=0.001), c, mat_m)

    # monitor
    seq_m, img = screen_material(seq_dir, nframes)
    F["screen_img"] = img
    bez = bm_box(SCREEN_W + 0.024, 0.022, SCREEN_H + 0.024, center=MON_C + Vector((0, 0.012, 0)), bevel=0.004)
    back = bm_box(SCREEN_W * 0.7, 0.05, SCREEN_H * 0.6, center=MON_C + Vector((0, 0.045, -0.02)), bevel=0.02)
    neck = bm_box(0.05, 0.03, 0.30, center=MON_C + Vector((0, 0.08, -0.17)))
    base = bm_box(0.26, 0.20, 0.012, center=(0, MON_C.y + 0.06, DESK_Z + 0.006), bevel=0.004)
    mesh_obj("Monitor_Body", merge(bez, back, neck, base), c, plastic_m)
    bm = bmesh.new()
    hw, hh = SCREEN_W / 2, SCREEN_H / 2
    vs = [bm.verts.new((x, MON_C.y - 0.0005, z)) for x, z in ((-hw + MON_C.x, MON_C.z - hh), (hw + MON_C.x, MON_C.z - hh),
                                                             (hw + MON_C.x, MON_C.z + hh), (-hw + MON_C.x, MON_C.z + hh))]
    f = bm.faces.new(vs)
    uv = bm.loops.layers.uv.new()
    for loop, (u, v) in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
        loop[uv].uv = (u, v)
    f.normal_update()
    if f.normal.y > 0:
        f.normal_flip()
    F["screen"] = mesh_obj("Monitor_Screen", bm, c, seq_m)
    # two side monitors, angled 30 deg towards the chair: left (GitHub graveyard), right (email avalanche)
    tex_dir = os.path.join(os.path.dirname(seq_dir), "textures")
    right_seq = os.path.join(os.path.dirname(seq_dir), "screen_right")

    # side monitors: animated sequences (left: #3 card, right: #2 card)
    left_seq = os.path.join(os.path.dirname(seq_dir), "screen_left")
    sm_l, l_img = screen_material(left_seq, nframes, name="M_Screen_left", first_file="screen_left_0001.jpg", img_name="LeftScreenSeq", strength=1.2)
    F["screen_left"] = side_monitor(c, "Monitor_Left", SIDE_C["left"], SIDE_YAW, SIDE_W, SIDE_H, sm_l, plastic_m)
    F["screen_left_mat"] = sm_l
    sm_r, r_img = screen_material(right_seq, nframes, name="M_Screen_right", first_file="screen_right_0001.jpg", img_name="RightScreenSeq", strength=1.2)
    F["screen_right"] = side_monitor(c, "Monitor_Right", SIDE_C["right"], -SIDE_YAW, SIDE_W, SIDE_H, sm_r, plastic_m)
    F["screen_right_mat"] = sm_r

    # LED light bar on top of the centre monitor (the warm practical that lights the desk)
    top = MON_C.z + SCREEN_H / 2 + 0.012
    mesh_obj("Monitor_LightBar", bm_box(0.36, 0.05, 0.022, center=(0, MON_C.y - 0.012, top + 0.011), bevel=0.004), c, metal_m)
    mesh_obj("Monitor_LightBar_Glow", bm_box(0.33, 0.006, 0.004, center=(0, MON_C.y - 0.035, top + 0.002)), c,
             emission_mat("M_LightBar", (0.5, 0.6, 0.9), 12.0))
    F["lamp_head"] = Vector((0.0, MON_C.y - 0.06, top))
    F["lamp_dir"] = Vector((0.0, -0.55, -0.83)).normalized()

    # sticky note on the bezel: "KEYFRAME #4,812"
    sticky_tex = os.path.join(tex_dir, "sticky_note.png")
    note_m = bpy.data.materials.new("M_Sticky")
    note_m.use_nodes = True
    nt = note_m.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    o = nt.nodes.new("ShaderNodeOutputMaterial")
    bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bs.inputs["Roughness"].default_value = 0.8
    if os.path.exists(sticky_tex):
        tx = nt.nodes.new("ShaderNodeTexImage")
        tx.image = bpy.data.images.load(sticky_tex, check_existing=True)
        nt.links.new(tx.outputs[0], bs.inputs["Base Color"])
    else:
        bs.inputs["Base Color"].default_value = (0.95, 0.9, 0.2, 1)
    nt.links.new(bs.outputs[0], o.inputs[0])

    nb = bm_box(0.065, 0.002, 0.065, center=(MON_C.x - SCREEN_W / 2 + 0.05, MON_C.y - 0.003, MON_C.z - SCREEN_H / 2 - 0.012))
    note = mesh_obj("Sticky_Note", nb, c, note_m)
    set_origin(note, (MON_C.x - SCREEN_W / 2 + 0.05, MON_C.y - 0.003, MON_C.z - SCREEN_H / 2 - 0.012))
    note.rotation_euler = (0, 0.08, 0)
    F["sticky_note"] = note

    # keyboard: base, backlight, keycaps (one Enter key kept separate for the "Run" press)
    kb_c = Vector((-0.02, 0.10, DESK_Z + 0.004))
    mesh_obj("Keyboard_Base", bm_box(0.44, 0.145, 0.02, center=kb_c + Vector((0, 0, 0.01)), bevel=0.005), c, plastic_m)
    glow = emission_mat("M_KeyGlow", (0.35, 0.18, 1.0), 3.0)
    F["key_glow_mat"] = glow
    mesh_obj("Keyboard_Glow", bm_box(0.425, 0.13, 0.002, center=kb_c + Vector((0, 0, 0.021))), c, glow)
    caps = []
    pitch = 0.0283
    mx = lambda x: 2 * kb_c.x - x       # mirror: rows run right->left so Enter sits under the typist's right hand (-X)
    for r in range(5):
        y = kb_c.y + 0.052 - r * pitch
        x = kb_c.x - 0.198
        n = 14 if r < 4 else 9
        for k in range(n):
            w = 0.0245
            if r == 4 and k == 4: w = 0.14   # space bar
            if r == 2 and k == n - 1:
                enter_x = x + 0.012; enter_y = y
                x += pitch * 1.6; continue
            caps.append(bm_box(w, 0.0245, 0.011, center=(mx(x + w / 2), y, kb_c.z + 0.027), bevel=0.003))
            x += w + 0.0038
    F["keycaps"] = mesh_obj("Keyboard_Keys", merge(*caps), c, key_m)
    ex = mx(enter_x + 0.021)
    ent = mesh_obj("Key_Enter", bm_box(0.042, 0.0245, 0.011, center=(ex, enter_y, kb_c.z + 0.027), bevel=0.003), c,
                   mat("M_KeyEnter", (0.05, 0.05, 0.06), rough=0.4))
    set_origin(ent, (ex, enter_y, kb_c.z + 0.027))
    F["enter"] = ent
    F["kb_center"] = kb_c

    # mouse, mug, plant, lamp
    mouse = bm_box(0.06, 0.105, 0.035, center=(-0.34, 0.04, DESK_Z + 0.0175), bevel=0.016, segs=2)
    mesh_obj("Mouse", mouse, c, plastic_m)
    mug_ms = [mat("M_Mug_White", (0.75, 0.74, 0.72), rough=0.25, coat=0.4), mat("M_Mug_Black", (0.02, 0.02, 0.025), rough=0.3, coat=0.4),
              mat("M_Mug_Red", (0.45, 0.04, 0.05), rough=0.3, coat=0.4), mat("M_Mug_Purple", (0.16, 0.07, 0.40), rough=0.3, coat=0.4)]
    coffee_m = mat("M_Coffee", (0.04, 0.02, 0.01), rough=0.1)
    stain_m = mat("M_CoffeeStain", (0.05, 0.025, 0.012), rough=0.6)
    # (x, y, handle angle, material, coffee level 0..1)
    # right-hand mugs sit towards the back this time: Claude walks to the front-right desk edge for the lesson
    mugs = [(-0.50, 0.13, 2.4, 0, 0.3), (-0.60, -0.01, 0.4, 1, 0.0), (-0.47, -0.06, -1.2, 3, 0.6),
            (0.70, 0.18, -0.6, 2, 0.15), (0.74, 0.48, 0.9, 0, 0.0), (-0.36, 0.40, 3.0, 1, 0.45)]
    for i, (x, y, ang, mi, lvl) in enumerate(mugs):
        hx, hy = math.cos(ang) * 0.045, math.sin(ang) * 0.045
        mesh_obj(f"Mug_{i}", merge(bm_cyl(0.042, 0.04, 0.10, center=(x, y, DESK_Z + 0.05), segs=14),
                                   bm_segment((x + hx, y + hy, DESK_Z + 0.075), (x + hx * 1.38, y + hy * 1.38, DESK_Z + 0.03), 0.008, 0.008, segs=5)),
                 c, mug_ms[mi])
        if lvl > 0:
            mesh_obj(f"Coffee_{i}", bm_cyl(0.037, 0.037, 0.004, center=(x, y, DESK_Z + 0.012 + 0.076 * lvl), segs=14), c, coffee_m)
        mesh_obj(f"MugRing_{i}", bm_cyl(0.047, 0.047, 0.0008, center=(x + 0.03, y - 0.02, DESK_Z + 0.0004), segs=14), c, stain_m)
    # a tipped-over empty mug
    tm_ = merge(bm_cyl(0.042, 0.04, 0.10, segs=14), bm_segment((0.045, 0, 0.025), (0.062, 0, -0.02), 0.008, 0.008, segs=5))
    bmesh.ops.rotate(tm_, verts=tm_.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(90), 3, "Y") @ Matrix.Rotation(math.radians(25), 3, "X"))
    bmesh.ops.translate(tm_, vec=(-0.70, 0.30, DESK_Z + 0.041), verts=tm_.verts)
    mesh_obj("Mug_Tipped", tm_, c, mug_ms[2])
    # energy drinks
    can_m = mat("M_Can", (0.05, 0.35, 0.08), rough=0.25, metal=0.85)
    lid_m = mat("M_CanLid", (0.6, 0.6, 0.62), rough=0.2, metal=1.0)
    for i, (x, y) in enumerate(((-0.72, 0.05), (-0.62, 0.19))):
        mesh_obj(f"Can_{i}", bm_cyl(0.033, 0.033, 0.122, center=(x, y, DESK_Z + 0.061), segs=12), c, can_m)
        mesh_obj(f"CanLid_{i}", bm_cyl(0.029, 0.029, 0.003, center=(x, y, DESK_Z + 0.1235), segs=12), c, lid_m)
    # crumpled paper (desk + floor)
    paper_m = mat("M_Paper", (0.7, 0.7, 0.66), rough=0.9)
    for i, (x, y, z) in enumerate(((0.24, 0.37, DESK_Z), (-0.24, 0.28, DESK_Z), (0.50, -0.62, 0.0), (-0.42, -0.75, 0.0), (0.72, -0.30, 0.0), (0.25, -0.95, 0.0))):
        pb = bm_sphere(0.032, center=(x, y, z + 0.028), u=6, v=5)
        facet(pb, amount=0.008, seed=40 + i)
        mesh_obj(f"Paper_{i}", pb, c, paper_m)

    # back wall dressing: LED strip, neon sign, hex panels, shelf with books + figure
    led = emission_mat("M_LED", (0.42, 0.22, 1.0), 12.0)
    F["led_mat"] = led
    mesh_obj("LED_Strip", bm_box(1.5, 0.01, 0.012, center=(0, 0.75, DESK_Z + 0.06)), c, led)
    mesh_obj("LED_Strip_Top", bm_box(3.2, 0.01, 0.012, center=(0, 0.75, 2.35)), c, led)
    neon = emission_mat("M_Neon", (1.0, 0.18, 0.75), 14.0)
    F["neon_mat"] = neon
    sign = text_obj("Neon_Sign", "</>", 0.20, (0.55, 0.745, 1.72), (math.radians(90), 0, 0), neon, c, extrude=0.004)
    hexes = []
    for i, (hx, hz) in enumerate([(-0.95, 1.55), (-0.78, 1.65), (-0.78, 1.45), (-0.61, 1.55), (-0.95, 1.75), (-0.61, 1.75), (-0.44, 1.65)]):
        b = bm_cyl(0.10, 0.10, 0.025, segs=6, axis="Y")
        bmesh.ops.rotate(b, verts=b.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(30), 3, "Y"))
        bmesh.ops.translate(b, vec=(hx, 0.75, hz), verts=b.verts)
        hexes.append(b)
    mesh_obj("Hex_Panels", merge(*hexes), c, hex_m)
    hex_led = emission_mat("M_HexLED", (0.25, 0.4, 1.0), 6.0)
    mesh_obj("Hex_Glow", bm_box(0.06, 0.006, 0.06, center=(-0.78, 0.735, 1.65)), c, hex_led)
    shelf = [bm_box(0.75, 0.2, 0.025, center=(0.95, 0.66, 1.32))]
    x = 0.62
    for i in range(9):
        w = rnd.uniform(0.025, 0.045); h = rnd.uniform(0.17, 0.24)
        shelf_b = bm_box(w, 0.15, h, center=(x + w / 2, 0.66, 1.3325 + h / 2))
        mesh_obj(f"Book_{i}", shelf_b, c, book_ms[i % len(book_ms)])
        x += w + 0.004
    mesh_obj("Shelf", merge(*shelf), c, wood_m)
    # tiny clay figure on the shelf – a nod to the mascot
    fig = bm_box(0.06, 0.035, 0.04, center=(1.12, 0.65, 1.365), bevel=0.006)
    mesh_obj("Shelf_Figure", fig, c, mat("M_Mascot_Orange", (0.83, 0.15, 0.036), rough=0.38))

    # window behind the Nerd with a blurred city at night (emissive)
    city_path = os.path.join(os.path.dirname(seq_dir), "textures", "city_bokeh.png")
    win_m = bpy.data.materials.new("M_CityWindow"); win_m.use_nodes = True
    nt = win_m.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    o = nt.nodes.new("ShaderNodeOutputMaterial"); e = nt.nodes.new("ShaderNodeEmission"); tx = nt.nodes.new("ShaderNodeTexImage")
    if os.path.exists(city_path):
        tx.image = bpy.data.images.load(city_path, check_existing=True)
    e.inputs["Strength"].default_value = 2.2
    nt.links.new(tx.outputs[0], e.inputs[0]); nt.links.new(e.outputs[0], o.inputs[0])
    bm = bmesh.new()
    vs = [bm.verts.new(p) for p in ((-1.4, -2.57, 0.95), (0.4, -2.57, 0.95), (0.4, -2.57, 2.25), (-1.4, -2.57, 2.25))]
    f = bm.faces.new(vs); uvl = bm.loops.layers.uv.new()
    for loop, uvv in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))): loop[uvl].uv = uvv
    mesh_obj("Window_City", bm, c, win_m)
    frame = [bm_box(1.86, 0.06, 0.05, center=(-0.5, -2.55, 0.94)), bm_box(1.86, 0.06, 0.05, center=(-0.5, -2.55, 2.26)),
             bm_box(0.05, 0.06, 1.36, center=(-1.42, -2.55, 1.6)), bm_box(0.05, 0.06, 1.36, center=(0.42, -2.55, 1.6)),
             bm_box(0.03, 0.06, 1.3, center=(-0.5, -2.55, 1.6))]
    mesh_obj("Window_Frame", merge(*frame), c, plastic_m)

    F["pen"] = None
    F["sleep_zs"] = []

    F["foam"] = []
    F["drips"] = []
    F["puddles"] = []


    # gaming chair (own root so it can roll / spin with the Nerd on it)
    chair_root = empty("Chair_Root", (0, -0.30, 0), c, 0.3, kind="CIRCLE")
    chair_c = col("Chair", c)
    seat_m = mat("M_ChairSeat", (0.015, 0.015, 0.02), rough=0.55, sheen=0.3)
    accent = mat("M_ChairAccent", (0.18, 0.06, 0.55), rough=0.5)
    pieces = []
    pieces.append(mesh_obj("Chair_Seat", bm_box(0.50, 0.48, 0.085, center=(0, -0.30, 0.44), bevel=0.03, segs=2), chair_c, seat_m))
    back_b = bm_box(0.50, 0.09, 0.80, center=(0, 0, 0.40), bevel=0.04, segs=2)
    bmesh.ops.rotate(back_b, verts=back_b.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(12), 3, "X"))
    bmesh.ops.translate(back_b, vec=(0, -0.58, 0.90), verts=back_b.verts)
    pieces.append(mesh_obj("Chair_Back", back_b, chair_c, seat_m))
    stripe = bm_box(0.08, 0.095, 0.62, center=(0, 0, 0.40))
    bmesh.ops.rotate(stripe, verts=stripe.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(12), 3, "X"))
    bmesh.ops.translate(stripe, vec=(0, -0.582, 0.92), verts=stripe.verts)
    pieces.append(mesh_obj("Chair_Stripe", stripe, chair_c, accent))
    arms_b = [bm_box(0.06, 0.30, 0.03, center=(s * 0.28, -0.32, 0.66), bevel=0.01) for s in (1, -1)]
    arms_b += [bm_box(0.03, 0.03, 0.2, center=(s * 0.28, -0.35, 0.55)) for s in (1, -1)]
    pieces.append(mesh_obj("Chair_Arms", merge(*arms_b), chair_c, plastic_m))
    base_b = [bm_cyl(0.025, 0.025, 0.30, center=(0, -0.30, 0.25), segs=10)]
    for i in range(5):
        a = i / 5 * 2 * math.pi
        p1 = Vector((0.30 * math.cos(a), -0.30 + 0.30 * math.sin(a), 0.06))
        base_b.append(bm_segment((0, -0.30, 0.10), p1, 0.02, 0.016, segs=5))
        base_b.append(bm_sphere(0.028, center=p1 + Vector((0, 0, -0.03)), u=8, v=6))
    pieces.append(mesh_obj("Chair_Base", merge(*base_b), chair_c, metal_m))
    for p in pieces:
        parent_keep(p, chair_root)
    F["chair_root"] = chair_root
    return F
