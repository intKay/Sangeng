"""build_mirror.py -- 《镜中》 90s public bath changing room, export mirror.glb.

headless:  blender.exe -b --factory-startup --python build_mirror.py
"""
import sys
import os
import math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_build as L

OUT = L.MODELS + r"\mirror.glb"


def hex_humanoid(group, prefix, x, y, body="MAT_entity_white",
                 hair="MAT_entity_hair", face="MAT_entity_face"):
    P = (x, y, 0.0)
    L.frustum(prefix + "_dress", (0.6, 0.48), (0.34, 0.26), 0.02, 1.15,
              (x, y), body, group=group, pivot=P)
    L.frustum(prefix + "_torso", (0.34, 0.26), (0.3, 0.22), 1.12, 1.42,
              (x, y), body, group=group, pivot=P)
    L.cyl_between(prefix + "_arm_l", (x - 0.17, y, 1.4), (x - 0.24, y + 0.02, 0.9),
                  0.035, body, segments=6, group=group, pivot=P)
    L.cyl_between(prefix + "_arm_r", (x + 0.17, y, 1.4), (x + 0.24, y + 0.02, 0.9),
                  0.035, body, segments=6, group=group, pivot=P)
    L.sphere(prefix + "_head", 0.1, (x, y, 1.56), body, subdiv=2,
             scale=(0.9, 0.85, 1.1), group=group, pivot=P)
    L.sphere(prefix + "_hair", 0.104, (x, y + 0.015, 1.59), hair, subdiv=2,
             scale=(0.95, 0.9, 0.95), group=group, pivot=P)
    L.slab(prefix + "_face", x - 0.06, x + 0.06, y - 0.102, y - 0.094,
           1.53, 1.6, face, front=(0, -1, 0), uv="unit", group=group, pivot=P)
    L.slab(prefix + "_hair_back", x - 0.12, x + 0.12, y + 0.05, y + 0.1,
           0.9, 1.58, hair, group=group, pivot=P)
    L.box(prefix + "_foot_l", (0.09, 0.2, 0.05), (x - 0.1, y - 0.04, 0.025),
          body, group=group, pivot=P)
    L.box(prefix + "_foot_r", (0.09, 0.2, 0.05), (x + 0.1, y - 0.04, 0.025),
          body, group=group, pivot=P)


def stool(group, prefix, x, y, r=0.2, h=0.45, wood="MAT_wood_pale"):
    P = (x, y, 0.0)
    L.cyl(prefix + "_seat", r, 0.05, (x, y, h), wood, segments=10,
          group=group, pivot=P)
    for i, (dx, dy) in enumerate([(-r * 0.7, -r * 0.7), (r * 0.7, -r * 0.7),
                                  (-r * 0.7, r * 0.7), (r * 0.7, r * 0.7)]):
        L.cyl(prefix + "_leg_%d" % i, 0.022, h, (x + dx, y + dy, h / 2),
              wood, segments=6, group=group, pivot=P)
    L.cyl(prefix + "_ring", r * 0.72, 0.025, (x, y, h * 0.35), wood,
          segments=10, group=group, pivot=P)


