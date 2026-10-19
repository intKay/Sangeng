"""《三更》贴图（一）：建筑与自然环境 —— 墙面/地面/瓷砖/金属/玻璃/木/土/草/树/石。

全部为周期性构造，可无缝平铺；工作分辨率 = 目标 2 倍，缩小时保留低分辨率笔触感。
"""
from __future__ import annotations

import math

import numpy as np

import artlib as A

SS = 2  # 工作分辨率倍率


def _work(w, h):
    return w * SS, h * SS


def _down(arr, w, h):
    return A.downscale_tiled(arr, w, h, SS)


def _post(rgb, r, grain_amt=0.022, desat=0.12, contrast=1.0, brightness=0.0):
    rgb = A.desaturate(rgb, desat)
    if contrast != 1.0 or brightness != 0.0:
        rgb = A.brighten_contrast(rgb, brightness, contrast)
    return A.grain(np.clip(rgb, 0, 1), r, grain_amt, 0.22)


# ------------------------------------------------------------------ 墙纸

def _sprig(cx, cy, cell, rot):
    """一枝小花：返回 (ellipse specs, stem segments)。"""
    ang = -0.72 + rot
    L = cell * 0.40
    dx, dy = math.cos(ang) * L * 0.5, math.sin(ang) * L * 0.5
    p0 = (cx - dx, cy - dy)
    p1 = (cx + dx, cy + dy)
    px, py = -dy / (L * 0.5 + 1e-6), dx / (L * 0.5 + 1e-6)
    ell = []
    for t, side in ((0.24, 1), (0.50, -1), (0.76, 1)):
        bx = p0[0] + (p1[0] - p0[0]) * t
        by = p0[1] + (p1[1] - p0[1]) * t
        lx = bx + px * side * cell * 0.10
        ly = by + py * side * cell * 0.10
        ell.append((ly, lx, cell * 0.032, cell * 0.095, ang + side * 0.95, 0.78))
    ell.append((p1[1] - dy * 0.20, p1[0] + dx * 0.20,
                cell * 0.028, cell * 0.028, ang, 0.72))
    return ell, [(*p0, *p1)]


def _wallpaper(w, h, dark=False):
    W, H = _work(w, h)
    shape = (H, W)
    name = "wallpaper_dark" if dark else "wallpaper"
    r = A.rng(name)
    yy, xx = A.coords(shape)

    lo = A.hexc("#5f5c45" if dark else "#9a9276")
    hi = A.hexc("#7c7760" if dark else "#bcb494")
    tone = A.fbm(shape, 3, 5, r, aniso=(3, 4))
    rgb = A.mix(lo[None, None], hi[None, None], 0.25 + 0.75 * tone)

    stripes = 0.5 + 0.5 * np.cos(2 * np.pi * xx * 8.0 / W)
    rgb *= (0.965 + 0.05 * stripes)[..., None]

    weave = A.pnoise(shape, (160, 160), r)
    rgb *= (0.94 + 0.10 * weave)[..., None]

    # 小花枝图案（5x5 错位排布）
    cell = W / 5.0
    ell_all, seg_all = [], []
    for i in range(5):
        for j in range(5):
            cx = (j + 0.5) * cell + (i % 2) * cell * 0.5
            cy = (i + 0.5) * cell
            cx += (r.random() - 0.5) * cell * 0.06
            cy += (r.random() - 0.5) * cell * 0.05
            e, s = _sprig(cx, cy, cell, (r.random() - 0.5) * 0.25)
            ell_all += e
            seg_all += s
    leaves = A.ellipses(shape, ell_all, feather=1.1)
    stems = A.seg_mask(shape, [(x0, y0, x1, y1, W * 0.004) for
                               (x0, y0, x1, y1) in seg_all], feather=1.0)
    wear = 0.62 + 0.38 * A.fbm(shape, 22, 4, r)
    leaves *= wear
    stems *= wear
    leaf_col = A.hexc("#62634a" if not dark else "#4a4c38")
    stem_col = A.hexc("#625b42" if not dark else "#47432f")
    rgb = A.over(rgb, leaf_col, leaves, 0.75)
    rgb = A.over(rgb, stem_col, stems, 0.62)

    # 水渍
    wat = A.smoothstep((A.fbm(shape, 5, 4, r) - 0.56) / 0.14)
    rgb = A.over(rgb, A.hexc("#7c6634"), wat, 0.30 if dark else 0.18)
    wat_edge = A.smoothstep((A.fbm(shape, 6, 4, r) - 0.68) / 0.03)
    rgb = A.over(rgb, A.hexc("#4a3d20"), wat_edge, 0.22)

    # 霉斑（成簇 + 细颗粒）
    mold_n = 90 if dark else 45
    clusters = [(r.uniform(0, H), r.uniform(0, W), r.uniform(40, 110))
                for _ in range(6)]
    specs = []
    for _ in range(mold_n):
        cy0, cx0, rad = clusters[r.integers(0, len(clusters))]
        cy = (cy0 + r.normal(0, rad * 0.6)) % H
        cx = (cx0 + r.normal(0, rad * 0.6)) % W
        specs.append((cy, cx, r.uniform(1.2, 6.0), r.uniform(0.35, 0.9)))
    mold = A.blobs(shape, specs, feather=2.2)
    fine_mold = A.smoothstep((A.pnoise(shape, (220, 220), r) - 0.80) / 0.06)
    mold = np.maximum(mold, fine_mold * 0.55)
    mold_col = A.hexc("#262a1a" if dark else "#3a3a24")
    rgb = A.over(rgb, mold_col, mold, 0.85 if dark else 0.6)

    # 竖向流下的污迹
    streak = A.smoothstep((A.fbm(shape, 0, 4, r, aniso=(70, 2)) - 0.52) / 0.2)
    rgb *= (1.0 - (0.18 if dark else 0.08) * streak)[..., None]

    if dark:
        chips = A.blobs(shape, [(r.uniform(0, H), r.uniform(0, W),
                                 r.uniform(10, 34), 1.0) for _ in range(7)],
                        feather=2.0)
        chips = A.smoothstep((chips - 0.45) / 0.08)
        rgb = A.over(rgb, A.hexc("#8a8272"), chips, 0.85)
        rim = np.clip(A.blur(chips, 1.2, periodic=True) - chips, 0, 1)
        rgb = A.over(rgb, A.hexc("#4c463a"), rim, 0.6)

    rgb = _post(rgb, r, 0.022, 0.18 if dark else 0.10)
    return _down(rgb, w, h)


def build_wallpaper(w, h):
    return _wallpaper(w, h, dark=False)


def build_wallpaper_dark(w, h):
    return _wallpaper(w, h, dark=True)


# ------------------------------------------------------------------ 白灰墙

