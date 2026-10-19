"""build_door.py -- 《门后》 corridor + 503 apartment, export door.glb.

headless:  blender.exe -b --factory-startup --python build_door.py
"""
import sys
import os
import math
from mathutils import Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_build as L

OUT = L.MODELS + r"\door.glb"


# ---------------------------------------------------------------------------
# wall helper: builds wall segments around openings; auto COL for floor-level parts
# ---------------------------------------------------------------------------
def wall_run(prefix, axis, f0, f1, a0, a1, z0, z1, mat, openings=(),
             group="S_corridor_shell", col_prefix=None, uv_scale=2.0):
    segs = []
    cur = a0
    z_lo, z_hi = z0, z1
    for (oa, ob, oz0, oz1) in sorted(openings):
        oa = max(a0, oa)
        ob = min(a1, ob)
        if oa > cur + 1e-6:
            segs.append((cur, oa, z_lo, z_hi))
        if oz0 > z_lo + 1e-6:
            segs.append((oa, ob, z_lo, oz0))
        if oz1 < z_hi - 1e-6:
            segs.append((oa, ob, oz1, z_hi))
        cur = max(cur, ob)
    if cur < a1 - 1e-6:
        segs.append((cur, a1, z_lo, z_hi))
    for i, (s, e, zz0, zz1) in enumerate(segs):
        nm = "S_%s_%02d" % (prefix, i)
        if axis == "y":
            L.slab(nm, f0, f1, s, e, zz0, zz1, mat, group=group,
                   uv_scale=uv_scale)
        else:
            L.slab(nm, s, e, f0, f1, zz0, zz1, mat, group=group,
                   uv_scale=uv_scale)
        if col_prefix is not None and abs(zz0 - z_lo) < 1e-6:
            cn = "COL_%s_%02d" % (col_prefix, i)
            if axis == "y":
                L.col_slab(cn, f0 - 0.02, f1 + 0.02, s, e, 0, 2.7)
            else:
                L.col_slab(cn, s, e, f0 - 0.02, f1 + 0.02, 0, 2.7)
    return segs


def baseboard(prefix, axis, f0, f1, a0, a1, mat="MAT_wood_dark", h=0.1,
              group="S_corridor_shell"):
    if axis == "y":
        L.slab("S_%s_bb" % prefix, f0, f1, a0, a1, 0.0, h, mat, group=group)
    else:
        L.slab("S_%s_bb" % prefix, a0, a1, f0, f1, 0.0, h, mat, group=group)


# ---------------------------------------------------------------------------
# corridor
# ---------------------------------------------------------------------------
def build_corridor():
    G = "S_corridor_shell"
    # floor / ceiling
    L.slab("S_corr_floor", -1.1, 1.1, -18.0, 0.0, -0.12, 0.0, "MAT_tile_floor", group=G)
    L.slab("S_corr_ceil", -1.1, 1.1, -18.0, 0.0, 2.7, 2.82, "MAT_paint_ceiling", group=G)
    # west wall + baseboard + dado
    wall_run("corr_w", "y", -1.25, -1.1, -18.0, 0.0, 0.0, 2.7,
             "MAT_wallpaper_dark", group=G, col_prefix="corr_w")
    L.slab("S_corr_w_dado", -1.1, -1.075, -18.0, 0.0, 0.0, 1.05,
           "MAT_plaster", group=G)
    baseboard("corr_w", "y", -1.1, -1.06, -18.0, 0.0)
    L.slab("S_corr_w_rail", -1.1, -1.07, -18.0, 0.0, 1.02, 1.08,
           "MAT_wood_dark", group=G)
    # east wall: 503 door opening + window at y -14..-13.4
    wall_run("corr_e", "y", 1.1, 1.25, -18.0, 0.0, 0.0, 2.7,
             "MAT_wallpaper_dark",
             openings=[(-5.85, -4.85, 0.0, 2.05),
                       (-14.6, -13.4, 1.5, 2.3)],
             group=G, col_prefix="corr_e")
    L.slab("S_corr_e_dado", 1.075, 1.1, -18.0, 0.0, 0.0, 1.05,
           "MAT_plaster", group=G)
    baseboard("corr_e", "y", 1.06, 1.1, -18.0, 0.0)
    L.slab("S_corr_e_rail", 1.07, 1.1, -18.0, 0.0, 1.02, 1.08,
           "MAT_wood_dark", group=G)
    # north / south end walls
    wall_run("corr_n", "x", 0.0, 0.15, -1.25, 1.25, 0.0, 2.7,
             "MAT_wallpaper_dark", group=G, col_prefix="corr_n")
    wall_run("corr_s", "x", -18.15, -18.0, -1.25, 1.25, 0.0, 2.7,
             "MAT_wallpaper_dark", group=G, col_prefix="corr_s")
    # floor grout lines + damaged tiles
    for i, yy in enumerate([-1.6 * k for k in range(1, 12)]):
        L.slab("S_corr_grout_%02d" % i, -1.1, 1.1, yy - 0.006, yy + 0.006,
               0.0, 0.006, "MAT_concrete", group=G)
    for i, (x0, x1, y0, y1) in enumerate([
            (-0.9, -0.35, -3.7, -3.15), (0.25, 0.95, -7.9, -7.3),
            (-0.8, -0.1, -12.9, -12.2), (0.1, 0.7, -16.8, -16.2)]):
        L.slab("S_corr_broken_%02d" % i, x0, x1, y0, y1, 0.0, 0.008,
               "MAT_concrete", group=G)
    # ceiling cable/pipe: two runs + drip pipe on west wall
    L.cyl_between("S_corr_pipe_01", (-0.85, 0.0, 2.52), (-0.85, -18.0, 2.52),
                  0.035, "MAT_metal_rust", segments=8, group=G)
    L.cyl_between("S_corr_pipe_02", (0.9, 0.0, 2.58), (0.9, -18.0, 2.58),
                  0.025, "MAT_metal_rust", segments=8, group=G)
    L.cyl_between("S_corr_drain", (-1.02, -17.9, 2.7), (-1.02, -17.9, 0.15),
                  0.04, "MAT_metal_rust", segments=8, group=G)
    # static stains / small ads on corridor walls
    L.slab("S_corr_stain_a", -1.101, -1.094, -12.3, -11.7, 1.2, 1.9,
           "MAT_stain_water", group=G)
    L.slab("S_corr_stain_b", 1.094, 1.101, -8.3, -7.6, 0.6, 1.7,
           "MAT_stain_mold", group=G)
    L.slab("S_corr_stain_c", -0.9, -0.1, -16.1, -15.4, 0.0, 0.008,
           "MAT_stain_water", group=G)
    for i, (yy, zz, sz) in enumerate([(-2.5, 1.55, 1), (-7.2, 1.4, 2),
                                      (-11.4, 1.7, 3), (-13.0, 1.2, 4)]):
        L.slab("S_corr_ad_%02d" % i, -1.15, -1.095, yy - 0.12 * sz, yy + 0.12 * sz,
               zz, zz + 0.18, "MAT_paper", front=(1, 0, 0), uv="unit", group=G)
    # notice board (west wall)
    L.slab("S_notice_board", -1.16, -1.095, -11.7, -10.3, 1.28, 2.22,
           "MAT_wood_dark", group=G)
    L.slab("S_notice_paper_1", -1.10, -1.092, -11.55, -11.1, 1.4, 1.95,
           "MAT_paper", front=(1, 0, 0), uv="unit", group=G)
    L.slab("S_notice_paper_2", -1.10, -1.092, -11.0, -10.45, 1.55, 2.05,
           "MAT_paper", front=(1, 0, 0), uv="unit", group=G)
    # fire extinguisher (west wall, y -9.6)
    L.cyl("S_extinguisher_body", 0.085, 0.52, (-0.9, -9.6, 0.32),
          "MAT_red_cloth", segments=10, group=G)
    L.cyl("S_extinguisher_top", 0.035, 0.10, (-0.9, -9.6, 0.63),
          "MAT_metal_rust", segments=8, group=G)
    L.cyl_between("S_extinguisher_hose", (-0.9, -9.6, 0.6), (-0.87, -9.63, 0.18),
                  0.012, "MAT_metal_locker", segments=6, group=G)
    # electrical meter box (west wall) + distribution box (east wall)
    L.slab("S_meter_box", -1.17, -1.09, -15.75, -15.1, 1.35, 1.85,
           "MAT_metal_locker", group=G)
    L.slab("S_meter_glass", -1.09, -1.085, -15.68, -15.2, 1.45, 1.78,
           "MAT_glass_dirty", group=G)
    L.slab("S_dist_box", 1.09, 1.17, -12.15, -11.55, 1.4, 1.9,
           "MAT_metal_locker", group=G)
    # mailboxes (east wall y -1.9..-1.1)
    L.slab("S_mail_body", 1.09, 1.25, -1.95, -1.05, 1.05, 1.85,
           "MAT_metal_locker", group=G)
    for i in range(8):
        col = i % 4
        row = i // 4
        y0 = -1.9 + col * 0.205
        z0 = 1.12 + row * 0.34
        L.slab("S_mail_door_%02d" % i, 1.085, 1.092, y0, y0 + 0.18, z0, z0 + 0.30,
               "MAT_metal_locker", group=G)
        L.slab("S_mail_slot_%02d" % i, 1.084, 1.086, y0 + 0.03, y0 + 0.15,
               z0 + 0.20, z0 + 0.23, "MAT_metal_rust", group=G)
    # trash bags near south end
    L.sphere("S_trash_01", 0.28, (-0.6, -17.25, 0.22), "MAT_fabric_blue",
             subdiv=1, scale=(1.0, 0.9, 0.85), group=G)
    L.sphere("S_trash_02", 0.22, (-0.15, -17.5, 0.18), "MAT_plaster",
             subdiv=1, scale=(1.0, 1.0, 0.8), group=G)
    # corridor light fixtures (5) + one extra dead housing visual
    for i, yy in enumerate([-1.8, -5.4, -9.0, -12.6, -16.2]):
        L.box("S_corr_light_%02d" % i, (1.18, 0.2, 0.07), (0, yy, 2.63),
              "MAT_metal_rust", group=G)
        L.box("S_corr_tube_%02d" % i, (1.06, 0.09, 0.045), (0, yy, 2.575),
              "MAT_lamp_tube", group=G)
    # pipe brackets
    for i, yy in enumerate([-2.0, -6.0, -10.0, -14.0]):
        L.box("S_corr_bracket_%02d" % i, (0.11, 0.03, 0.06), (-0.85, yy, 2.52),
              "MAT_metal_rust", group=G)
    # window at east wall y -14.6..-13.4 (night city)
    L.slab("S_corr_win_glass", 1.19, 1.21, -14.55, -13.45, 1.52, 2.28,
           "MAT_window_night", group=G)
    L.slab("S_corr_win_sill", 1.05, 1.3, -14.65, -13.35, 1.46, 1.52,
           "MAT_concrete", group=G)
    L.slab("S_corr_win_top", 1.08, 1.27, -14.62, -13.38, 2.28, 2.34,
           "MAT_concrete", group=G)
    L.slab("S_corr_win_mull", 1.17, 1.23, -14.05, -13.97, 1.5, 2.3,
           "MAT_metal_rust", group=G)
    for i in range(3):
        L.cyl_between("S_corr_win_bar_%d" % i, (1.16, -14.5 + i * 0.35, 1.5),
                      (1.16, -14.5 + i * 0.35, 2.3), 0.012,
                      "MAT_metal_rust", segments=6, group=G)


