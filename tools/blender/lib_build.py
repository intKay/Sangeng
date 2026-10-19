"""lib_build.py -- shared headless-Blender helpers for the three 三更 GLB scenes.

Run inside:  blender.exe -b --factory-startup --python build_<scene>.py
Never touches the user's interactive Blender session.

Conventions (see docs/ASSET_SPEC.md):
  * metres, Blender Z-up, ground z = 0
  * all exported objects live in collection EXPORT, materials are pure-colour MAT_*
  * static decorative geometry may be grouped; groups are joined at export time
  * named gameplay objects (SPAWN/LOOK/LIGHT/INT/ENTITY/MARK/V2_/V3_/COL_) stay independent
"""
import bpy
import bmesh
import math
from mathutils import Vector, Euler, Matrix

from pathlib import Path
ROOT = str(Path(__file__).resolve().parents[2])
MODELS = ROOT + r"\assets\models"

EXPORT_COLL = None
STATIC = {}          # group key -> [objects]  (joined at export)
PROPS_DEFERRED = []  # (object name, dict)
ALL_NAMED = set()


# ----------------------------------------------------------------------------
# materials
# ----------------------------------------------------------------------------
# name: (basecolour, roughness, metallic, emission colour or None, emission strength)
PALETTE = {
    "MAT_wallpaper":        ("#b3a982", 0.92, 0.0, None, 0.0),
    "MAT_wallpaper_dark":   ("#6f6a52", 0.94, 0.0, None, 0.0),
    "MAT_plaster":          ("#cfc9b8", 0.90, 0.0, None, 0.0),
    "MAT_wood_floor":       ("#6b4230", 0.72, 0.0, None, 0.0),
    "MAT_wood_door":        ("#7a4633", 0.68, 0.0, None, 0.0),
    "MAT_wood_dark":        ("#4a3527", 0.78, 0.0, None, 0.0),
    "MAT_wood_pale":        ("#c2a374", 0.80, 0.0, None, 0.0),
    "MAT_paint_ceiling":    ("#d8d4c4", 0.95, 0.0, None, 0.0),
    "MAT_concrete":         ("#8c8a80", 0.95, 0.0, None, 0.0),
    "MAT_tile_green":       ("#5c7a68", 0.55, 0.0, None, 0.0),
    "MAT_tile_white":       ("#d9ddd6", 0.50, 0.0, None, 0.0),
    "MAT_tile_floor":       ("#9a978b", 0.80, 0.0, None, 0.0),
    "MAT_metal_locker":     ("#7f8b84", 0.45, 0.15, None, 0.0),
    "MAT_metal_rust":       ("#7a5138", 0.70, 0.10, None, 0.0),
    "MAT_glass_dirty":      ("#38453f", 0.22, 0.05, None, 0.0),
    "MAT_window_night":     ("#0b1220", 0.30, 0.0, "#16223a", 0.5),
    "MAT_curtain":          ("#b9a77f", 0.92, 0.0, None, 0.0),
    "MAT_fabric_red":       ("#8e2c22", 0.95, 0.0, None, 0.0),
    "MAT_fabric_white":     ("#d5d1c6", 0.95, 0.0, None, 0.0),
    "MAT_fabric_blue":      ("#52636e", 0.95, 0.0, None, 0.0),
    "MAT_paper":            ("#cfc3a2", 0.90, 0.0, None, 0.0),
    "MAT_photo":            ("#8f7f6a", 0.85, 0.0, None, 0.0),
    "MAT_tv_static":        ("#c8ccd0", 0.35, 0.0, "#9fb4c8", 0.8),
    "MAT_lamp_tube":        ("#eef6ee", 0.25, 0.0, "#d8fff0", 2.5),
    "MAT_lamp_warm":        ("#ffd9a0", 0.30, 0.0, "#ffc46a", 2.0),
    "MAT_lantern_paper":    ("#c8452c", 0.70, 0.0, "#ff7a3c", 1.2),
    "MAT_soil":             ("#5a4a38", 0.98, 0.0, None, 0.0),
    "MAT_grass":            ("#2f3d2a", 0.98, 0.0, None, 0.0),
    "MAT_bark":             ("#4a3a2c", 0.95, 0.0, None, 0.0),
    "MAT_leaves":           ("#2c3a28", 0.95, 0.0, None, 0.0),
    "MAT_stone":            ("#7d7a72", 0.92, 0.0, None, 0.0),
    "MAT_shrine_wood":      ("#6a3b2a", 0.85, 0.0, None, 0.0),
    "MAT_sign_night_1":     ("#5b4632", 0.85, 0.0, None, 0.0),
    "MAT_sign_night_2":     ("#5b4632", 0.85, 0.0, None, 0.0),
    "MAT_sign_bath":        ("#eee6d6", 0.70, 0.0, None, 0.0),
    "MAT_shrine_tablet":    ("#6f6a62", 0.90, 0.0, None, 0.0),
    "MAT_door_number_501":  ("#9b9488", 0.55, 0.10, None, 0.0),
    "MAT_door_number_502":  ("#9b9488", 0.55, 0.10, None, 0.0),
    "MAT_door_number_503":  ("#9b9488", 0.55, 0.10, None, 0.0),
    "MAT_door_number_504":  ("#9b9488", 0.55, 0.10, None, 0.0),
    "MAT_clock_face":       ("#ddd6c2", 0.75, 0.0, None, 0.0),
    "MAT_mirror_grime":     ("#9fb2ad", 0.75, 0.0, None, 0.0),
    "MAT_stain_mold":       ("#3c4432", 0.98, 0.0, None, 0.0),
    "MAT_stain_water":      ("#7a6d50", 0.92, 0.0, None, 0.0),
    "MAT_entity_white":     ("#cfd3cd", 0.92, 0.0, None, 0.0),
    "MAT_entity_hair":      ("#14161a", 0.95, 0.0, None, 0.0),
    "MAT_entity_face":      ("#ded6c8", 0.85, 0.0, None, 0.0),
    "MAT_red_cloth":        ("#9a2b24", 0.92, 0.0, None, 0.0),
    "MAT_paper_money":      ("#c9b36b", 0.92, 0.0, None, 0.0),
    "MAT_steam":            ("#cfd6d2", 0.60, 0.0, None, 0.0),
}
ALLOWED_MATS = set(PALETTE.keys())