def build_plaster(w, h):
    W, H = _work(w, h)
    shape = (H, W)
    r = A.rng("plaster")
    yy, xx = A.coords(shape)

    base = A.mix(A.hexc("#c6c0b0")[None, None], A.hexc("#ded8c8")[None, None],
                 A.fbm(shape, 4, 5, r)[..., None])
    base *= (0.94 + 0.10 * A.pnoise(shape, (150, 150), r))[..., None]

    chipfield = A.fbm(shape, 4, 5, r)
    chips = A.smoothstep((chipfield - 0.665) / 0.018)
    big = A.blobs(shape, [(r.uniform(0, H), r.uniform(0, W), r.uniform(18, 55), 1.0)
                          for _ in range(5)], feather=2.2)
    big = A.smoothstep((big - 0.58) / 0.06)
    chips = np.maximum(chips, big * 0.72)

    sub = A.mix(A.hexc("#948b7c")[None, None], A.hexc("#a89e8e")[None, None],
                A.fbm(shape, 10, 4, r)[..., None])
    sub *= (0.90 + 0.16 * A.pnoise(shape, (120, 120), r))[..., None]
    rgb = A.mix(base, sub, chips * 0.85)
    rim = np.clip(A.blur(chips, 1.6, periodic=True) - chips, 0, 1)
    rgb = A.over(rgb, A.hexc("#5a5447"), rim, 0.38)

    cr = A.ridged(shape, 3, 4, r)
    crack = A.smoothstep((cr - 0.985) / 0.012)
    crack *= A.smoothstep((A.fbm(shape, 6, 3, r) - 0.35) / 0.15)
    rgb = A.over(rgb, A.hexc("#554e42"), crack, 0.55)
    crack2 = A.smoothstep((A.ridged(shape, 7, 3, r) - 0.993) / 0.008)
    rgb = A.over(rgb, A.hexc("#6f6858"), crack2, 0.35)

    wat = A.smoothstep((A.fbm(shape, 4, 4, r) - 0.64) / 0.08)
    rgb = A.over(rgb, A.hexc("#94825a"), wat, 0.22)
    mold = A.blobs(shape, [(r.uniform(0, H), r.uniform(0, W), r.uniform(2, 10),
                            r.uniform(0.25, 0.65)) for _ in range(22)], feather=1.8)
    rgb = A.over(rgb, A.hexc("#41452c"), mold, 0.5)

    segs = [(r.uniform(0, W), r.uniform(0, H),
             r.uniform(0, W), r.uniform(0, H), r.uniform(0.8, 1.8))
            for _ in range(14)]
    sc = A.seg_mask(shape, segs, feather=1.0)
    rgb = A.over(rgb, A.hexc("#e2dccb"), sc, 0.22)

    rgb = _post(rgb, r, 0.025, 0.2)
    return _down(rgb, w, h)


# ------------------------------------------------------------------ 木地板

def build_wood_floor(w, h):
    W, H = _work(w, h)
    shape = (H, W)
    r = A.rng("wood_floor")
    yy, xx = A.coords(shape)

    rows = 16
    rh = H / rows
    palette = [A.hexc(c) for c in ("#593226", "#5f3628", "#653a29",
                                   "#553024", "#5c3426", "#623829")]
    grain_field = A.fbm(shape, 0, 4, r, aniso=(70, 5))
    broad = A.blur(A.fbm(shape, 2, 3, r), 8.0, periodic=True)

    rgb = np.zeros((H, W, 3), np.float32)
    for i in range(rows):
        y0 = int(round(i * rh))
        y1 = int(round((i + 1) * rh))
        k = 1 if r.random() < 0.45 else (2 if r.random() < 0.8 else 3)
        joints = np.sort(r.uniform(0, W, k))
        xs = np.arange(W, dtype=np.float32)
        bi = np.searchsorted(joints, xs, side="right") - 1
        if k == 1:
            starts = np.full(W, joints[0], np.float32)
            length = np.full(W, float(W), np.float32)
            seg = np.zeros(W, np.int64)
        else:
            starts = np.where(bi >= 0, joints[np.maximum(bi, 0)], joints[-1])
            ends = np.where(bi >= 0,
                            np.where(bi < k - 1,
                                     joints[np.minimum(bi + 1, k - 1)],
                                     joints[0] + W),
                            joints[0] + W)
            length = np.maximum(ends - starts, 1.0)
            seg = bi % k
        up = ((xs - starts) % W) / length
        nseg = max(k, 1)
        col_lut = np.array([palette[r.integers(0, len(palette))]
                            for _ in range(nseg)], np.float32)
        cyc = (1.4 + 1.8 * r.random(nseg)).astype(np.float32)
        phase = r.random(nseg).astype(np.float32)
        tone = (0.980 + 0.040 * r.random(nseg)).astype(np.float32)
        cols = col_lut[seg]
        grain = 0.5 + 0.5 * np.sin(2 * np.pi * (up * cyc[seg] + phase[seg]))
        grain = grain ** 3 * 0.8 + 0.2
        dist_px = np.minimum(up, 1.0 - up) * length
        joint = A.smoothstep((2.2 - dist_px) / 2.2)
        fac = tone[seg] * (0.82 + 0.26 * grain) * (1.0 - 0.20 * joint)
        row_field = 0.90 + 0.20 * grain_field[y0:y1, :]
        rgb[y0:y1] = cols[None, :, :] * (fac[None, :, None] * row_field[..., None])

    # 磨亮/打过蜡的局部
    sheen = A.smoothstep((broad - 0.58) / 0.14)
    rgb *= (1.0 + 0.16 * sheen)[..., None]

    # 横向拼缝（+0.5 使缝中心落在贴图边界上，平铺后左右对称）
    ry = (yy + 0.5) % rh
    dist_y = np.minimum(ry, rh - ry)
    groove = A.smoothstep((1.7 - dist_y) / 1.7)
    rgb *= (1.0 - 0.22 * groove)[..., None]
    groove_hi = np.exp(-((dist_y - 3.0) / 1.4) ** 2)
    rgb += (0.028 * groove_hi)[..., None]

    # 污垢、磨损、划痕
    dirt = A.blobs(shape, [(r.uniform(0, H), r.uniform(0, W),
                            r.uniform(6, 26), r.uniform(0.25, 0.6))
                           for _ in range(24)], feather=4.0)
    rgb = A.over(rgb, A.hexc("#2e1d15"), dirt, 0.32)
    worn = A.smoothstep((A.fbm(shape, 7, 4, r) - 0.66) / 0.1)
    rgb = A.over(rgb, A.hexc("#8f6248"), worn, 0.14)
    segs = [(r.uniform(0, W), r.uniform(0, H),
             r.uniform(0, W), r.uniform(0, H), r.uniform(0.7, 2.0))
            for _ in range(30)]
    sc = A.seg_mask(shape, segs, feather=0.9)
    rgb = A.over(rgb, A.hexc("#b98a63"), sc, 0.18)
    dseg = [(r.uniform(0, W), r.uniform(0, H),
             r.uniform(0, W), r.uniform(0, H), r.uniform(0.6, 1.4))
            for _ in range(16)]
    rgb = A.over(rgb, A.hexc("#2a1a12"), A.seg_mask(shape, dseg, 0.9), 0.20)

    rgb = _post(rgb, r, 0.02, 0.16, contrast=1.02)
    return _down(rgb, w, h)


# ------------------------------------------------------------------ 木门（旧红漆）