# ---------------------------------------------------------------------------
# apartment shell
# ---------------------------------------------------------------------------
def build_apartment():
    G = "S_apartment_shell"
    # floors (top at z=0)
    L.slab("S_floor_entry", 1.1, 2.6, -6.3, -4.3, -0.1, 0.0, "MAT_concrete", group=G)
    L.slab("S_floor_living", 2.6, 6.6, -7.8, -2.9, -0.1, 0.0, "MAT_wood_floor", group=G)
    L.slab("S_floor_kitchen", 2.6, 4.2, -9.6, -7.8, -0.1, 0.0, "MAT_tile_floor", group=G)
    L.slab("S_floor_bedroom", 6.72, 9.4, -7.8, -3.4, -0.1, 0.0, "MAT_wood_floor", group=G)
    # one ceiling slab over the flat
    L.slab("S_flat_ceiling", 1.1, 9.52, -9.72, -2.9, 2.7, 2.82,
           "MAT_paint_ceiling", group=G)
    # entry (玄关) walls
    wall_run("entry_n", "x", -4.3, -4.18, 1.1, 2.6, 0.0, 2.7,
             "MAT_wallpaper", group=G, col_prefix="entry_n")
    wall_run("entry_s", "x", -6.42, -6.3, 1.1, 2.6, 0.0, 2.7,
             "MAT_wallpaper", group=G, col_prefix="entry_s")
    # x = 2.6 wall: open between entry and living (y -6.3..-4.3), solid elsewhere
    wall_run("liv_w", "y", 2.6, 2.72, -7.8, -2.9, 0.0, 2.7,
             "MAT_wallpaper",
             openings=[(-6.3, -4.3, 0.0, 2.1)],
             group=G, col_prefix="liv_w")
    L.slab("S_entry_header", 2.48, 2.72, -6.3, -4.3, 2.1, 2.7,
           "MAT_wallpaper", group=G)
    # kitchen walls
    wall_run("kit_e", "y", 4.2, 4.32, -9.6, -7.8, 0.0, 2.7,
             "MAT_plaster", group=G, col_prefix="kit_e")
    wall_run("kit_s", "x", -9.72, -9.6, 2.6, 4.2, 0.0, 2.7,
             "MAT_plaster", group=G, col_prefix="kit_s")
    wall_run("kit_w", "y", 2.48, 2.6, -9.6, -7.8, 0.0, 2.7,
             "MAT_plaster", group=G, col_prefix="kit_w")
    L.slab("S_kit_header", 2.6, 4.2, -7.92, -7.8, 2.1, 2.7,
           "MAT_plaster", group=G)
    # living outer north wall (y=-2.9) and east wall / bedroom west wall
    wall_run("liv_n", "x", -3.02, -2.9, 2.6, 6.6, 0.0, 2.7,
             "MAT_wallpaper", group=G, col_prefix="liv_n")
    wall_run("bed_w", "y", 6.6, 6.72, -7.8, -2.9, 0.0, 2.7,
             "MAT_wallpaper",
             openings=[(-6.1, -5.15, 0.0, 2.05)],
             group=G, col_prefix="bed_w")
    # bedroom outer walls
    wall_run("bed_n", "x", -3.52, -3.4, 6.72, 9.4, 0.0, 2.7,
             "MAT_wallpaper", group=G, col_prefix="bed_n")
    wall_run("bed_e", "y", 9.4, 9.52, -7.8, -3.4, 0.0, 2.7,
             "MAT_wallpaper", group=G, col_prefix="bed_e")
    # south wall with two windows (living 4.7..6.1, bedroom 7.4..8.7)
    wall_run("flat_s", "x", -7.92, -7.8, 4.2, 9.4, 0.0, 2.7,
             "MAT_wallpaper",
             openings=[(4.7, 6.1, 0.9, 2.1), (7.4, 8.7, 0.9, 2.1)],
             group=G, col_prefix="flat_s")
    # baseboards inside flat
    for nm, ax, f0, f1, a0, a1 in [
            ("entry_n_bb", "x", -4.3, -4.27, 1.1, 2.6),
            ("liv_n_bb", "x", -2.9, -2.87, 2.6, 6.6),
            ("bed_n_bb", "x", -3.4, -3.37, 6.72, 9.4),
            ("liv_e_bb", "y", 6.57, 6.6, -7.8, -2.9),
            ("bed_e_bb", "y", 9.37, 9.4, -7.8, -3.4),
            ("bed_s_bb", "x", -7.8, -7.77, 6.72, 9.4)]:
        baseboard(nm, ax, f0, f1, a0, a1, group=G)
    # kitchen tiles (lower wall) + living wainscot
    L.slab("S_kit_tile_s", 2.6, 4.2, -9.6, -9.57, 0.0, 1.5, "MAT_tile_white", group=G)
    L.slab("S_kit_tile_e", 4.17, 4.2, -9.6, -7.8, 0.0, 1.5, "MAT_tile_white", group=G)
    # thresholds + floor patches under openings
    L.slab("S_thr_503", 1.1, 1.25, -5.85, -4.85, 0.0, 0.025, "MAT_concrete", group=G)
    L.slab("S_thr_bed", 6.6, 6.72, -6.1, -5.15, 0.0, 0.025, "MAT_wood_dark", group=G)
    L.slab("S_floor_bedgap", 6.6, 6.72, -6.1, -5.15, -0.1, 0.0, "MAT_wood_floor", group=G)
    L.slab("S_floor_entrygap", 2.6, 2.72, -6.3, -4.3, -0.1, 0.0, "MAT_concrete", group=G)
    # living wainscot along the two solid parts of the west wall
    L.slab("S_liv_dado_a", 2.72, 2.75, -7.8, -6.3, 0.0, 1.05, "MAT_wallpaper_dark", group=G)
    L.slab("S_liv_dado_b", 2.72, 2.75, -4.3, -2.9, 0.0, 1.05, "MAT_wallpaper_dark", group=G)
    # living ceiling lamp + entry lamp (decorative fixture, actual light = LIGHT_*)
    L.box("S_lamp_living", (0.42, 0.42, 0.09), (5.0, -5.0, 2.62),
          "MAT_metal_rust", group=G)
    L.cyl("S_lamp_living_shade", 0.2, 0.16, (5.0, -5.0, 2.51),
          "MAT_lamp_warm", segments=12, radius2=0.06, group=G)
    L.box("S_lamp_entry", (0.26, 0.26, 0.06), (1.85, -5.3, 2.63),
          "MAT_metal_rust", group=G)
    L.sphere("S_lamp_entry_shade", 0.11, (1.85, -5.3, 2.52), "MAT_lamp_warm",
             subdiv=1, group=G)
    L.box("S_lamp_kitchen", (0.3, 0.3, 0.06), (3.4, -8.7, 2.63),
          "MAT_metal_rust", group=G)
    L.cyl("S_lamp_kitchen_shade", 0.14, 0.12, (3.4, -8.7, 2.54),
          "MAT_lamp_warm", segments=10, radius2=0.05, group=G)
    # living / bedroom windows
    for nm, x0, x1 in [("living", 4.7, 6.1), ("bedroom", 7.4, 8.7)]:
        y = -7.8
        L.slab("S_win_%s_glass" % nm, x0, x1, y - 0.015, y + 0.015, 0.92, 2.08,
               "MAT_window_night", group=G)
        L.slab("S_win_%s_sill" % nm, x0 - 0.06, x1 + 0.06, y - 0.12, y + 0.09,
               0.84, 0.92, "MAT_concrete", group=G)
        L.slab("S_win_%s_frame_l" % nm, x0, x0 + 0.05, y - 0.04, y + 0.05, 0.9, 2.1,
               "MAT_wood_dark", group=G)
        L.slab("S_win_%s_frame_r" % nm, x1 - 0.05, x1, y - 0.04, y + 0.05, 0.9, 2.1,
               "MAT_wood_dark", group=G)
        L.slab("S_win_%s_frame_t" % nm, x0, x1, y - 0.04, y + 0.05, 2.05, 2.1,
               "MAT_wood_dark", group=G)
        L.slab("S_win_%s_mull" % nm, (x0 + x1) / 2 - 0.025, (x0 + x1) / 2 + 0.025,
               y - 0.03, y + 0.04, 0.9, 2.1, "MAT_wood_dark", group=G)
        # curtains (two panels, wavy)
        L.grid_panel("S_curtain_%s_L" % nm, x0 - 0.15, (x0 + x1) / 2 - 0.05,
                     y + 0.12, 0.12, 2.35, "MAT_curtain", folds=4, amp=0.04,
                     group=G)
        L.grid_panel("S_curtain_%s_R" % nm, (x0 + x1) / 2 + 0.05, x1 + 0.15,
                     y + 0.12, 0.12, 2.35, "MAT_curtain", folds=4, amp=0.04,
                     group=G)
        L.cyl_between("S_curtain_rod_%s" % nm, (x0 - 0.2, y + 0.12, 2.38),
                      (x1 + 0.2, y + 0.12, 2.38), 0.014, "MAT_metal_rust",
                      segments=6, group=G)
    # bedroom ceiling fixture
    L.box("S_lamp_bedroom", (0.3, 0.3, 0.06), (8.0, -5.3, 2.63),
          "MAT_metal_rust", group=G)
    L.cyl("S_lamp_bedroom_shade", 0.15, 0.12, (8.0, -5.3, 2.54),
          "MAT_lamp_warm", segments=10, radius2=0.05, group=G)
    # wall clock support not needed (INT_clock itself)