def locker_bank(name, x0, x1, with_open_door=False):
    """Bank of steel lockers against the south wall.  with_open_door: leave the
    2nd door slot for the separate INT_locker_02 object."""
    G = name
    y0, y1 = -2.79, -2.38
    L.slab(name + "_body", x0, x1, y0, y1, 0.08, 2.0, "MAT_metal_locker",
           group=G)
    L.slab(name + "_plinth", x0, x1, -2.8, -2.36, 0.0, 0.08, "MAT_concrete",
           group=G)
    L.slab(name + "_top", x0 - 0.03, x1 + 0.03, -2.82, -2.34, 2.0, 2.06,
           "MAT_metal_rust", group=G)
    n = 5
    dw = (x1 - x0 - 0.06) / n
    for k in range(n):
        dx0 = x0 + 0.03 + k * dw
        if with_open_door and k == 1:
            continue
        L.slab(name + "_door_%d" % k, dx0 + 0.012, dx0 + dw - 0.012,
               -2.365, -2.345, 0.12, 1.95, "MAT_metal_locker", group=G)
        L.slab(name + "_vent_%d" % k, dx0 + 0.06, dx0 + dw - 0.06,
               -2.343, -2.339, 1.72, 1.76, "MAT_metal_rust", group=G)
        L.box(name + "_handle_%d" % k, (0.03, 0.025, 0.1),
              (dx0 + dw - 0.09, -2.335, 1.05), "MAT_metal_rust", group=G)
    # dust and old towels on top
    L.slab(name + "_dust", x0 + 0.1, x1 - 0.15, -2.7, -2.45, 2.06, 2.075,
           "MAT_concrete", group=G)
    L.box(name + "_towel_1", (0.45, 0.3, 0.08), (x0 + 0.6, -2.6, 2.1),
          "MAT_fabric_white", group=G)
    L.box(name + "_towel_2", (0.3, 0.34, 0.06), (x0 + 1.0, -2.55, 2.1),
          "MAT_fabric_white", group=G)
    L.col("COL_" + name, ((x0 + x1) / 2, (y0 + y1) / 2, 1.0),
          (x1 - x0, y1 - y0, 2.0))


def build_room():
    # shell: tiled lower walls + plaster upper, floor/ceiling
    L.slab("S_floor", -3.6, 3.6, -2.8, 2.8, -0.1, 0.0, "MAT_tile_floor")
    L.slab("S_ceiling", -3.75, 3.75, -2.95, 2.95, 3.0, 3.12,
           "MAT_paint_ceiling")
    # north / south
    for nm, y0, y1 in [("north", 2.8, 2.95), ("south", -2.95, -2.8)]:
        L.slab("S_wall_%s_tile" % nm, -3.75, 3.75, y0, y1, 0.0, 1.7,
               "MAT_tile_green")
        L.slab("S_wall_%s_plaster" % nm, -3.75, 3.75, y0, y1, 1.7, 3.0,
               "MAT_plaster")
    # west / east
    for nm, x0, x1 in [("west", -3.75, -3.6), ("east", 3.6, 3.75)]:
        L.slab("S_wall_%s_tile" % nm, x0, x1, -2.95, 2.95, 0.0, 1.7,
               "MAT_tile_green")
        L.slab("S_wall_%s_plaster" % nm, x0, x1, -2.95, 2.95, 1.7, 3.0,
               "MAT_plaster")
    # tile skirting + a few damaged/missing tiles + wall stains
    L.slab("S_skirt_n", -3.6, 3.6, 2.74, 2.8, 0.0, 0.12, "MAT_tile_white")
    L.slab("S_skirt_w", -3.6, -3.54, -2.8, 2.8, 0.0, 0.12, "MAT_tile_white")
    L.slab("S_skirt_e", 3.54, 3.6, -2.8, 2.8, 0.0, 0.12, "MAT_tile_white")
    L.slab("S_damaged_tile_1", 1.4, 1.85, -2.798, -2.79, 2.62, 2.95,
           "MAT_concrete")
    L.slab("S_damaged_tile_2", -3.598, -3.59, -1.2, -0.75, 0.22, 0.6,
           "MAT_concrete")
    L.slab("S_wall_stain_1", 2.0, 3.0, -2.797, -2.79, 2.0, 2.7,
           "MAT_stain_mold")
    L.slab("S_wall_stain_2", -3.597, -3.59, 0.4, 1.5, 1.8, 2.6,
           "MAT_stain_water")
    L.slab("S_floor_stain_1", -1.4, 0.2, -1.9, -1.1, 0.0, 0.006,
           "MAT_stain_water")
    L.slab("S_floor_stain_2", 1.2, 2.4, 0.6, 1.6, 0.0, 0.006,
           "MAT_stain_water")
    # puddles
    L.slab("S_puddle_1", -2.9, -1.8, -0.6, 0.3, 0.0, 0.004, "MAT_stain_water")
    L.slab("S_puddle_2", 0.4, 1.5, -2.2, -1.4, 0.0, 0.004, "MAT_stain_water")
    # drain
    L.circle_disc("S_drain", 0.14, (0.7, -1.9, 0.006), "MAT_metal_rust",
                  axis="Z", segments=12, uv="tile")
    L.circle_disc("S_drain_hole", 0.09, (0.7, -1.9, 0.012), "MAT_concrete",
                  axis="Z", segments=12, uv="tile")
    # cracked / missing floor tiles
    for i, (x0, x1, y0, y1) in enumerate([(-2.2, -1.75, 0.9, 1.4),
                                          (0.9, 1.4, -1.1, -0.65),
                                          (2.0, 2.45, -0.4, 0.05)]):
        L.slab("S_broken_tile_%d" % i, x0, x1, y0, y1, 0.0, 0.007,
               "MAT_concrete")
    # ceiling tubes (fixtures; real lighting comes from LIGHT_* empties)
    for i, xx in enumerate([-1.2, 1.2]):
        L.box("S_tube_%02d" % (i + 1), (0.2, 1.25, 0.08), (xx, 0, 2.94),
              "MAT_metal_rust", group="S_tube_%02d" % (i + 1))
        L.box("S_tube_%02d_glow" % (i + 1), (0.12, 1.15, 0.06), (xx, 0, 2.885),
              "MAT_lamp_tube", group="S_tube_%02d" % (i + 1))
    # wall pipes (feed the basin taps)
    L.cyl_between("S_pipe_north", (-2.0, 2.79, 0.15), (-2.0, 2.79, 2.95), 0.03,
                  "MAT_metal_rust", segments=8)
    L.cyl_between("S_pipe_north2", (2.45, 2.79, 0.15), (2.45, 2.79, 1.15), 0.03,
                  "MAT_metal_rust", segments=8)