def build_wood_door(w, h):
    W, H = _work(w, h)
    shape = (H, W)
    r = A.rng("wood_door")
    yy, xx = A.coords(shape)

    rgb = A.mix(A.hexc("#4e241c")[None, None], A.hexc("#703526")[None, None],
                A.fbm(shape, 3, 5, r)[..., None])
    grain = A.fbm(shape, 0, 4, r, aniso=(6, 130))
    rgb *= (0.86 + 0.26 * grain)[..., None]

    # 竖板缝（6 块板）
    period = W / 6.0
    seam_d = np.minimum(xx % period, period - (xx % period))
    seam = A.smoothstep((2.2 - seam_d) / 2.2)
    rgb *= (1.0 - 0.22 * seam)[..., None]

    # 旧漆起皮：小面积、低对比
    chipfield = A.fbm(shape, 5, 5, r, persistence=0.58)
    chips = A.smoothstep((chipfield - 0.705) / 0.012) * 0.9
    tiny = A.smoothstep((A.pnoise(shape, (150, 150), r) - 0.825) / 0.02) * 0.45
    chips = np.clip(chips + tiny, 0, 1)
    pale = A.mix(A.hexc("#8a6f48")[None, None], A.hexc("#a3855a")[None, None],
                 A.fbm(shape, 0, 3, r, aniso=(6, 100))[..., None])
    rgb = A.mix(rgb, pale, chips * 0.80)
    rim = np.clip(A.blur(chips, 1.0, periodic=True) - chips, 0, 1)
    rgb = A.over(rgb, A.hexc("#33201a"), rim, 0.42)

    # 竖向油污/水痕
    streak = A.smoothstep((A.fbm(shape, 0, 4, r, aniso=(60, 2)) - 0.55) / 0.18)
    rgb *= (1.0 - 0.20 * streak)[..., None]

    segs = [(r.uniform(0, W), r.uniform(0, H),
             r.uniform(0, W), r.uniform(0, H), r.uniform(0.6, 1.6))
            for _ in range(22)]
    rgb = A.over(rgb, A.hexc("#c8a57c"), A.seg_mask(shape, segs, 0.9), 0.18)
    dsegs = [(r.uniform(0, W), r.uniform(0, H),
              r.uniform(0, W), r.uniform(0, H), r.uniform(0.6, 1.4))
             for _ in range(14)]
    rgb = A.over(rgb, A.hexc("#2a1712"), A.seg_mask(shape, dsegs, 0.9), 0.22)

    rgb = _post(rgb, r, 0.022, 0.16)
    return _down(rgb, w, h)


# ------------------------------------------------------------------ 深色/浅色木

def build_wood_dark(w, h):
    W, H = _work(w, h)
    shape = (H, W)
    r = A.rng("wood_dark")
    rgb = A.mix(A.hexc("#33251d")[None, None], A.hexc("#4b3628")[None, None],
                A.fbm(shape, 3, 5, r)[..., None])
    grain = A.fbm(shape, 0, 4, r, aniso=(5, 100))
    rgb *= (0.86 + 0.26 * grain)[..., None]
    fine = A.pnoise(shape, (240, 28), r)
    rgb *= (0.94 + 0.12 * fine)[..., None]
    # 使用痕迹：擦亮的边与浅划痕
    sheen = A.smoothstep((A.fbm(shape, 3, 3, r) - 0.62) / 0.15)
    rgb *= (1.0 + 0.18 * sheen)[..., None]
    segs = [(r.uniform(0, W), r.uniform(0, H),
             r.uniform(0, W), r.uniform(0, H), r.uniform(0.6, 1.5))
            for _ in range(20)]
    rgb = A.over(rgb, A.hexc("#7a5a42"), A.seg_mask(shape, segs, 0.9), 0.18)
    dirt = A.blobs(shape, [(r.uniform(0, H), r.uniform(0, W),
                            r.uniform(8, 30), 0.6) for _ in range(14)], feather=5)
    rgb = A.over(rgb, A.hexc("#1e1510"), dirt, 0.25)
    rgb = _post(rgb, r, 0.018, 0.14)
    return _down(rgb, w, h)


def build_wood_pale(w, h):
    W, H = _work(w, h)
    shape = (H, W)
    r = A.rng("wood_pale")
    rgb = A.mix(A.hexc("#bda274")[None, None], A.hexc("#d6c191")[None, None],
                A.fbm(shape, 3, 5, r)[..., None])
    # 三合板的大片木纹（横向条纹 + 拉长噪声）
    bands = 0.5 + 0.5 * np.sin(2 * np.pi * (A.coords(shape)[0] * 8.0 / H
                                           + 0.12 * A.fbm(shape, 2, 3, r)))
    grain = A.fbm(shape, 0, 4, r, aniso=(60, 4))
    rgb *= (0.90 + 0.16 * bands + 0.10 * grain)[..., None]
    # 节疤
    knot_centers = [(r.uniform(0, H), r.uniform(0, W)) for _ in range(3)]
    for (ky, kx) in knot_centers:
        d = A.radial_field(shape, kx, ky, W * 0.05, periodic=True)
        ring = np.exp(-((d - 0.75) / 0.18) ** 2)
        core = np.exp(-(d / 0.35) ** 2)
        rgb = A.over(rgb, A.hexc("#7c5a36"), ring, 0.5)
        rgb = A.over(rgb, A.hexc("#4f3720"), core, 0.7)
    # 水渍/污渍
    wat = A.smoothstep((A.fbm(shape, 5, 4, r) - 0.58) / 0.12)
    rgb = A.over(rgb, A.hexc("#8c7444"), wat, 0.28)
    dirt = A.blobs(shape, [(r.uniform(0, H), r.uniform(0, W),
                            r.uniform(8, 30), 0.6) for _ in range(18)], feather=5)
    rgb = A.over(rgb, A.hexc("#5f5034"), dirt, 0.25)
    segs = [(r.uniform(0, W), r.uniform(0, H),
             r.uniform(0, W), r.uniform(0, H), r.uniform(0.7, 1.8))
            for _ in range(24)]
    rgb = A.over(rgb, A.hexc("#8a7148"), A.seg_mask(shape, segs, 0.9), 0.22)
    rgb = _post(rgb, r, 0.024, 0.16)
    return _down(rgb, w, h)


# ------------------------------------------------------------------ 顶棚

def build_paint_ceiling(w, h):
    W, H = _work(w, h)
    shape = (H, W)
    r = A.rng("paint_ceiling")
    yy, xx = A.coords(shape)
    rgb = A.mix(A.hexc("#bdb8a8")[None, None], A.hexc("#d8d4c6")[None, None],
                A.fbm(shape, 3, 5, r)[..., None])
    rgb *= (0.94 + 0.09 * A.pnoise(shape, (140, 140), r))[..., None]

    # 水渍：2 圈不规则的黄褐色水痕
    for _ in range(3):
        cyc, cxc = r.uniform(0, H), r.uniform(0, W)
        R = r.uniform(W * 0.10, W * 0.20)
        dy, dx = A.torus_delta(yy, xx, cyc, cxc, H, W)
        d = np.sqrt(dy * dy + dx * dx)
        ang = np.arctan2(dy, dx)
        rn = R * (1.0 + 0.22 * np.sin(3 * ang + r.uniform(0, 6))
                  + 0.10 * np.sin(7 * ang + r.uniform(0, 6)))
        ring = np.exp(-((d - rn) / (W * 0.010)) ** 2)
        inside = A.smoothstep((rn - d) / (W * 0.06))
        rgb = A.over(rgb, A.hexc("#a8905c"), inside, 0.16)
        rgb = A.over(rgb, A.hexc("#7c6236"), ring, 0.55)

    # 霉点与裂纹
    mold = A.blobs(shape, [(r.uniform(0, H), r.uniform(0, W), r.uniform(1.5, 9),
                            r.uniform(0.3, 0.85)) for _ in range(26)], feather=2.0)
    rgb = A.over(rgb, A.hexc("#3f4229"), mold, 0.65)
    crack = A.smoothstep((A.ridged(shape, 4, 4, r) - 0.985) / 0.01)
    rgb = A.over(rgb, A.hexc("#6d6656"), crack, 0.5)
    scuffs = A.seg_mask(shape, [(r.uniform(0, W), r.uniform(0, H),
                                 r.uniform(0, W), r.uniform(0, H),
                                 r.uniform(0.7, 1.6)) for _ in range(14)], 1.0)
    rgb = A.over(rgb, A.hexc("#9b9482"), scuffs, 0.22)
    rgb = _post(rgb, r, 0.02, 0.18)
    return _down(rgb, w, h)


