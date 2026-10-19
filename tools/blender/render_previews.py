"""render_previews.py -- import each exported GLB in headless Blender and render
3 x 960x540 EEVEE previews with temporary cameras/lights (never exported).

Usage:
    blender.exe -b --factory-startup --python render_previews.py -- door
    (no scene argument = all three)
"""
import bpy
import math
import os
import sys
from mathutils import Vector

from pathlib import Path
ROOT = str(Path(__file__).resolve().parents[2])
MODELS = os.path.join(ROOT, "assets", "models")
OUTDIR = os.path.join(ROOT, "reports", "modeler")
os.makedirs(OUTDIR, exist_ok=True)

# per scene: (file, [(name, cam_loc, look_at, lens, extra_lights)])
# extra_lights: list of (kind, loc, energy, color, radius/size)
VIEWS = {
    "door": ("door.glb", [
        ("door_preview_corridor.png", (0.0, -0.6, 1.62), (0.0, -10.0, 1.45), 20,
         [("point", (0.0, -4.0, 2.4), 120, (0.82, 0.88, 0.85), 6),
          ("point", (0.0, -9.0, 2.4), 120, (0.82, 0.88, 0.85), 6),
          ("point", (0.0, -14.0, 2.4), 100, (0.82, 0.88, 0.85), 6),
          ("point", (0.0, -5.3, 2.4), 40, (1.0, 0.85, 0.7), 3),
          ("point", (0.5, -2.0, 1.9), 90, (1.0, 0.9, 0.8), 4)]),
        ("door_preview_living.png", (3.45, -3.55, 1.62), (5.3, -6.1, 1.05), 22,
         [("point", (4.7, -4.6, 2.35), 260, (1.0, 0.82, 0.62), 7),
          ("point", (5.6, -6.6, 1.6), 120, (1.0, 0.85, 0.7), 4),
          ("point", (3.1, -3.3, 1.6), 90, (1.0, 0.8, 0.6), 4),
          ("point", (4.0, -5.5, 1.4), 60, (1.0, 0.85, 0.7), 4)]),
        ("door_preview_bedroom.png", (9.0, -6.9, 1.62), (7.1, -3.9, 1.0), 22,
         [("point", (8.0, -5.3, 2.4), 240, (1.0, 0.72, 0.52), 6),
          ("point", (8.6, -7.3, 1.6), 130, (0.55, 0.65, 0.9), 4),
          ("point", (7.0, -4.2, 1.2), 70, (1.0, 0.8, 0.6), 3)]),
    ]),
    "mirror": ("mirror.glb", [
        ("mirror_preview_room.png", (0.0, -2.45, 1.62), (0.0, 2.8, 1.25), 18,
         [("point", (-1.4, 0.0, 2.75), 180, (0.85, 0.95, 0.9), 7),
          ("point", (1.4, -1.0, 2.75), 180, (0.85, 0.95, 0.9), 7),
          ("point", (0.0, 2.2, 2.0), 60, (1.0, 0.85, 0.7), 4)]),
        ("mirror_preview_mirror.png", (0.0, -0.75, 1.55), (0.0, 2.74, 1.7), 24,
         [("point", (0.0, 1.6, 2.5), 200, (0.88, 0.98, 0.92), 6),
          ("point", (-2.0, 1.2, 2.4), 100, (0.85, 0.95, 0.9), 5),
          ("point", (2.0, 1.2, 2.4), 100, (0.85, 0.95, 0.9), 5)]),
        ("mirror_preview_lockers.png", (0.35, -0.65, 1.62), (-2.0, -2.75, 1.15), 24,
         [("point", (0.0, 0.0, 2.6), 180, (0.85, 0.95, 0.9), 7),
          ("point", (-2.0, -1.8, 1.8), 80, (1.0, 0.85, 0.7), 4),
          ("point", (2.0, -1.8, 1.8), 80, (1.0, 0.85, 0.7), 4)]),
    ]),
    "nightroad": ("nightroad.glb", [
        ("nightroad_preview_start.png", (0.0, 1.2, 1.62), (1.0, -22.0, 1.3), 24,
         [("sun", (30, -10, 20), 2.4, (0.5, 0.62, 0.9), 0),
          ("point", (1.5, -12.0, 1.5), 180, (1.0, 0.45, 0.2), 8),
          ("point", (0.5, -28.0, 1.5), 160, (1.0, 0.45, 0.2), 8),
          ("point", (0.0, -6.0, 4.0), 120, (0.6, 0.7, 0.95), 12)]),
        ("nightroad_preview_mid.png", (1.2, -20.0, 1.62), (-0.2, -36.0, 1.3), 24,
         [("sun", (30, -10, 20), 2.0, (0.5, 0.62, 0.9), 0),
          ("point", (1.0, -28.5, 1.5), 220, (1.0, 0.45, 0.2), 8),
          ("point", (-1.0, -44.0, 1.5), 200, (1.0, 0.45, 0.2), 8),
          ("point", (0.0, -36.0, 3.0), 150, (0.6, 0.7, 0.9), 14)]),
        ("nightroad_preview_shrine.png", (0.0, -91.0, 1.62), (0.0, -98.2, 1.15), 26,
         [("sun", (20, -80, 18), 1.4, (0.5, 0.62, 0.9), 0),
          ("point", (0.0, -97.5, 2.0), 420, (1.0, 0.55, 0.3), 8),
          ("point", (0.0, -94.0, 1.4), 120, (1.0, 0.5, 0.3), 5),
          ("point", (0.0, -98.25, 1.35), 80, (1.0, 0.72, 0.45), 2)]),
    ]),
}


