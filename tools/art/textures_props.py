"""《三更》贴图（二）：道具、布、纸、灯具、招牌门牌、表盘、贴花、实体、水汽。

文字类贴图用 Windows 自带楷体/黑体/宋体绘制后再做磨损、掉漆、龟裂处理。
"""
from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageDraw

import artlib as A

SS = 2


def _work(w, h):
    return w * SS, h * SS


def _down(arr, w, h):
    return A.downscale(arr, w, h, SS)


def _down_tiled(arr, w, h):
    return A.downscale_tiled(arr, w, h, SS)


def _post(rgb, r, grain_amt=0.022, desat=0.12, contrast=1.0, brightness=0.0,
          vignette=0.0):
    rgb = A.desaturate(rgb, desat)
    if contrast != 1.0 or brightness != 0.0:
        rgb = A.brighten_contrast(rgb, brightness, contrast)
    if vignette > 0:
        vg = A.vignette_mask(rgb.shape, vignette, 2.0)
        rgb = rgb * vg[..., None]
    return A.grain(np.clip(rgb, 0, 1), r, grain_amt, 0.22)


# ------------------------------------------------------------------ 织物

def build_fabric_red(w, h):
    W, H = _work(w, h)
    shape = (H, W)
    r = A.rng("fabric_red")
    rgb = A.mix(A.hexc("#7e322d")[None, None], A.hexc("#a0433b")[None, None],
                A.fbm(shape, 4, 4, r)[..., None])
    # 毛巾的毛圈（高频颗粒）+ 织纹
    terry = A.pnoise(shape, (300, 300), r)
    rgb *= (0.82 + 0.34 * terry)[..., None]
    weave = 0.5 + 0.5 * np.cos(2 * np.pi * A.coords(shape)[0] * 60.0 / H)
    rgb *= (0.94 + 0.10 * weave)[..., None]
    # 褪色与旧渍
    fade = A.smoothstep((A.fbm(shape, 5, 4, r) - 0.55) / 0.15)
    rgb = A.over(rgb, A.hexc("#b2705d"), fade, 0.30)
    stain = A.blobs(shape, [(r.uniform(0, H), r.uniform(0, W), r.uniform(4, 16),
                            r.uniform(0.2, 0.5)) for _ in range(16)], feather=4)
    rgb = A.over(rgb, A.hexc("#5a3826"), stain, 0.3)
    rgb = _post(rgb, r, 0.03, 0.14, vignette=0.15)
    return _down(rgb, w, h)


def build_fabric_white(w, h):
    W, H = _work(w, h)
    shape = (H, W)
    r = A.rng("fabric_white")
    rgb = A.mix(A.hexc("#c0bbaa")[None, None], A.hexc("#e0dbce")[None, None],
                A.fbm(shape, 4, 5, r)[..., None])
    weave = A.pnoise(shape, (280, 60), r)
    rgb *= (0.90 + 0.16 * weave)[..., None]
    # 褶皱：更强的斜向明暗
    wr = A.fbm(shape, 0, 4, r, aniso=(5, 26))
    rgb *= (1.0 + 0.34 * (wr - 0.5))[..., None]
    fold = A.smoothstep((A.fbm(shape, 3, 3, r) - 0.56) / 0.1)
    rgb = A.over(rgb, A.hexc("#9c9a88"), fold, 0.38)
    # 折痕细线
    crease = A.smoothstep((A.ridged(shape, 5, 3, r) - 0.977) / 0.01)
    rgb = A.over(rgb, A.hexc("#8e8b7a"), crease, 0.30)
    # 泛黄与旧污
    yellow = A.smoothstep((A.fbm(shape, 4, 4, r) - 0.60) / 0.12)
    rgb = A.over(rgb, A.hexc("#b09d70"), yellow, 0.30)
    stain = A.blobs(shape, [(r.uniform(0, H), r.uniform(0, W), r.uniform(3, 12),
                            r.uniform(0.2, 0.5)) for _ in range(14)], feather=4)
    rgb = A.over(rgb, A.hexc("#8a7a52"), stain, 0.32)
    rgb = _post(rgb, r, 0.026, 0.18, vignette=0.12)
    return _down(rgb, w, h)


def build_fabric_blue(w, h):
    W, H = _work(w, h)
    shape = (H, W)
    r = A.rng("fabric_blue")
    yy, xx = A.coords(shape)
    rgb = A.mix(A.hexc("#3d4a55")[None, None], A.hexc("#5a6a73")[None, None],
                A.fbm(shape, 4, 4, r)[..., None])
    # 斜纹
    twill = 0.5 + 0.5 * np.cos(2 * np.pi * ((xx + yy) * 26.0 / W))
    rgb *= (0.90 + 0.16 * twill)[..., None]
    # 洗旧的泛白
    fade = A.smoothstep((A.fbm(shape, 5, 4, r) - 0.52) / 0.2)
    rgb = A.over(rgb, A.hexc("#8b98a0"), fade, 0.28)
    # 褶皱阴影
    wr = A.fbm(shape, 0, 4, r, aniso=(4, 22))
    rgb *= (1.0 + 0.18 * (wr - 0.5))[..., None]
    # 油渍/磨损边缘
    stain = A.blobs(shape, [(r.uniform(0, H), r.uniform(0, W), r.uniform(5, 18),
                            r.uniform(0.2, 0.5)) for _ in range(14)], feather=4)
    rgb = A.over(rgb, A.hexc("#2b2f30"), stain, 0.35)
    segs = [(r.uniform(0, W), r.uniform(0, H),
             r.uniform(0, W), r.uniform(0, H), r.uniform(0.6, 1.4))
            for _ in range(16)]
    rgb = A.over(rgb, A.hexc("#8f9a9f"), A.seg_mask(shape, segs, 0.9), 0.18)
    rgb = _post(rgb, r, 0.026, 0.12, vignette=0.12)
    return _down(rgb, w, h)


# ------------------------------------------------------------------ 纸

def build_paper(w, h):
    W, H = _work(w, h)
    shape = (H, W)
    r = A.rng("paper")
    yy, xx = A.coords(shape)
    rgb = A.mix(A.hexc("#c8b88f")[None, None], A.hexc("#e0d2ae")[None, None],
                A.fbm(shape, 4, 5, r)[..., None])
    # 纤维
    fiber = A.fbm(shape, 0, 4, r, aniso=(9, 160))
    rgb *= (0.92 + 0.14 * fiber)[..., None]
    # 折痕（两条交叉直线）
    crease = np.zeros(shape, np.float32)
    for ang, off in ((0.9, 0.42), (-0.6, 0.62)):
        d = np.abs((xx - W * 0.5) * math.sin(ang) + (yy - H * off) * math.cos(ang))
        crease = np.maximum(crease, np.exp(-(d / (W * 0.012)) ** 2))
    rgb *= (1.0 - 0.10 * crease)[..., None]
    rgb += (0.04 * np.roll(crease, 2, axis=0))[..., None]
    # 霉点/褐色斑点
    fox = A.blobs(shape, [(r.uniform(0, H), r.uniform(0, W),
                          r.uniform(1.5, 7), r.uniform(0.25, 0.7))
                         for _ in range(30)], feather=1.8)
    rgb = A.over(rgb, A.hexc("#8a6b3a"), fox, 0.5)
    # 边缘泛黄
    vg = A.vignette_mask(shape, 0.35, 1.6)
    rgb *= (0.86 + 0.14 * vg)[..., None]
    rgb = _post(rgb, r, 0.024, 0.18, vignette=0.18)
    return _down(rgb, w, h)


# ------------------------------------------------------------------ 旧照片

def _person_mask(shape, cx, cy, ph, kind=0):
    H, W = shape
    im = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(im)
    head_r = ph * 0.11
    d.ellipse([cx - head_r, cy - ph * 0.5 - head_r,
               cx + head_r, cy - ph * 0.5 + head_r], fill=255)
    # 脖子+肩+身体（梯形）
    top = cy - ph * 0.5 + head_r * 0.7
    bot = cy + ph * 0.5
    sh = ph * 0.24
    d.polygon([(cx - head_r * 0.55, top),
               (cx + head_r * 0.55, top),
               (cx + sh, top + ph * 0.16),
               (cx + sh * 0.8, bot),
               (cx - sh * 0.8, bot),
               (cx - sh, top + ph * 0.16)], fill=255)
    return np.asarray(im, np.float32) / 255.0