# ------------------------------------------------------------------ 水泥

def build_concrete(w, h):
    W, H = _work(w, h)
    shape = (H, W)
    r = A.rng("concrete")
    rgb = A.mix(A.hexc("#716f66")[None, None], A.hexc("#94918a")[None, None],
                A.fbm(shape, 3, 5, r)[..., None])
    rgb *= (0.88 + 0.18 * A.pnoise(shape, (90, 90), r))[..., None]
    # 骨料颗粒
    agg = A.pnoise(shape, (300, 300), r)
    bright = A.smoothstep((agg - 0.78) / 0.05)
    dark = A.smoothstep((0.20 - agg) / 0.04)
    rgb = A.over(rgb, A.hexc("#c0bcb0"), bright, 0.5)
    rgb = A.over(rgb, A.hexc("#3f3d37"), dark, 0.6)
    # 大块补丁
    patch = A.smoothstep((A.fbm(shape, 4, 4, r) - 0.58) / 0.05)
    rgb = A.over(rgb, A.hexc("#6a675e"), patch, 0.35)
    # 裂缝
    crack = A.smoothstep((A.ridged(shape, 4, 4, r) - 0.978) / 0.012)
    rgb = A.over(rgb, A.hexc("#35332d"), crack, 0.7)
    crack2 = A.smoothstep((A.ridged(shape, 8, 3, r) - 0.992) / 0.006)
    rgb = A.over(rgb, A.hexc("#4d4a43"), crack2, 0.35)
    # 潮湿/油污
    damp = A.smoothstep((A.fbm(shape, 5, 4, r) - 0.60) / 0.12)
    rgb = A.over(rgb, A.hexc("#4c4d46"), damp, 0.4)
    oil = A.blobs(shape, [(r.uniform(0, H), r.uniform(0, W), r.uniform(10, 28),
                          r.uniform(0.2, 0.5)) for _ in range(14)], feather=6)
    rgb = A.over(rgb, A.hexc("#3c3a33"), oil, 0.35)
    sc = A.seg_mask(shape, [(r.uniform(0, W), r.uniform(0, H),
                             r.uniform(0, W), r.uniform(0, H),
                             r.uniform(0.7, 2.0)) for _ in range(26)], 1.0)
    rgb = A.over(rgb, A.hexc("#b3afa4"), sc, 0.18)
    rgb = _post(rgb, r, 0.026, 0.16)
    return _down(rgb, w, h)


# ------------------------------------------------------------------ 瓷砖

def _tile_surface(w, h, name, palette, grout_col, grout_px, cells=16,
                  weather=1.0, chip_n=14, mold_amt=1.0, streak_col="#c9c9b8",
                  streak_amt=0.18, fine_grout=True):
    W, H = _work(w, h)
    shape = (H, W)
    r = A.rng(name)
    yy, xx = A.coords(shape)
    cell = W / cells

    gx = xx + 0.5
    gy = yy + 0.5
    fx = (gx % cell) / cell
    fy = (gy % cell) / cell
    ti = (np.floor(gx / cell).astype(int)) % cells
    tj = (np.floor(gy / cell).astype(int)) % cells
    var = r.random((cells, cells)).astype(np.float32)
    palette_arr = np.array([A.hexc(c) for c in palette], np.float32)
    idx = np.minimum((var * len(palette)).astype(int), len(palette) - 1)
    tile_col = palette_arr[idx]           # (cells,cells,3)
    cols = tile_col[tj, ti]               # (H,W,3)

    # 每块砖的细微明暗 + 倒角（光从左上）
    per_tile = (0.90 + 0.16 * var)[tj, ti]
    bevel = per_tile * (1.0 + 0.10 * (0.5 - fy) - 0.06 * (fx - 0.5))
    cols = cols * bevel[..., None]

    # 灰缝
    ex = np.minimum(fx, 1.0 - fx) * cell
    ey = np.minimum(fy, 1.0 - fy) * cell
    edge_px = np.minimum(ex, ey)
    grout = A.smoothstep((grout_px * 0.5 + 1.0 - edge_px) / 1.2)
    gcol = A.hexc(grout_col)
    grout_var = 0.85 + 0.30 * A.pnoise(shape, (200, 200), r if fine_grout else r)
    gcol_img = gcol[None, None] * grout_var[..., None]
    rgb = A.mix(cols, gcol_img, grout)

    # 水垢/白华：顺墙下流的浅色条纹
    streak = A.smoothstep((A.fbm(shape, 0, 4, r, aniso=(40, 3)) - 0.55) / 0.18)
    rgb = A.over(rgb, A.hexc(streak_col), streak * grout, 0.35)
    rgb = A.over(rgb, A.hexc(streak_col),
                 streak * (1 - grout) * 0.5, streak_amt)

    # 黄褐色水渍
    wat = A.smoothstep((A.fbm(shape, 4, 4, r) - 0.62) / 0.10)
    rgb = A.over(rgb, A.hexc("#8f7442"), wat, 0.20 * weather)

    # 灰缝里的霉
    mold = A.blobs(shape, [(r.uniform(0, H), r.uniform(0, W),
                            r.uniform(1.0, 5.0), r.uniform(0.3, 0.8))
                           for _ in range(int(46 * mold_amt))], feather=1.8)
    mold *= (0.4 + 0.6 * grout)
    rgb = A.over(rgb, A.hexc("#252b1d"), mold, 0.8)

    # 缺角/崩边
    chips_specs = []
    for _ in range(chip_n):
        ci, cj = r.integers(0, cells), r.integers(0, cells)
        # 放在砖的某个角
        corner_x = (cj + (0.0 if r.random() < 0.5 else 1.0)) * cell
        corner_y = (ci + (0.0 if r.random() < 0.5 else 1.0)) * cell
        chips_specs.append((corner_y + r.normal(0, 3), corner_x + r.normal(0, 3),
                            r.uniform(2, 6), 1.0))
    chips = A.blobs(shape, chips_specs, feather=1.3)
    rgb = A.over(rgb, gcol * 0.85, chips, 0.75)

    # 划痕与污垢
    sc = A.seg_mask(shape, [(r.uniform(0, W), r.uniform(0, H),
                             r.uniform(0, W), r.uniform(0, H),
                             r.uniform(0.6, 1.4)) for _ in range(18)], 0.9)
    rgb = A.over(rgb, A.hexc("#d2d0c2"), sc, 0.16)
    dirt = A.blobs(shape, [(r.uniform(0, H), r.uniform(0, W),
                            r.uniform(6, 24), r.uniform(0.2, 0.5))
                           for _ in range(20)], feather=5)
    rgb = A.over(rgb, A.hexc("#3a3730"), dirt, 0.22)
    rgb = _post(rgb, r, 0.02, 0.14, contrast=1.01)
    return _down(rgb, w, h)