_MAT_CACHE = {}


def _rgba(hexs):
    """sRGB hex -> linear RGBA (Blender base colours are linear)."""
    def lin(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return (lin(int(hexs[1:3], 16)), lin(int(hexs[3:5], 16)),
            lin(int(hexs[5:7], 16)), 1.0)


def get_mat(name):
    if name in _MAT_CACHE:
        return _MAT_CACHE[name]
    if name not in PALETTE:
        raise RuntimeError("material not in ASSET_SPEC list: " + name)
    col, rough, metal, emis, estr = PALETTE[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    rgba = _rgba(col)
    bsdf.inputs["Base Color"].default_value = rgba
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if emis:
        bsdf.inputs["Emission Color"].default_value = _rgba(emis)
        bsdf.inputs["Emission Strength"].default_value = estr
    m.diffuse_color = rgba
    _MAT_CACHE[name] = m
    return m


# ----------------------------------------------------------------------------
# scene setup
# ----------------------------------------------------------------------------
def reset(scene_name="scene"):
    """Empty the factory scene (no read_factory_settings: the user's live .blend
    is a different process; we only clean this headless one)."""
    global EXPORT_COLL, STATIC, PROPS_DEFERRED
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for coll in list(bpy.data.collections):
        bpy.data.collections.remove(coll)
    for me in list(bpy.data.meshes):
        bpy.data.meshes.remove(me)
    for ma in list(bpy.data.materials):
        bpy.data.materials.remove(ma)
    _MAT_CACHE.clear()
    STATIC = {}
    PROPS_DEFERRED = []
    ALL_NAMED.clear()
    EXPORT_COLL = bpy.data.collections.new("EXPORT")
    bpy.context.scene.collection.children.link(EXPORT_COLL)
    sc = bpy.context.scene
    sc.name = scene_name
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0


def _link(name, me, pivot):
    ob = bpy.data.objects.new(name, me)
    EXPORT_COLL.objects.link(ob)
    ob.location = Vector(pivot)
    ALL_NAMED.add(name)
    return ob


def _unique(name):
    if name in bpy.data.objects:
        raise RuntimeError("duplicate object name: " + name)
    return name


# ----------------------------------------------------------------------------
# UV projection
# ----------------------------------------------------------------------------
def _uv_tile(ob, uv_scale=2.0):
    me = ob.data
    if not me.uv_layers:
        me.uv_layers.new(name="UVMap")
    uv = me.uv_layers.active.data
    mw = ob.matrix_world
    for poly in me.polygons:
        n = poly.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        for li in poly.loop_indices:
            co = mw @ me.vertices[me.loops[li].vertex_index].co
            if ax == 0:
                u, v = co.y, co.z
            elif ax == 1:
                u, v = co.x, co.z
            else:
                u, v = co.x, co.y
            uv[li].uv = (u / uv_scale, v / uv_scale)


def _uv_unit_front(ob, front):
    """Map the face(s) pointing along `front` to a full 0..1 rectangle, upright,
    not mirrored.  Other faces get a cheap tile projection."""
    me = ob.data
    if not me.uv_layers:
        me.uv_layers.new(name="UVMap")
    uv = me.uv_layers.active.data
    n = Vector(front).normalized()
    up = Vector((0, 0, 1))
    if abs(n.dot(up)) > 0.9:
        up = Vector((0, 1, 0))
    u_axis = up.cross(n).normalized()
    v_axis = up
    us, vs = [], []
    for v in me.vertices:
        us.append(v.co.dot(u_axis))
        vs.append(v.co.dot(v_axis))
    umin, umax = min(us), max(us)
    vmin, vmax = min(vs), max(vs)
    du = max(umax - umin, 1e-6)
    dv = max(vmax - vmin, 1e-6)
    for poly in me.polygons:
        fn = poly.normal
        if fn.dot(n) > 0.35:
            for li in poly.loop_indices:
                co = me.vertices[me.loops[li].vertex_index].co
                uv[li].uv = ((co.dot(u_axis) - umin) / du,
                             (co.dot(v_axis) - vmin) / dv)
        else:
            ax = max(range(3), key=lambda i: abs(fn[i]))
            for li in poly.loop_indices:
                co = me.vertices[me.loops[li].vertex_index].co
                if ax == 0:
                    u, w = co.y, co.z
                elif ax == 1:
                    u, w = co.x, co.z
                else:
                    u, w = co.x, co.y
                uv[li].uv = (u, w)


def _assign_mats(ob, mat_names):
    for mn in mat_names:
        ob.data.materials.append(get_mat(mn))


def _finish_mesh(name, bm, mat_names, pivot, uv, uv_scale, front, group,
                 bevel, smooth, up_faces):
    if bevel and bevel > 0:
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bevel, segments=1,
                        affect="EDGES", profile=0.5, clamp_overlap=True)
    if up_faces:
        bm.normal_update()
        bad = [f for f in bm.faces if f.normal.z < -0.2]
        if bad:
            bmesh.ops.reverse_faces(bm, faces=bad)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.update()
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    ob = _link(_unique(name), me, pivot)
    _assign_mats(ob, mat_names)
    if uv == "tile":
        _uv_tile(ob, uv_scale)
    elif uv == "unit":
        _uv_unit_front(ob, front or (0, -1, 0))
    if group:
        STATIC.setdefault(group, []).append(ob)
    return ob


# ----------------------------------------------------------------------------
# primitive builders
# ----------------------------------------------------------------------------
def box(name, size, loc, mat, rot=(0, 0, 0), bevel=0.0, uv="tile",
        uv_scale=2.0, front=None, group=None, pivot=None):
    """Axis box centred on `loc` (rot baked into the mesh).  mats: str or list."""
    _unique(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= size[0]
        v.co.y *= size[1]
        v.co.z *= size[2]
    if any(rot):
        bm.transform(Euler(rot, "XYZ").to_matrix().to_4x4())
    p = Vector(pivot) if pivot is not None else Vector((0, 0, 0))
    bm.transform(Matrix.Translation(Vector(loc) - p))
    mats = [mat] if isinstance(mat, str) else list(mat)
    return _finish_mesh(name, bm, mats, p, uv, uv_scale, front, group,
                        bevel, False, False)


def slab(name, x0, x1, y0, y1, z0, z1, mat, bevel=0.0, uv="tile",
         uv_scale=2.0, front=None, group=None, pivot=None):
    """Box given by world-space extents."""
    size = (abs(x1 - x0), abs(y1 - y0), abs(z1 - z0))
    loc = ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)
    return box(name, size, loc, mat, bevel=bevel, uv=uv, uv_scale=uv_scale,
               front=front, group=group, pivot=pivot)


def cyl(name, radius, depth, loc, mat, axis="Z", segments=10, radius2=None,
        bevel=0.0, uv="tile", uv_scale=2.0, group=None, pivot=None, smooth=True):
    _unique(name)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segments,
                          radius1=radius,
                          radius2=radius if radius2 is None else radius2,
                          depth=depth)
    rot = Matrix.Identity(4)
    if axis == "X":
        rot = Euler((0, math.radians(90), 0)).to_matrix().to_4x4()
    elif axis == "Y":
        rot = Euler((math.radians(90), 0, 0)).to_matrix().to_4x4()
    bm.transform(rot)
    p = Vector(pivot) if pivot is not None else Vector((0, 0, 0))
    bm.transform(Matrix.Translation(Vector(loc) - p))
    mats = [mat] if isinstance(mat, str) else list(mat)
    return _finish_mesh(name, bm, mats, p, uv, uv_scale, None, group,
                        bevel, smooth, False)