def build_photo(w, h):
    W, H = _work(w, h)
    shape = (H, W)
    r = A.rng("photo")
    yy, xx = A.coords(shape)

    # 相纸白边
    bw = int(W * 0.045)
    rgb = np.ones((H, W, 3), np.float32) * A.hexc("#d5ceba")
    rgb *= (0.90 + 0.14 * A.pnoise(shape, (60, 60), r))[..., None]

    inner = np.zeros(shape, np.float32)
    inner[bw:H - bw, bw:W - bw] = 1.0
    # 内画面：褪色墙面 + 地面
    inner_rgb = A.mix(A.hexc("#8e8166")[None, None], A.hexc("#b3a582")[None, None],
                      (yy / H)[..., None])
    ground = np.clip((yy - H * 0.70) / (H * 0.3), 0, 1)
    inner_rgb = A.over(inner_rgb, A.hexc("#6f6450"), ground, 0.5)
    # 人物：三代同堂，均虚化
    figures = [(_person_mask(shape, W * 0.36, H * 0.58, H * 0.52), "#4d4234", 0.92),
               (_person_mask(shape, W * 0.60, H * 0.60, H * 0.48), "#574a3a", 0.88),
               (_person_mask(shape, W * 0.48, H * 0.72, H * 0.30), "#5f5140", 0.9)]
    for mask, col, op in figures:
        m = A.blur(mask, W * 0.012, periodic=False)
        inner_rgb = A.over(inner_rgb, A.hexc(col), m, op)
    # 人的浅色衣服/脸（模糊后的亮部）
    for (fx, fy, fr) in ((W * 0.48, H * 0.55, W * 0.035),
                         (W * 0.36, H * 0.36, W * 0.022),
                         (W * 0.60, H * 0.38, W * 0.020)):
        d = np.sqrt((xx - fx) ** 2 + (yy - fy) ** 2)
        rgb_face = np.exp(-(d / fr) ** 2)
        inner_rgb = A.over(inner_rgb, A.hexc("#c9b696"), A.blur(rgb_face, 3), 0.55)
    # 内画面整体虚化与褪色
    inner_rgb = A.blur(inner_rgb, W * 0.003, periodic=False)
    inner_rgb = A.desaturate(inner_rgb, 0.35)
    inner_rgb = A.over(inner_rgb, A.hexc("#b9a170"), np.ones(shape) * 0.18)
    rgb = inner_rgb * inner[..., None] + rgb * (1 - inner[..., None])

    # 相纸划痕、污点、暗角
    segs = [(r.uniform(0, W), r.uniform(0, H),
             r.uniform(0, W), r.uniform(0, H), r.uniform(0.6, 1.5))
            for _ in range(22)]
    rgb = A.over(rgb, A.hexc("#e8e0cc"), A.seg_mask(shape, segs, 0.8), 0.20)
    spots = A.blobs(shape, [(r.uniform(0, H), r.uniform(0, W), r.uniform(2, 9),
                            r.uniform(0.2, 0.5)) for _ in range(26)], feather=3)
    rgb = A.over(rgb, A.hexc("#6f5a38"), spots, 0.35)
    vg = A.vignette_mask(shape, 0.42, 1.7)
    rgb *= vg[..., None]
    # 过曝的一角
    corner = np.exp(-(((xx - W * 0.05) / (W * 0.25)) ** 2 +
                      ((yy - H * 0.08) / (H * 0.25)) ** 2))
    rgb = A.over(rgb, A.hexc("#e8dcc0"), corner, 0.25)
    rgb = _post(rgb, r, 0.024, 0.12)
    return _down(rgb, w, h)


# ------------------------------------------------------------------ CRT 雪花

def build_tv_static(w, h):
    W, H = _work(w, h)
    shape = (H, W)
    r = A.rng("tv_static")
    yy, xx = A.coords(shape)
    n = r.random(shape).astype(np.float32)
    n = A.blur(n, 0.6, periodic=False)
    n = (n - n.min()) / (n.max() - n.min())
    # 扫描线
    scan = 1.0 - 0.38 * ((np.arange(H) % 3) == 0)[:, None].astype(np.float32)
    # 滚动亮带 + 暗带
    roll = 0.84 + 0.16 * np.sin(2 * np.pi * (yy / H * 1.3 - 0.2))
    val = n * scan * roll
    # 行抖动（同步不良）
    for _ in range(6):
        row = r.integers(0, H)
        val[row:row + 2] = np.roll(val[row:row + 2], int(r.integers(-6, 7)), axis=1)
    rgb = np.repeat(val[..., None], 3, axis=2)
    # 很弱的彩色噪点（保持近黑白）
    chroma = r.normal(0, 1.0, (H, W, 3)).astype(np.float32)
    chroma = A.blur(chroma, 1.2, periodic=False)
    rgb = rgb + chroma * 0.018
    rgb = rgb * np.array([0.98, 1.0, 1.02], np.float32)[None, None] +         np.array([0.008, 0.012, 0.015], np.float32)[None, None]
    # 中央略亮、四角暗
    d = A.radial_field(shape, W / 2, H / 2, W * 0.7)
    rgb *= (1.12 - 0.35 * np.clip(d, 0, 1))[..., None]
    vg = A.vignette_mask(shape, 0.55, 1.7)
    rgb *= vg[..., None]
    rgb = _post(rgb, r, 0.03, 0.0)
    return _down(rgb, w, h)


# ------------------------------------------------------------------ 灯具

def build_lamp_tube(w, h):
    W, H = _work(w, h)
    shape = (H, W)
    r = A.rng("lamp_tube")
    yy, xx = A.coords(shape)
    u = xx / W
    v = yy / H
    core = 0.82 + 0.18 * np.cos(2 * np.pi * (u - 0.5))
    ends = A.smoothstep(v / 0.10) * A.smoothstep((1 - v) / 0.10)
    ends = 0.72 + 0.28 * ends
    val = np.clip(core * ends, 0, 1)
    rgb = A.mix(A.hexc("#a9d8c4")[None, None], A.hexc("#f2fff6")[None, None],
                val[..., None])
    # 灰/灰尘点
    dust = A.blobs(shape, [(r.uniform(0, H), r.uniform(0, W), r.uniform(1, 5),
                           r.uniform(0.2, 0.6)) for _ in range(20)], feather=1.5)
    rgb = A.over(rgb, A.hexc("#8a8f80"), dust, 0.35)
    rgb = np.clip(rgb, 0, 1)
    return _down(rgb, w, h)


def build_lamp_warm(w, h):
    W, H = _work(w, h)
    shape = (H, W)
    r = A.rng("lamp_warm")
    d = A.radial_field(shape, W / 2, H / 2, W * 0.5)
    d = np.clip(d, 0, 1)
    rgb = A.ramp(1 - d, [0.0, 0.35, 0.7, 1.0],
                 [A.hexc("#c47a33"), A.hexc("#e09a4a"),
                  A.hexc("#ffcf8a"), A.hexc("#fff6dc")])
    # 灯丝的暗痕/灰尘
    specks = A.blobs(shape, [(r.uniform(0, H), r.uniform(0, W), r.uniform(1, 4),
                             r.uniform(0.2, 0.5)) for _ in range(14)], feather=1.2)
    rgb = A.over(rgb, A.hexc("#8a5a2a"), specks, 0.3)
    return _down(rgb, w, h)


def build_lantern_paper(w, h):
    W, H = _work(w, h)
    shape = (H, W)
    r = A.rng("lantern_paper")
    yy, xx = A.coords(shape)
    v = yy / H
    # 竹骨：横截面上的 8 根竖棱（x 方向周期，保证绕柱无缝）
    f = (xx * 8.0 / W) % 1.0
    rib = np.exp(-((np.minimum(f, 1 - f)) / 0.055) ** 2)
    base = A.mix(A.hexc("#9c2e22")[None, None], A.hexc("#c8492f")[None, None],
                 A.fbm(shape, 4, 4, r)[..., None])
    # 纸的明暗：中间最亮，上下收口暗
    glow = 0.55 + 0.45 * np.sin(np.pi * np.clip(v, 0, 1)) ** 0.6
    rgb = base * (0.62 + 0.55 * glow)[..., None]
    rgb = A.over(rgb, A.hexc("#6f2018"), rib, 0.55)
    # 骨架两侧的高光
    hi = np.exp(-((np.minimum(f, 1 - f) - 0.10) / 0.04) ** 2)
    rgb += (0.10 * hi * glow)[..., None]
    # 纸张纤维与污渍
    weave = A.pnoise(shape, (200, 200), r)
    fine = A.pnoise(shape, (310, 310), r)
    rgb *= (0.90 + 0.15 * weave + 0.06 * fine)[..., None]
    stain = A.smoothstep((A.fbm(shape, 5, 4, r) - 0.62) / 0.12)
    rgb = A.over(rgb, A.hexc("#5f2418"), stain, 0.3)
    rgb = np.clip(rgb, 0, 1)
    rgb = A.grain(rgb, r, 0.02, 0.2)
    return _down(rgb, w, h)