def clear_scene():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for coll in list(bpy.data.collections):
        bpy.data.collections.remove(coll)
    for me in list(bpy.data.meshes):
        bpy.data.meshes.remove(me)
    for ma in list(bpy.data.materials):
        bpy.data.materials.remove(ma)
    for la in list(bpy.data.lights):
        bpy.data.lights.remove(la)
    for ca in list(bpy.data.cameras):
        bpy.data.cameras.remove(ca)


def setup_render():
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.resolution_x = 960
    sc.render.resolution_y = 540
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.film_transparent = False
    try:
        sc.eevee.taa_render_samples = 24
    except Exception:
        pass
    # dark world
    world = bpy.data.worlds.new("PreviewWorld") if not bpy.data.worlds else bpy.data.worlds[0]
    sc.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (0.012, 0.016, 0.022, 1.0)
        bg.inputs[1].default_value = 1.0
    # exposure / look
    try:
        sc.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        pass


def add_light(kind, loc, energy, color, size=5.0):
    data = bpy.data.lights.new("L_preview", type="POINT")
    data.energy = energy
    data.color = color
    if kind == "sun":
        data.type = "SUN"
        data.energy = energy
    else:
        data.type = "POINT"
        data.energy = energy
        try:
            data.shadow_soft_size = size / 10.0
        except Exception:
            pass
    ob = bpy.data.objects.new("L_preview", data)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    if kind == "sun":
        ob.rotation_euler = (math.radians(55), 0, math.radians(210))
    return ob


def hide_helpers():
    """Hide engine-only objects (collision, hidden variants, entities, markers)."""
    for ob in bpy.data.objects:
        nm = ob.name
        if (nm.startswith(("COL_", "V2_", "V3_", "ENTITY_", "MARK_", "LIGHT_",
                           "SPAWN_", "LOOK_", "S_steam"))
                or ob.get("hidden")):
            try:
                ob.hide_render = True
            except Exception:
                pass


def render_view(glb, name, cam_loc, target, lens, lights, outdir):
    clear_scene()
    bpy.ops.import_scene.gltf(filepath=glb)
    hide_helpers()
    setup_render()
    sc = bpy.context.scene
    # camera
    cam_data = bpy.data.cameras.new("PreviewCam")
    cam_data.lens = lens
    cam_data.sensor_width = 36
    cam_data.clip_start = 0.05
    cam = bpy.data.objects.new("PreviewCam", cam_data)
    sc.collection.objects.link(cam)
    cam.location = Vector(cam_loc)
    d = Vector(target) - cam.location
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    sc.camera = cam
    # lights
    for (kind, loc, energy, color, size) in lights:
        add_light(kind, loc, energy, color, size)
    # small headlight so near geometry never reads as pure black
    hl = add_light("point", (cam_loc[0], cam_loc[1] + 0.4, cam_loc[2] + 0.5), 12,
                   (1.0, 0.9, 0.8), 3)
    out = os.path.join(outdir, name)
    sc.render.filepath = out
    bpy.ops.render.render(write_still=True)
    print("PREVIEW", out)
    # cleanup lights/camera for next view
    for ob in list(bpy.data.objects):
        if ob.type in ("CAMERA", "LIGHT"):
            bpy.data.objects.remove(ob, do_unlink=True)


def main():
    argv = sys.argv
    args = argv[argv.index("--") + 1:] if "--" in argv else []
    scenes = args if args else list(VIEWS.keys())
    for scene in scenes:
        fname, views = VIEWS[scene]
        glb = os.path.join(MODELS, fname)
        if not os.path.exists(glb):
            print("MISSING GLB", glb)
            continue
        for (name, cam_loc, target, lens, lights) in views:
            render_view(glb, name, cam_loc, target, lens, lights, OUTDIR)
    print("PREVIEWS DONE")


if __name__ == "__main__":
    main()