# ---------------------------------------------------------------------------
# doors
# ---------------------------------------------------------------------------
def door_leaf(group, name_prefix, hinge, width, thick, dir_y, faces,
              mat="MAT_wood_door", bevel=0.008, panel_mat="MAT_wood_dark"):
    """Door leaf hinged at `hinge` (x,y,z=0), extending dir_y*width along Y.
    faces: list of face normals (+1 / -1 along X) that get raised panels.
    Origin of the leaf object = hinge bottom."""
    hx, hy, _ = hinge
    P = (hx, hy, 0.0)
    cx = hx
    # main slab
    L.box(name_prefix + "_slab", (thick, width, 2.0),
          (cx, hy + dir_y * width / 2, 1.01), mat,
          bevel=bevel, group=group, pivot=P)
    # panels on requested faces
    for face in faces:
        px = hx + face * (thick / 2 + 0.006)
        for k, (z0, z1) in enumerate([(0.22, 0.92), (1.08, 1.85)]):
            L.box(name_prefix + "_panel_%s_%d" % ("p" if face > 0 else "n", k),
                  (0.012, width * 0.66, z1 - z0),
                  (px, hy + dir_y * width / 2, (z0 + z1) / 2),
                  panel_mat, group=group, pivot=P)
    # handle on corridor side
    hxs = hx - (thick / 2 + 0.035) if faces and faces[0] < 0 else hx + (thick / 2 + 0.035)
    L.cyl(name_prefix + "_handle", 0.014, 0.1,
          (hxs, hy + dir_y * (width - 0.12), 1.02), "MAT_metal_locker",
          axis="X", segments=8, group=group, pivot=P)
    L.sphere(name_prefix + "_handle_base", 0.025,
             (hxs - (0.05 if faces and faces[0] < 0 else -0.05),
              hy + dir_y * (width - 0.12), 1.02),
             "MAT_metal_locker", subdiv=1, group=group, pivot=P)
    return P


