"""build_nightroad.py -- 《夜路》 night country road + shrine, export nightroad.glb.

headless:  blender.exe -b --factory-startup --python build_nightroad.py
"""
import sys
import os
import math
import random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_build as L

OUT = L.MODELS + r"\nightroad.glb"
random.seed(20261018)

CTRL = [(0.0, 0.0), (1.5, -16.0), (-0.5, -32.0), (2.0, -48.0),
        (0.0, -64.0), (-1.5, -80.0), (0.0, -98.0)]


def catmull_samples(step=2.0):
    P = [CTRL[0]] + list(CTRL) + [CTRL[-1]]
    dense = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(12):
            t = k / 12.0
            t2, t3 = t * t, t * t * t
            x = 0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * t +
                       (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 +
                       (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3)
            y = 0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t +
                       (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 +
                       (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
            dense.append((x, y))
    dense.append(CTRL[-1])
    # resample by arc length
    out = [dense[0]]
    acc = 0.0
    last = dense[0]
    for pt in dense[1:]:
        acc += math.hypot(pt[0] - last[0], pt[1] - last[1])
        last = pt
        if acc >= step:
            out.append(pt)
            acc = 0.0
    if out[-1] != dense[-1]:
        out.append(dense[-1])
    return out


def road_center(y):
    """Approximate centreline x for a given y (search samples)."""
    best = min(CENTER, key=lambda p: abs(p[1] - y))
    return best[0]


CENTER = catmull_samples(2.0)


def build_ground_road():
    # ground
    # Subdivide the broad field so vertex-interpolated fog can represent
    # local depth. This alone did not fix the earlier blue-field lighting.
    ground=[];faces=[];cols,rows=14,16
    for j in range(rows+1):
        for i in range(cols+1):ground.append((-70+i*10,8-j*9.875,0))
    for j in range(rows):
        for i in range(cols):
            a=j*(cols+1)+i;faces.append((a,a+cols+1,a+cols+2,a+1))
    L.mesh_custom('S_ground',ground,faces,'MAT_grass',up_faces=True,uv_scale=2)
    # road ribbon: custom UVs, 1 UV unit = 2 m, v along the road
    half = 1.6
    verts, faces, uvs = [], [], []
    dist = 0.0
    for i, (x, y) in enumerate(CENTER):
        if i == 0:
            dx, dy = CENTER[1][0] - x, CENTER[1][1] - y
        else:
            dx, dy = x - CENTER[i - 1][0], y - CENTER[i - 1][1]
        ln = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / ln, dx / ln
        edge=half+.07*math.sin(i*2.13)+.035*math.sin(i*5.1)
        verts.append((x + nx * edge, y + ny * edge, 0.012))
        verts.append((x - nx * edge, y - ny * edge, 0.012))
        if i > 0:
            dist += math.hypot(x - CENTER[i - 1][0], y - CENTER[i - 1][1])
        uvs.append((1.6, dist / 2.0))
        uvs.append((0.0, dist / 2.0))
    n = len(CENTER)
    loop_uvs = []
    for i in range(n - 1):
        a = i * 2
        faces.append((a, a + 1, a + 3, a + 2))
        loop_uvs.extend([uvs[a], uvs[a + 1], uvs[a + 3], uvs[a + 2]])
    L.mesh_custom("S_road", verts, faces, "MAT_soil_road", loop_uvs=loop_uvs,
                  up_faces=True)
    # field ridges beside the road + scattered stones and grass tufts
    for i in range(9):
        yy = -8 - i * 10
        xx = road_center(yy)
        for side in (-1, 1):
            x0,x1=sorted([xx+side*3.2,xx+side*9.5])
            L.mesh_custom('S_ridge_%02d_%s'%(i,'L' if side<0 else 'R'),
                [(x0,yy-.18,.005),(x1,yy-.18,.005),(x0,yy,.12),(x1,yy,.12),(x0,yy+.18,.005),(x1,yy+.18,.005)],
                [(0,1,3,2),(2,3,5,4),(0,2,4),(1,5,3)],'MAT_soil',group='S_field_ridges')
    for i in range(18):
        yy = -4 - i * 5.2
        xx = road_center(yy) + random.choice([-1, 1]) * random.uniform(1.8, 2.4)
        L.sphere("S_stone_%02d" % i, random.uniform(0.08, 0.18),
                 (xx, yy + random.uniform(-1, 1), 0.04), "MAT_stone",
                 subdiv=1, scale=(1.0, 1.0, 0.55), group="S_stones")
    for i in range(100):
        yy=-2-i*.96;side=-1 if i%2 else 1
        xx=road_center(yy)+side*random.uniform(1.65,3.1)
        verts=[];faces=[]
        for k in range(5):
            a=random.uniform(0,math.tau);h=random.uniform(.16,.48);w=random.uniform(.025,.055)
            bx=xx+random.uniform(-.13,.13);by=yy+random.uniform(-.15,.15)
            dx=math.cos(a)*w;dy=math.sin(a)*w;j=len(verts)
            verts.extend([(bx-dx,by-dy,.01),(bx+dx,by+dy,.01),(bx+side*.08,by+.05,h)])
            faces.extend([(j,j+1,j+2),(j+2,j+1,j)])
        L.mesh_custom('S_grass_%03d'%i,verts,faces,'MAT_grass',group='S_grass_tufts')


def tree(name, x, y, s=1.0):
    L.cyl(name + "_trunk", 0.16 * s, 2.9 * s, (x, y, 1.45 * s), "MAT_bark",
          segments=6, group=name)
    L.cyl_between(name + "_branch1", (x, y, 2.2 * s),
                  (x + 0.7 * s, y + 0.3 * s, 3.3 * s), 0.07 * s, "MAT_bark",
                  segments=5, group=name)
    L.cyl_between(name + "_branch2", (x, y, 2.4 * s),
                  (x - 0.6 * s, y - 0.5 * s, 3.5 * s), 0.06 * s, "MAT_bark",
                  segments=5, group=name)
    for k, (dx, dy, dz, r) in enumerate([
            (0.0, 0.0, 3.9, 1.65), (-1.0, 0.4, 3.4, 1.2),
            (0.9, -0.4, 3.5, 1.3), (0.1, 0.7, 3.2, 1.0)]):
        L.sphere(name + "_leaf_%d" % k, r * s,
                 (x + dx * s, y + dy * s, dz * s), "MAT_leaves",
                 subdiv=1, scale=(1.0, 0.9, 0.75), group=name)


def build_trees():
    spots = [(-6.5, -6, 1.0), (8.0, -11, 0.9), (-8.5, -18, 1.15),
             (7.5, -25, 1.0), (-9.0, -33, 0.9), (9.0, -41, 1.1),
             (-7.5, -50, 1.0), (8.5, -58, 0.95), (-9.5, -67, 1.1),
             (-3.0, -94.5, 1.25)]
    for i, (x, y, s) in enumerate(spots):
        tree("S_tree_%02d" % (i + 1), x, y, s)
    # dead tree by the road (extra silhouette, part of the main tree group)
    L.cyl("S_tree_10_dead", 0.1, 2.4, (-3.0, -93.0, 1.2), "MAT_bark",
          segments=5, group="S_tree_10")


def lantern(i, x, y, side):
    """Wooden pole + arm + red paper lantern.  Object origin = lantern centre."""
    g = "INT_lantern_%02d" % i
    cx, cy, cz = x - side * 0.38, y, 1.35
    P = (cx, cy, cz)
    # pole + arm + hook (world geometry, pivot at lantern centre)
    L.cyl(g + "_pole", 0.045, 1.9, (x, y, 0.95), "MAT_bark", segments=6,
          group=g, pivot=P)
    L.cyl_between(g + "_arm", (x, y, 1.78), (x - side * 0.42, y, 1.72),
                  0.03, "MAT_wood_dark", segments=5, group=g, pivot=P)
    L.cyl_between(g + "_string", (x - side * 0.38, y, 1.72),
                  (cx, cy, 1.55), 0.008, "MAT_metal_rust", segments=4,
                  group=g, pivot=P)
    # lantern body
    L.cyl(g + "_body", 0.17, 0.34, P, "MAT_lantern_paper", segments=8,
          group=g, pivot=P)
    L.cyl(g + "_rim_top", 0.185, 0.04, (cx, cy, cz + 0.19),
          "MAT_wood_dark", segments=8, group=g, pivot=P)
    L.cyl(g + "_rim_bot", 0.185, 0.04, (cx, cy, cz - 0.19),
          "MAT_wood_dark", segments=8, group=g, pivot=P)
    for k in range(4):
        a = math.radians(45 * k)
        L.box(g + "_rib_%d" % k, (0.012, 0.012, 0.36),
              (cx + 0.165 * math.cos(a), cy + 0.165 * math.sin(a), cz),
              "MAT_wood_dark", rot=(0, 0, a), group=g, pivot=P)
    L.cyl(g + "_tassel", 0.018, 0.16, (cx, cy, cz - 0.28), "MAT_red_cloth",
          segments=5, group=g, pivot=P)
    L.props(g, interact="lantern", prompt="点亮灯笼", id="lantern%d" % i)


def build_lanterns():
    spots = [(-12.0, 2.1, 1), (-28.0, -2.1, -1), (-44.0, 2.1, 1),
             (-60.0, -2.1, -1), (-78.0, 2.3, 1)]
    for i, (y, off, side) in enumerate(spots):
        x = road_center(y) + off
        lantern(i + 1, x, y, side)


def build_shrine():
    G = "S_shrine"
    L.box("S_shrine_base", (2.3, 1.9, 0.18), (0, -98.0, 0.09), "MAT_stone",
          bevel=.025, group=G)
    L.box("S_shrine_plinth", (1.5, 1.25, 0.42), (0, -98.1, 0.39), "MAT_stone",
          bevel=.025, group=G)
    # shrine body: back + side walls + pillars (front open)
    L.box("S_shrine_back", (1.2, 0.1, 0.95), (0, -98.6, 1.02),
          "MAT_shrine_wood", group=G)
    for sx in (-1, 1):
        L.box("S_shrine_side_%d" % (sx + 1), (0.1, 1.0, 0.95),
              (sx * 0.55, -98.08, 1.02), "MAT_shrine_wood", group=G)
        L.cyl("S_shrine_pillar_%d" % (sx + 1), 0.06, 0.95,
              (sx * 0.46, -97.6, 1.02), "MAT_shrine_wood", segments=6, group=G)
    # roof: two slopes + ridge (ridge along X)
    L.box("S_shrine_roof_front", (1.85, 0.8, 0.07), (0, -97.9, 1.58),
          "MAT_roof_tile", rot=(math.radians(-28), 0, 0), group=G)
    L.box("S_shrine_roof_back", (1.85, 0.8, 0.07), (0, -98.2, 1.58),
          "MAT_roof_tile", rot=(math.radians(28), 0, 0), group=G)
    L.box("S_shrine_ridge", (2.0, 0.16, 0.12), (0, -98.05, 1.72),
          "MAT_roof_tile", group=G)
    # altar shelf inside
    L.box("S_shrine_altar", (1.0, 0.5, 0.12), (0, -98.32, 0.92),
          "MAT_shrine_wood", group=G)
    # red cloth drapes (valance above the tablet, strips on the pillars)
    L.box("S_shrine_cloth_top", (1.05, 0.05, 0.16), (0, -98.1, 1.59),
          "MAT_red_cloth", group="S_shrine_cloth")
    for k, sx in enumerate((-0.4, 0.4)):
        L.box("S_shrine_cloth_hang_%d" % k, (0.16, 0.04, 0.7),
              (sx, -97.75, 1.0), "MAT_red_cloth", group="S_shrine_cloth")
    # tablet (front UV 0-1), standing on the altar, visible from the road
    L.box("S_shrine_tablet_body", (0.34, 0.05, 0.55), (0, -98.3, 1.25),
          "MAT_shrine_tablet", group="S_shrine_tablet")
    L.slab("S_shrine_tablet_face", -0.15, 0.15, -98.274, -98.269, 1.0, 1.48,
           "MAT_shrine_tablet", front=(0, 1, 0), uv="unit",
           group="S_shrine_tablet")
    # incense burner (S_incense_burner)
    b = "S_incense_burner"
    L.cyl(b + "_bowl", 0.2, 0.18, (0, -97.45, 0.62), "MAT_stone", segments=10,
          group=b)
    L.cyl(b + "_rim", 0.22, 0.04, (0, -97.45, 0.72), "MAT_stone", segments=10,
          group=b)
    L.cyl(b + "_ash", 0.17, 0.02, (0, -97.45, 0.73), "MAT_concrete",
          segments=10, group=b)
    for k in range(3):
        a = math.radians(120 * k + 30)
        L.cyl(b + "_leg_%d" % k, 0.035, 0.14,
              (0.14 * math.cos(a), -97.45 + 0.14 * math.sin(a), 0.47),
              "MAT_stone", segments=6, group=b)
    # incense bundle (LIVE)
    P = (0.0, -97.45, 0.76)
    for k in range(3):
        dx = (k - 1) * 0.03
        L.cyl_between("INT_incense_stick_%d" % k, (dx, -97.45, 0.76),
                      (dx * 2.2, -97.45, 1.08), 0.007, "MAT_paper",
                      segments=4, group="INT_incense", pivot=P)
    L.cyl("INT_incense_ember", 0.012, 0.02, (0, -97.45, 1.08),
          "MAT_lamp_warm", segments=4, group="INT_incense", pivot=P)
    L.props("INT_incense", interact="incense", prompt="上香", id="incense")
    # candles + offerings
    for k, sx in enumerate((-0.34, 0.34)):
        L.cyl("S_shrine_candle_%d" % k, 0.035, 0.2, (sx, -98.1, 1.0),
              "MAT_lamp_warm", segments=8, group=G)
        L.cyl("S_shrine_candle_base_%d" % k, 0.07, 0.04, (sx, -98.1, 0.9),
              "MAT_stone", segments=8, group=G)
    L.cyl("S_shrine_plate", 0.16, 0.03, (0.0, -97.9, 0.99), "MAT_paper",
          segments=8, group=G)
    L.sphere("S_shrine_fruit", 0.06, (-0.34, -97.9, 1.03), "MAT_red_cloth",
             subdiv=1, group=G)
    # steps in front
    for k in range(3):
        L.slab("S_shrine_step_%d" % k, -0.8 + k * 0.06, 0.8 - k * 0.06,
               -97.15 - k * 0.22, -96.95 - k * 0.22, 0.0, 0.14 - k * 0.04,
               "MAT_stone", group=G)
    L.col("COL_shrine", (0, -98.1, 0.7), (2.4, 2.0, 1.4))


def build_signs():
    for idx, (y, x) in enumerate([(-8.0, 2.5), (-50.0, -2.5)]):
        nm = "S_sign_%d" % (idx + 1)
        L.cyl(nm + "_post", 0.05, 2.0, (x, y - 0.03, 1.0), "MAT_wood_dark",
              segments=6, group=nm)
        L.box(nm + "_board", (1.1, 0.06, 0.58), (x, y, 1.55),
              "MAT_sign_night_%d" % (idx + 1), group=nm)
        L.slab(nm + "_face", x - 0.5, x + 0.5, y + 0.031, y + 0.036,
               1.3, 1.8, "MAT_sign_night_%d" % (idx + 1), front=(0, 1, 0),
               uv="unit", group=nm)


def build_graves_scarecrow_bicycle():
    for i, (x, y) in enumerate([(-5.0, -30.0), (6.2, -55.0), (-6.8, -74.0)]):
        g = "S_grave_%02d" % (i + 1)
        L.sphere(g + "_mound", 1.0, (x, y, 0.05), "MAT_soil", subdiv=1,
                 scale=(0.85, 1.25, 0.35), group=g)
        L.box(g + "_stone", (0.5, 0.14, 0.7), (x, y + 0.55, 0.36),
              "MAT_stone", group=g)
        L.box(g + "_cap", (0.6, 0.2, 0.08), (x, y + 0.55, 0.73),
              "MAT_stone", group=g)
    # paper money along the road
    for i in range(4):
        yy = -10.5 - i * 17.5
        xx = road_center(yy) + (-1 if i % 2 else 1) * random.uniform(0.6, 1.4)
        L.box("S_paper_money_%02d" % (i + 1), (0.13, 0.13, 0.006),
              (xx, yy, 0.02), "MAT_paper_money",
              rot=(0, 0, random.uniform(0, 1.5)), group="S_paper_money_%02d" % (i + 1))
    # scarecrow in the field
    g = "S_scarecrow"
    L.cyl(g + "_pole", 0.04, 2.1, (-5.6, -36.0, 1.05), "MAT_bark", segments=6,
          group=g)
    L.box(g + "_arm", (1.6, 0.06, 0.06), (-5.6, -36.0, 1.6), "MAT_bark",
          group=g)
    L.box(g + "_body", (0.5, 0.14, 0.66), (-5.6, -36.0, 1.25),
          "MAT_fabric_white", group=g)
    L.sphere(g + "_head", 0.14, (-5.6, -36.0, 1.83), "MAT_paper", subdiv=1,
             group=g)
    L.cyl(g + "_hat", 0.22, 0.18, (-5.6, -36.0, 2.0), "MAT_wood_dark",
          segments=8, radius2=0.02, group=g)
    for k, sx in enumerate((-0.55, 0.55)):
        L.box(g + "_sleeve_%d" % k, (0.3, 0.12, 0.14), (-5.6 + sx, -36.0, 1.55),
              "MAT_fabric_white", group=g)
    # fallen bicycle
    g = "S_bicycle"
    for k, (xx, zz) in enumerate([(2.3, 0.34), (3.5, 0.34)]):
        L.cyl(g + "_wheel_%d" % k, 0.34, 0.035, (xx, -70.0, zz),
              "MAT_metal_rust", axis="Y", segments=12, group=g)
    L.cyl_between(g + "_frame1", (2.3, -70.0, 0.34), (3.0, -70.0, 0.72),
                  0.025, "MAT_metal_rust", segments=6, group=g)
    L.cyl_between(g + "_frame2", (3.0, -70.0, 0.72), (3.5, -70.0, 0.34),
                  0.025, "MAT_metal_rust", segments=6, group=g)
    L.cyl_between(g + "_frame3", (2.3, -70.0, 0.34), (3.5, -70.0, 0.34),
                  0.025, "MAT_metal_rust", segments=6, group=g)
    L.box(g + "_seat", (0.22, 0.1, 0.05), (3.0, -70.0, 0.78), "MAT_entity_hair",
          group=g)
    L.cyl_between(g + "_bar", (3.45, -70.1, 0.4), (3.55, -70.0, 0.95),
                  0.02, "MAT_metal_rust", segments=5, group=g)


def build_poles_village():
    pole_y = [-20.0, -46.0, -72.0, -90.0]
    tops = []
    for i, yy in enumerate(pole_y):
        x = road_center(yy) + 3.0
        g = "S_pole_%02d" % (i + 1)
        L.cyl(g + "_pole", 0.1, 6.4, (x, yy, 3.2), "MAT_bark", segments=6,
              group=g)
        L.box(g + "_arm", (1.8, 0.09, 0.09), (x, yy, 5.8), "MAT_wood_dark",
              group=g)
        for k, dx in enumerate((-0.7, 0.7)):
            L.cyl(g + "_ins_%d" % k, 0.05, 0.1, (x + dx, yy, 5.9),
                  "MAT_glass_dirty", segments=6, group=g)
        tops.append((x, yy, 5.82))
    # sagging wires between successive poles (two per span)
    for i in range(len(tops) - 1):
        p0 = tops[i]
        p1 = tops[i + 1]
        for off in (-0.7, 0.7):
            pts = []
            for k in range(7):
                t = k / 6.0
                x = p0[0] + (p1[0] - p0[0]) * t + off
                y = p0[1] + (p1[1] - p0[1]) * t
                z = 5.82 + 4 * 0.55 * t * (t - 1)  # sag 0.55 m
                pts.append((x, y, z))
            for k in range(6):
                L.cyl_between("S_wire_%02d_%d_%02d" % (i, 0 if off < 0 else 1, k),
                              pts[k], pts[k + 1], 0.014, "MAT_metal_rust",
                              segments=4, group="S_wires")
    # distant village: dark silhouettes + warm window lights
    g = "S_village_lights"
    for i, (x, y, w, h) in enumerate([(-8, -122, 4, 3), (0, -126, 5, 3.4),
                                      (7, -121, 3.4, 2.6)]):
        L.box("S_village_house_%d" % i, (w, 3.5, h), (x, y, h / 2),
              "MAT_plaster", group=g)
        L.box("S_village_roof_%d" % i, (w + 0.6, 3.9, 0.3), (x, y, h + 0.15),
              "MAT_entity_hair", group=g)
        L.box("S_village_win_%d" % i, (0.5, 0.1, 0.6), (x, y + 1.76, h * 0.55),
              "MAT_lamp_warm", group=g)
    for k, (x, y, z) in enumerate([(-3, -112, 2.2), (2, -110, 1.8),
                                   (9, -115, 2.5), (-11, -118, 2.0)]):
        L.sphere("S_village_lamp_%d" % k, 0.09, (x, y, z), "MAT_lamp_warm",
                 subdiv=1, group=g)


def build_entity_lights():
    # 纸人: paper figure, origin at feet centre
    g = "ENTITY_paper"
    P = (0.0, -86.0, 0.0)
    x, y = 0.0, -86.0
    L.frustum(g + "_robe", (0.4, 0.3), (0.3, 0.22), 0.02, 1.0,
              (x, y), "MAT_paper", group=g, pivot=P)
    L.frustum(g + "_torso", (0.3, 0.22), (0.26, 0.2), 0.98, 1.38,
              (x, y), "MAT_paper", group=g, pivot=P)
    for k, sx in enumerate((-1, 1)):
        L.cyl_between(g + "_arm_%d" % k, (x + sx * 0.15, y, 1.35),
                      (x + sx * 0.28, y + 0.02, 0.78), 0.035,
                      "MAT_fabric_white", segments=5, group=g, pivot=P)
        L.box(g + "_leg_%d" % k, (0.08, 0.1, 0.42),
              (x + sx * 0.1, y, 0.21), "MAT_paper", group=g, pivot=P)
    L.sphere(g + "_head", 0.13, (x, y, 1.55), "MAT_paper", subdiv=2,
             scale=(0.9, 0.85, 1.1), group=g, pivot=P)
    L.slab(g + "_face", x - 0.09, x + 0.09, y - 0.125, y - 0.12,
           1.47, 1.62, "MAT_entity_face", front=(0, -1, 0), uv="unit",
           group=g, pivot=P)
    for k, sx in enumerate((-1, 1)):
        L.slab(g + "_eye_%d" % k, x + sx * 0.045 - 0.018, x + sx * 0.045 + 0.018,
               y - 0.128, y - 0.124, 1.555, 1.575, "MAT_entity_hair",
               group=g, pivot=P)
        L.slab(g + "_cheek_%d" % k, x + sx * 0.065 - 0.02, x + sx * 0.065 + 0.02,
               y - 0.128, y - 0.124, 1.5, 1.53, "MAT_red_cloth",
               group=g, pivot=P)
    L.box(g + "_sash", (0.34, 0.26, 0.07), (x, y, 1.02), "MAT_red_cloth",
          group=g, pivot=P)
    L.box(g + "_hat", (0.3, 0.3, 0.1), (x, y, 1.7), "MAT_entity_hair",
          group=g, pivot=P)
    L.props("ENTITY_paper", hidden=True)
    L.spawn("SPAWN_night_start", (0.0, 1.2, 0.0))
    L.look("LOOK_night_start", (0.0, -25.0, 1.4))
    L.light("LIGHT_shrine", (0.0, -97.0, 1.6), power=12,
            color="#ff9a5a", radius=4, flicker=0.08)
    L.light("LIGHT_village", (0.0, -118.0, 4.0), power=8,
            color="#ff9a5a", radius=10, flicker=0.05)


def build_cols():
    y_edges = [0.0, -12.25, -24.5, -36.75, -49.0, -61.25, -73.5, -85.75, -98.0]
    for i in range(8):
        ya, yb = y_edges[i], y_edges[i + 1]
        xa, xb = road_center(ya), road_center(yb)
        dx = abs(xb - xa)
        for side, tag in ((-1, "L"), (1, "R")):
            m = road_center((ya + yb) / 2)
            cx = m + side * (1.9 + dx / 2)
            w = dx + 0.6
            L.col("COL_path_edge_%s_%02d" % (tag, i + 1),
                  (cx, (ya + yb) / 2, 1.0), (w, abs(yb - ya) + 0.1, 2.0))


def main():
    L.reset("nightroad")
    build_ground_road()
    build_trees()
    build_lanterns()
    build_shrine()
    build_signs()
    build_graves_scarecrow_bicycle()
    build_poles_village()
    build_entity_lights()
    build_cols()
    L.finalize(OUT)
    print("NIGHTROAD BUILD DONE")


if __name__ == "__main__":
    main()
