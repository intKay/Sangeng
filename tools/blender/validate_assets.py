"""validate_assets.py -- verify the three exported GLB scenes against
horror-demos/docs/ASSET_SPEC.md.  Pure Python (no Blender needed).

Usage:
    python validate_assets.py            # validate all three scenes
    python validate_assets.py door       # one scene
Writes reports/modeler/validate.txt and prints VALIDATE OK / VALIDATE FAIL.
"""
import json
import os
import struct
import sys
import datetime

from pathlib import Path
ROOT = str(Path(__file__).resolve().parents[2])
MODELS = os.path.join(ROOT, "assets", "models")
REPORT = os.path.join(ROOT, "reports", "modeler", "validate.txt")

ALLOWED_MATS = {
    "MAT_rug_faded", "MAT_enamel_worn", "MAT_bakelite",
    "MAT_wallpaper", "MAT_wallpaper_dark", "MAT_plaster", "MAT_wood_floor",
    "MAT_wood_door", "MAT_wood_dark", "MAT_wood_pale", "MAT_paint_ceiling",
    "MAT_concrete", "MAT_tile_green", "MAT_tile_white", "MAT_tile_floor",
    "MAT_metal_locker", "MAT_metal_rust", "MAT_glass_dirty",
    "MAT_window_night", "MAT_curtain", "MAT_fabric_red", "MAT_fabric_white",
    "MAT_fabric_blue", "MAT_paper", "MAT_photo", "MAT_tv_static",
    "MAT_lamp_tube", "MAT_lamp_warm", "MAT_lantern_paper", "MAT_soil",
    "MAT_grass", "MAT_bark", "MAT_leaves", "MAT_stone", "MAT_shrine_wood",
    "MAT_sign_night_1", "MAT_sign_night_2", "MAT_sign_bath",
    "MAT_shrine_tablet", "MAT_door_number_501", "MAT_door_number_502",
    "MAT_door_number_503", "MAT_door_number_504", "MAT_clock_face",
    "MAT_mirror_grime", "MAT_stain_mold", "MAT_stain_water",
    "MAT_entity_white", "MAT_entity_hair", "MAT_entity_face",
    "MAT_red_cloth", "MAT_paper_money", "MAT_steam",
    # v1.0.2 story-layer materials
    "MAT_photo_family_1", "MAT_photo_family_2", "MAT_photo_family_3",
    "MAT_child_drawing", "MAT_calendar", "MAT_notice_board", "MAT_couplet",
    "MAT_bath_poster", "MAT_bath_notice", "MAT_mirror_crack",
    "MAT_handprint", "MAT_bath_ticket",
}

DOOR_LIGHTS = ["LIGHT_corr_01", "LIGHT_corr_02", "LIGHT_corr_03",
               "LIGHT_corr_04", "LIGHT_corr_05", "LIGHT_entry",
               "LIGHT_living", "LIGHT_tv", "LIGHT_floor_lamp",
               "LIGHT_kitchen", "LIGHT_bedroom", "LIGHT_moon_bed"]
MIRROR_LIGHTS = ["LIGHT_tube_01", "LIGHT_tube_02", "LIGHT_bench",
                 "LIGHT_bath", "LIGHT_window"]
NIGHT_LIGHTS = ["LIGHT_shrine", "LIGHT_village"]