def build_tile_green(w, h):
    return _tile_surface(w, h, "tile_green",
                         ["#3c5748", "#446251", "#37504a", "#4a6552", "#3a5450"],
                         "#252a22", 3.2, weather=1.35, mold_amt=1.6,
                         streak_col="#c4cbb8", streak_amt=0.26)


def build_tile_white(w, h):
    return _tile_surface(w, h, "tile_white",
                         ["#d0ccbe", "#c7c1b0", "#d6d2c3", "#c2bba6", "#cbc5b6"],
                         "#5a584d", 3.0, weather=1.6, mold_amt=1.6,
                         streak_col="#b9a97e", streak_amt=0.26)


def build_tile_floor(w, h):
    return _tile_surface(w, h, "tile_floor",
                         ["#8a7f66", "#9a8a6a", "#7a6f5a", "#a08d6d",
                          "#6f6553", "#8f8270"],
                         "#3d3a30", 3.4, weather=1.3, mold_amt=0.8,
                         streak_col="#b8ad90", streak_amt=0.12)


# ------------------------------------------------------------------ 金属

def build_metal_locker(w, h):
    W, H = _work(w, h)
    shape = (H, W)
    r = A.rng("metal_locker")
    rgb = A.mix(A.hexc("#5c7068")[None, None], A.hexc("#7f9087")[None, None],
                A.fbm(shape, 3, 4, r)[..., None])
    brush = A.fbm(shape, 0, 4, r, aniso=(4, 190))
    rgb *= (0.90 + 0.16 * brush)[..., None]
    # 大面积轻微褪色
    fade = A.smoothstep((A.fbm(shape, 3, 3, r) - 0.55) / 0.18)
    rgb = A.over(rgb, A.hexc("#9daaa1"), fade, 0.14)
    # 掉漆露铁（少量）+ 锈
    chip = A.smoothstep((A.fbm(shape, 5, 5, r, persistence=0.58) - 0.755) / 0.02)
    rgb = A.over(rgb, A.hexc("#8a8a82"), chip, 0.75)
    rust = A.smoothstep((A.fbm(shape, 7, 4, r) - 0.74) / 0.05) * chip
    rgb = A.over(rgb, A.hexc("#7a4a2c"), rust, 0.6)
    # 凹痕阴影
    dent = A.blobs(shape, [(r.uniform(0, H), r.uniform(0, W), r.uniform(8, 26),
                           r.uniform(0.12, 0.3)) for _ in range(10)], feather=6)
    rgb = A.over(rgb, A.hexc("#42504a"), dent, 0.3)
    # 划痕（更明显）
    sc = A.seg_mask(shape, [(r.uniform(0, W), r.uniform(0, H),
                             r.uniform(0, W), r.uniform(0, H),
                             r.uniform(0.6, 1.6)) for _ in range(40)], 0.9)
    rgb = A.over(rgb, A.hexc("#c9cec4"), sc, 0.26)
    # 灰与污
    dirt = A.blobs(shape, [(r.uniform(0, H), r.uniform(0, W), r.uniform(8, 26),
                           r.uniform(0.15, 0.4)) for _ in range(16)], feather=5)
    rgb = A.over(rgb, A.hexc("#4c4a3e"), dirt, 0.25)
    rgb = _post(rgb, r, 0.02, 0.13)
    return _down(rgb, w, h)


def build_metal_rust(w, h):
    W, H = _work(w, h)
    shape = (H, W)
    r = A.rng("metal_rust")
    rgb = A.mix(A.hexc("#4b3a2c")[None, None], A.hexc("#65503c")[None, None],
                A.fbm(shape, 3, 5, r)[..., None])
    rustf = A.fbm(shape, 4, 5, r)
    rust = A.smoothstep((rustf - 0.50) / 0.30)
    rc = A.ramp(rustf, [0.0, 0.45, 0.7, 1.0],
                [A.hexc("#4f3a2a"), A.hexc("#65412a"),
                 A.hexc("#82521f"), A.hexc("#9a642d")])
    rgb = A.mix(rgb, rc, rust * 0.85)
    # 锈皮的亮边与暗边
    flake = A.smoothstep((A.ridged(shape, 6, 4, r) - 0.96) / 0.02)
    rgb = A.over(rgb, A.hexc("#b57f42"), flake, 0.35)
    fdark = np.clip(A.smoothstep((A.ridged(shape, 6, 4, r) - 0.87) / 0.03) - flake, 0, 1)
    rgb = A.over(rgb, A.hexc("#2f1e13"), fdark, 0.45)
    # 锈坑与孔洞
    pits = A.blobs(shape, [(r.uniform(0, H), r.uniform(0, W), r.uniform(1.5, 6),
                           r.uniform(0.4, 0.9)) for _ in range(36)], feather=1.5)
    rgb = A.over(rgb, A.hexc("#241408"), pits, 0.7)
    holes = A.blobs(shape, [(r.uniform(0, H), r.uniform(0, W), r.uniform(2, 4.5),
                             1.0) for _ in range(4)], feather=0.8)
    rgb = A.over(rgb, A.hexc("#0c0805"), holes, 0.9)
    # 残留铁灰与尘土
    bare = A.smoothstep((A.fbm(shape, 5, 4, r) - 0.62) / 0.12)
    rgb = A.mix(rgb, A.hexc("#5b574d"), bare * 0.4)
    dust = A.smoothstep((A.pnoise(shape, (230, 230), r) - 0.72) / 0.1)
    rgb = A.over(rgb, A.hexc("#8d7a5c"), dust, 0.22)
    rgb = _post(rgb, r, 0.026, 0.16)
    return _down(rgb, w, h)


# ------------------------------------------------------------------ 玻璃/窗

def build_glass_dirty(w, h):
    W, H = _work(w, h)
    shape = (H, W)
    r = A.rng("glass_dirty")
    yy, xx = A.coords(shape)
    rgb = A.mix(A.hexc("#2b3734")[None, None], A.hexc("#4a5650")[None, None],
                (yy / H)[..., None] * 0.7 + 0.15)
    # 斜向反光条
    proj = (xx * 0.82 + yy * 0.57) / W
    bands = 0.5 + 0.5 * np.sin(2 * np.pi * (proj * 3.0 + 0.15))
    bands = A.blur(bands, 6.0) ** 1.5
    rgb = A.over(rgb, A.hexc("#a9bdb4"), bands, 0.45)
    band2 = 0.5 + 0.5 * np.sin(2 * np.pi * (proj * 1.3 + 0.62))
    rgb = A.over(rgb, A.hexc("#7d968d"), A.blur(band2, 12.0), 0.22)
    # 窗框投影（左右两条暗边）
    edge_ln = np.exp(-(xx / (W * 0.05)) ** 2) + np.exp(-(((W - xx)) / (W * 0.05)) ** 2)
    rgb *= (1.0 - 0.35 * edge_ln)[..., None]
    # 水垢/雨痕/污点
    spots = [(r.uniform(0, H), r.uniform(0, W), r.uniform(2, 9), r.uniform(0.2, 0.6))
             for _ in range(70)]
    rgb = A.over(rgb, A.hexc("#c8cabc"), A.blobs(shape, spots, feather=2.0), 0.25)
    smudge = A.blobs(shape, [(r.uniform(0, H), r.uniform(0, W), r.uniform(14, 40),
                             r.uniform(0.2, 0.5)) for _ in range(8)], feather=12)
    rgb = A.over(rgb, A.hexc("#121b18"), smudge, 0.32)
    # 雨痕
    rain = A.smoothstep((A.fbm(shape, 0, 4, r, aniso=(60, 2)) - 0.58) / 0.14)
    rgb = A.over(rgb, A.hexc("#7c8f88"), rain, 0.18)
    dust = A.fbm(shape, 6, 5, r)
    rgb *= (0.88 + 0.18 * dust)[..., None]
    # 边缘暗角
    vg = A.vignette_mask(shape, 0.50, 2.0)
    rgb *= vg[..., None]
    rgb = _post(rgb, r, 0.02, 0.12)
    return _down(rgb, w, h)


