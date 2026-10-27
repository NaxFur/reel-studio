"""Lighting rig + world + render settings. Colours are animated in animate.py."""
import math
import bpy
from mathutils import Vector
from util import col

KELVIN_2700 = (1.0, 0.54, 0.22)


def area(name, c, loc, rot, size, color, energy, shape="RECTANGLE", size_y=None):
    ld = bpy.data.lights.new(name, "AREA")
    ld.shape = shape
    ld.size = size
    if size_y:
        ld.size_y = size_y
    ld.color = color
    ld.energy = energy
    ob = bpy.data.objects.new(name, ld)
    ob.location = loc
    ob.rotation_euler = rot
    c.objects.link(ob)
    return ob


def aim(ob, target):
    d = Vector(target) - ob.location
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def build(parent_col, F):
    c = col("Lights", parent_col)
    L = {}
    # screen spill on the faces (colour follows the screen state)
    L["screen"] = area("L_Screen", c, (0.0, 0.43, 1.105), (0, 0, 0), 0.62, (0.62, 0.74, 1.0), 9.0, size_y=0.34)
    aim(L["screen"], (0.0, -0.4, 1.12))
    # warm practical desk lamp
    ld = bpy.data.lights.new("L_Lamp", "SPOT")
    ld.color = KELVIN_2700; ld.energy = 7.0; ld.spot_size = math.radians(95); ld.spot_blend = 0.75
    ld.shadow_soft_size = 0.05
    L["lamp"] = bpy.data.objects.new("L_Lamp", ld); c.objects.link(L["lamp"])
    L["lamp"].location = F["lamp_head"]
    aim(L["lamp"], (0.05, -0.05, 0.85))
    # warm bounce from the lamp onto the Nerd's left side
    L["lamp_fill"] = area("L_LampFill", c, (-0.75, 0.05, 1.25), (0, 0, 0), 0.5, KELVIN_2700, 4.0)
    aim(L["lamp_fill"], (0, -0.3, 1.15))
    # LED wash on the back wall (purple/blue -> red on crash -> green on pass)
    L["led_wall"] = area("L_LEDWash", c, (0, 0.62, 0.84), (0, 0, 0), 1.6, (0.42, 0.22, 1.0), 25.0, size_y=0.06)
    aim(L["led_wall"], (0, 0.80, 1.4))
    L["led_top"] = area("L_LEDTop", c, (0, 0.62, 2.30), (0, 0, 0), 3.0, (0.42, 0.22, 1.0), 30.0, size_y=0.08)
    aim(L["led_top"], (0, 0.75, 1.6))
    # cinematic red rim from behind the Nerd (the "red" of the red/purple palette)
    L["rim"] = area("L_Rim", c, (-0.55, -1.7, 1.75), (0, 0, 0), 1.2, (1.0, 0.10, 0.14), 22.0)
    aim(L["rim"], (0, -0.25, 1.15))
    L["rim2"] = area("L_Rim2", c, (0.9, -1.2, 1.5), (0, 0, 0), 0.8, (0.55, 0.3, 1.0), 10.0)
    aim(L["rim2"], (0, -0.25, 1.1))
    # neon sign glow
    ld = bpy.data.lights.new("L_Neon", "POINT"); ld.color = (1.0, 0.2, 0.75); ld.energy = 3.0; ld.shadow_soft_size = 0.1
    L["neon"] = bpy.data.objects.new("L_Neon", ld); c.objects.link(L["neon"]); L["neon"].location = (0.55, 0.68, 1.72)
    # gentle overall fill so shadows never crush on a phone screen
    L["fill"] = area("L_Fill", c, (0.2, -1.0, 2.4), (0, 0, 0), 2.5, (0.45, 0.45, 0.75), 18.0)
    aim(L["fill"], (0, 0, 0.9))
    # spill from the two side monitors
    for side, sgn in (("left", -1), ("right", 1)):
        L[f"screen_{side}"] = area(f"L_Screen_{side.title()}", c, (sgn * 0.52, 0.29, 1.07), (0, 0, 0), 0.45, (0.62, 0.70, 1.0), 3.5, size_y=0.25)
        aim(L[f"screen_{side}"], (0.0, -0.3, 1.1))
    # small key on the mascot's spot on the desk
    L["mascot_key"] = area("L_MascotKey", c, (0.55, -0.2, 1.05), (0, 0, 0), 0.25, (1.0, 0.75, 0.6), 2.5)
    aim(L["mascot_key"], (0.36, 0.2, 0.82))

    world = bpy.data.worlds.new("W_Night") if not bpy.context.scene.world else bpy.context.scene.world
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.004, 0.005, 0.012, 1)
    bg.inputs["Strength"].default_value = 1.0
    bpy.context.scene.world = world
    return L


def render_settings(scene, res=(1080, 1920), samples=48):
    for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            scene.render.engine = eng; break
        except TypeError:
            pass
    r = scene.render
    r.resolution_x, r.resolution_y = res
    r.resolution_percentage = 100
    r.fps = 30
    r.use_motion_blur = True
    r.motion_blur_shutter = 0.4
    r.film_transparent = False
    ee = scene.eevee
    ee.taa_render_samples = samples
    ee.use_raytracing = True
    ee.ray_tracing_method = "SCREEN"
    try:
        ee.ray_tracing_options.resolution_scale = "2"
        ee.ray_tracing_options.use_denoise = True
    except Exception:
        pass
    ee.use_fast_gi = True
    ee.use_shadows = True
    ee.shadow_ray_count = 2
    ee.shadow_step_count = 6
    ee.motion_blur_steps = 1
    ee.use_volumetric_shadows = False
    scene.view_settings.view_transform = "AgX"
    for look in ("AgX - Medium High Contrast", "AgX - Punchy", "Medium High Contrast"):
        try:
            scene.view_settings.look = look; break
        except TypeError:
            pass
    scene.view_settings.exposure = 0.0
    r.image_settings.file_format = "PNG"
    r.image_settings.color_mode = "RGB"
    r.image_settings.compression = 25