def build_mirror_wall():
    # vanity counter
    L.slab("S_basin_counter", -2.1, 2.1, 2.24, 2.79, 0.0, 0.8,
           "MAT_tile_white")
    L.slab("S_basin_counter_top", -2.14, 2.14, 2.2, 2.79, 0.8, 0.88,
           "MAT_tile_white")
    # dark front kick + panel lines
    L.slab("S_basin_kick", -2.1, 2.1, 2.24, 2.27, 0.0, 0.12, "MAT_concrete")
    for i, xx in enumerate([-1.4, 0.0, 1.4]):
        L.cyl("S_basin_%d" % i, 0.21, 0.05, (xx, 2.5, 0.9), "MAT_tile_white",
              segments=12)
        L.cyl("S_basin_inner_%d" % i, 0.16, 0.03, (xx, 2.5, 0.915),
              "MAT_metal_locker", segments=12)
        L.cyl_between("S_basin_drain_%d" % i, (xx, 2.5, 0.914), (xx, 2.5, 0.918),
                      0.02, "MAT_metal_rust", segments=6)
    L.col("COL_basin_counter", (0, 2.5, 0.5), (4.24, 0.6, 1.0))
    # three faucets (separate named objects, origin at wall side)
    for i, xx in enumerate([-1.4, 0.0, 1.4]):
        g = "S_faucet_%02d" % (i + 1)
        L.cyl(g + "_body", 0.024, 0.16, (xx, 2.72, 0.96), "MAT_metal_rust",
              segments=8, group=g)
        L.cyl(g + "_spout", 0.018, 0.16, (xx, 2.63, 1.03), "MAT_metal_rust",
              axis="Y", segments=8, group=g)
        L.cyl(g + "_handle", 0.04, 0.03, (xx + 0.07, 2.72, 0.94),
              "MAT_metal_rust", axis="Z", segments=8, group=g)
    # soap dish / cup / towel bar
    L.box("S_soap_dish", (0.16, 0.1, 0.04), (-0.65, 2.5, 0.9),
          "MAT_tile_white")
    L.box("S_soap", (0.09, 0.06, 0.03), (-0.65, 2.5, 0.94), "MAT_fabric_white")
    L.cyl("S_cup", 0.04, 0.09, (2.0, 2.58, 0.925), "MAT_fabric_white",
          segments=8)
    # MIRROR surface (independent flat mesh, full 0-1 UV front)
    L.slab("MIRROR_surface", -2.1, 2.1, 2.735, 2.745, 1.0, 2.5,
           "MAT_mirror_grime", front=(0, -1, 0), uv="unit")
    # mirror frame
    L.slab("S_mirror_frame_top", -2.24, 2.24, 2.7, 2.8, 2.5, 2.66,
           "MAT_wood_dark", group="S_mirror_frame")
    L.slab("S_mirror_frame_bottom", -2.24, 2.24, 2.7, 2.8, 0.86, 1.0,
           "MAT_wood_dark", group="S_mirror_frame")
    L.slab("S_mirror_frame_left", -2.24, -2.1, 2.7, 2.8, 0.86, 2.66,
           "MAT_wood_dark", group="S_mirror_frame")
    L.slab("S_mirror_frame_right", 2.1, 2.24, 2.7, 2.8, 0.86, 2.66,
           "MAT_wood_dark", group="S_mirror_frame")
    # towel hooks beside the mirror + MARK
    for i, xx in enumerate([-2.55, 2.55]):
        L.cyl_between("S_hook_%d" % i, (xx, 2.79, 1.55), (xx, 2.66, 1.52),
                      0.012, "MAT_metal_rust", segments=6)
    L.mark("MARK_towel_hook", (-2.55, 2.68, 1.55))
    # valve on the exposed pipe right of the mirror (origin = wheel axis)
    P = (2.45, 2.70, 1.2)
    L.cyl("INT_valve_wheel", 0.09, 0.03, P, "MAT_metal_rust", axis="Y",
          segments=10, group="INT_valve", pivot=P)
    for k in range(4):
        a = math.radians(45 + k * 90)
        L.box("INT_valve_spoke_%d" % k, (0.016, 0.012, 0.16),
              (P[0] + 0.0, P[1], P[2] + 0.0), "MAT_metal_rust",
              rot=(0, a, 0), group="INT_valve", pivot=P)
    L.cyl("INT_valve_hub", 0.025, 0.05, P, "MAT_metal_locker", axis="Y",
          segments=8, group="INT_valve", pivot=P)
    L.props("INT_valve", interact="valve", prompt="拧阀门", id="valve")