def build_window_night(w, h):
    W, H = _work(w, h)
    shape = (H, W)
    r = A.rng("window_night")
    yy, xx = A.coords(shape)
    top = A.hexc("#070d14")
    mid = A.hexc("#0d1720")
    bot = A.hexc("#16222b")
    rgb = A.gradient_v(H, W, [0.0, 0.62, 1.0], [top, mid, bot])
    # 云/雾
    cloud = A.fbm(shape, 3, 4, r)
    rgb += (cloud[..., None] - 0.5) * np.array([0.02, 0.03, 0.035], np.float32)
    # 远处零星暖灯
    specs = [(r.uniform(H * 0.30, H * 0.85), r.uniform(0, W),
              r.uniform(2, 5), 1.0) for _ in range(14)]
    lights = A.blobs(shape, specs, feather=2.5)
    lights = A.blur(lights, 1.5, periodic=False)
    rgb = A.over(rgb, A.hexc("#ffb25e"), np.clip(lights * 1.4, 0, 1), 0.85)
    glow = A.blur(lights, 9.0, periodic=False)
    rgb = A.over(rgb, A.hexc("#b06a2c"), np.clip(glow * 2.2, 0, 1), 0.35)
    # 一点月光/反光
    proj = (xx * 0.7 + yy * 0.7) / W
    refl = A.smoothstep((0.5 + 0.5 * np.sin(2 * np.pi * (proj * 1.4 + 0.2)) - 0.75) / 0.1)
    rgb = A.over(rgb, A.hexc("#4a6a74"), A.blur(refl, 8.0), 0.15)
    # 玻璃脏与暗角
    dirt = A.fbm(shape, 8, 4, r)
    rgb *= (0.88 + 0.18 * dirt)[..., None]
    vg = A.vignette_mask(shape, 0.5, 1.8)
    rgb *= vg[..., None]
    rgb = _post(rgb, r, 0.018, 0.05)
    return _down(rgb, w, h)


# ------------------------------------------------------------------ 窗帘

def build_curtain(w, h):
    W, H = _work(w, h)
    shape = (H, W)
    r = A.rng("curtain")
    yy, xx = A.coords(shape)
    pleat = 0.5 + 0.5 * np.cos(2 * np.pi * xx * 6.0 / W)
    pleat = pleat ** 1.4
    base = A.mix(A.hexc("#b3a67e")[None, None], A.hexc("#d3c69c")[None, None],
                 A.fbm(shape, 3, 4, r)[..., None])
    rgb = base * (0.58 + 0.55 * pleat)[..., None]
    # 织纹
    weave = A.pnoise(shape, (260, 40), r)
    rgb *= (0.92 + 0.13 * weave)[..., None]
    # 蕾丝小花点
    cell = W / 16.0
    fx = (xx % cell) / cell
    fy = (yy % cell) / cell
    lace = np.exp(-(((fx - 0.5) / 0.18) ** 2 + ((fy - 0.5) / 0.24) ** 2))
    lace *= A.smoothstep((0.55 - A.pnoise(shape, (80, 80), r)) / 0.15)
    rgb = A.over(rgb, A.hexc("#a2936e"), lace, 0.22)
    # 泛黄水渍
    stain = A.smoothstep((A.fbm(shape, 4, 4, r) - 0.60) / 0.12)
    rgb = A.over(rgb, A.hexc("#9c8545"), stain, 0.30)
    # 竖向褶皱阴影与灰尘
    shade = A.smoothstep((A.fbm(shape, 0, 4, r, aniso=(24, 2)) - 0.55) / 0.2)
    rgb *= (1.0 - 0.20 * shade)[..., None]
    rgb = _post(rgb, r, 0.022, 0.2)
    return _down(rgb, w, h)


# ------------------------------------------------------------------ 土路

def build_soil(w, h):
    W, H = _work(w, h)
    shape = (H, W)
    r = A.rng("soil")
    yy, xx = A.coords(shape)
    rgb = A.mix(A.hexc("#5b4a36")[None, None], A.hexc("#7d6a4f")[None, None],
                A.fbm(shape, 3, 5, r)[..., None])
    mottle = A.fbm(shape, 8, 5, r)
    rgb *= (0.84 + 0.28 * mottle)[..., None]

    # 车辙（沿 y 方向、轻摆）
    phase1 = 2 * np.pi * yy / H
    xc1 = W * (0.34 + 0.03 * np.sin(phase1 + 0.7))
    xc2 = W * (0.64 + 0.03 * np.sin(phase1 + 2.4))
    for xc in (xc1, xc2):
        band = np.exp(-((xx - xc) / (W * 0.065)) ** 2)
        rgb *= (1.0 - 0.10 * band)[..., None]
    # 中间的踩踏暗带
    mid = np.exp(-((xx - W * 0.5) / (W * 0.16)) ** 2)
    rgb *= (1.0 - 0.06 * mid)[..., None]

    # 碎石（带一点亮边）
    agg = A.pnoise(shape, (300, 300), r)
    bright = A.smoothstep((agg - 0.78) / 0.05)
    dark = A.smoothstep((0.22 - agg) / 0.04)
    rgb = A.over(rgb, A.hexc("#a08f74"), bright, 0.5)
    rgb = A.over(rgb, A.hexc("#2f261c"), dark, 0.55)
    pebbles = A.blobs(shape, [(r.uniform(0, H), r.uniform(0, W),
                              r.uniform(1.2, 3.2), 1.0) for _ in range(34)],
                      feather=1.0)
    hi = np.roll(pebbles, (-1, -1), axis=(0, 1)) - pebbles * 0.7
    rgb = A.over(rgb, A.hexc("#8f8168"), pebbles, 0.45)
    rgb = A.over(rgb, A.hexc("#d0c2a2"), np.clip(hi, 0, 1), 0.35)

    # 干草茎
    for col, amt in ((A.hexc("#8c7a45"), 0.42), (A.hexc("#6b6037"), 0.32)):
        segs = []
        for _ in range(24):
            x0, y0 = r.uniform(0, W), r.uniform(0, H)
            ang = r.normal(0.3, 0.5)
            L = r.uniform(5, 16)
            segs.append((x0, y0, x0 + math.cos(ang) * L, y0 + math.sin(ang) * L,
                         r.uniform(0.7, 1.3)))
        rgb = A.over(rgb, col, A.seg_mask(shape, segs, 0.8), amt)

    # 潮湿暗斑
    damp = A.blobs(shape, [(r.uniform(0, H), r.uniform(0, W), r.uniform(8, 30),
                           r.uniform(0.12, 0.35)) for _ in range(20)], feather=6)
    rgb = A.over(rgb, A.hexc("#2d251b"), damp, 0.3)
    # 干土亮斑
    dry = A.smoothstep((A.fbm(shape, 7, 4, r) - 0.66) / 0.1)
    rgb = A.over(rgb, A.hexc("#94805e"), dry, 0.15)
    rgb = _post(rgb, r, 0.028, 0.1)
    return _down(rgb, w, h)