SCENES = {
    "door": {
        "file": "door.glb",
        "target": 6000, "cap": 10000, "min_col": 18,
        "required_names": [
            "SPAWN_corridor", "LOOK_corridor",
            "SPAWN_apartment", "LOOK_apartment",
            "SPAWN_bedroom", "LOOK_bedroom",
            "INT_fire_door", "INT_elevator_button",
            "INT_door_503", "INT_door_bedroom",
            "INT_door_501", "INT_door_502", "INT_door_504",
            "INT_switch_corridor", "INT_switch_living",
            "INT_flashlight", "INT_battery_01", "INT_battery_02",
            "INT_letter_01", "INT_letter_02", "INT_letter_03",
            "INT_letter_final", "INT_clock",
            "S_photo_1", "S_photo_2", "S_chair_final", "S_shoe_cabinet",
            "ENTITY_she", "ENTITY_she_sitting",
            # v1.0.2 storytelling props
            "INT_photo_1", "INT_photo_2", "INT_photo_3", "INT_calendar",
            "INT_phone", "INT_child_drawing", "INT_sewing_machine",
            "INT_thermos", "INT_chair_final", "INT_notice_board",
            "INT_couplet", "INT_shoes_waiting",
            "V2_shoes_waiting", "V2_light_under_door", "V2_drawing_corr",
            "V3_handprints_door", "V3_wet_footprints",
            "V2_corr_chair", "V2_door_501_ajar", "V2_mail_scatter",
            "V2_bulb_dead", "V2_stain_01", "V2_stain_02", "V2_stain_03",
            "V3_handprints_01", "V3_handprints_02", "V3_handprints_03",
            "V3_door_502_ajar", "V3_door_504_ajar", "V3_corr_water",
            "V3_stain_04", "V3_stain_05", "V3_stain_06",
        ] + DOOR_LIGHTS,
        "interact": {
            "INT_door_503": "door", "INT_door_bedroom": "door",
            "INT_door_501": "door", "INT_door_502": "door",
            "INT_door_504": "door", "INT_fire_door": "examine",
            "INT_elevator_button": "examine",
            "INT_switch_corridor": "switch", "INT_switch_living": "switch",
            "INT_flashlight": "pickup", "INT_battery_01": "pickup",
            "INT_battery_02": "pickup", "INT_letter_01": "pickup",
            "INT_letter_02": "pickup", "INT_letter_03": "pickup",
            "INT_letter_final": "pickup", "INT_clock": "examine",
            "INT_photo_1": "examine", "INT_photo_2": "examine",
            "INT_photo_3": "examine", "INT_calendar": "examine",
            "INT_phone": "examine", "INT_child_drawing": "examine",
            "INT_sewing_machine": "examine", "INT_thermos": "examine",
            "INT_chair_final": "examine", "INT_notice_board": "examine",
            "INT_couplet": "examine", "INT_shoes_waiting": "examine",
        },
        "door_extras": ["INT_door_503", "INT_door_bedroom"],
        "hidden": ["ENTITY_she", "ENTITY_she_sitting", "INT_letter_final",
                   "V2_corr_chair", "V2_door_501_ajar", "V2_mail_scatter",
                   "V2_bulb_dead", "V2_stain_01", "V2_stain_02",
                   "V2_stain_03", "V3_handprints_01", "V3_handprints_02",
                   "V3_handprints_03", "V3_door_502_ajar",
                   "V3_door_504_ajar", "V3_corr_water",
                   "V3_stain_04", "V3_stain_05", "V3_stain_06",
                   "V2_shoes_waiting", "V2_light_under_door",
                   "V2_drawing_corr", "V3_handprints_door",
                   "V3_wet_footprints"],
        "lights": DOOR_LIGHTS,
    },
    "mirror": {
        "file": "mirror.glb",
        "target": 5000, "cap": 7000, "min_col": 10,
        "required_names": [
            "MIRROR_surface",
            "SPAWN_mirror", "LOOK_mirror",
            "INT_towel", "INT_valve", "INT_switch", "INT_stool_01",
            "INT_stool_02", "INT_locker_02", "INT_radio", "INT_mannequin",
            "INT_clock",
            "MARK_towel_floor", "MARK_towel_hook",
            "MARK_stool_home", "MARK_stool_away",
            "ENTITY_reflection",
            "S_mirror_frame", "S_basin_counter", "S_locker_bank_1",
            "S_locker_bank_2", "S_bench", "S_door_bath", "S_sign_bath",
            "S_window_high", "S_tube_01", "S_tube_02",
            "S_steam_01", "S_steam_02",
            "S_faucet_01", "S_faucet_02", "S_faucet_03",
            # v1.0.2 life layer + story planes
            "S_bath_poster", "S_bath_notice", "S_ticket_board",
            "S_bath_ticket", "S_open_locker_clothes", "S_shoes_bench",
            "S_towel_pile", "S_basin", "S_bucket", "S_mop", "S_bottles",
            "S_comb", "S_cigarette", "S_newspaper_bench", "S_hair_drain",
            "S_ceiling_leak", "S_bench_extra",
            "S_handprint_1", "S_handprint_2", "S_handprint_3",
            "S_mirror_crack",
        ] + MIRROR_LIGHTS,
        "interact": {
            "INT_towel": "move", "INT_valve": "valve", "INT_switch": "switch",
            "INT_stool_01": "move", "INT_stool_02": "move",
            "INT_locker_02": "move", "INT_radio": "radio",
            "INT_mannequin": "move", "INT_clock": "examine",
        },
        "door_extras": [],
        "hidden": ["ENTITY_reflection", "S_handprint_1", "S_handprint_2",
                   "S_handprint_3", "S_mirror_crack"],
        "lights": MIRROR_LIGHTS,
    },
    "nightroad": {
        "file": "nightroad.glb",
        "target": 9000, "cap": 12000, "min_col": 16,
        "required_names": [
            "SPAWN_night_start", "LOOK_night_start",
            "INT_lantern_01", "INT_lantern_02", "INT_lantern_03",
            "INT_lantern_04", "INT_lantern_05",
            "INT_incense", "ENTITY_paper",
            "S_shrine", "S_shrine_tablet", "S_incense_burner",
            "S_sign_1", "S_sign_2",
            "S_grave_01", "S_grave_02", "S_grave_03", "S_scarecrow",
            "S_shrine_cloth", "S_village_lights",
        ] + ["S_tree_%02d" % i for i in range(1, 11)]
          + ["S_pole_%02d" % i for i in range(1, 5)]
          + ["S_paper_money_%02d" % i for i in range(1, 5)]
          + ["COL_path_edge_L_%02d" % i for i in range(1, 9)]
          + ["COL_path_edge_R_%02d" % i for i in range(1, 9)]
          + ["COL_shrine"] + NIGHT_LIGHTS,
        "interact": {
            "INT_lantern_01": "lantern", "INT_lantern_02": "lantern",
            "INT_lantern_03": "lantern", "INT_lantern_04": "lantern",
            "INT_lantern_05": "lantern", "INT_incense": "incense",
        },
        "door_extras": [],
        "hidden": ["ENTITY_paper"],
        "lights": NIGHT_LIGHTS,
    },
}