# ------------------------------------------------------------------ 文字/招牌工具

def _text_line(shape, text, font_path, size, center, tracking=0, stroke=0):
    H, W = shape
    img = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(img)
    font = A.get_font(font_path, int(size))
    cx, cy = center
    if not tracking:
        d.text((cx, cy), text, font=font, fill=255, anchor="mm",
               stroke_width=stroke)
        return np.asarray(img, np.float32) / 255.0
    widths = []
    for ch in text:
        bb = d.textbbox((0, 0), ch, font=font, stroke_width=stroke)
        widths.append(bb[2] - bb[0])
    total = sum(widths) + tracking * (len(text) - 1)
    x = cx - total * 0.5
    for ch, wch in zip(text, widths):
        d.text((x, cy), ch, font=font, fill=255, anchor="lm",
               stroke_width=stroke)
        x += wch + tracking
    return np.asarray(img, np.float32) / 255.0


def _vtext(shape, text, font_path, size, center, gap=1.15, stroke=0):
    H, W = shape
    img = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(img)
    font = A.get_font(font_path, int(size))
    cx, cy = center
    step = size * gap
    y0 = cy - step * (len(text) - 1) * 0.5
    for i, ch in enumerate(text):
        d.text((cx, y0 + i * step), ch, font=font, fill=255, anchor="mm",
               stroke_width=stroke)
    return np.asarray(img, np.float32) / 255.0


def _wear_text(mask, r, wear=0.25, pit=0.5):
    H, W = mask.shape
    m = mask * (0.55 + 0.45 * A.fbm((H, W), 11, 4, r))
    m = A.smoothstep((m - wear) / max(1 - wear, 1e-3))
    pits = A.smoothstep((A.pnoise((H, W), (190, 190), r) - 0.76) / 0.05)
    m *= (1.0 - pit * pits)
    return m


def _wood_board(shape, r, horizontal=True, planks=3, base=("#5c4c39", "#7a6449"),
                seam_dark="#241d15"):
    H, W = shape
    lo, hi = A.hexc(base[0]), A.hexc(base[1])
    rgb = A.mix(lo[None, None], hi[None, None], A.fbm(shape, 3, 5, r)[..., None])
    if horizontal:
        grain = A.fbm(shape, 0, 4, r, aniso=(110, 5))
        seam_pos = np.arange(1, planks) * (H / planks)
        dist = np.min(np.stack([np.abs(A.coords(shape)[0] - p) for p in seam_pos]),
                      axis=0)
        seam = A.smoothstep((3.2 - dist) / 3.2)
    else:
        grain = A.fbm(shape, 0, 4, r, aniso=(5, 110))
        seam_pos = np.arange(1, planks) * (W / planks)
        dist = np.min(np.stack([np.abs(A.coords(shape)[1] - p) for p in seam_pos]),
                      axis=0)
        seam = A.smoothstep((3.2 - dist) / 3.2)
    rgb *= (0.82 + 0.34 * grain)[..., None]
    fine = A.pnoise(shape, (220, 220), r)
    rgb *= (0.92 + 0.14 * fine)[..., None]
    rgb *= (1.0 - 0.45 * seam)[..., None]
    # 木纹裂缝与污渍
    crack = A.smoothstep((A.ridged(shape, 8, 3, r) - 0.988) / 0.008)
    rgb = A.over(rgb, A.hexc(seam_dark), crack, 0.5)
    damp = A.smoothstep((A.fbm(shape, 4, 4, r) - 0.6) / 0.1)
    rgb = A.over(rgb, A.hexc("#3f3527"), damp, 0.3)
    return rgb


def _nails(shape, r, positions, color="#8f8a76"):
    H, W = shape
    rgb = np.zeros((H, W, 3), np.float32)
    alpha = np.zeros((H, W), np.float32)
    for (cx, cy) in positions:
        d = A.radial_field(shape, cx, cy, W * 0.018)
        head = A.smoothstep((1 - d) / 0.25)
        alpha = np.maximum(alpha, head)
    return alpha


def _sign(w, h, name, lines, font_sizes, line_ys, font_path, text_hex,
          base=("#5c4c39", "#7a6449"), wear=0.25, planks=3, border=False):
    W, H = _work(w, h)
    shape = (H, W)
    r = A.rng(name)
    rgb = _wood_board(shape, r, horizontal=True, planks=planks, base=base)

    # 边框（手绘线条）
    if border:
        yy, xx = A.coords(shape)
        inset = W * 0.035
        edge = A.border_dist(shape, inset, inset)
        bl = A.smoothstep((2.0 - np.abs(edge)) / 2.0)
        rgb = A.over(rgb, A.hexc("#c9bd9c"), bl, 0.45)

    # 文字（先画在蒙版上，再磨损）
    masks = []
    for text, size, cy in zip(lines, font_sizes, line_ys):
        masks.append(_text_line(shape, text, font_path, size,
                                (W * 0.5, H * cy)))
    m = np.maximum.reduce(masks)
    m = _wear_text(m, r, wear=wear)
    # 字的阴影
    sh = np.roll(np.roll(m, int(W * 0.004), axis=1), int(W * 0.004), axis=0)
    rgb = A.over(rgb, A.hexc("#2b2118"), A.blur(sh, 1.2) * 0.5, 0.45)
    rgb = A.over(rgb, A.hexc(text_hex), m, 0.92)
    # 字的边缘被木头吸收
    rgb = A.over(rgb, A.hexc("#8a7657"), np.clip(A.blur(m, 1.0) - m, 0, 1), 0.35)

    # 从上往下的漆滴
    drip = np.zeros(shape, np.float32)
    for i in range(1, 26):
        drip = np.maximum(drip, np.roll(m, i, axis=0) * (1 - i / 26.0))
    drip = A.blur(drip, 1.5) * 0.5
    rgb = A.over(rgb, A.hexc("#6b5a40"), drip, 0.25)

    # 钉子
    nails = _nails(shape, r, [(W * 0.06, H * 0.08), (W * 0.94, H * 0.08),
                              (W * 0.06, H * 0.92), (W * 0.94, H * 0.92)])
    rgb = A.over(rgb, A.hexc("#6f6a58"), nails, 0.8)
    d = A.radial_field(shape, W * 0.06, H * 0.08, W * 0.018)
    rgb = A.over(rgb, A.hexc("#d8d2bc"), A.smoothstep((0.55 - d) / 0.2), 0.6)

    # 泥点与暗角
    mud = A.blobs(shape, [(r.uniform(0, H), r.uniform(0, W), r.uniform(2, 10),
                          r.uniform(0.2, 0.5)) for _ in range(30)], feather=2.5)
    rgb = A.over(rgb, A.hexc("#3a2f22"), mud, 0.4)
    rgb = _post(rgb, r, 0.026, 0.1, vignette=0.25)
    return _down(rgb, w, h)


# ------------------------------------------------------------------ 夜路木牌

def build_sign_night_1(w, h):
    return _sign(w, h, "sign_night_1",
                 ["土地庙", "前方 500 米"],
                 [h * SS * 0.335, h * SS * 0.175],
                 [0.35, 0.69], A.FONT_KAI, "#d9d0b2",
                 base=("#5a4a37", "#77634a"), wear=0.26, planks=3, border=True)


def build_sign_night_2(w, h):
    return _sign(w, h, "sign_night_2",
                 ["夜路难行", "早些回家"],
                 [h * SS * 0.26, h * SS * 0.26],
                 [0.34, 0.68], A.FONT_KAI, "#cfc5a6",
                 base=("#514538", "#6b5b46"), wear=0.36, planks=2, border=False)