def build_doors():
    # --- 503: real opening in east wall x=1.1..1.25, opening y -5.85..-4.85
    # frame
    L.slab("S_door503_jamb_s", 1.08, 1.27, -5.9, -5.85, 0.0, 2.12,
           "MAT_wood_dark", group="S_corridor_shell")
    L.slab("S_door503_jamb_n", 1.08, 1.27, -4.85, -4.80, 0.0, 2.12,
           "MAT_wood_dark", group="S_corridor_shell")
    L.slab("S_door503_header", 1.08, 1.27, -5.9, -4.80, 2.05, 2.16,
           "MAT_wood_dark", group="S_corridor_shell")
    door_leaf("INT_door_503", "INT_door_503", (1.175, -5.85, 0.0), 0.96,
              0.045, 1, [-1, 1])
    L.props("INT_door_503", interact="door", prompt="开门", id="door503",
            open_angle=95.0, open_dir=1, locked=False)
    L.slab("S_num_503", 1.094, 1.100, -4.62, -4.44, 1.62, 1.74,
           "MAT_door_number_503", front=(-1, 0, 0), uv="unit",
           group="S_corridor_shell")
    # --- bedroom door: real opening in x=6.6..6.72 wall, y -6.1..-5.15
    L.slab("S_doorbed_jamb_s", 6.57, 6.75, -6.15, -6.1, 0.0, 2.12,
           "MAT_wood_dark", group="S_apartment_shell")
    L.slab("S_doorbed_jamb_n", 6.57, 6.75, -5.15, -5.10, 0.0, 2.12,
           "MAT_wood_dark", group="S_apartment_shell")
    L.slab("S_doorbed_header", 6.57, 6.75, -6.15, -5.10, 2.05, 2.16,
           "MAT_wood_dark", group="S_apartment_shell")
    door_leaf("INT_door_bedroom", "INT_door_bedroom", (6.66, -6.1, 0.0), 0.95,
              0.045, 1, [-1, 1])
    L.props("INT_door_bedroom", interact="door", prompt="开门（锁着）",
            id="door_bed", open_angle=95.0, open_dir=-1, locked=True)
    # --- fake doors on west wall: 501 (y=-3.2) + 502 (y=-8.4)
    for num, hy, yy in [("501", -3.2, -3.2), ("502", -8.4, -8.4)]:
        L.slab("S_door%s_jamb_a" % num, -1.16, -1.08, yy - 0.52, yy - 0.47,
               0.0, 2.12, "MAT_wood_dark", group="S_corridor_shell")
        L.slab("S_door%s_jamb_b" % num, -1.16, -1.08, yy + 0.47, yy + 0.52,
               0.0, 2.12, "MAT_wood_dark", group="S_corridor_shell")
        L.slab("S_door%s_header" % num, -1.16, -1.08, yy - 0.52, yy + 0.52,
               2.05, 2.16, "MAT_wood_dark", group="S_corridor_shell")
        door_leaf("INT_door_" + num, "INT_door_" + num, (-1.115, yy - 0.47, 0.0),
                  0.94, 0.045, 1, [1])
        L.props("INT_door_" + num, interact="door", prompt="开门（锁着）",
                id="door" + num, open_angle=95.0, open_dir=1, locked=True)
        L.slab("S_num_%s" % num, -1.100, -1.094, yy + 0.05, yy + 0.23,
               1.62, 1.74, "MAT_door_number_" + num, front=(1, 0, 0), uv="unit",
               group="S_corridor_shell")
    # --- 504 fake door on east wall y=-10.2
    L.slab("S_door504_jamb_a", 1.08, 1.16, -10.72, -10.67, 0.0, 2.12,
           "MAT_wood_dark", group="S_corridor_shell")
    L.slab("S_door504_jamb_b", 1.08, 1.16, -9.73, -9.68, 0.0, 2.12,
           "MAT_wood_dark", group="S_corridor_shell")
    L.slab("S_door504_header", 1.08, 1.16, -10.72, -9.68, 2.05, 2.16,
           "MAT_wood_dark", group="S_corridor_shell")
    door_leaf("INT_door_504", "INT_door_504", (1.115, -10.67, 0.0), 0.94,
              0.045, 1, [-1])
    L.props("INT_door_504", interact="door", prompt="开门（锁着）",
            id="door504", open_angle=95.0, open_dir=-1, locked=True)
    L.slab("S_num_504", 1.094, 1.100, -10.62, -10.44, 1.62, 1.74,
           "MAT_door_number_504", front=(-1, 0, 0), uv="unit",
           group="S_corridor_shell")
    # --- fire door (north end, y=0)
    L.slab("S_firedoor_frame", -1.0, 1.0, -0.06, 0.0, 0.0, 2.3,
           "MAT_metal_rust", group="S_corridor_shell")
    L.slab("S_fire_leaf_l", -0.94, -0.02, -0.09, -0.02, 0.02, 2.22,
           "MAT_metal_locker", bevel=0.01, group="INT_fire_door", pivot=(0, 0, 0))
    L.slab("S_fire_leaf_r", 0.02, 0.94, -0.09, -0.02, 0.02, 2.22,
           "MAT_metal_locker", bevel=0.01, group="INT_fire_door", pivot=(0, 0, 0))
    L.cyl_between("S_fire_bar", (-0.7, -0.11, 1.0), (0.7, -0.11, 1.0), 0.018,
                  "MAT_metal_rust", segments=8, group="INT_fire_door")
    L.slab("S_exit_sign", -0.18, 0.18, -0.05, -0.01, 2.36, 2.44,
           "MAT_lamp_tube", group="S_corridor_shell")
    # --- elevator (south end y=-18)
    L.slab("S_elev_frame", -0.9, 0.9, -18.0, -17.86, 0.0, 2.3,
           "MAT_metal_rust", group="S_corridor_shell")
    L.slab("S_elev_door_l", -0.86, -0.01, -18.05, -17.9, 0.02, 2.18,
           "MAT_metal_locker", group="S_corridor_shell")
    L.slab("S_elev_door_r", 0.01, 0.86, -18.05, -17.9, 0.02, 2.18,
           "MAT_metal_locker", group="S_corridor_shell")
    L.slab("S_elev_seam", -0.012, 0.012, -18.07, -17.88, 0.02, 2.18,
           "MAT_metal_rust", group="S_corridor_shell")
    L.slab("S_elev_indicator", -0.15, 0.15, -18.06, -17.87, 2.32, 2.46,
           "MAT_lamp_warm", group="S_corridor_shell")
    L.slab("S_elev_button_panel", 0.78, 0.94, -18.02, -17.9, 1.0, 1.24,
           "MAT_metal_locker", group="INT_elevator_button")
    L.cyl("S_elev_btn_up", 0.026, 0.02, (0.86, -17.88, 1.16), "MAT_lamp_warm",
          axis="Y", segments=10, group="INT_elevator_button")
    L.cyl("S_elev_btn_down", 0.026, 0.02, (0.86, -17.88, 1.07), "MAT_metal_rust",
          axis="Y", segments=10, group="INT_elevator_button")
    L.props("INT_elevator_button", interact="examine", prompt="按电梯",
            id="elevator_btn")
    L.props("INT_fire_door", interact="examine", prompt="推防火门",
            id="firedoor")