# ------------------------------------------------------------------ 草

def build_grass(w, h):
    W, H = _work(w, h)
    shape = (H, W)
    r = A.rng("grass")
    yy, xx = A.coords(shape)
    rgb = A.mix(A.hexc("#131a0e")[None, None], A.hexc("#28331a")[None, None],
                A.fbm(shape, 3, 4, r)[..., None])
    rgb *= (0.82 + 0.3 * A.fbm(shape, 9, 4, r))[..., None]

    groups = [("#31401d", 70, 0.85), ("#445525", 62, 0.8),
              ("#596a2d", 46, 0.7), ("#243318", 60, 0.8),
              ("#6d6a34", 22, 0.55)]
    for color, n, alpha in groups:
        segs = []
        for _ in range(n):
            x0, y0 = r.uniform(0, W), r.uniform(0, H)
            ang = -np.pi / 2 + r.normal(0, 0.55)
            L = r.uniform(H * 0.05, H * 0.16)
            x1 = x0 + math.cos(ang) * L
            y1 = y0 + math.sin(ang) * L
            segs.append((x0, y0, x1, y1, r.uniform(1.1, 2.6)))
        mask = A.seg_mask(shape, segs, feather=0.85)
        rgb = A.over(rgb, A.hexc(color), mask, alpha)
    # 露水/亮点
    dew = A.smoothstep((A.pnoise(shape, (280, 280), r) - 0.82) / 0.04)
    rgb = A.over(rgb, A.hexc("#9fae7a"), dew, 0.25)
    # 泥土暗部
    dirt = A.smoothstep((A.fbm(shape, 5, 4, r) - 0.62) / 0.1)
    rgb = A.over(rgb, A.hexc("#1a140d"), dirt, 0.4)
    rgb = _post(rgb, r, 0.022, 0.12)
    return _down(rgb, w, h)


# ------------------------------------------------------------------ 树皮/树叶

def build_bark(w, h):
    W, H = _work(w, h)
    shape = (H, W)
    r = A.rng("bark")
    ridge = A.fbm(shape, 0, 4, r, aniso=(8, 30))
    ridge = 1.0 - np.abs(ridge * 2 - 1)
    ridge = ridge ** 1.6
    rgb = A.ramp(ridge, [0.0, 0.35, 0.6, 0.85, 1.0],
                 [A.hexc("#2e2620"), A.hexc("#4a3d31"),
                  A.hexc("#5d4c3b"), A.hexc("#6d5a46"),
                  A.hexc("#7d6a52")])
    # 纵向裂隙
    crack = A.smoothstep((A.ridged(shape, 7, 3, r) - 0.985) / 0.01)
    rgb = A.over(rgb, A.hexc("#1a140f"), crack, 0.7)
    # 横向小裂纹
    sc = A.seg_mask(shape, [(r.uniform(0, W), r.uniform(0, H),
                             r.uniform(0, W), r.uniform(0, H),
                             r.uniform(0.5, 1.1)) for _ in range(30)], 0.7)
    rgb = A.over(rgb, A.hexc("#241b14"), sc, 0.35)
    # 地衣/苔
    lich = A.blobs(shape, [(r.uniform(0, H), r.uniform(0, W), r.uniform(2, 9),
                           r.uniform(0.2, 0.55)) for _ in range(34)], feather=2.5)
    rgb = A.over(rgb, A.hexc("#7b8158"), lich, 0.35)
    rgb = _post(rgb, r, 0.024, 0.1)
    return _down(rgb, w, h)


def build_leaves(w, h):
    W, H = _work(w, h)
    shape = (H, W)
    r = A.rng("leaves")
    rgb = A.mix(A.hexc("#0d130a")[None, None], A.hexc("#1b2412")[None, None],
                A.fbm(shape, 3, 4, r)[..., None])
    layers = [("#1c2a12", 26, 0.95), ("#283a18", 26, 0.9),
              ("#34461d", 22, 0.85), ("#415523", 16, 0.8),
              ("#4d4a22", 8, 0.6)]
    for color, n, alpha in layers:
        specs = []
        for _ in range(n):
            cy, cx = r.uniform(0, H), r.uniform(0, W)
            L = r.uniform(H * 0.05, H * 0.13)
            specs.append((cy, cx, L * 0.5, L * 0.28,
                          r.uniform(0, math.pi), r.uniform(0.6, 1.0)))
        rgb = A.over(rgb, A.hexc(color), A.ellipses(shape, specs, feather=1.6),
                     alpha)
    # 叶脉高光
    segs = []
    for _ in range(60):
        x0, y0 = r.uniform(0, W), r.uniform(0, H)
        ang = r.uniform(0, math.pi)
        L = r.uniform(3, 9)
        segs.append((x0, y0, x0 + math.cos(ang) * L, y0 + math.sin(ang) * L, 0.7))
    rgb = A.over(rgb, A.hexc("#5e6b38"), A.seg_mask(shape, segs, 0.8), 0.22)
    # 暗部空隙
    gap = A.smoothstep((A.fbm(shape, 5, 4, r) - 0.68) / 0.08)
    rgb = A.over(rgb, A.hexc("#070a05"), gap, 0.5)
    rgb = _post(rgb, r, 0.024, 0.1)
    return _down(rgb, w, h)


# ------------------------------------------------------------------ 石头

def build_stone(w, h):
    W, H = _work(w, h)
    shape = (H, W)
    r = A.rng("stone")
    rgb = A.mix(A.hexc("#605e56")[None, None], A.hexc("#87857b")[None, None],
                A.fbm(shape, 3, 5, r)[..., None])
    rgb *= (0.85 + 0.25 * A.pnoise(shape, (160, 160), r))[..., None]
    # 花岗岩颗粒
    agg = A.pnoise(shape, (300, 300), r)
    rgb = A.over(rgb, A.hexc("#c4c1b4"), A.smoothstep((agg - 0.80) / 0.05), 0.5)
    rgb = A.over(rgb, A.hexc("#3c3a34"), A.smoothstep((0.18 - agg) / 0.04), 0.55)
    # 裂缝与崩口
    crack = A.smoothstep((A.ridged(shape, 4, 4, r) - 0.982) / 0.01)
    rgb = A.over(rgb, A.hexc("#2f2d28"), crack, 0.6)
    pits = A.blobs(shape, [(r.uniform(0, H), r.uniform(0, W), r.uniform(1.5, 7),
                           r.uniform(0.3, 0.8)) for _ in range(40)], feather=1.6)
    rgb = A.over(rgb, A.hexc("#46443d"), pits, 0.5)
    # 苔/水渍
    moss = A.blobs(shape, [(r.uniform(0, H), r.uniform(0, W), r.uniform(3, 14),
                           r.uniform(0.25, 0.6)) for _ in range(24)], feather=4)
    rgb = A.over(rgb, A.hexc("#4a5232"), moss, 0.5)
    damp = A.smoothstep((A.fbm(shape, 4, 4, r) - 0.62) / 0.1)
    rgb = A.over(rgb, A.hexc("#3d4038"), damp, 0.3)
    rgb = _post(rgb, r, 0.024, 0.08)
    return _down(rgb, w, h)