def cyl_between(name, p1, p2, radius, mat, segments=8, uv="tile",
                uv_scale=2.0, group=None, pivot=None, smooth=True):
    p1, p2 = Vector(p1), Vector(p2)
    d = p2 - p1
    length = d.length
    if length < 1e-5:
        length = 1e-3
    _unique(name)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segments,
                          radius1=radius, radius2=radius, depth=length)
    quat = d.normalized().to_track_quat("Z", "Y")
    bm.transform(quat.to_matrix().to_4x4())
    p = Vector(pivot) if pivot is not None else Vector((0, 0, 0))
    bm.transform(Matrix.Translation((p1 + p2) / 2 - p))
    mats = [mat] if isinstance(mat, str) else list(mat)
    return _finish_mesh(name, bm, mats, p, uv, uv_scale, None, group,
                        0.0, smooth, False)


def sphere(name, radius, loc, mat, subdiv=2, scale=(1, 1, 1), uv="tile",
           uv_scale=2.0, group=None, pivot=None, smooth=False):
    _unique(name)
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=radius)
    for v in bm.verts:
        v.co.x *= scale[0]
        v.co.y *= scale[1]
        v.co.z *= scale[2]
    p = Vector(pivot) if pivot is not None else Vector((0, 0, 0))
    bm.transform(Matrix.Translation(Vector(loc) - p))
    mats = [mat] if isinstance(mat, str) else list(mat)
    return _finish_mesh(name, bm, mats, p, uv, uv_scale, None, group,
                        0.0, smooth, False)