# ---------------------------------------------------------------------------
# furniture: 玄关 / 客厅 / 厨房 / 卧室
# ---------------------------------------------------------------------------
def chair(group, prefix, x, y, facing_deg, mat="MAT_wood_dark"):
    rot = math.radians(facing_deg)
    c, s = math.cos(rot), math.sin(rot)

    def P(lx, ly, lz):
        return (x + lx * c - ly * s, y + lx * s + ly * c, lz)

    L.box(prefix + "_seat", (0.42, 0.42, 0.05), P(0, 0, 0.45), mat,
          rot=(0, 0, rot), group=group)
    L.box(prefix + "_back", (0.42, 0.05, 0.42), P(0, 0.2, 0.7), mat,
          rot=(0, 0, rot), group=group)
    for i, (lx, ly) in enumerate([(-0.17, -0.17), (0.17, -0.17),
                                  (-0.17, 0.17), (0.17, 0.17)]):
        L.box(prefix + "_leg_%d" % i, (0.04, 0.04, 0.45), P(lx, ly, 0.225),
              mat, group=group)
    L.box(prefix + "_slat", (0.36, 0.02, 0.06), P(0, 0.2, 0.82), mat,
          rot=(0, 0, rot), group=group)


def build_furniture():
    G = "S_furniture"
    # ---------------- 玄关
    L.box("S_shoe_cabinet_body", (1.18, 0.32, 0.9), (1.86, -6.1, 0.45),
          "MAT_wood_pale", group="S_shoe_cabinet")
    L.box("S_shoe_cabinet_top", (1.24, 0.36, 0.05), (1.86, -6.1, 0.925),
          "MAT_wood_dark", group="S_shoe_cabinet")
    for i, xx in enumerate([1.56, 2.16]):
        L.box("S_shoe_cabinet_door_%d" % i, (0.55, 0.02, 0.78),
              (xx, -5.93, 0.47), "MAT_wood_pale", group="S_shoe_cabinet")
        L.cyl("S_shoe_cabinet_knob_%d" % i, 0.018, 0.03,
              (xx + (0.2 if i == 0 else -0.2), -5.91, 0.5),
              "MAT_metal_rust", axis="Y", segments=6, group="S_shoe_cabinet")
    L.col("COL_shoe_cabinet", (1.86, -6.1, 0.5), (1.3, 0.4, 1.0))
    # flashlight on cabinet
    L.cyl("INT_flashlight_body", 0.038, 0.24, (1.45, -6.08, 0.99),
          "MAT_metal_locker", axis="Y", segments=8,
          group="INT_flashlight")
    L.cyl("INT_flashlight_head", 0.055, 0.07, (1.45, -5.95, 0.99),
          "MAT_metal_locker", axis="Y", segments=8, radius2=0.048,
          group="INT_flashlight")
    L.cyl("INT_flashlight_lens", 0.05, 0.012, (1.45, -5.913, 0.99),
          "MAT_lamp_warm", axis="Y", segments=8, group="INT_flashlight")
    L.props("INT_flashlight", interact="pickup", prompt="捡起手电筒", id="flashlight")
    # coat hooks + old coat on north wall of entry
    for i, xx in enumerate([1.35, 1.65, 1.95, 2.25]):
        L.cyl_between("S_hook_%d" % i, (xx, -4.3, 1.62), (xx, -4.42, 1.6),
                      0.012, "MAT_metal_rust", segments=6, group=G)
    L.box("S_coat_body", (0.42, 0.1, 0.62), (1.68, -4.4, 1.2),
          "MAT_fabric_blue", group=G)
    L.box("S_coat_sleeve", (0.1, 0.08, 0.42), (1.45, -4.4, 1.16),
          "MAT_fabric_blue", group=G)
    # slippers
    for i, xx in enumerate([1.28, 1.45]):
        L.box("S_slipper_%d" % i, (0.1, 0.24, 0.035), (xx, -5.55, 0.018),
              "MAT_fabric_blue", group=G)
    # umbrella
    L.cyl("S_umbrella", 0.035, 0.75, (1.2, -6.22, 0.4), "MAT_fabric_red",
          segments=8, bevel=0.005, group=G)
    # full length mirror on entry north wall
    L.slab("S_hall_mirror_frame", 1.98, 2.42, -4.30, -4.26, 0.45, 1.95,
           "MAT_wood_dark", group=G)
    L.slab("S_hall_mirror_glass", 2.02, 2.38, -4.263, -4.256, 0.5, 1.9,
           "MAT_mirror_grime", group=G)
    # ---------------- living: sofa along west wall
    L.box("S_sofa_base", (0.78, 2.1, 0.32), (3.0, -5.45, 0.18),
          "MAT_fabric_blue", group=G)
    L.box("S_sofa_back", (0.2, 2.1, 0.72), (2.72, -5.45, 0.52),
          "MAT_fabric_blue", group=G)
    for i, yy in enumerate([-6.38, -4.52]):
        L.box("S_sofa_arm_%d" % i, (0.72, 0.18, 0.5), (3.0, yy, 0.35),
              "MAT_fabric_blue", group=G)
    for i, yy in enumerate([-6.05, -5.45, -4.85]):
        L.box("S_sofa_cushion_%d" % i, (0.62, 0.52, 0.12), (3.06, yy, 0.4),
              "MAT_fabric_white", group=G)
    L.col("COL_sofa", (3.0, -5.45, 0.4), (0.9, 2.2, 0.9))
    # coffee table
    L.box("S_coffee_top", (1.0, 0.62, 0.06), (4.45, -5.45, 0.42),
          "MAT_wood_dark", group=G)
    for i, (xx, yy) in enumerate([(4.02, -5.7), (4.88, -5.7),
                                  (4.02, -5.2), (4.88, -5.2)]):
        L.box("S_coffee_leg_%d" % i, (0.05, 0.05, 0.42), (xx, yy, 0.21),
              "MAT_wood_dark", group=G)
    L.col("COL_coffee_table", (4.45, -5.45, 0.3), (1.05, 0.67, 0.6))
    # TV cabinet + CRT (north-east part of living)
    L.box("S_tv_cabinet", (0.38, 1.5, 0.5), (6.38, -3.65, 0.25),
          "MAT_wood_dark", group=G)
    for i, yy in enumerate([-4.1, -3.65, -3.2]):
        L.box("S_tv_cab_door_%d" % i, (0.02, 0.36, 0.36), (6.18, yy, 0.24),
              "MAT_wood_pale", group=G)
    L.box("S_crt", (0.44, 0.64, 0.5), (6.24, -3.65, 0.78), "MAT_wood_dark",
          bevel=0.012, group=G)
    L.slab("S_crt_screen", 6.01, 6.02, -3.93, -3.37, 0.62, 0.96,
           "MAT_tv_static", front=(-1, 0, 0), uv="unit", group=G)
    L.cyl("S_crt_knob_1", 0.022, 0.02, (6.01, -3.5, 0.58), "MAT_metal_rust",
          axis="X", segments=8, group=G)
    L.cyl("S_crt_knob_2", 0.022, 0.02, (6.01, -3.42, 0.58), "MAT_metal_rust",
          axis="X", segments=8, group=G)
    L.col("COL_tv_cabinet", (6.3, -3.65, 0.4), (0.6, 1.6, 0.8))
    # battery on tv cabinet
    L.cyl("INT_battery_02", 0.016, 0.09, (6.3, -2.95, 0.545),
          "MAT_metal_locker", segments=8, group="INT_battery_02")
    L.props("INT_battery_02", interact="pickup", prompt="捡起电池", id="battery2")
    # battery on top of the mailbox in the corridor
    L.cyl("INT_battery_01", 0.016, 0.09, (1.16, -1.0, 1.895),
          "MAT_metal_locker", segments=8, group="INT_battery_01")
    L.props("INT_battery_01", interact="pickup", prompt="捡起电池", id="battery1")
    # bookshelf on north wall
    L.box("S_bookshelf", (1.5, 0.3, 1.9), (4.1, -3.08, 0.95),
          "MAT_wood_dark", group=G)
    for i in range(4):
        L.box("S_shelf_board_%d" % i, (1.42, 0.28, 0.04),
              (4.1, -3.08, 0.05 + i * 0.46), "MAT_wood_pale", group=G)
    for i in range(6):
        L.box("S_book_%d" % i, (0.06, 0.2, 0.3),
              (3.5 + i * 0.22, -3.08, 0.35 + (i % 3) * 0.46),
              "MAT_fabric_red" if i % 2 else "MAT_curtain", group=G)
    L.col("COL_bookshelf", (4.1, -3.08, 0.95), (1.55, 0.36, 1.9))
    # INT_letter_03 on bookshelf
    L.box("INT_letter_03", (0.16, 0.012, 0.22), (4.32, -2.92, 1.26),
          "MAT_paper", group="INT_letter_03")
    L.props("INT_letter_03", interact="pickup", prompt="捡起字条", id="letter3")
    # dining table + 2 chairs
    L.box("S_dining_table", (1.15, 0.8, 0.06), (5.25, -6.95, 0.73),
          "MAT_wood_dark", group=G)
    for i, (xx, yy) in enumerate([(4.75, -7.28), (5.75, -7.28),
                                  (4.75, -6.62), (5.75, -6.62)]):
        L.box("S_dining_leg_%d" % i, (0.055, 0.055, 0.72), (xx, yy, 0.36),
              "MAT_wood_dark", group=G)
    chair(G, "S_dining_chair_1", 4.55, -6.95, 90)
    chair(G, "S_dining_chair_2", 5.95, -6.95, -90)
    L.col("COL_dining_table", (5.25, -6.95, 0.4), (1.2, 0.85, 0.8))
    # letter_01 on table
    L.box("INT_letter_01", (0.17, 0.02, 0.23), (5.05, -6.9, 0.77),
          "MAT_paper", group="INT_letter_01")
    L.props("INT_letter_01", interact="pickup", prompt="捡起字条", id="letter1")
    # rug
    L.box("S_rug", (2.2, 1.7, 0.02), (4.5, -4.9, 0.01), "MAT_curtain",
          group=G)
    # floor lamp (north-west living corner)
    L.cyl("S_floor_lamp_base", 0.16, 0.04, (3.0, -3.2, 0.02), "MAT_metal_rust",
          segments=10, group=G)
    L.cyl("S_floor_lamp_pole", 0.018, 1.5, (3.0, -3.2, 0.78), "MAT_metal_rust",
          segments=8, group=G)
    L.cyl("S_floor_lamp_shade", 0.2, 0.26, (3.0, -3.2, 1.62),
          "MAT_fabric_white", segments=12, radius2=0.26, group=G)
    L.box("S_lamp_shade_glow", (0.1, 0.1, 0.1), (3.0, -3.2, 1.62),
          "MAT_lamp_warm", group=G)
    # wall clock LIVE (INT_clock)
    L.cyl("INT_clock_body", 0.17, 0.05, (1.9, -2.92, 2.1), "MAT_wood_dark",
          axis="Y", segments=12, group="INT_clock")
    L.circle_disc("INT_clock_face", 0.155, (1.9, -2.948, 2.1), "MAT_clock_face",
                  axis="Y", segments=12, front=(0, -1, 0), group="INT_clock")
    L.box("INT_clock_hand_h", (0.012, 0.008, 0.09), (1.955, -2.954, 2.1),
          "MAT_entity_hair", group="INT_clock")
    L.box("INT_clock_hand_m", (0.012, 0.008, 0.13), (1.9, -2.954, 2.135),
          "MAT_entity_hair", group="INT_clock")
    L.props("INT_clock", interact="examine", prompt="看钟", id="clock_living")
    # family photos
    L.slab("S_photo_1_frame", 2.72, 2.735, -4.2, -3.78, 1.55, 1.95,
           "MAT_wood_dark", group="S_photo_1")
    L.slab("S_photo_1", 2.735, 2.741, -4.17, -3.81, 1.58, 1.92,
           "MAT_photo", front=(1, 0, 0), uv="unit", group="S_photo_1")
    L.slab("S_photo_2_frame", 4.55, 4.9, -2.935, -2.90, 1.6, 1.95,
           "MAT_wood_dark", group="S_photo_2")
    L.slab("S_photo_2", 4.58, 4.87, -2.941, -2.935, 1.63, 1.92,
           "MAT_photo", front=(0, -1, 0), uv="unit", group="S_photo_2")
    # living light switch on the solid west wall next to the entry opening
    L.slab("S_switch_living_plate", 2.72, 2.73, -4.16, -4.04, 1.22, 1.38,
           "MAT_wood_pale", group="INT_switch_living")
    L.box("S_switch_living_btn", (0.012, 0.05, 0.05), (2.737, -4.1, 1.3),
          "MAT_fabric_white", group="INT_switch_living")
    L.props("INT_switch_living", interact="switch", prompt="开灯", id="switch_living")
    # corridor switch near player start
    L.slab("S_switch_corr_plate", -1.115, -1.09, -1.32, -1.2, 1.22, 1.38,
           "MAT_wood_pale", group="INT_switch_corridor")
    L.box("S_switch_corr_btn", (0.012, 0.05, 0.05), (-1.085, -1.26, 1.3),
          "MAT_fabric_white", group="INT_switch_corridor")
    L.props("INT_switch_corridor", interact="switch", prompt="开灯",
            id="switch_corridor")
    # ---------------- kitchen
    L.box("S_counter_body", (1.5, 0.55, 0.86), (3.35, -9.25, 0.43),
          "MAT_wood_pale", group=G)
    L.box("S_counter_top", (1.58, 0.62, 0.06), (3.35, -9.25, 0.89),
          "MAT_tile_white", group=G)
    for i, xx in enumerate([2.9, 3.6]):
        L.box("S_counter_door_%d" % i, (0.55, 0.02, 0.62), (xx, -8.97, 0.42),
              "MAT_wood_pale", group=G)
        L.cyl("S_counter_knob_%d" % i, 0.016, 0.03, (xx + 0.2, -8.955, 0.48),
              "MAT_metal_rust", axis="Y", segments=6, group=G)
    # sink
    L.slab("S_sink_basin", 3.05, 3.55, -9.42, -9.05, 0.9, 0.94,
           "MAT_metal_locker", group=G)
    L.slab("S_sink_hole", 3.15, 3.45, -9.35, -9.12, 0.86, 0.9,
           "MAT_concrete", group=G)
    L.cyl_between("S_kit_faucet", (3.3, -9.45, 0.94), (3.3, -9.3, 1.14),
                  0.018, "MAT_metal_locker", segments=8, group=G)
    L.cyl_between("S_kit_faucet2", (3.3, -9.3, 1.14), (3.3, -9.18, 1.14),
                  0.015, "MAT_metal_locker", segments=8, group=G)
    # stove
    L.box("S_stove", (0.5, 0.5, 0.04), (2.83, -9.22, 0.94), "MAT_metal_rust",
          group=G)
    for i, (xx, yy) in enumerate([(2.72, -9.33), (2.94, -9.33),
                                  (2.72, -9.11), (2.94, -9.11)]):
        L.cyl("S_burner_%d" % i, 0.07, 0.02, (xx, yy, 0.97), "MAT_metal_locker",
              segments=8, group=G)
    L.box("S_range_hood", (0.56, 0.4, 0.16), (2.83, -9.4, 1.95),
          "MAT_metal_rust", group=G)
    # upper cabinets
    L.box("S_upper_cab", (1.5, 0.32, 0.62), (3.35, -9.35, 1.82),
          "MAT_wood_pale", group=G)
    for i, xx in enumerate([2.95, 3.75]):
        L.box("S_upper_door_%d" % i, (0.72, 0.02, 0.54), (xx, -9.18, 1.82),
              "MAT_wood_pale", group=G)
    L.col("COL_kitchen_counter", (3.35, -9.25, 0.45), (1.62, 0.64, 0.95))
    # letter_02 on counter
    L.box("INT_letter_02", (0.17, 0.02, 0.23), (3.85, -9.12, 0.94),
          "MAT_paper", group="INT_letter_02")
    L.props("INT_letter_02", interact="pickup", prompt="捡起字条", id="letter2")
    # ---------------- bedroom
    # bed along north wall
    L.box("S_bed_frame", (1.8, 1.35, 0.22), (7.9, -4.2, 0.11),
          "MAT_wood_dark", group=G)
    L.box("S_bed_headboard", (1.84, 0.08, 0.75), (7.9, -3.45, 0.6),
          "MAT_wood_dark", group=G)
    L.box("S_bed_mattress", (1.72, 1.26, 0.24), (7.9, -4.18, 0.34),
          "MAT_fabric_white", group=G)
    L.box("S_bed_pillow", (0.5, 0.3, 0.12), (7.35, -3.75, 0.51),
          "MAT_fabric_white", group=G)
    L.box("S_bed_blanket", (1.5, 1.1, 0.08), (7.95, -4.4, 0.47),
          "MAT_fabric_blue", group=G)
    L.col("COL_bed", (7.9, -4.2, 0.4), (1.85, 1.4, 0.8))
    # nightstand + lamp
    L.box("S_nightstand", (0.45, 0.4, 0.52), (9.12, -4.75, 0.26),
          "MAT_wood_dark", group=G)
    L.box("S_nightstand_top", (0.49, 0.44, 0.04), (9.12, -4.75, 0.54),
          "MAT_wood_pale", group=G)
    L.cyl("S_bed_lamp_base", 0.05, 0.03, (9.12, -4.75, 0.57),
          "MAT_metal_rust", segments=8, group=G)
    L.cyl("S_bed_lamp_stem", 0.012, 0.16, (9.12, -4.75, 0.65),
          "MAT_metal_rust", segments=6, group=G)
    L.cyl("S_bed_lamp_shade", 0.09, 0.13, (9.12, -4.75, 0.79),
          "MAT_fabric_white", segments=10, radius2=0.13, group=G)
    L.sphere("S_bed_lamp_glow", 0.045, (9.12, -4.75, 0.79), "MAT_lamp_warm",
             subdiv=1, group=G)
    L.col("COL_nightstand", (9.12, -4.75, 0.28), (0.5, 0.45, 0.6))
    # wardrobe against west wall (south of door)
    L.box("S_wardrobe", (0.55, 1.35, 2.15), (6.995, -7.0, 1.075),
          "MAT_wood_dark", group="S_wardrobe")
    L.box("S_wardrobe_top", (0.6, 1.4, 0.06), (6.995, -7.0, 2.16),
          "MAT_wood_pale", group="S_wardrobe")
    for i, yy in enumerate([-7.35, -6.68]):
        L.box("S_wardrobe_door_%d" % i, (0.02, 0.63, 1.95),
              (7.265, yy, 1.1), "MAT_wood_pale", group="S_wardrobe")
        L.cyl("S_wardrobe_knob_%d" % i, 0.018, 0.03, (7.282, yy + 0.24, 1.05),
              "MAT_metal_rust", axis="X", segments=6, group="S_wardrobe")
    L.col("COL_wardrobe", (6.995, -7.0, 1.0), (0.6, 1.4, 2.0))
    # final chair facing the south window
    chair("S_chair_final", "S_chair_final", 7.3, -6.55, 180, mat="MAT_wood_dark")
    L.col("COL_chair_final", (7.3, -6.55, 0.4), (0.5, 0.5, 0.8))
    # letter_final on bed (hidden)
    L.box("INT_letter_final", (0.18, 0.02, 0.24), (8.35, -4.55, 0.63),
          "MAT_paper", group="INT_letter_final")
    L.props("INT_letter_final", interact="pickup", prompt="读信", id="final_letter",
            hidden=True)
    # bedroom photos
    L.slab("S_bed_photo_frame", 8.4, 8.75, -7.80, -7.77, 1.65, 1.98,
           "MAT_wood_dark", group=G)
    L.slab("S_bed_photo", 8.43, 8.72, -7.773, -7.768, 1.67, 1.95,
           "MAT_photo", front=(0, 1, 0), uv="unit", group=G)
    # hallway / living misc details: shoes rack near entrance, umbrella stand
    L.box("S_umbrella_stand", (0.16, 0.16, 0.4), (1.2, -6.2, 0.2),
          "MAT_metal_rust", group=G)