# ---------------------------------------------------------------------------
def load_glb(path):
    with open(path, "rb") as f:
        data = f.read()
    magic, version, length = struct.unpack("<III", data[:12])
    if magic != 0x46546C67:
        raise ValueError("not a GLB: " + path)
    off = 12
    js = None
    while off < length:
        clen, ctype = struct.unpack("<II", data[off:off + 8])
        off += 8
        chunk = data[off:off + clen]
        off += clen
        if ctype == 0x4E4F534A:
            js = json.loads(chunk.decode("utf-8"))
    return js, len(data)


def scene_info(js, size):
    nodes = js.get("nodes", [])
    meshes = js.get("meshes", [])
    acc = js.get("accessors", [])
    materials = [m.get("name", "?") for m in js.get("materials", [])]

    tris = 0
    per_mesh = {}
    node_mesh = {}
    for n in nodes:
        if "mesh" in n:
            node_mesh[n.get("name", "?")] = n["mesh"]
    for mi, m in enumerate(meshes):
        mt = 0
        for p in m.get("primitives", []):
            mode = p.get("mode", 4)
            if "indices" in p:
                cnt = acc[p["indices"]]["count"]
            else:
                cnt = acc[p["attributes"]["POSITION"]]["count"]
            if mode == 4:
                mt += cnt // 3
        per_mesh[mi] = mt
    for n in nodes:
        if "mesh" in n:
            tris += per_mesh.get(n["mesh"], 0)

    node_names = [n.get("name", "") for n in nodes]
    empties = [n.get("name", "") for n in nodes if "mesh" not in n]
    extras = {}
    for n in nodes:
        if n.get("extras"):
            extras[n.get("name", "")] = n["extras"]

    # material coverage per mesh
    mesh_mat_ok = {}
    for mi, m in enumerate(meshes):
        mats = set()
        for p in m.get("primitives", []):
            if "material" in p:
                mats.add(js["materials"][p["material"]].get("name", "?"))
        mesh_mat_ok[mi] = mats
    return {
        "size": size,
        "nodes": node_names,
        "tris": tris,
        "per_mesh": per_mesh,
        "materials": materials,
        "empties": empties,
        "extras": extras,
        "node_mesh": node_mesh,
        "mesh_mats": mesh_mat_ok,
        "has_cameras": bool(js.get("cameras")),
        "lights_ext": "KHR_lights_punctual" in (js.get("extensionsUsed") or []),
        "raw": js,
    }