def mesh_custom(name, verts, faces, mat, pivot=(0, 0, 0), uv="tile",
                uv_scale=2.0, front=None, group=None, bevel=0.0,
                smooth=False, up_faces=False, loop_uvs=None):
    """verts in world coordinates, faces are tuples of indices.
    loop_uvs: optional flat list of (u,v), one per face-loop in creation order."""
    _unique(name)
    p = Vector(pivot)
    bm = bmesh.new()
    bv = [bm.verts.new(Vector(v) - p) for v in verts]
    bm.verts.ensure_lookup_table()
    bmfaces = []
    for f in faces:
        try:
            bmfaces.append(bm.faces.new([bv[i] for i in f]))
        except ValueError:
            pass
    bm.normal_update()
    mats = [mat] if isinstance(mat, str) else list(mat)
    ob = _finish_mesh(name, bm, mats, p, None if loop_uvs else uv, uv_scale,
                      front, group, bevel, smooth, up_faces)
    if loop_uvs is not None:
        me = ob.data
        if not me.uv_layers:
            me.uv_layers.new(name="UVMap")
        uvl = me.uv_layers.active.data
        k = 0
        for poly in me.polygons:
            for li in poly.loop_indices:
                if k < len(loop_uvs):
                    uvl[li].uv = loop_uvs[k]
                    k += 1
    return ob