# ---------------------------------------------------------------------------
# entities + hidden variants
# ---------------------------------------------------------------------------
def humanoid(group, prefix, x, y, h=1.72, body_mat="MAT_entity_white",
             hair_mat="MAT_entity_hair", face_mat="MAT_entity_face"):
    P = (x, y, 0.0)
    # long dress / legs
    L.frustum(prefix + "_dress", (0.62, 0.5), (0.34, 0.26), 0.02, 1.18,
              (x, y), body_mat, group=group, pivot=P, bevel=0.0)
    # torso
    L.frustum(prefix + "_torso", (0.34, 0.26), (0.3, 0.22), 1.15, 1.44,
              (x, y), body_mat, group=group, pivot=P)
    # arms
    L.cyl_between(prefix + "_arm_l", (x - 0.17, y, 1.42), (x - 0.24, y + 0.02, 0.92),
                  0.035, body_mat, segments=6, group=group, pivot=P)
    L.cyl_between(prefix + "_arm_r", (x + 0.17, y, 1.42), (x + 0.24, y + 0.02, 0.92),
                  0.035, body_mat, segments=6, group=group, pivot=P)
    # neck + head
    L.cyl(prefix + "_neck", 0.045, 0.1, (x, y, 1.49), body_mat, segments=8,
          group=group, pivot=P)
    L.sphere(prefix + "_head", 0.105, (x, y, 1.6), body_mat, subdiv=2,
             scale=(0.9, 0.85, 1.12), group=group, pivot=P)
    L.slab(prefix + "_face", x - 0.06, x + 0.06, y - 0.105, y - 0.095,
           1.58, 1.66, face_mat, front=(0, -1, 0), uv="unit", group=group,
           pivot=P)
    # hair: cap + long back sheet
    L.sphere(prefix + "_hair_cap", 0.108, (x, y + 0.015, 1.63), hair_mat,
             subdiv=2, scale=(0.95, 0.9, 0.95), group=group, pivot=P)
    L.slab(prefix + "_hair_back", x - 0.13, x + 0.13, y + 0.06, y + 0.11,
           0.75, 1.62, hair_mat, group=group, pivot=P)
    L.slab(prefix + "_hair_l", x - 0.14, x - 0.1, y + 0.04, y + 0.1,
           1.0, 1.62, hair_mat, group=group, pivot=P)
    L.slab(prefix + "_hair_r", x + 0.1, x + 0.14, y + 0.04, y + 0.1,
           1.0, 1.62, hair_mat, group=group, pivot=P)
    # feet
    L.box(prefix + "_foot_l", (0.09, 0.2, 0.05), (x - 0.1, y - 0.05, 0.025),
          body_mat, group=group, pivot=P)
    L.box(prefix + "_foot_r", (0.09, 0.2, 0.05), (x + 0.1, y - 0.05, 0.025),
          body_mat, group=group, pivot=P)
    # dark eye hints
    L.slab(prefix + "_eye_l", x - 0.05, x - 0.025, y - 0.108, y - 0.104,
           1.615, 1.63, hair_mat, group=group, pivot=P)
    L.slab(prefix + "_eye_r", x + 0.025, x + 0.05, y - 0.108, y - 0.104,
           1.615, 1.63, hair_mat, group=group, pivot=P)