def check(scene):
    spec = SCENES[scene]
    path = os.path.join(MODELS, spec["file"])
    lines = []
    errs = []
    warns = []

    def out(s=""):
        lines.append(s)

    out("=" * 78)
    out("SCENE: %s   (%s)" % (scene, spec["file"]))
    out("=" * 78)
    if not os.path.exists(path):
        errs.append("missing file " + path)
        out("FAIL: file missing")
        return lines, errs, warns
    js, size = load_glb(path)
    info = scene_info(js, size)
    out("file      : %s" % path)
    out("size      : %.1f KB" % (size / 1024.0))
    out("meshes    : %d   tris: %d   (target <= %d, cap <= %d)"
        % (len(info["raw"].get("meshes", [])), info["tris"],
           spec["target"], spec["cap"]))
    out("materials : %d  -> %s" % (len(info["materials"]),
                                   ", ".join(sorted(info["materials"]))))
    out("nodes     : %d   empties: %d" % (len(info["nodes"]),
                                          len(info["empties"])))

    # --- names
    names = set(info["nodes"])
    missing = [n for n in spec["required_names"] if n not in names]
    if missing:
        errs.append("missing required names: " + ", ".join(missing))
        out("MISSING NAMES (%d): %s" % (len(missing), ", ".join(missing)))
    else:
        out("required names: all %d present" % len(spec["required_names"]))

    # --- materials
    bad_mats = [m for m in info["materials"] if m not in ALLOWED_MATS]
    if bad_mats:
        errs.append("materials outside ASSET_SPEC list: " + ", ".join(bad_mats))
        out("BAD MATERIALS: " + ", ".join(bad_mats))
    else:
        out("material names: all in ASSET_SPEC list")

    # material coverage for non-COL meshes
    col_meshes, naked = [], []
    for n in info["nodes"]:
        if n.startswith("COL_"):
            col_meshes.append(n)
            continue
        if n in info["node_mesh"]:
            mi = info["node_mesh"][n]
            if not info["mesh_mats"].get(mi):
                naked.append(n)
    if naked:
        errs.append("meshes without material: " + ", ".join(naked))
        out("MESHES WITHOUT MATERIAL: " + ", ".join(naked))
    else:
        out("every non-COL mesh has a material")

    # --- tris budget
    if info["tris"] > spec["cap"]:
        errs.append("tri budget exceeded: %d > cap %d"
                    % (info["tris"], spec["cap"]))
    elif info["tris"] > spec["target"]:
        warns.append("tris %d above target %d (under cap)"
                     % (info["tris"], spec["target"]))
    out("tri budget: %s" % ("OK" if info["tris"] <= spec["cap"] else "FAIL"))

    # --- cameras / lights
    if info["has_cameras"]:
        errs.append("glTF contains cameras")
    if info["lights_ext"]:
        errs.append("glTF contains light objects (KHR_lights_punctual)")
    out("no cameras/lights in GLB: %s"
        % ("OK" if not info["has_cameras"] and not info["lights_ext"] else "FAIL"))

    # --- COL
    cols = [n for n in info["nodes"] if n.startswith("COL_")]
    if len(cols) < spec["min_col"]:
        errs.append("too few COL_ objects: %d < %d"
                    % (len(cols), spec["min_col"]))
    for c in col_meshes:
        mi = info["node_mesh"][c]
        if info["mesh_mats"].get(mi):
            errs.append("COL has material: " + c)
    out("COL objects: %d (min %d)" % (len(cols), spec["min_col"]))

    # --- custom props
    ex = info["extras"]
    for oname, kind in spec["interact"].items():
        if oname not in names:
            continue
        e = ex.get(oname, {})
        if e.get("interact") != kind:
            errs.append("%s interact=%r expected %r"
                        % (oname, e.get("interact"), kind))
        if not e.get("prompt"):
            errs.append("%s missing prompt" % oname)
        if not e.get("id"):
            errs.append("%s missing id" % oname)
    out("interact props checked: %d objects" % len(spec["interact"]))

    for dn in spec.get("door_extras", []):
        e = ex.get(dn, {})
        for k in ("open_angle", "open_dir", "locked"):
            if k not in e:
                errs.append("%s missing door prop %s" % (dn, k))
    if spec.get("door_extras"):
        out("door props checked: " + ", ".join(spec["door_extras"]))

    hidden_missing = [h for h in spec["hidden"]
                      if h in names and not ex.get(h, {}).get("hidden")]
    for h in hidden_missing:
        errs.append("%s should have hidden=True" % h)
    out("hidden variants: %d checked, %d bad"
        % (len(spec["hidden"]), len(hidden_missing)))

    for ln in spec["lights"]:
        if ln not in names:
            continue
        e = ex.get(ln, {})
        for k in ("light_kind", "light_power", "light_color", "light_radius"):
            if k not in e:
                errs.append("%s missing %s" % (ln, k))
        if e.get("light_kind") not in ("point", "spot"):
            errs.append("%s light_kind invalid" % ln)
    out("light empties checked: %d" % len(spec["lights"]))

    # spawn/look pairing
    spawns = [n for n in names if n.startswith("SPAWN_")]
    looks = [n for n in names if n.startswith("LOOK_")]
    if len(spawns) != len(looks):
        errs.append("SPAWN/LOOK count mismatch %d/%d"
                    % (len(spawns), len(looks)))
    for s in spawns:
        lk = "LOOK_" + s[len("SPAWN_"):]
        if lk not in names:
            errs.append("LOOK missing for " + s)
    out("spawn/look pairs: %d/%d" % (len(spawns), len(looks)))

    # entity pivot sanity: entity origin z near 0 (node translation)
    node_by_name = {n.get("name", ""): n for n in info["raw"].get("nodes", [])}
    for n in names:
        if n.startswith("ENTITY_"):
            tr = node_by_name[n].get("translation", [0, 0, 0])
            # glTF Y-up: Blender z -> glTF y
            if abs(tr[1]) > 0.05:
                warns.append("%s origin y=%.2f (expected feet at 0)" % (n, tr[1]))
    out("")
    return lines, errs, warns