def build_lockers_props():
    locker_bank("S_locker_bank_1", -3.2, -0.7, with_open_door=True)
    locker_bank("S_locker_bank_2", 0.7, 3.2)
    # INT_locker_02: second door of bank 1, origin at left hinge bottom
    x0 = -3.2 + 0.03 + ((3.2 - 0.7 - 0.06) / 5)  # 2nd column of bank1
    dw = (3.2 - 0.7 - 0.06) / 5
    hinge = (x0 + 0.012, -2.355, 0.0)
    P = hinge
    L.box("INT_locker_02_panel", (dw - 0.024, 0.02, 1.83),
          (x0 + 0.012 + dw / 2, -2.355, 1.035), "MAT_metal_locker",
          group="INT_locker_02", pivot=P)
    L.box("INT_locker_02_handle", (0.03, 0.03, 0.1),
          (x0 + dw - 0.07, -2.34, 1.05), "MAT_metal_rust",
          group="INT_locker_02", pivot=P)
    L.box("INT_locker_02_vent", (dw - 0.12, 0.012, 0.04),
          (x0 + 0.012 + dw / 2, -2.342, 1.74), "MAT_metal_rust",
          group="INT_locker_02", pivot=P)
    L.props("INT_locker_02", interact="move", prompt="打开柜门", id="locker2",
            open_angle=100.0, open_dir=1)
    # bench
    L.box("S_bench_top", (1.8, 0.45, 0.08), (0.0, -0.4, 0.44),
          "MAT_wood_pale", group="S_bench")
    for i, (xx, yy) in enumerate([(-0.78, -0.55), (0.78, -0.55),
                                  (-0.78, -0.25), (0.78, -0.25)]):
        L.box("S_bench_leg_%d" % i, (0.06, 0.06, 0.4), (xx, yy, 0.2),
              "MAT_wood_pale", group="S_bench")
    L.box("S_bench_stretcher", (1.56, 0.06, 0.05), (0.0, -0.4, 0.18),
          "MAT_wood_dark", group="S_bench")
    L.col("COL_bench", (0.0, -0.4, 0.45), (1.85, 0.5, 0.9))
    L.slab("S_bench_wet", -0.75, 0.85, -0.52, -0.32, 0.481, 0.486,
           "MAT_stain_water")
    # radio on the bench
    L.box("INT_radio_body", (0.3, 0.14, 0.2), (0.45, -0.42, 0.58),
          "MAT_wood_dark", group="INT_radio")
    L.box("INT_radio_dial", (0.08, 0.012, 0.05), (0.36, -0.49, 0.58),
          "MAT_lamp_warm", group="INT_radio")
    L.box("INT_radio_grille", (0.12, 0.012, 0.12), (0.52, -0.49, 0.58),
          "MAT_metal_rust", group="INT_radio")
    L.cyl_between("INT_radio_antenna", (0.56, -0.44, 0.68), (0.64, -0.4, 0.98),
                  0.006, "MAT_metal_rust", segments=6, group="INT_radio")
    L.props("INT_radio", interact="radio", prompt="打开收音机", id="radio")
    # towel on the floor (LIVE, movable)
    L.box("INT_towel", (0.42, 0.6, 0.045), (1.3, 1.5, 0.028),
          "MAT_fabric_red", rot=(0, 0, 0.18), bevel=0.008, group="INT_towel")
    L.props("INT_towel", interact="move", prompt="拿起毛巾", id="towel")
    L.mark("MARK_towel_floor", (1.3, 1.5, 0.0))
    # stools (LIVE)
    stool("INT_stool_01", "INT_stool_01", 0.85, 0.15)
    L.props("INT_stool_01", interact="move", prompt="搬动凳子", id="stool1")
    stool("INT_stool_02", "INT_stool_02", -3.15, -1.0)
    L.props("INT_stool_02", interact="move", prompt="搬动凳子", id="stool2")
    L.mark("MARK_stool_home", (-3.15, -1.0, 0.0))
    L.mark("MARK_stool_away", (0.0, 2.35, 0.0))
    # mannequin in the SE corner (LIVE, whole object rotates)
    P = (3.1, -1.75, 0.0)
    L.cyl("INT_mannequin_base", 0.22, 0.05, (3.1, -1.75, 0.025),
          "MAT_wood_dark", segments=10, group="INT_mannequin", pivot=P)
    L.cyl("INT_mannequin_pole", 0.025, 0.75, (3.1, -1.75, 0.42),
          "MAT_metal_rust", segments=6, group="INT_mannequin", pivot=P)
    L.frustum("INT_mannequin_torso", (0.36, 0.22), (0.42, 0.24), 0.75, 1.42,
              (3.1, -1.75), "MAT_wood_pale", group="INT_mannequin", pivot=P)
    L.cyl("INT_mannequin_neck", 0.04, 0.1, (3.1, -1.75, 1.47),
          "MAT_wood_pale", segments=8, group="INT_mannequin", pivot=P)
    L.sphere("INT_mannequin_head", 0.09, (3.1, -1.75, 1.57), "MAT_wood_pale",
             subdiv=2, group="INT_mannequin", pivot=P)
    L.cyl_between("INT_mannequin_arm_l", (2.94, -1.75, 1.34), (2.86, -1.75, 0.9),
                  0.03, "MAT_wood_pale", segments=6, group="INT_mannequin", pivot=P)
    L.cyl_between("INT_mannequin_arm_r", (3.26, -1.75, 1.34), (3.34, -1.75, 0.9),
                  0.03, "MAT_wood_pale", segments=6, group="INT_mannequin", pivot=P)
    L.props("INT_mannequin", interact="move", prompt="转动模特", id="mannequin")
    L.col("COL_mannequin", (3.1, -1.75, 0.8), (0.55, 0.55, 1.6))
    # old work clothes on the west wall + hooks
    for i, yy in enumerate([-0.5, -0.2, 0.1]):
        L.cyl_between("S_cloth_hook_%d" % i, (-3.59, yy, 2.25), (-3.5, yy, 2.22),
                      0.012, "MAT_metal_rust", segments=6)
    L.box("S_work_clothes", (0.12, 0.55, 0.62), (-3.5, -0.25, 1.9),
          "MAT_fabric_blue", group="S_work_clothes")
    L.box("S_work_clothes_sleeve", (0.1, 0.14, 0.4), (-3.48, -0.6, 1.9),
          "MAT_fabric_blue", group="S_work_clothes")
    L.cyl("S_bucket", 0.16, 0.3, (3.15, -1.0, 0.15), "MAT_metal_rust",
          segments=10)
    L.cyl_between("S_mop_handle", (3.15, -1.0, 0.25), (3.05, -0.9, 1.25),
                  0.018, "MAT_wood_pale", segments=6)
    L.sphere("S_mop_head", 0.1, (3.07, -0.91, 1.28), "MAT_fabric_white",
             subdiv=1, scale=(1.0, 0.7, 1.4))
    L.box("S_newspaper", (0.3, 0.22, 0.006), (-0.5, -0.85, 0.49),
          "MAT_paper", rot=(0, 0, 0.3))
    L.box("S_cigarette", (0.06, 0.008, 0.008), (0.2, -0.2, 0.49),
          "MAT_fabric_white")
    # high window on west wall (night glass, dirty)
    L.slab("S_window_high", -3.6, -3.58, -0.9, 0.9, 2.15, 2.85,
           "MAT_window_night")
    L.slab("S_window_high_frame_l", -3.61, -3.57, -0.95, -0.9, 2.1, 2.9,
           "MAT_wood_dark")
    L.slab("S_window_high_frame_r", -3.61, -3.57, 0.9, 0.95, 2.1, 2.9,
           "MAT_wood_dark")
    L.slab("S_window_high_frame_t", -3.61, -3.57, -0.95, 0.95, 2.85, 2.9,
           "MAT_wood_dark")
    L.slab("S_window_high_frame_b", -3.61, -3.57, -0.95, 0.95, 2.1, 2.15,
           "MAT_wood_dark")
    L.slab("S_window_high_mull", -3.59, -3.57, -0.03, 0.03, 2.15, 2.85,
           "MAT_wood_dark")
    # wall clock (LIVE)
    L.cyl("INT_clock_body", 0.17, 0.05, (-3.56, -2.05, 2.25), "MAT_wood_dark",
          axis="X", segments=12, group="INT_clock")
    L.circle_disc("INT_clock_face", 0.155, (-3.53, -2.05, 2.25),
                  "MAT_clock_face", axis="X", segments=12, front=(1, 0, 0),
                  group="INT_clock")
    L.box("INT_clock_hand_h", (0.008, 0.012, 0.09), (-3.522, -2.05, 2.25),
          "MAT_entity_hair", group="INT_clock")
    L.props("INT_clock", interact="examine", prompt="看钟", id="clock_mirror")
    # light switch near the bath door (LIVE)
    L.slab("INT_switch_plate", 3.57, 3.58, -0.62, -0.46, 1.22, 1.4,
           "MAT_wood_pale", group="INT_switch")
    L.box("INT_switch_btn", (0.012, 0.05, 0.05), (3.56, -0.54, 1.31),
          "MAT_fabric_white", group="INT_switch")
    L.props("INT_switch", interact="switch", prompt="开关灯", id="switch_bath")
    # bath door (east wall) + sign + steam
    L.slab("S_door_bath", 3.56, 3.6, -0.12, 0.9, 0.02, 2.08,
           "MAT_wood_dark", bevel=0.01)
    L.slab("S_door_bath_jamb_l", 3.55, 3.6, 0.9, 0.96, 0.0, 2.16,
           "MAT_wood_dark")
    L.slab("S_door_bath_jamb_r", 3.55, 3.6, -0.18, -0.12, 0.0, 2.16,
           "MAT_wood_dark")
    L.slab("S_door_bath_header", 3.55, 3.6, -0.18, 0.96, 2.08, 2.16,
           "MAT_wood_dark")
    L.cyl("S_door_bath_handle", 0.02, 0.1, (3.54, 0.2, 1.05),
          "MAT_metal_rust", axis="X", segments=8)
    L.slab("S_sign_bath", 3.575, 3.585, 0.18, 0.62, 2.22, 2.88,
           "MAT_sign_bath", front=(-1, 0, 0), uv="unit")
    L.slab("S_steam_01", 3.53, 3.55, -0.1, 0.85, 0.0, 0.5, "MAT_steam")
    L.slab("S_steam_02", 3.52, 3.54, 0.1, 0.6, 0.0, 0.25, "MAT_steam")
    # radiator on east wall + pipes
    for i in range(6):
        L.box("S_radiator_fin_%d" % i, (0.1, 0.06, 0.55),
              (3.52, -2.2 + i * 0.12, 0.35), "MAT_metal_rust")
    L.slab("S_radiator_top", 3.45, 3.56, -2.25, -1.6, 0.6, 0.66,
           "MAT_metal_rust")
    L.col("COL_radiator", (3.5, -1.93, 0.35), (0.2, 0.75, 0.7))
    L.col("COL_bath_door", (3.58, 0.4, 1.05), (0.08, 1.1, 2.1))
    # wall COLs
    L.col_slab("COL_wall_north", -3.75, 3.75, 2.8, 2.95)
    L.col_slab("COL_wall_south", -3.75, 3.75, -2.95, -2.8)
    L.col_slab("COL_wall_west", -3.75, -3.6, -2.95, 2.95)
    L.col_slab("COL_wall_east", 3.6, 3.75, -2.95, 2.95)