def ajar_leaf(group, x_center, hinge_y, sign_y, width, angle_deg, thick=0.045):
    """A door leaf rotated around its hinge (hidden variant)."""
    P = (x_center, hinge_y, 0.0)
    objs = [
        L.slab(group + "_leaf", x_center - thick / 2, x_center + thick / 2,
               hinge_y, hinge_y + sign_y * width, 0.02, 2.02,
               "MAT_wood_door", bevel=0.008, group=group, pivot=P),
        L.box(group + "_panel", (0.012, width * 0.62, 1.35),
              (x_center - thick / 2 - 0.006, hinge_y + sign_y * width / 2, 1.05),
              "MAT_wood_dark", group=group, pivot=P),
    ]
    rot = Matrix.Rotation(math.radians(angle_deg), 4, "Z")
    for ob in objs:
        ob.data.transform(rot)
    return P


def build_entities_variants():
    # entity in bedroom, origin at feet, hidden
    humanoid("ENTITY_she", "ENTITY_she", 7.3, -6.15)
    L.props("ENTITY_she", hidden=True)
    # --- V2 (round 2)
    chair("V2_corr_chair", "V2_corr_chair", 0.0, -9.4, 0, mat="MAT_metal_rust")
    L.props("V2_corr_chair", hidden=True)
    ajar_leaf("V2_door_501_ajar", -1.115, -3.67, 1, 0.94, -28)
    L.props("V2_door_501_ajar", hidden=True)
    ajar_leaf("V3_door_502_ajar", -1.115, -8.87, 1, 0.94, -24)
    L.props("V3_door_502_ajar", hidden=True)
    ajar_leaf("V3_door_504_ajar", 1.115, -10.67, 1, 0.94, 25)
    L.props("V3_door_504_ajar", hidden=True)
    # stains
    stains = [
        ("V2_stain_01", -1.101, -1.093, -7.2, -6.3, 0.3, 1.6, "MAT_stain_mold"),
        ("V2_stain_02", 1.093, 1.101, -11.6, -10.9, 0.15, 1.3, "MAT_stain_water"),
        ("V2_stain_03", -0.7, 0.1, -13.0, -12.2, 0.0, 0.008, "MAT_stain_water"),
        ("V3_stain_04", 1.093, 1.101, -3.6, -2.6, 0.2, 1.9, "MAT_stain_mold"),
        ("V3_stain_05", -1.101, -1.093, -16.6, -15.7, 0.0, 1.5, "MAT_stain_mold"),
        ("V3_stain_06", 3.2, 4.9, -2.91, -2.903, 1.9, 2.6, "MAT_stain_water"),
    ]
    for nm, x0, x1, y0, y1, z0, z1, mat in stains:
        L.slab(nm, x0, x1, y0, y1, z0, z1, mat, group=nm)
        L.props(nm, hidden=True)
    # handprints / claw marks on corridor walls (thin dark planes)
    for i, (x, yy, zz) in enumerate([(-1.095, -4.4, 1.45), (1.094, -7.0, 1.3),
                                     (1.094, -15.0, 1.55)]):
        nm = "V3_handprints_%02d" % (i + 1)
        L.slab(nm, x, x + (0.006 if x > 0 else -0.006), yy - 0.09, yy + 0.09,
               zz - 0.13, zz + 0.13, "MAT_stain_mold", group=nm)
        L.props(nm, hidden=True)
    # scattered mail
    for i, (x, yy, rot) in enumerate([(0.55, -2.1, 0.3), (0.2, -1.9, -0.6),
                                      (-0.1, -2.35, 0.9), (0.7, -2.5, -0.2)]):
        L.box("V2_mail_scatter_%d" % i, (0.16, 0.02, 0.22),
              (x, yy, 0.012), "MAT_paper", rot=(0, 0, rot),
              group="V2_mail_scatter")
    L.props("V2_mail_scatter", hidden=True)
    # dead fluorescent tube (round 2)
    L.box("V2_bulb_dead_housing", (1.18, 0.2, 0.07), (0, -9.0, 2.63),
          "MAT_metal_rust", group="V2_bulb_dead")
    L.box("V2_bulb_dead_tube", (1.0, 0.07, 0.035), (0, -9.0, 2.56),
          "MAT_metal_rust", group="V2_bulb_dead")
    L.props("V2_bulb_dead", hidden=True)
    # corridor puddle (round 3)
    L.box("V3_corr_water", (1.9, 6.0, 0.008), (0, -13.5, 0.006),
          "MAT_stain_water", group="V3_corr_water")
    L.props("V3_corr_water", hidden=True)