# ------------------------------------------------------------------ 澡堂门牌

def build_sign_bath(w, h):
    W, H = _work(w, h)
    shape = (H, W)
    r = A.rng("sign_bath")
    yy, xx = A.coords(shape)

    # 底：旧珐琅牌（深青底 + 白边）
    rgb = A.mix(A.hexc("#2c4644")[None, None], A.hexc("#3b5a55")[None, None],
                A.fbm(shape, 4, 4, r)[..., None])
    rgb *= (0.90 + 0.16 * A.pnoise(shape, (150, 150), r))[..., None]
    border = A.border_dist(shape, W * 0.055, H * 0.035)
    bl = A.smoothstep((4.0 - np.abs(border)) / 4.0)
    rgb = A.over(rgb, A.hexc("#cfc9b0"), bl, 0.8)
    # 珐琅的细微龟裂
    crack = A.smoothstep((A.ridged(shape, 9, 3, r) - 0.99) / 0.006)
    rgb = A.over(rgb, A.hexc("#7a8474"), crack, 0.35)
    # 锈迹（从上往下流）
    rust = A.smoothstep((A.fbm(shape, 0, 4, r, aniso=(60, 4)) - 0.70) / 0.08)
    rust *= (yy / H) ** 0.8
    rgb = A.over(rgb, A.hexc("#8a4a24"), rust, 0.55)
    chips = A.blobs(shape, [(r.uniform(0, H), r.uniform(0, W), r.uniform(2, 8),
                            r.uniform(0.3, 0.7)) for _ in range(26)], feather=1.4)
    rgb = A.over(rgb, A.hexc("#6f5230"), chips, 0.45)

    # 竖排「男湯」
    size = H * 0.235
    m = _vtext(shape, "男湯", A.FONT_HEI, size, (W * 0.5, H * 0.5), gap=1.12)
    m = _wear_text(m, r, wear=0.22, pit=0.35)
    sh = np.roll(m, int(W * 0.006), axis=1)
    rgb = A.over(rgb, A.hexc("#3a4038"), A.blur(sh, 1.0) * 0.5, 0.35)
    rgb = A.over(rgb, A.hexc("#e4dfcd"), m, 0.95)
    # 字上的污渍/划痕
    dirt = A.smoothstep((A.fbm(shape, 6, 4, r) - 0.62) / 0.1)
    rgb = A.over(rgb, A.hexc("#5a5544"), dirt * m, 0.3)
    # 四角螺丝
    for (cx, cy) in ((W * 0.07, H * 0.04), (W * 0.93, H * 0.04),
                     (W * 0.07, H * 0.96), (W * 0.93, H * 0.96)):
        d = A.radial_field(shape, cx, cy, W * 0.022)
        rgb = A.over(rgb, A.hexc("#8f8a76"), A.smoothstep((1 - d) / 0.3), 0.8)
    # 底部水渍
    stain = A.smoothstep((A.fbm(shape, 5, 4, r) - 0.58) / 0.12)
    rgb = A.over(rgb, A.hexc("#4a3a24"), stain, 0.25)
    rgb = _post(rgb, r, 0.024, 0.1, vignette=0.28)
    return _down(rgb, w, h)


# ------------------------------------------------------------------ 石牌位

def build_shrine_tablet(w, h):
    W, H = _work(w, h)
    shape = (H, W)
    r = A.rng("shrine_tablet")
    yy, xx = A.coords(shape)

    rgb = A.mix(A.hexc("#5c594f")[None, None], A.hexc("#7e7b6e")[None, None],
                A.fbm(shape, 4, 5, r)[..., None])
    rgb *= (0.85 + 0.22 * A.pnoise(shape, (180, 180), r))[..., None]
    agg = A.pnoise(shape, (300, 300), r)
    rgb = A.over(rgb, A.hexc("#a8a496"), A.smoothstep((agg - 0.80) / 0.05), 0.4)
    rgb = A.over(rgb, A.hexc("#35332c"), A.smoothstep((0.18 - agg) / 0.04), 0.45)
    # 内凹面板
    inset = A.border_dist(shape, W * 0.12, H * 0.06)
    panel = A.smoothstep(inset / 6.0)
    rgb = A.over(rgb, A.hexc("#4a483f"), panel * 0.5, 0.7)
    rim = np.clip(A.blur(panel, 2.0) - panel, 0, 1)
    rgb = A.over(rgb, A.hexc("#2a2924"), rim, 0.5)
    rgb = A.over(rgb, A.hexc("#969283"), np.clip(panel - A.blur(panel, 2.0), 0, 1), 0.4)

    # 竖排「土地之神位」
    size = H * 0.135
    m = _vtext(shape, "土地之神位", A.FONT_SONG, size,
               (W * 0.5, H * 0.50), gap=1.22, stroke=3)
    m = _wear_text(m, r, wear=0.30, pit=0.4)
    # 阴刻：字的暗部 + 右下亮边
    rgb = A.over(rgb, A.hexc("#24221d"), m, 0.8)
    edge_hi = np.clip(np.roll(np.roll(m, -2, axis=0), 2, axis=1) - m, 0, 1)
    rgb = A.over(rgb, A.hexc("#9c9788"), edge_hi, 0.5)
    # 残留红漆
    red = A.smoothstep((A.fbm(shape, 8, 4, r) - 0.58) / 0.1) * m
    rgb = A.over(rgb, A.hexc("#7c2c22"), red, 0.5)
    # 香灰、苔、崩边
    soot = A.smoothstep((A.fbm(shape, 4, 4, r) - 0.55) / 0.15)
    rgb = A.over(rgb, A.hexc("#2a251c"), soot * (yy / H), 0.35)
    moss = A.blobs(shape, [(r.uniform(H * 0.6, H), r.uniform(0, W), r.uniform(3, 14),
                           r.uniform(0.2, 0.5)) for _ in range(20)], feather=4)
    rgb = A.over(rgb, A.hexc("#4a5232"), moss, 0.45)
    chips = A.smoothstep((A.ridged(shape, 7, 3, r) - 0.985) / 0.01)
    rgb = A.over(rgb, A.hexc("#2a2822"), chips, 0.4)
    rgb = _post(rgb, r, 0.026, 0.06, vignette=0.22)
    return _down(rgb, w, h)


# ------------------------------------------------------------------ 门牌