# ------------------------------------------------------------------ 庙宇旧红木

def build_shrine_wood(w, h):
    W, H = _work(w, h)
    shape = (H, W)
    r = A.rng("shrine_wood")
    rgb = A.mix(A.hexc("#5a2a22")[None, None], A.hexc("#7d3b2b")[None, None],
                A.fbm(shape, 3, 5, r)[..., None])
    grain = A.fbm(shape, 0, 4, r, aniso=(6, 90))
    rgb *= (0.86 + 0.24 * grain)[..., None]
    # 掉漆露木
    chip = A.smoothstep((A.fbm(shape, 4, 5, r, persistence=0.56) - 0.705) / 0.015)
    chip = np.maximum(chip, A.smoothstep((A.pnoise(shape, (70, 70), r) - 0.73) / 0.03))
    wood = A.mix(A.hexc("#6f5d45")[None, None], A.hexc("#877150")[None, None],
                 A.fbm(shape, 0, 3, r, aniso=(6, 80))[..., None])
    rgb = A.mix(rgb, wood, chip * 0.78)
    rim = np.clip(A.blur(chip, 1.1, periodic=True) - chip, 0, 1)
    rgb = A.over(rgb, A.hexc("#301711"), rim, 0.55)
    # 香火熏黑
    soot = A.smoothstep((A.fbm(shape, 4, 4, r) - 0.60) / 0.12)
    rgb = A.over(rgb, A.hexc("#241a14"), soot, 0.45)
    # 灰尘与裂纹
    dust = A.smoothstep((A.pnoise(shape, (240, 240), r) - 0.66) / 0.1)
    rgb = A.over(rgb, A.hexc("#8d8168"), dust, 0.22)
    crack = A.smoothstep((A.ridged(shape, 6, 3, r) - 0.988) / 0.008)
    rgb = A.over(rgb, A.hexc("#2a1710"), crack, 0.5)
    rgb = _post(rgb, r, 0.022, 0.08)
    return _down(rgb, w, h)


# ------------------------------------------------------------------ 清单

SPECS = [
    dict(key="MAT_wallpaper", file="wallpaper_old.jpg", w=256, h=256,
         tiled=True, fn=build_wallpaper, tint="#efe8d4",
         note="暗绿米色老墙纸，细花枝、霉点、水渍"),
    dict(key="MAT_wallpaper_dark", file="wallpaper_old_dark.jpg", w=256, h=256,
         tiled=True, fn=build_wallpaper_dark, tint="#d8d2b8",
         note="同款更深更脏的墙纸（走廊/第三轮）"),
    dict(key="MAT_plaster", file="plaster.jpg", w=256, h=256,
         tiled=True, fn=build_plaster, tint="#ffffff",
         note="剥落白灰墙，露底、裂纹、霉斑"),
    dict(key="MAT_wood_floor", file="wood_floor.jpg", w=256, h=256,
         tiled=True, fn=build_wood_floor, tint="#f0dcc8",
         note="深红棕拼板木地板，磨损与污垢"),
    dict(key="MAT_wood_door", file="wood_door.jpg", w=256, h=256,
         tiled=True, fn=build_wood_door, tint="#f2e2d2",
         note="红棕漆木门，旧漆起皮、划痕"),
    dict(key="MAT_wood_dark", file="wood_dark.jpg", w=256, h=256,
         tiled=True, fn=build_wood_dark, tint="#ffffff",
         note="深棕旧家具木纹"),
    dict(key="MAT_wood_pale", file="wood_pale.jpg", w=256, h=256,
         tiled=True, fn=build_wood_pale, tint="#f6ecd8",
         note="浅黄三合板/廉价木，水渍与节疤"),
    dict(key="MAT_paint_ceiling", file="paint_ceiling.jpg", w=256, h=256,
         tiled=True, fn=build_paint_ceiling, tint="#ffffff",
         note="脏白顶棚，水渍圈、霉点、裂纹"),
    dict(key="MAT_concrete", file="concrete.jpg", w=256, h=256,
         tiled=True, fn=build_concrete, tint="#ffffff",
         note="水泥地/楼梯间，骨料、裂缝、油污"),
    dict(key="MAT_tile_green", file="tile_green.jpg", w=256, h=256,
         tiled=True, fn=build_tile_green, tint="#ffffff",
         note="澡堂暗绿方砖，勾缝发黑、水垢"),
    dict(key="MAT_tile_white", file="tile_white.jpg", w=256, h=256,
         tiled=True, fn=build_tile_white, tint="#ffffff",
         note="白瓷砖，水垢、霉缝、崩边"),
    dict(key="MAT_tile_floor", file="tile_floor.jpg", w=256, h=256,
         tiled=True, fn=build_tile_floor, tint="#ffffff",
         note="小方砖地面，脏缝、磨损"),
    dict(key="MAT_metal_locker", file="metal_locker.jpg", w=256, h=256,
         tiled=True, fn=build_metal_locker, tint="#ffffff",
         note="更衣柜漆面金属，划痕、掉漆、锈点"),
    dict(key="MAT_metal_rust", file="metal_rust.jpg", w=256, h=256,
         tiled=True, fn=build_metal_rust, tint="#ffffff",
         note="锈蚀铁皮，锈皮、孔洞、尘土"),
    dict(key="MAT_glass_dirty", file="glass_dirty.jpg", w=256, h=256,
         tiled=False, fn=build_glass_dirty, tint="#ffffff",
         note="脏玻璃/窗，深色反光条纹、污点"),
    dict(key="MAT_window_night", file="window_night.jpg", w=256, h=256,
         tiled=False, fn=build_window_night, tint="#ffffff",
         note="窗外夜色，深蓝黑 + 零星暖灯点"),
    dict(key="MAT_curtain", file="curtain.jpg", w=256, h=256,
         tiled=True, fn=build_curtain, tint="#f4e8c8",
         note="泛黄蕾丝/的确良窗帘，褶皱与黄渍"),
    dict(key="MAT_soil", file="soil.jpg", w=256, h=256,
         tiled=True, fn=build_soil, tint="#ffffff",
         note="乡间土路，车辙、碎石、干草"),
    dict(key="MAT_grass", file="grass.jpg", w=256, h=256,
         tiled=True, fn=build_grass, tint="#ffffff",
         note="深色野草/稻田，层叠草叶"),
    dict(key="MAT_bark", file="bark.jpg", w=256, h=256,
         tiled=True, fn=build_bark, tint="#ffffff",
         note="树皮，纵裂、地衣"),
    dict(key="MAT_leaves", file="leaves.jpg", w=256, h=256,
         tiled=True, fn=build_leaves, tint="#ffffff",
         note="暗色树叶/树冠，层叠叶簇"),
    dict(key="MAT_stone", file="stone.jpg", w=256, h=256,
         tiled=True, fn=build_stone, tint="#ffffff",
         note="石头/墓碑/界碑，花岗岩颗粒、苔"),
    dict(key="MAT_shrine_wood", file="shrine_wood.jpg", w=256, h=256,
         tiled=True, fn=build_shrine_wood, tint="#ffffff",
         note="土地庙旧红木，掉漆、熏黑"),
]