def frustum(name, bottom, top, z0, z1, loc_xy, mat, bevel=0.0, uv="tile",
            uv_scale=2.0, group=None, pivot=None):
    """Tapered box: bottom/top = (sx, sy) sizes, centred on loc_xy."""
    _unique(name)
    cx, cy = loc_xy
    bx, by = bottom[0] / 2, bottom[1] / 2
    tx, ty = top[0] / 2, top[1] / 2
    verts = [(cx - bx, cy - by, z0), (cx + bx, cy - by, z0),
             (cx + bx, cy + by, z0), (cx - bx, cy + by, z0),
             (cx - tx, cy - ty, z1), (cx + tx, cy - ty, z1),
             (cx + tx, cy + ty, z1), (cx - tx, cy + ty, z1)]
    faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5),
             (2, 3, 7, 6), (3, 0, 4, 7)]
    p = Vector(pivot) if pivot is not None else Vector((0, 0, 0))
    return mesh_custom(name, verts, faces, mat, pivot=p, uv=uv,
                       uv_scale=uv_scale, group=group, bevel=bevel,
                       up_faces=False)


def grid_panel(name, x0, x1, y, z0, z1, mat, folds=8, amp=0.035, axis="x",
               group=None, uv_scale=2.0, thickness=0.006):
    """Wavy curtain-like double-sided panel hanging at fixed y (or x)."""
    _unique(name)
    n = folds * 2
    verts, faces = [], []
    for side in (-1, 1):
        base = len(verts)
        for i in range(n + 1):
            t = i / n
            if axis == "x":
                x = x0 + (x1 - x0) * t
                yy = y + side * math.sin(math.pi * t * folds) * amp
                for z in (z0, z1):
                    verts.append((x, yy + side * thickness / 2, z))
            else:
                yy = x0 + (x1 - x0) * t
                xx = y + side * math.sin(math.pi * t * folds) * amp
                for z in (z0, z1):
                    verts.append((xx + side * thickness / 2, yy, z))
        for i in range(n):
            a = base + i * 2
            b = base + i * 2 + 1
            c = base + i * 2 + 3
            d = base + i * 2 + 2
            if side > 0:
                faces.append((a, b, c, d))
            else:
                faces.append((a, d, c, b))
    return mesh_custom(name, verts, faces, mat, uv="tile", uv_scale=uv_scale,
                       group=group)


def circle_disc(name, radius, loc, mat, axis="Y", segments=16, uv="unit",
                front=(0, -1, 0), bevel=0.0, group=None, pivot=None):
    """Flat disc (clock face etc.)."""
    _unique(name)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segments,
                          radius1=radius, radius2=radius, depth=0.012)
    if axis == "X":
        bm.transform(Euler((0, math.radians(90), 0)).to_matrix().to_4x4())
    elif axis == "Y":
        bm.transform(Euler((math.radians(90), 0, 0)).to_matrix().to_4x4())
    p = Vector(pivot) if pivot is not None else Vector((0, 0, 0))
    bm.transform(Matrix.Translation(Vector(loc) - p))
    mats = [mat] if isinstance(mat, str) else list(mat)
    return _finish_mesh(name, bm, mats, p, uv, 1.0, front, group, bevel,
                        True, False)