def _door_plate(w, h, name, digits, plate_hex, digit_hex, wear, tilt=0.0):
    W, H = _work(w, h)
    shape = (H, W)
    r = A.rng(name)
    yy, xx = A.coords(shape)

    # 底板蒙版（圆角矩形）
    margin = int(W * 0.10)
    plate_img = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(plate_img)
    d.rounded_rectangle([margin, margin // 2, W - margin, H - margin // 2],
                        radius=int(W * 0.05), fill=255)
    plate = np.asarray(plate_img, np.float32) / 255.0

    # 金属底板
    rgb = np.zeros((H, W, 3), np.float32)
    metal = A.mix(A.hexc(plate_hex), A.hexc("#9a9686"),
                  A.fbm(shape, 3, 4, r)[..., None] * 0.35)
    metal *= (0.86 + 0.2 * A.pnoise(shape, (170, 170), r))[..., None]
    rgb = metal
    # 底板边缘的倒角与投影
    inner = A.blur(plate, 4.0)
    bevel = 1.0 + 0.35 * (inner - plate)
    rgb *= bevel[..., None]
    # 划痕/锈/污垢
    sc = A.seg_mask(shape, [(r.uniform(margin, W - margin),
                             r.uniform(0, H),
                             r.uniform(margin, W - margin),
                             r.uniform(0, H), r.uniform(0.5, 1.3))
                            for _ in range(16)], 0.8)
    rgb = A.over(rgb, A.hexc("#c9c5b4"), sc, 0.25)
    rust = A.smoothstep((A.fbm(shape, 7, 4, r) - 0.68) / 0.08) * plate
    rgb = A.over(rgb, A.hexc("#7a4a28"), rust, 0.5)
    grime = A.fbm(shape, 5, 4, r)
    rgb *= (1.0 - wear * 0.35 * grime)[..., None]
    # 灰尘/泥
    dirt = A.smoothstep((A.pnoise(shape, (200, 200), r) - 0.74) / 0.08)
    rgb = A.over(rgb, A.hexc("#3f3a2e"), dirt * plate, wear * 0.5)
    # 螺丝（四角）
    for (cx, cy) in ((margin * 1.7, margin * 1.15), (W - margin * 1.7, margin * 1.15),
                     (margin * 1.7, H - margin * 1.15),
                     (W - margin * 1.7, H - margin * 1.15)):
        dd = A.radial_field(shape, cx, cy, W * 0.035)
        screw = A.smoothstep((1 - dd) / 0.35)
        rgb = A.over(rgb, A.hexc("#8f8a76"), screw, 0.9)
        slot = A.seg_mask(shape, [(cx - W * 0.03, cy, cx + W * 0.03, cy,
                                   W * 0.012)], 0.6)
        rgb = A.over(rgb, A.hexc("#4a463a"), slot * screw, 0.7)
        rgb = A.over(rgb, A.hexc("#6d4a24"), A.blur(screw, 2.5) * 0.4, 0.3)

    # 数字
    size = W * 0.42
    m = _text_line(shape, digits, A.FONT_HEI, size, (W * 0.5, H * 0.53),
                   tracking=size * 0.02)
    m *= plate
    m = _wear_text(m, r, wear=0.18 if digits == "503" else 0.30, pit=0.35)
    sh = np.roll(np.roll(m, int(W * 0.006), axis=1), int(W * 0.006), axis=0)
    rgb = A.over(rgb, A.hexc("#1d1b16"), A.blur(sh, 0.8) * 0.5, 0.4)
    rgb = A.over(rgb, A.hexc(digit_hex), m, 0.95)

    # 板面之外的墙面/背景（暗）
    rgb = A.over(rgb, A.hexc("#2b2823"), 1.0 - plate, 1.0)
    rgb = _post(rgb, r, 0.022, 0.08, vignette=0.3)
    return _down(rgb, w, h)


def build_door_number_501(w, h):
    return _door_plate(w, h, "door_number_501", "501", "#63798a", "#d8d4c2",
                       wear=0.55, tilt=-1.0)


def build_door_number_502(w, h):
    return _door_plate(w, h, "door_number_502", "502", "#657a6c", "#ddd8c6",
                       wear=0.5)


def build_door_number_503(w, h):
    return _door_plate(w, h, "door_number_503", "503", "#c8c2ae", "#211f1a",
                       wear=0.28)


def build_door_number_504(w, h):
    return _door_plate(w, h, "door_number_504", "504", "#8a7d68", "#e0dbc9",
                       wear=0.65)


# ------------------------------------------------------------------ 挂钟表盘

def build_clock_face(w, h):
    W, H = _work(w, h)
    shape = (H, W)
    r = A.rng("clock_face")
    yy, xx = A.coords(shape)
    cx, cy = W * 0.5, H * 0.5
    R = W * 0.47

    # 表盘外的暗背景
    rgb = np.ones((H, W, 3), np.float32) * A.hexc("#241f18")
    d = A.radial_field(shape, cx, cy, R)
    face = A.smoothstep((1 - d) / 0.02)
    # 表盘纸/漆面
    face_col = A.mix(A.hexc("#bcb093")[None, None], A.hexc("#d6cbb0")[None, None],
                     A.fbm(shape, 4, 4, r)[..., None])
    face_col *= (0.92 + 0.12 * A.pnoise(shape, (160, 160), r))[..., None]
    rgb = A.mix(rgb, face_col, face)

    # 边缘金属圈
    ring = np.exp(-((d - 0.985) / 0.025) ** 2) * face
    rgb = A.over(rgb, A.hexc("#8a8268"), ring, 0.7)
    ring2 = np.exp(-((d - 0.93) / 0.008) ** 2) * face
    rgb = A.over(rgb, A.hexc("#5f5844"), ring2, 0.6)

    # 12 个罗马数字
    roman = ["XII", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI"]
    for i, txt in enumerate(roman):
        ang = -math.pi / 2 + i * 2 * math.pi / 12
        tx = cx + math.cos(ang) * R * 0.76
        ty = cy + math.sin(ang) * R * 0.76
        m = _text_line(shape, txt, A.FONT_SONG, W * 0.070, (tx, ty))
        rgb = A.over(rgb, A.hexc("#2e2a22"), m * face, 0.9)
    # 60 刻度
    for i in range(60):
        ang = -math.pi / 2 + i * 2 * math.pi / 60
        r0, r1 = R * (0.86 if i % 5 == 0 else 0.90), R * 0.945
        x0, x1 = cx + math.cos(ang) * r0, cx + math.cos(ang) * r1
        y0, y1 = cy + math.sin(ang) * r0, cy + math.sin(ang) * r1
        m = A.seg_mask(shape, [(x0, y0, x1, y1, W * 0.008)], 0.7)
        rgb = A.over(rgb, A.hexc("#2e2a22"), m * face, 0.85)

    # 指针：时针→3点，分针→12点，秒针→9点
    def hand(angle, length, width, color, shadow=True):
        nonlocal rgb
        ca, sa = math.cos(-math.pi / 2 + angle), math.sin(-math.pi / 2 + angle)
        m = A.seg_mask(shape, [(cx - ca * length * 0.10, cy - sa * length * 0.10,
                                cx + ca * length, cy + sa * length, width)], 0.8)
        if shadow:
            rgb = A.over(rgb, A.hexc("#1c1914"),
                         np.roll(np.roll(m, 2, axis=0), 2, axis=1) * 0.45, 0.5)
        rgb = A.over(rgb, A.hexc(color), m, 0.9)

    hand(0.0, R * 0.95, W * 0.020, "#2b2720")        # 分针指向 12
    hand(math.pi / 2, R * 0.62, W * 0.028, "#2b2720")  # 时针指向 3
    hand(-math.pi / 2, R * 0.99, W * 0.006, "#7a2a20")  # 秒针指向 9
    # 中心轴
    dd = A.radial_field(shape, cx, cy, W * 0.028)
    rgb = A.over(rgb, A.hexc("#6b5a3a"), A.smoothstep((1 - dd) / 0.4), 0.9)
    dd2 = A.radial_field(shape, cx, cy, W * 0.010)
    rgb = A.over(rgb, A.hexc("#c8b98c"), A.smoothstep((1 - dd2) / 0.5), 0.9)

    # 品牌小字
    tiny = _text_line(shape, "上海", A.FONT_SONG, W * 0.028,
                      (cx, cy + R * 0.52))
    rgb = A.over(rgb, A.hexc("#3a342a"), tiny * face, 0.8)
    # 霉斑、水渍、龟裂、玻璃反光
    fox = A.blobs(shape, [(r.uniform(0, H), r.uniform(0, W), r.uniform(1.5, 6),
                          r.uniform(0.2, 0.6)) for _ in range(30)], feather=2)
    rgb = A.over(rgb, A.hexc("#8a7040"), fox * face, 0.4)
    crack = A.smoothstep((A.ridged(shape, 8, 3, r) - 0.988) / 0.008) * face
    rgb = A.over(rgb, A.hexc("#4a453a"), crack, 0.4)
    glare = A.smoothstep((A.fbm(shape, 0, 3, r, aniso=(3, 12)) - 0.62) / 0.1) * face
    rgb = A.over(rgb, A.hexc("#e2dcc4"), glare, 0.16)
    vg = A.vignette_mask(shape, 0.5, 1.8)
    rgb *= vg[..., None]
    rgb = _post(rgb, r, 0.02, 0.1)
    return _down(rgb, w, h)


# ------------------------------------------------------------------ 镜面污渍（RGBA 叠加）

def build_mirror_grime(w, h):
    W, H = _work(w, h)
    shape = (H, W)
    r = A.rng("mirror_grime")
    yy, xx = A.coords(shape)

    alpha = np.zeros(shape, np.float32)
    color = np.ones((H, W, 3), np.float32) * A.hexc("#cdd2c2")

    # 边缘雾化污
    edge = A.border_dist(shape, 0, 0)
    haze = np.exp(-(edge / (W * 0.10)) ** 1.5) * (0.35 + 0.4 * A.fbm(shape, 6, 4, r))
    alpha = np.maximum(alpha, haze * 0.55)

    # 自上而下的水痕
    for _ in range(16):
        x0 = r.uniform(0, W)
        y0 = r.uniform(0, H * 0.7)
        L = r.uniform(H * 0.15, H * 0.5)
        wdt = r.uniform(W * 0.004, W * 0.018)
        dy = np.clip((yy - y0) / L, 0, 1)
        sx = x0 + r.normal(0, 4, 1)[0] * dy
        m = np.exp(-((xx - sx) / wdt) ** 2) * (1 - dy) ** 1.3
        alpha = np.maximum(alpha, m * r.uniform(0.18, 0.4))
    # 指纹/手印（椭圆团）
    for _ in range(3):
        fx, fy = r.uniform(W * 0.2, W * 0.8), r.uniform(H * 0.2, H * 0.8)
        for k in range(5):
            ex = fx + r.normal(0, W * 0.03)
            ey = fy + r.normal(0, H * 0.035)
            dd = np.sqrt(((xx - ex) / (W * 0.045)) ** 2 +
                         ((yy - ey) / (H * 0.02)) ** 2)
            alpha = np.maximum(alpha, np.exp(-dd ** 2) * 0.16)
    # 灰尘膜
    dust = A.fbm(shape, 7, 5, r)
    alpha = np.maximum(alpha, A.smoothstep((dust - 0.55) / 0.25) * 0.16)
    # 皂点
    for _ in range(18):
        cx, cy = r.uniform(0, W), r.uniform(0, H)
        rr = r.uniform(W * 0.005, W * 0.02)
        dd = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / rr
        spot = A.smoothstep((1 - dd) / 0.3) * 0.6 + \
            np.exp(-((dd - 1.0) / 0.15) ** 2) * 0.4
        alpha = np.maximum(alpha, spot * r.uniform(0.10, 0.25))
    # 划痕
    sc = A.seg_mask(shape, [(r.uniform(0, W), r.uniform(0, H),
                             r.uniform(0, W), r.uniform(0, H),
                             r.uniform(0.6, 1.2)) for _ in range(22)], 0.7)
    alpha = np.maximum(alpha, sc * 0.22)
    # 少量黄渍
    yellow = A.smoothstep((A.fbm(shape, 4, 4, r) - 0.62) / 0.1)
    color = A.mix(color, A.hexc("#b09a68"), yellow[..., None])
    alpha = np.clip(alpha, 0, 0.75)
    color = A.grain(color, r, 0.02, 0.2)

    rgb = (color * 255).astype(np.float32) / 255.0
    rgba = np.dstack([rgb, alpha])
    return _down(rgba, w, h)


# ------------------------------------------------------------------ 污渍贴花（RGBA，可平铺）

def build_stain_mold(w, h):
    W, H = _work(w, h)
    shape = (H, W)
    r = A.rng("stain_mold")

    # 有机的大块霉斑：多尺度噪声叠合 + 周期性模糊（保持无缝）
    f1 = A.fbm(shape, 3, 5, r)
    f2 = A.fbm(shape, 7, 5, r)
    f3 = A.fbm(shape, 16, 4, r)
    field = 0.55 * f1 + 0.30 * f2 + 0.15 * f3
    field = A.blur(field, 1.8, periodic=True)
    big = A.smoothstep((field - 0.545) / 0.085)
    fringe = A.smoothstep((field - 0.50) / 0.12) * 0.30
    dots = A.smoothstep((A.pnoise(shape, (250, 250), r) - 0.755) / 0.045) * 0.65
    alpha = np.clip(big * 1.05 + fringe * 0.55 + dots * 0.85, 0, 0.96)
    core = A.smoothstep((field - 0.60) / 0.12)
    tint = A.pnoise(shape, (60, 60), r)
    rgb = A.ramp(np.clip(0.35 * core + 0.45 * big + 0.20 * tint, 0, 1),
                 [0.0, 0.45, 0.8, 1.0],
                 [A.hexc("#3c4626"), A.hexc("#232b18"),
                  A.hexc("#12170d"), A.hexc("#080b06")])
    alpha *= np.clip(0.72 + 0.55 * core, 0, 1)
    rgb = A.grain(rgb, r, 0.018, 0.2)
    rgba = np.dstack([rgb, alpha])
    return _down_tiled(rgba, w, h)


def build_stain_water(w, h):
    W, H = _work(w, h)
    shape = (H, W)
    r = A.rng("stain_water")
    yy, xx = A.coords(shape)
    alpha = np.zeros(shape, np.float32)

    # 2~3 圈带有污边的水渍
    for _ in range(3):
        cyc, cxc = r.uniform(0, H), r.uniform(0, W)
        R = r.uniform(W * 0.12, W * 0.26)
        dy, dx = A.torus_delta(yy, xx, cyc, cxc, H, W)
        d = np.sqrt(dy * dy + dx * dx)
        ang = np.arctan2(dy, dx)
        rn = R * (1.0 + 0.13 * np.sin(3 * ang + r.uniform(0, 6))
                  + 0.07 * np.sin(6 * ang + r.uniform(0, 6)))
        inside = A.smoothstep((rn - d) / (W * 0.04)) * 0.30
        ring = np.exp(-((d - rn) / (W * 0.008)) ** 2) * 0.95
        alpha = np.maximum(alpha, np.maximum(inside, ring))
    # 流下的水痕（y 方向周期）
    for _ in range(9):
        x0 = r.uniform(0, W)
        y0 = r.uniform(0, H)
        L = r.uniform(H * 0.15, H * 0.4)
        wdt = r.uniform(W * 0.006, W * 0.02)
        yy_rel = (yy - y0) % H
        dy = np.clip(yy_rel / L, 0, 1)
        m = np.exp(-((xx - x0) / wdt) ** 2) * (1 - dy) ** 1.2
        m *= (yy_rel < L)
        alpha = np.maximum(alpha, m * r.uniform(0.18, 0.4))
    # 边缘更脏
    yellow = A.smoothstep((A.fbm(shape, 6, 4, r) - 0.5) / 0.2)
    rgb = A.mix(A.hexc("#b39a62")[None, None], A.hexc("#7d6535")[None, None],
                yellow[..., None])
    alpha = np.clip(alpha, 0, 0.85)
    rgb = A.grain(rgb, r, 0.02, 0.25)
    rgba = np.dstack([rgb, alpha])
    return _down_tiled(rgba, w, h)


# ------------------------------------------------------------------ 实体材质

def build_entity_white(w, h):
    W, H = _work(w, h)
    shape = (H, W)
    r = A.rng("entity_white")
    yy, xx = A.coords(shape)
    rgb = A.mix(A.hexc("#c9c8bf")[None, None], A.hexc("#e6e4da")[None, None],
                A.fbm(shape, 3, 5, r)[..., None])
    # 纸/皮肤的纤维与褶皱
    fiber = A.pnoise(shape, (240, 240), r)
    rgb *= (0.93 + 0.11 * fiber)[..., None]
    wr = A.fbm(shape, 0, 4, r, aniso=(6, 24))
    rgb *= (1.0 - 0.20 * (wr - 0.5))[..., None]
    # 冷蓝阴影
    shade = A.smoothstep((A.fbm(shape, 5, 4, r) - 0.6) / 0.12)
    rgb = A.over(rgb, A.hexc("#9aa3a4"), shade, 0.25)
    # 细裂纹/纸缝
    crack = A.smoothstep((A.ridged(shape, 6, 3, r) - 0.985) / 0.01)
    rgb = A.over(rgb, A.hexc("#8d8b80"), crack, 0.35)
    # 污点
    stain = A.blobs(shape, [(r.uniform(0, H), r.uniform(0, W), r.uniform(3, 14),
                            r.uniform(0.15, 0.4)) for _ in range(18)], feather=4)
    rgb = A.over(rgb, A.hexc("#a89f86"), stain, 0.35)
    rgb = _post(rgb, r, 0.02, 0.08, vignette=0.12)
    return _down(rgb, w, h)


def build_entity_hair(w, h):
    W, H = _work(w, h)
    shape = (H, W)
    r = A.rng("entity_hair")
    rgb = np.ones((H, W, 3), np.float32) * A.hexc("#0b0a0b")
    # 竖长发丝（带少量高光）
    for color, n, alpha, wid in (("#191719", 150, 0.75, 0.9),
                                 ("#262229", 80, 0.6, 0.8),
                                 ("#38343c", 40, 0.45, 0.7)):
        segs = []
        for _ in range(n):
            x0 = r.uniform(0, W)
            y0 = r.uniform(-H * 0.1, H)
            L = r.uniform(H * 0.15, H * 0.6)
            ang = -np.pi / 2 + r.normal(0, 0.10)
            segs.append((x0, y0, x0 + math.cos(ang) * L,
                         y0 + math.sin(ang) * L, r.uniform(wid, wid * 2.2)))
        rgb = A.over(rgb, A.hexc(color), A.seg_mask(shape, segs, 0.8), alpha)
    # 湿发的团块高光
    sheen = A.smoothstep((A.fbm(shape, 0, 3, r, aniso=(3, 22)) - 0.66) / 0.1)
    rgb = A.over(rgb, A.hexc("#4a4650"), sheen, 0.35)
    rgb = A.grain(np.clip(rgb, 0, 1), r, 0.015, 0.2)
    return _down(rgb, w, h)


def build_entity_face(w, h):
    W, H = _work(w, h)
    shape = (H, W)
    r = A.rng("entity_face")
    yy, xx = A.coords(shape)
    cx = W * 0.5
    # 纸白底
    rgb = A.mix(A.hexc("#d9d5c8")[None, None], A.hexc("#eee9dc")[None, None],
                A.fbm(shape, 3, 5, r)[..., None])
    fiber = A.pnoise(shape, (240, 240), r)
    rgb *= (0.94 + 0.10 * fiber)[..., None]
    # 纸的褶皱/水痕
    wr = A.fbm(shape, 0, 4, r, aniso=(5, 20))
    rgb *= (1.0 - 0.16 * (wr - 0.5))[..., None]
    stain = A.smoothstep((A.fbm(shape, 5, 4, r) - 0.62) / 0.1)
    rgb = A.over(rgb, A.hexc("#b6a887"), stain, 0.25)

    def ellipse_mask(ecx, ecy, rx, ry, ang=0.0, feather=2.0):
        dd = np.sqrt(((xx - ecx) / rx) ** 2 + ((yy - ecy) / ry) ** 2)
        return A.smoothstep((1 - dd) * min(rx, ry) / feather)

    # 红颊（软腮红）
    for side in (-1, 1):
        cheek = np.exp(-((((xx - (cx + side * W * 0.19)) / (W * 0.10)) ** 2 +
                         ((yy - H * 0.55) / (H * 0.09)) ** 2)))
        rgb = A.over(rgb, A.hexc("#bd6259"), cheek, 0.34)
    # 眉毛：细墨线
    for side in (-1, 1):
        ex = cx + side * W * 0.155
        m = ellipse_mask(ex, H * 0.365, W * 0.085, H * 0.010,
                         feather=1.0)
        rgb = A.over(rgb, A.hexc("#2b2623"), m, 0.85)
    # 眼睛：墨线杏眼（黑眼窝 + 极小高光）
    for side in (-1, 1):
        ex = cx + side * W * 0.155
        ecy = H * 0.44 + (H * 0.006 if side < 0 else 0)
        eye = ellipse_mask(ex, ecy, W * 0.072, H * 0.026, feather=1.0)
        rgb = A.over(rgb, A.hexc("#181513"), eye, 0.95)
        # 眼线外扩
        line = ellipse_mask(ex, ecy, W * 0.086, H * 0.033, feather=1.0) - eye
        rgb = A.over(rgb, A.hexc("#3a332c"), np.clip(line, 0, 1), 0.55)
        socket = ellipse_mask(ex, ecy, W * 0.100, H * 0.042, feather=3.0)
        rgb = A.over(rgb, A.hexc("#b6aa95"), np.clip(socket - eye, 0, 1), 0.28)
    # 鼻：一小竖线 + 鼻翼
    nose = A.seg_mask(shape, [(cx + W * 0.004, H * 0.47, cx - W * 0.006,
                               H * 0.56, W * 0.006)], 0.8)
    rgb = A.over(rgb, A.hexc("#8d8374"), nose, 0.35)
    nostril = ellipse_mask(cx, H * 0.565, W * 0.030, H * 0.008, feather=1.0)
    rgb = A.over(rgb, A.hexc("#8a7d6d"), nostril, 0.3)
    # 嘴：细弯的暗红线
    mouth_pts = []
    for t in np.linspace(-1, 1, 15):
        mouth_pts.append((cx + t * W * 0.085, H * 0.685 + (t * t) * H * 0.012))
    mm = A.seg_mask(shape, [(p[0], p[1], q[0], q[1], W * 0.0075)
                            for p, q in zip(mouth_pts[:-1], mouth_pts[1:])], 0.8)
    rgb = A.over(rgb, A.hexc("#582320"), mm, 0.8)
    # 纸的裂纹（一道横过左颊）
    crack = A.smoothstep((A.ridged(shape, 8, 3, r) - 0.987) / 0.009)
    rgb = A.over(rgb, A.hexc("#8f8878"), crack * 0.6, 0.4)
    # 污渍与暗角
    smudge = A.blobs(shape, [(r.uniform(0, H), r.uniform(0, W), r.uniform(6, 24),
                             r.uniform(0.15, 0.4)) for _ in range(12)], feather=6)
    rgb = A.over(rgb, A.hexc("#8a7d62"), smudge, 0.3)
    rgb = _post(rgb, r, 0.02, 0.06, vignette=0.2)
    return _down(rgb, w, h)


def build_red_cloth(w, h):
    W, H = _work(w, h)
    shape = (H, W)
    r = A.rng("red_cloth")
    yy, xx = A.coords(shape)
    rgb = A.mix(A.hexc("#6f2621")[None, None], A.hexc("#93392f")[None, None],
                A.fbm(shape, 4, 4, r)[..., None])
    # 布的褶皱
    fold = 0.5 + 0.5 * np.cos(2 * np.pi * (xx * 2.0 / W + 0.2 * A.fbm(shape, 2, 3, r)))
    rgb *= (0.72 + 0.42 * fold)[..., None]
    weave = A.pnoise(shape, (260, 100), r)
    rgb *= (0.92 + 0.13 * weave)[..., None]
    # 褪色/灰尘
    fade = A.smoothstep((A.fbm(shape, 5, 4, r) - 0.55) / 0.15)
    rgb = A.over(rgb, A.hexc("#a55a48"), fade, 0.25)
    dust = A.smoothstep((A.pnoise(shape, (220, 220), r) - 0.66) / 0.1)
    rgb = A.over(rgb, A.hexc("#8a7a5e"), dust, 0.2)
    stain = A.blobs(shape, [(r.uniform(0, H), r.uniform(0, W), r.uniform(4, 16),
                            r.uniform(0.2, 0.5)) for _ in range(14)], feather=4)
    rgb = A.over(rgb, A.hexc("#4a241a"), stain, 0.3)
    rgb = _post(rgb, r, 0.024, 0.1, vignette=0.15)
    return _down(rgb, w, h)


def build_paper_money(w, h):
    W, H = _work(w, h)
    shape = (H, W)
    r = A.rng("paper_money")
    yy, xx = A.coords(shape)
    rgb = A.mix(A.hexc("#c9ab63")[None, None], A.hexc("#ddc27e")[None, None],
                A.fbm(shape, 4, 4, r)[..., None])
    fiber = A.pnoise(shape, (250, 250), r)
    rgb *= (0.92 + 0.12 * fiber)[..., None]
    # 红印：粗外框 + 中央红圆（内方孔）+ 上下小字印
    red = A.hexc("#9c2f26")
    m = np.zeros(shape, np.float32)
    border = A.border_dist(shape, W * 0.09, H * 0.09)
    m = np.maximum(m, A.smoothstep((4.0 - np.abs(border)) / 4.0))
    d = np.sqrt((xx - W * 0.5) ** 2 + (yy - H * 0.5) ** 2)
    m = np.maximum(m, np.exp(-((d - W * 0.20) / (W * 0.014)) ** 2))
    m = np.maximum(m, A.smoothstep((W * 0.055 - np.abs(d - W * 0.10)) / 2.0))
    # 方孔（挖掉，只影响中央圆）
    hole = A.border_dist(shape, W * 0.44, H * 0.44)
    hole_inside = A.smoothstep(hole / 2.0)
    m *= (1.0 - hole_inside)
    # 边缘红波浪纹
    wave = 0.5 + 0.5 * np.sin(2 * np.pi * (xx / W * 6 + 0.10))
    m = np.maximum(m, np.clip((wave - 0.86) / 0.06, 0, 1) * 0.55)
    for ty in (0.16, 0.84):
        m = np.maximum(m, _text_line(shape, "冥府", A.FONT_SONG, W * 0.085,
                                     (W * 0.5, H * ty)))
    m = _wear_text(m, r, wear=0.20, pit=0.35)
    rgb = A.over(rgb, red, m, 0.80)
    # 褪色与折痕
    rgb = A.over(rgb, A.hexc("#e0cf9c"), np.ones(shape) * 0.10)
    crease = np.exp(-((xx - W * 0.5) / (W * 0.008)) ** 2)
    rgb *= (1 - 0.06 * crease)[..., None]
    # 边缘发毛
    vg = A.vignette_mask(shape, 0.4, 1.5)
    rgb *= (0.85 + 0.15 * vg)[..., None]
    rgb = _post(rgb, r, 0.024, 0.06, vignette=0.15)
    return _down(rgb, w, h)


def build_steam(w, h):
    W, H = _work(w, h)
    shape = (H, W)
    r = A.rng("steam")
    yy, xx = A.coords(shape)
    # 多层雾团
    base = A.fbm(shape, 4, 5, r, persistence=0.55)
    base = base + 0.35 * A.fbm(shape, 9, 4, r)
    alpha = A.smoothstep((base - 0.62) / 0.28) * 0.65
    # 竖直的水汽拉丝
    wisp = A.fbm(shape, 0, 4, r, aniso=(6, 26))
    alpha = np.maximum(alpha, A.smoothstep((wisp - 0.66) / 0.14) * 0.35)
    # 边缘淡出
    edge = A.border_dist(shape, 0, 0)
    fade = A.smoothstep(edge / (W * 0.12))
    alpha *= fade
    alpha = np.clip(alpha, 0, 0.7)
    color = A.mix(A.hexc("#cdd2cc")[None, None], A.hexc("#e9e9e2")[None, None],
                  A.fbm(shape, 3, 3, r)[..., None])
    rgba = np.dstack([color, alpha])
    return _down(rgba, w, h)


# ------------------------------------------------------------------ 清单

SPECS = [
    dict(key="MAT_fabric_red", file="fabric_red.jpg", w=128, h=128,
         tiled=False, fn=build_fabric_red, tint="#ffffff",
         note="红毛巾/红布，起球、褪色"),
    dict(key="MAT_fabric_white", file="fabric_white.jpg", w=128, h=128,
         tiled=False, fn=build_fabric_white, tint="#ffffff",
         note="白布/纸衣/旧衬衫，泛黄褶皱"),
    dict(key="MAT_fabric_blue", file="fabric_blue.jpg", w=128, h=128,
         tiled=False, fn=build_fabric_blue, tint="#ffffff",
         note="蓝灰旧工装，斜纹、洗旧"),
    dict(key="MAT_paper", file="paper.jpg", w=128, h=128,
         tiled=False, fn=build_paper, tint="#f6eed8",
         note="发黄纸张/字条/纸钱底"),
    dict(key="MAT_photo", file="photo_old.jpg", w=256, h=256,
         tiled=False, fn=build_photo, tint="#ffffff",
         note="模糊褪色全家福（无清晰人脸）"),
    dict(key="MAT_tv_static", file="tv_static.jpg", w=256, h=256,
         tiled=False, fn=build_tv_static, tint="#ffffff",
         emissive="#a9bcc2", emissiveIntensity=0.55,
         note="CRT 雪花屏（黑白噪点 + 扫描线）"),
    dict(key="MAT_lamp_tube", file="lamp_tube.jpg", w=128, h=128,
         tiled=False, fn=build_lamp_tube, tint="#ffffff",
         emissive="#dff5e8", emissiveIntensity=1.6,
         note="日光灯管（自发光青白）"),
    dict(key="MAT_lamp_warm", file="lamp_warm.jpg", w=128, h=128,
         tiled=False, fn=build_lamp_warm, tint="#ffffff",
         emissive="#ffcf92", emissiveIntensity=1.5,
         note="白炽灯泡（自发光暖黄）"),
    dict(key="MAT_lantern_paper", file="lantern_paper.jpg", w=256, h=256,
         tiled=False, fn=build_lantern_paper, tint="#ffffff",
         emissive="#ff6a3a", emissiveIntensity=1.35,
         note="红纸灯笼（自发光橙红、竹骨）"),
    dict(key="MAT_sign_night_1", file="sign_night_1.jpg", w=512, h=256,
         tiled=False, fn=build_sign_night_1, tint="#ffffff",
         note="木牌：土地庙 前方 500 米"),
    dict(key="MAT_sign_night_2", file="sign_night_2.jpg", w=512, h=256,
         tiled=False, fn=build_sign_night_2, tint="#ffffff",
         note="木牌：夜路难行 早些回家"),
    dict(key="MAT_sign_bath", file="sign_bath.jpg", w=256, h=512,
         tiled=False, fn=build_sign_bath, tint="#ffffff",
         note="澡堂门牌：男湯（竖排）"),
    dict(key="MAT_shrine_tablet", file="shrine_tablet.jpg", w=256, h=512,
         tiled=False, fn=build_shrine_tablet, tint="#ffffff",
         note="石牌位：土地之神位（竖排）"),
    dict(key="MAT_door_number_501", file="door_number_501.jpg", w=128, h=128,
         tiled=False, fn=build_door_number_501, tint="#ffffff",
         note="门牌 501（旧金属底）"),
    dict(key="MAT_door_number_502", file="door_number_502.jpg", w=128, h=128,
         tiled=False, fn=build_door_number_502, tint="#ffffff",
         note="门牌 502"),
    dict(key="MAT_door_number_503", file="door_number_503.jpg", w=128, h=128,
         tiled=False, fn=build_door_number_503, tint="#ffffff",
         note="门牌 503（最重要，清晰）"),
    dict(key="MAT_door_number_504", file="door_number_504.jpg", w=128, h=128,
         tiled=False, fn=build_door_number_504, tint="#ffffff",
         note="门牌 504"),
    dict(key="MAT_clock_face", file="clock_face.jpg", w=256, h=256,
         tiled=False, fn=build_clock_face, tint="#ffffff",
         note="挂钟表盘（罗马数字、旧、指针 3:00）"),
    dict(key="MAT_mirror_grime", file="mirror_grime.png", w=512, h=512,
         tiled=False, fn=build_mirror_grime, tint="#ffffff", alpha=True,
         transparent=True,
         note="镜面污渍/水痕/指纹（半透明叠加 PNG）"),
    dict(key="MAT_stain_mold", file="stain_mold.png", w=256, h=256,
         tiled=True, fn=build_stain_mold, tint="#ffffff", alpha=True,
         transparent=True,
         note="霉斑贴花（可平铺，RGBA）"),
    dict(key="MAT_stain_water", file="stain_water.png", w=256, h=256,
         tiled=True, fn=build_stain_water, tint="#ffffff", alpha=True,
         transparent=True,
         note="水渍贴花（可平铺，RGBA）"),
    dict(key="MAT_entity_white", file="entity_white.jpg", w=256, h=256,
         tiled=False, fn=build_entity_white, tint="#ffffff",
         note="实体惨白皮肤/纸（冷白、细纹）"),
    dict(key="MAT_entity_hair", file="entity_hair.jpg", w=128, h=128,
         tiled=False, fn=build_entity_hair, tint="#ffffff",
         note="黑色发丝/纸黑"),
    dict(key="MAT_entity_face", file="entity_face.jpg", w=256, h=256,
         tiled=False, fn=build_entity_face, tint="#ffffff",
         note="纸人脸（白底、红颊、墨线眼）"),
    dict(key="MAT_red_cloth", file="red_cloth.jpg", w=128, h=128,
         tiled=False, fn=build_red_cloth, tint="#ffffff",
         note="庙里的红布/红绳"),
    dict(key="MAT_paper_money", file="paper_money.jpg", w=128, h=128,
         tiled=False, fn=build_paper_money, tint="#ffffff",
         note="黄纸红印的纸钱"),
    dict(key="MAT_steam", file="steam.png", w=256, h=256,
         tiled=False, fn=build_steam, tint="#ffffff", alpha=True,
         transparent=True,
         note="水汽/蒸汽（半透明 PNG，边缘柔）"),
]