def main(argv):
    wanted = argv[1:] or list(SCENES.keys())
    all_lines, all_errs, all_warns = [], [], []
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    all_lines.append("三更 GLB validation  " + stamp)
    all_lines.append("ASSET_SPEC: horror-demos/docs/ASSET_SPEC.md")
    all_errs_total = []
    all_warns_total = []
    for sc in wanted:
        if sc not in SCENES:
            print("unknown scene", sc)
            continue
        lines, errs, warns = check(sc)
        all_lines.extend(lines)
        all_errs_total.extend("%s: %s" % (sc, e) for e in errs)
        all_warns_total.extend("%s: %s" % (sc, w) for w in warns)
    all_lines.append("=" * 78)
    if all_warns_total:
        all_lines.append("WARNINGS (%d):" % len(all_warns_total))
        all_lines.extend("  - " + w for w in all_warns_total)
    if all_errs_total:
        all_lines.append("ERRORS (%d):" % len(all_errs_total))
        all_lines.extend("  - " + e for e in all_errs_total)
        all_lines.append("VALIDATE FAIL: %d error(s)" % len(all_errs_total))
    else:
        all_lines.append("VALIDATE OK")
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(all_lines) + "\n")
    print("\n".join(all_lines[-30:]))
    if all_errs_total:
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv)