# ---------------------------------------------------------------------------
# lights / spawns
# ---------------------------------------------------------------------------
def build_light_spawns():
    for i, yy in enumerate([-1.8, -5.4, -9.0, -12.6, -16.2]):
        L.light("LIGHT_corr_%02d" % (i + 1), (0, yy, 2.45), kind="point",
                power=20, color="#cfe0d8", radius=7, flicker=0.12)
    L.light("LIGHT_entry", (1.85, -5.3, 2.45), power=10, color="#ffcf9a",
            radius=4, flicker=0.0)
    L.light("LIGHT_living", (5.0, -5.0, 2.45), power=25, color="#ffcf9a",
            radius=7, flicker=0.0)
    L.light("LIGHT_tv", (6.05, -3.65, 1.0), power=8, color="#8fb4ff",
            radius=3, flicker=0.35)
    L.light("LIGHT_floor_lamp", (3.0, -3.2, 1.55), power=18,
            color="#ffcf9a", radius=5, flicker=0.0)
    L.light("LIGHT_kitchen", (3.4, -8.7, 2.45), power=12, color="#cfe0d8",
            radius=4, flicker=0.0)
    L.light("LIGHT_bedroom", (8.0, -5.3, 2.45), power=12, color="#d99a6a",
            radius=4, flicker=0.0)
    L.light("LIGHT_moon_bed", (8.0, -7.5, 1.8), power=6, color="#7e9cc8",
            radius=5, flicker=0.0)
    # spawns
    L.spawn("SPAWN_corridor", (0.0, -1.0, 0.0))
    L.look("LOOK_corridor", (0.0, -10.0, 1.55))
    L.spawn("SPAWN_apartment", (1.9, -5.3, 0.0))
    L.look("LOOK_apartment", (4.5, -5.2, 1.55))
    L.spawn("SPAWN_bedroom", (7.0, -5.4, 0.0))
    L.look("LOOK_bedroom", (8.6, -6.4, 1.4))


# ---------------------------------------------------------------------------
def main():
    L.reset("door")
    build_corridor()
    build_apartment()
    build_doors()
    build_furniture()
    build_entities_variants()
    build_light_spawns()
    L.finalize(OUT)
    print("DOOR BUILD DONE")


if __name__ == "__main__":
    main()