def build_entity_lights():
    hex_humanoid("ENTITY_reflection", "ENTITY_reflection", 0.0, 1.95)
    L.props("ENTITY_reflection", hidden=True)
    L.spawn("SPAWN_mirror", (0.0, -1.6, 0.0))
    L.look("LOOK_mirror", (0.0, 2.5, 1.5))
    L.light("LIGHT_tube_01", (-1.2, 0.0, 2.78), power=25,
            color="#d7f0e4", radius=8, flicker=0.08)
    L.light("LIGHT_tube_02", (1.2, 0.0, 2.78), power=25,
            color="#d7f0e4", radius=8, flicker=0.0)
    L.light("LIGHT_bench", (0.0, -0.5, 1.9), power=15, color="#ffcf9a",
            radius=4, flicker=0.0)
    L.light("LIGHT_bath", (3.25, 0.4, 2.0), power=10, color="#ffb87a",
            radius=3, flicker=0.05)
    L.light("LIGHT_window", (-3.1, 0.0, 2.6), power=8, color="#7e9cc8",
            radius=6, flicker=0.0)


def main():
    L.reset("mirror")
    build_room()
    build_mirror_wall()
    build_lockers_props()
    build_entity_lights()
    L.finalize(OUT)
    print("MIRROR BUILD DONE")


if __name__ == "__main__":
    main()