# ----------------------------------------------------------------------------
# gameplay helpers
# ----------------------------------------------------------------------------
def empty(name, loc, props=None):
    _unique(name)
    ob = bpy.data.objects.new(name, None)
    EXPORT_COLL.objects.link(ob)
    ob.location = Vector(loc)
    ob.empty_display_type = "PLAIN_AXES"
    ob.empty_display_size = 0.2
    ALL_NAMED.add(name)
    for k, v in (props or {}).items():
        ob[k] = v
    return ob


def props(target, **kv):
    if isinstance(target, str):
        PROPS_DEFERRED.append((target, kv))
    else:
        for k, v in kv.items():
            target[k] = v


def spawn(name, loc):
    return empty(name, loc)


def look(name, loc):
    return empty(name, loc)


def mark(name, loc):
    return empty(name, loc)


def light(name, loc, kind="point", power=20.0, color="#cfe0d8", radius=7.0,
          cone=55.0, flicker=0.0):
    p = {"light_kind": kind, "light_power": float(power),
         "light_color": color, "light_radius": float(radius),
         "light_flicker": float(flicker)}
    if kind == "spot":
        p["light_cone_deg"] = float(cone)
    return empty(name, loc, p)


def col(name, center, size):
    """Invisible AABB collision proxy (no material)."""
    _unique(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= size[0]
        v.co.y *= size[1]
        v.co.z *= size[2]
        v.co += Vector(center)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = _link(name, me, (0, 0, 0))
    return ob


def col_slab(name, x0, x1, y0, y1, z0=0.0, z1=2.7):
    return col(name, ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2),
               (abs(x1 - x0), abs(y1 - y0), abs(z1 - z0)))


# ----------------------------------------------------------------------------
# joining + export
# ----------------------------------------------------------------------------
def _deselect_all():
    for o in list(bpy.data.objects):
        try:
            o.select_set(False)
        except Exception:
            pass


def _join(objs, final_name):
    if len(objs) == 1:
        ob = objs[0]
        ob.name = final_name
        ob.data.name = final_name
        return ob
    vl = bpy.context.view_layer
    _deselect_all()
    for o in objs:
        o.select_set(True)
    vl.objects.active = objs[0]
    bpy.ops.object.join()
    ob = vl.objects.active
    ob.name = final_name
    ob.data.name = final_name
    return ob


def tri_count():
    n = 0
    for ob in bpy.data.objects:
        if ob.type == "MESH":
            for p in ob.data.polygons:
                n += max(len(p.vertices) - 2, 0)
    return n


def finalize(filepath, groups=None, apply_names=None):
    """Join static groups, apply deferred props, select everything and export GLB."""
    groups = groups or {}
    joined = {}
    for gkey, objs in list(STATIC.items()):
        final_name = groups.get(gkey, gkey)
        joined[gkey] = _join(objs, final_name)
    STATIC.clear()
    # deferred custom properties (they may target just-joined objects)
    for name, kv in PROPS_DEFERRED:
        ob = bpy.data.objects.get(name)
        if ob is None:
            raise RuntimeError("deferred props target missing: " + name)
        for k, v in kv.items():
            ob[k] = v
    PROPS_DEFERRED.clear()
    # every object should now have identity-ish transforms (geometry baked)
    for ob in bpy.data.objects:
        if ob.type == "MESH":
            ob.rotation_euler = (0, 0, 0)
            ob.scale = (1, 1, 1)
    vl = bpy.context.view_layer
    _deselect_all()
    export_objs = [o for o in EXPORT_COLL.objects]
    for o in export_objs:
        o.select_set(True)
    vl.objects.active = export_objs[0]
    bpy.ops.export_scene.gltf(
        filepath=filepath,
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_extras=True,
        export_yup=True,
        export_cameras=False,
        export_lights=False,
        export_texcoords=True,
        export_normals=True,
        export_materials="EXPORT",
        export_image_format="NONE",
    )
    tris = tri_count()
    print("EXPORTED", filepath)
    print("OBJECTS", len(export_objs), "TRIS", tris)
    return joined

