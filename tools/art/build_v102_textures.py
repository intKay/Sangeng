"""v1.0.2 叙事贴图：家庭照片 / 儿童蜡笔画 / 挂历 / 通知板 / 对联 / 澡堂物料 / 镜面裂纹 / 手印。

在现有 tools/art/artlib.py 风格与工具上增量生成；固定 seed、无外部图片素材。
输出：
  assets/textures/ 下 12 张新贴图 + 追加写入 manifest.json（保留原有 50 条）
  reports/art/v1.0.2-verify.txt

用法（仓库根目录）：
  python tools/art/build_v102_textures.py
  python tools/art/build_v102_textures.py --only MAT_calendar,MAT_mirror_crack
  python tools/art/build_v102_textures.py --list
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np                                       # noqa: E402
from PIL import Image, ImageDraw, ImageFont, ImageFilter  # noqa: E402

import artlib as A                                       # noqa: E402

SS = 2            # 工作分辨率倍率
NEW_BUDGET = 500 * 1024   # 新增素材总大小上限（字节）


# ================================================================ 基础工具

def _work(w, h):
    return w * SS, h * SS


def _down(arr, w, h):
    return A.downscale(arr, w, h, SS)


def _post(rgb, r, grain_amt=0.02, desat=0.15, contrast=1.0, brightness=0.0,
          vignette=0.0):
    rgb = A.desaturate(rgb, desat)
    if contrast != 1.0 or brightness != 0.0:
        rgb = A.brighten_contrast(rgb, brightness, contrast)
    if vignette > 0:
        vg = A.vignette_mask(rgb.shape, vignette, 2.0)
        rgb = rgb * vg[..., None]
    return A.grain(np.clip(rgb, 0, 1), r, grain_amt, 0.22)


def _pil_mask(shape, draw_fn):
    H, W = shape
    im = Image.new("L", (W, H), 0)
    draw_fn(ImageDraw.Draw(im))
    return np.asarray(im, np.float32) / 255.0


def _ellipse_mask(shape, cx, cy, rx, ry, angle=0.0, feather=1.5):
    yy, xx = A.coords(shape)
    ca, sa = math.cos(angle), math.sin(angle)
    dx, dy = xx - cx, yy - cy
    u = dx * ca + dy * sa
    v = -dx * sa + dy * ca
    d = np.sqrt((u / max(rx, 1e-3)) ** 2 + (v / max(ry, 1e-3)) ** 2)
    return A.smoothstep((1.0 - d) * min(rx, ry) / max(feather, 1e-3))


def _text_block(shape, lines, font_path, size, x_center, y_start, line_gap,
                tracking=0, stroke=0):
    m = np.zeros(shape[:2], np.float32)
    y = y_start
    for line in lines:
        m = np.maximum(m, A.text_mask(line, font_path, size, shape,
                                      center=(x_center, y), tracking=tracking,
                                      stroke_width=stroke))
        y += line_gap
    return m


def _wear_text(mask, r, wear=0.25, pit=0.5):
    H, W = mask.shape
    m = mask * (0.58 + 0.42 * A.fbm((H, W), 11, 4, r))
    m = A.smoothstep((m - wear) / max(1 - wear, 1e-3))
    pits = A.smoothstep((A.pnoise((H, W), (190, 190), r) - 0.76) / 0.05)
    m *= (1.0 - pit * pits)
    return m


def _paper_base(shape, r, base="#ded4b8", mottle=0.10, fiber=0.10, foxing=18):
    H, W = shape
    rgb = A.mix(A.hexc(base)[None, None], A.hexc("#f0e8d2")[None, None],
                A.fbm(shape, 4, 5, r)[..., None])
    rgb *= (1.0 - mottle + 2 * mottle * A.pnoise(shape, (150, 150), r))[..., None]
    fib = A.fbm(shape, 0, 4, r, aniso=(9, 150))
    rgb *= (1.0 - fiber * 0.5 + fiber * fib)[..., None]
    fox = A.blobs(shape, [(r.uniform(0, H), r.uniform(0, W),
                           r.uniform(1.5, 6.0), r.uniform(0.2, 0.5))
                          for _ in range(foxing)], feather=2.0)
    rgb = A.over(rgb, A.hexc("#8a6b3a"), fox, 0.4)
    return rgb


def _crease(shape, r, n=2, width=0.006, dark=0.10):
    H, W = shape
    yy, xx = A.coords(shape)
    out = np.zeros(shape[:2], np.float32)
    for _ in range(n):
        ang = r.uniform(-0.5, 0.5) + (math.pi / 2 if r.random() < 0.5 else 0)
        cx, cy = r.uniform(0.2, 0.8) * W, r.uniform(0.2, 0.8) * H
        d = np.abs((xx - cx) * math.sin(ang) + (yy - cy) * math.cos(ang))
        out = np.maximum(out, np.exp(-(d / (W * width)) ** 2))
    return out


def _scratches(rgb, r, shape, n=14, color="#ded6c0", alpha=0.16, wmin=0.5, wmax=1.5):
    H, W = shape
    segs = [(r.uniform(0, W), r.uniform(0, H), r.uniform(0, W),
             r.uniform(0, H), r.uniform(wmin, wmax)) for _ in range(n)]
    return A.over(rgb, A.hexc(color), A.seg_mask((H, W), segs, 0.8), alpha)


def _dust(rgb, r, shape, n=40, color="#b8ad96", alpha=0.2):
    H, W = shape
    specs = [(r.uniform(0, H), r.uniform(0, W), r.uniform(0.6, 2.4),
              r.uniform(0.3, 1.0)) for _ in range(n)]
    return A.over(rgb, A.hexc(color), A.blobs((H, W), specs, feather=1.2), alpha)


def _photo_effects(rgb, r, shape, border=0.0, sepia=0.35, desat=0.45,
                   blur_px=0.6, lifts=0.06):
    """老照片：褪色、偏黄、软焦、颗粒、划痕、暗角、污点。"""
    H, W = shape
    rgb = A.desaturate(rgb, desat)
    rgb = A.over(rgb, A.hexc("#b09368"), np.ones((H, W), np.float32) * 0.22, sepia)
    rgb = A.blur(rgb, blur_px, periodic=False)
    # 提亮黑位、降对比（旧照片发灰）
    rgb = rgb * (1.0 - lifts) + lifts
    # 污点/划痕
    spots = A.blobs((H, W), [(r.uniform(0, H), r.uniform(0, W),
                              r.uniform(1.0, 5.0), r.uniform(0.2, 0.5))
                             for _ in range(26)], feather=2.0)
    rgb = A.over(rgb, A.hexc("#7a6440"), spots, 0.3)
    rgb = _scratches(rgb, r, shape, 16, "#e4dcc8", 0.16)
    # 光斑/漏光
    corner = A.blobs((H, W), [(r.uniform(0, H), r.uniform(0, W),
                               r.uniform(20, 60), 1.0) for _ in range(2)],
                     feather=14.0)
    rgb = A.over(rgb, A.hexc("#e6d6ae"), corner, 0.10)
    vg = A.vignette_mask((H, W), 0.4, 1.7)
    rgb *= vg[..., None]
    rgb = A.grain(np.clip(rgb, 0, 1), r, 0.024, 0.3)
    return rgb


def _stamp_date(img: Image.Image, text, xy, size, color=(210, 138, 66)):
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype(A.FONT_SONG, int(size))
    x, y = xy
    d.text((x + 1, y + 1), text, font=font, fill=(46, 30, 14))
    d.text((x, y), text, font=font, fill=tuple(color))
    return img


# ================================================================ 人物（模糊剪影）

def _bust_masks(shape, cx, head_cy, head_r, sh_w, bottom, hair="short"):
    """返回 (head, hair, body, neck) 四个软蒙版；只有轮廓，没有五官。"""
    H, W = shape
    head = _ellipse_mask(shape, cx, head_cy, head_r * 0.88, head_r * 1.00,
                         feather=1.4)
    hair_cap = _ellipse_mask(shape, cx, head_cy - head_r * 0.06,
                             head_r * 1.05, head_r * 1.10, feather=1.6)
    face_open = _ellipse_mask(shape, cx, head_cy + head_r * 0.26,
                              head_r * 0.74, head_r * 0.80, feather=2.2)
    hair_m = np.clip(hair_cap - face_open * 0.85, 0, 1)
    if hair == "long":
        for side in (-1, 1):
            lock = _ellipse_mask(shape, cx + side * head_r * 0.62,
                                 head_cy + head_r * 0.95,
                                 head_r * 0.44, head_r * 1.20, feather=3.0)
            hair_m = np.maximum(hair_m, lock * 0.92)
    neck = _pil_mask(shape, lambda d: d.rectangle(
        [cx - head_r * 0.30, head_cy + head_r * 0.55,
         cx + head_r * 0.30, head_cy + head_r * 1.15], fill=255))
    top = head_cy + head_r * 0.82
    body = _pil_mask(shape, lambda d: d.rounded_rectangle(
        [cx - sh_w, top, cx + sh_w, bottom], radius=int(sh_w * 0.55), fill=255))
    return head, hair_m, body, neck


def _paint_bust(rgb, masks, colors, blur_px=2.0, cloth_shade=0.22):
    H, W = rgb.shape[:2]
    head, hair, body, neck = masks
    yy, xx = A.coords(rgb.shape[:2])
    body_b = A.blur(body, blur_px * 1.7, periodic=False)
    head_b = A.blur(head, blur_px * 1.3, periodic=False)
    neck_b = A.blur(neck, blur_px, periodic=False)
    hair_b = A.blur(hair, blur_px * 1.4, periodic=False)
    # 衣服：竖向 + 侧向明暗
    ny = (yy / H)
    nx = (xx / W - 0.5)
    shade = (1.0 - cloth_shade * ny) * (1.0 - 0.35 * np.abs(nx))
    cloth = A.hexc(colors["cloth"])[None, None] * shade[..., None]
    rgb = A.mix(rgb, np.broadcast_to(cloth, rgb.shape).astype(np.float32),
                body_b * 0.96)
    # 脖子 + 脸（只是一块更亮的模糊色）
    skin_m = np.clip(head_b + neck_b * 0.85, 0, 1)
    rgb = A.over(rgb, A.hexc(colors["skin"]), skin_m * 0.92)
    face_soft = A.blur(head_b, blur_px * 2.4, periodic=False)
    rgb = A.over(rgb, A.hexc(colors["skin_light"]), face_soft * 0.42)
    # 头发（只盖发区，露出脸部）
    rgb = A.over(rgb, A.hexc(colors["hair"]), hair_b * 0.92)
    # 整个头部再糊一层，保证没有五官感
    blurred = A.blur(rgb, blur_px * 2.0, periodic=False)
    face_region = A.blur(head_b, blur_px * 1.8, periodic=False) * 0.8
    rgb = A.mix(rgb, blurred, face_region)
    return rgb


# ================================================================ 1-3 家庭照片

def _photo_frame(w, h, rng_name, border_frac=0.05):
    W, H = _work(w, h)
    shape = (H, W)
    r = A.rng(rng_name)
    b = int(min(W, H) * border_frac)
    paper = _paper_base(shape, r, "#d8d0ba", mottle=0.05, fiber=0.04, foxing=10)
    # 相纸白边略黄、四角磨损
    inner = A.border_dist(shape, b, b)
    inner_m = A.smoothstep(inner / 2.0)
    paper = A.over(paper, A.hexc("#efe8d4"), inner_m, 0.25)
    edge = np.clip(1.0 - inner_m, 0, 1)
    paper = A.over(paper, A.hexc("#b0a184"), edge, 0.35)
    return shape, r, paper, inner_m, b


def build_photo_family_1(w, h):
    """父母+孩子的家庭合影（室内，彩色褪色，人脸模糊）。"""
    shape, r, canvas, inner_m, b = _photo_frame(w, h, "photo_family_1")
    H, W = shape
    # 背景：室内墙面 + 窗帘皱褶
    yy, xx = A.coords(shape)
    bg = A.gradient_v(H, W, [0.0, 0.55, 1.0],
                      [A.hexc("#8a8068"), A.hexc("#9c9078"), A.hexc("#6d614e")])
    drape = 0.5 + 0.5 * np.cos(2 * np.pi * (xx / W * 3.1 + 0.25 * A.fbm(shape, 2, 3, r)))
    bg *= (0.82 + 0.25 * drape)[..., None]
    bg *= (0.88 + 0.22 * A.fbm(shape, 4, 3, r))[..., None]
    rgb = bg
    # 三个人：父亲（右后）、母亲（左后）、孩子（中间前）
    figs = [
        dict(cx=0.63 * W, head=0.30 * H, hr=0.088 * H, sh=0.155 * W, bot=H * 0.99,
             cloth="#46505c", skin="#c6a686", skin_light="#d8bf9f",
             hair="#2b2620", hair_kind="short"),
        dict(cx=0.355 * W, head=0.335 * H, hr=0.082 * H, sh=0.150 * W, bot=H * 0.99,
             cloth="#8a5d55", skin="#c9ab8d", skin_light="#dcc4a6",
             hair="#2e2622", hair_kind="long"),
        dict(cx=0.50 * W, head=0.545 * H, hr=0.064 * H, sh=0.105 * W, bot=H * 0.93,
             cloth="#d5c9a8", skin="#ceb293", skin_light="#e1cbb0",
             hair="#30261f", hair_kind="short"),
    ]
    for f in figs:
        masks = _bust_masks(shape, f["cx"], f["head"], f["hr"], f["sh"], f["bot"],
                            f["hair_kind"])
        rgb = _paint_bust(rgb, masks, dict(cloth=f["cloth"], skin=f["skin"],
                                           skin_light=f["skin_light"], hair=f["hair"]),
                          blur_px=2.6)
    # 轻微双重曝光（老相机手抖），让人脸更模糊
    ghost = A.blur(A.desaturate(rgb, 0.4), 6.0, periodic=False)
    rgb = A.mix(rgb, ghost, 0.12)
    rgb = _photo_effects(rgb, r, shape, sepia=0.58, desat=0.34, blur_px=1.0)
    rgb = A.mix(rgb, A.hexc("#a8845a")[None, None], 0.09)
    rgb = canvas * (1 - inner_m[..., None]) + rgb * inner_m[..., None]
    # 相纸边缘阴影
    inner_shadow = np.clip(A.blur(inner_m, 3.0, periodic=False) - inner_m, 0, 1)
    rgb *= (1.0 - 0.35 * inner_shadow)[..., None]
    rgb = _post(rgb, r, 0.02, 0.06)
    out = A.to_img(_down(rgb, w, h))
    out = _stamp_date(out, "95 6 1", (w - 66, h - 22), max(9, int(h * 0.055)),
                      (208, 132, 62))
    return np.asarray(out, np.float32) / 255.0


def build_photo_family_2(w, h):
    """母亲与孩子旧照（竖幅、黑白偏棕、划痕多）。"""
    shape, r, canvas, inner_m, b = _photo_frame(w, h, "photo_family_2",
                                                 border_frac=0.055)
    H, W = shape
    yy, xx = A.coords(shape)
    bg = A.gradient_v(H, W, [0.0, 0.6, 1.0],
                      [A.hexc("#a29c8c"), A.hexc("#b3ac9a"), A.hexc("#8a8474")])
    bg *= (0.88 + 0.2 * A.fbm(shape, 3, 4, r))[..., None]
    rgb = bg
    figs = [
        dict(cx=0.57 * W, head=0.27 * H, hr=0.088 * W, sh=0.21 * W, bot=H * 0.98,
             cloth="#5f5a54", skin="#cdbfa9", skin_light="#dfd2bd",
             hair="#2b2621", hair_kind="long"),
        dict(cx=0.44 * W, head=0.53 * H, hr=0.070 * W, sh=0.155 * W, bot=H * 0.94,
             cloth="#9a9384", skin="#d3c5b0", skin_light="#e3d7c4",
             hair="#322a23", hair_kind="short"),
    ]
    for f in figs:
        masks = _bust_masks(shape, f["cx"], f["head"], f["hr"], f["sh"], f["bot"],
                            f["hair_kind"])
        rgb = _paint_bust(rgb, masks, dict(cloth=f["cloth"], skin=f["skin"],
                                           skin_light=f["skin_light"], hair=f["hair"]),
                          blur_px=3.0)
    ghost = A.blur(A.desaturate(rgb, 0.5), 7.0, periodic=False)
    rgb = A.mix(rgb, ghost, 0.16)
    # 黑白偏棕
    rgb = _photo_effects(rgb, r, shape, sepia=0.42, desat=0.88, blur_px=1.2)
    rgb = A.brighten_contrast(rgb, 0.015, 1.22)
    rgb = A.over(rgb, A.hexc("#8f7c5e"), np.ones(shape, np.float32) * 0.10, 0.5)
    rgb = canvas * (1 - inner_m[..., None]) + rgb * inner_m[..., None]
    inner_shadow = np.clip(A.blur(inner_m, 3.0, periodic=False) - inner_m, 0, 1)
    rgb *= (1.0 - 0.4 * inner_shadow)[..., None]
    # 边角破损
    corner = A.blobs(shape, [(H * 0.98, W * 0.02, W * 0.08, 1.0)], feather=4)
    rgb = A.over(rgb, A.hexc("#8a7c62"), corner * 0.5, 0.5)
    rgb = _post(rgb, r, 0.022, 0.05)
    return np.asarray(A.to_img(_down(rgb, w, h)), np.float32) / 255.0


def build_photo_family_3(w, h):
    """年轻时的合影 / 结婚照（室内布景，褪色带红）。"""
    shape, r, canvas, inner_m, b = _photo_frame(w, h, "photo_family_3",
                                                 border_frac=0.045)
    H, W = shape
    yy, xx = A.coords(shape)
    bg = A.gradient_v(H, W, [0.0, 0.5, 1.0],
                      [A.hexc("#9a8a70"), A.hexc("#b0a086"), A.hexc("#6f6552")])
    # 布景：左侧暗、右侧亮 + 幕布竖褶
    key = 0.75 + 0.5 * np.exp(-((xx - W * 0.7) / (W * 0.4)) ** 2)
    bg *= key[..., None]
    bg *= (0.86 + 0.25 * A.fbm(shape, 3, 4, r))[..., None]
    rgb = bg
    figs = [
        dict(cx=0.40 * W, head=0.31 * H, hr=0.078 * H, sh=0.14 * W, bot=H * 0.99,
             cloth="#3a3a3e", skin="#c8aa8b", skin_light="#d9bfa0",
             hair="#26211d", hair_kind="short"),
        dict(cx=0.60 * W, head=0.33 * H, hr=0.072 * H, sh=0.13 * W, bot=H * 0.99,
             cloth="#d3cbb8", skin="#cfb597", skin_light="#e0c9ad",
             hair="#2a231e", hair_kind="long"),
    ]
    for f in figs:
        masks = _bust_masks(shape, f["cx"], f["head"], f["hr"], f["sh"], f["bot"],
                            f["hair_kind"])
        rgb = _paint_bust(rgb, masks, dict(cloth=f["cloth"], skin=f["skin"],
                                           skin_light=f["skin_light"], hair=f["hair"]),
                          blur_px=2.4, cloth_shade=0.28)
    # 新郎胸前的红花 / 新娘手里的花（褪色的红）
    flower1 = A.blobs(shape, [(H * 0.57, W * 0.46, W * 0.030, 1.0),
                              (H * 0.555, W * 0.445, W * 0.020, 1.0)], feather=2.0)
    rgb = A.over(rgb, A.hexc("#8f3a34"), flower1, 0.55)
    flower2 = A.blobs(shape, [(H * 0.66, W * 0.63, W * 0.026, 1.0)], feather=2.5)
    rgb = A.over(rgb, A.hexc("#a34a44"), flower2, 0.45)
    ghost = A.blur(A.desaturate(rgb, 0.45), 6.0, periodic=False)
    rgb = A.mix(rgb, ghost, 0.10)
    rgb = _photo_effects(rgb, r, shape, sepia=0.55, desat=0.30, blur_px=0.9)
    rgb = canvas * (1 - inner_m[..., None]) + rgb * inner_m[..., None]
    # 右下角水渍
    water = A.blobs(shape, [(H * 0.94, W * 0.92, W * 0.18, 1.0),
                            (H * 0.86, W * 0.86, W * 0.10, 1.0)], feather=10)
    rgb = A.over(rgb, A.hexc("#8a7448"), water, 0.25)
    inner_shadow = np.clip(A.blur(inner_m, 3.0, periodic=False) - inner_m, 0, 1)
    rgb *= (1.0 - 0.35 * inner_shadow)[..., None]
    rgb = _post(rgb, r, 0.02, 0.06)
    out = A.to_img(_down(rgb, w, h))
    out = _stamp_date(out, "88 11 12", (w - 78, h - 24), max(9, int(h * 0.052)),
                      (206, 130, 60))
    return np.asarray(out, np.float32) / 255.0


# ================================================================ 4 儿童蜡笔画

def _crayon(rgb, shape, r, segs, color, alpha=0.75, width=(2.0, 4.2)):
    H, W = shape
    s = [(a, b, c, d, r.uniform(*width)) for (a, b, c, d) in segs]
    m = A.seg_mask((H, W), s, feather=1.0)
    wax = 0.55 + 0.45 * A.pnoise((H, W), (300, 300), r)
    m *= wax
    return A.over(rgb, A.hexc(color), m, alpha)


def _crayon_poly(rgb, shape, r, pts, color, alpha=0.6, n=90, width=(2.0, 4.0)):
    """用短笔触“涂”多边形内部（蜡笔排线）。"""
    H, W = shape
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    segs = []
    for _ in range(n):
        x = r.uniform(min(xs), max(xs))
        y = r.uniform(min(ys), max(ys))
        ang = r.uniform(-0.9, 0.9)
        L = r.uniform(10, 26)
        segs.append((x, y, x + math.cos(ang) * L, y + math.sin(ang) * L))
    # 限定在多边形内
    mask_poly = _pil_mask(shape, lambda d: d.polygon(pts, fill=255))
    m = A.seg_mask((H, W), [(a, b, c, d, r.uniform(*width))
                            for (a, b, c, d) in segs], feather=1.0)
    m *= mask_poly
    wax = 0.55 + 0.45 * A.pnoise((H, W), (300, 300), r)
    return A.over(rgb, A.hexc(color), m * wax, alpha)


def build_child_drawing(w, h):
    shape_r = None
    W, H = _work(w, h)
    shape = (H, W)
    r = A.rng("child_drawing")
    rgb = _paper_base(shape, r, "#e2d8ba", mottle=0.07, fiber=0.08, foxing=14)
    # 天空：蓝色蜡笔排线（画得不满，留白）
    sky_segs = []
    for _ in range(90):
        x = r.uniform(W * 0.03, W * 0.97)
        y = r.uniform(H * 0.05, H * 0.52)
        sky_segs.append((x, y, x + r.uniform(8, 34), y + r.normal(0, 3)))
    rgb = _crayon(rgb, shape, r, sky_segs, "#5d86b8", 0.55, (2.2, 4.5))
    # 太阳
    sun_c = (W * 0.82, H * 0.16)
    sun_segs = []
    for k in range(26):
        a = k / 26 * math.pi * 2
        rr = W * 0.055
        sun_segs.append((sun_c[0] + math.cos(a) * rr * 0.85,
                         sun_c[1] + math.sin(a) * rr * 0.85,
                         sun_c[0] + math.cos(a) * rr,
                         sun_c[1] + math.sin(a) * rr))
    rgb = _crayon(rgb, shape, r, sun_segs, "#d9862f", 0.8, (3, 5))
    for k in range(9):
        a = k / 9 * math.pi * 2 + 0.2
        rgb = _crayon(rgb, shape, r, [
            (sun_c[0] + math.cos(a) * W * 0.075, sun_c[1] + math.sin(a) * W * 0.075,
             sun_c[0] + math.cos(a) * W * 0.115, sun_c[1] + math.sin(a) * W * 0.115)],
            "#d9862f", 0.75, (3, 6))
    # 草地
    grass_segs = []
    for _ in range(120):
        x = r.uniform(W * 0.02, W * 0.98)
        y = r.uniform(H * 0.58, H * 0.80)
        grass_segs.append((x, y, x + r.uniform(6, 24), y + r.normal(0, 2.5)))
    rgb = _crayon(rgb, shape, r, grass_segs, "#5a7a3c", 0.6, (2.2, 4.2))
    # 房子：红屋顶 + 黄墙 + 棕门 + 蓝窗
    roof = [(W * 0.30, H * 0.38), (W * 0.50, H * 0.20), (W * 0.70, H * 0.38)]
    rgb = _crayon_poly(rgb, shape, r, roof, "#a8443a", 0.72, 120)
    rgb = _crayon(rgb, shape, r, [(W * 0.30, H * 0.38, W * 0.50, H * 0.20),
                                    (W * 0.50, H * 0.20, W * 0.70, H * 0.38)],
                  "#a8443a", 0.9, (4.0, 6.0))
    wall = [(W * 0.335, H * 0.38), (W * 0.665, H * 0.38),
            (W * 0.665, H * 0.62), (W * 0.335, H * 0.62)]
    rgb = _crayon_poly(rgb, shape, r, wall, "#d9b154", 0.66, 170)
    rgb = _crayon(rgb, shape, r, [(W * 0.335, H * 0.38, W * 0.665, H * 0.38),
                                    (W * 0.665, H * 0.38, W * 0.665, H * 0.62),
                                    (W * 0.665, H * 0.62, W * 0.335, H * 0.62),
                                    (W * 0.335, H * 0.62, W * 0.335, H * 0.38)],
                  "#b98a34", 0.85, (3.5, 5.5))
    door = [(W * 0.465, H * 0.49), (W * 0.535, H * 0.49),
            (W * 0.535, H * 0.62), (W * 0.465, H * 0.62)]
    rgb = _crayon_poly(rgb, shape, r, door, "#7a5236", 0.78, 60)
    rgb = _crayon(rgb, shape, r, [(W * 0.465, H * 0.49, W * 0.535, H * 0.49),
                                    (W * 0.535, H * 0.49, W * 0.535, H * 0.62),
                                    (W * 0.535, H * 0.62, W * 0.465, H * 0.62),
                                    (W * 0.465, H * 0.62, W * 0.465, H * 0.49)],
                  "#5a3a26", 0.85, (2.5, 4.0))
    for wx in (0.39, 0.585):
        win = [(W * (wx - 0.028), H * 0.45), (W * (wx + 0.028), H * 0.45),
               (W * (wx + 0.028), H * 0.52), (W * (wx - 0.028), H * 0.52)]
        rgb = _crayon_poly(rgb, shape, r, win, "#5a7fa0", 0.7, 30)
        rgb = _crayon(rgb, shape, r, [(W * wx, H * 0.45, W * wx, H * 0.52)],
                      "#3f5c74", 0.8, (1.8, 2.6))
    # 三个人：爸爸/妈妈/我（牵手）
    people = [
        (W * 0.30, H * 0.80, "#48608a"),   # 爸爸
        (W * 0.50, H * 0.80, "#9a4a44"),   # 妈妈
        (W * 0.70, H * 0.82, "#c2a03c"),   # 我
    ]
    for (cx, base, col) in people:
        hr = W * 0.056
        rgb = _crayon(rgb, shape, r, [(cx, base - hr * 2.0, cx, base - hr * 3.6)],
                      col, 0.75, (2.5, 4.0))  # 身体
        head_ring = []
        for k in range(16):
            a = k / 16 * math.pi * 2
            head_ring.append((cx + math.cos(a) * hr * 0.8,
                              base - hr * 4.4 + math.sin(a) * hr * 0.8))
        for p, q in zip(head_ring[:-1], head_ring[1:]):
            rgb = _crayon(rgb, shape, r, [(p[0], p[1], q[0], q[1])], col, 0.8, (2, 3.2))
        # 腿
        rgb = _crayon(rgb, shape, r, [
            (cx, base - hr * 2.0, cx - hr * 0.75, base),
            (cx, base - hr * 2.0, cx + hr * 0.75, base)], col, 0.7, (2.2, 3.6))
        # 手臂
        rgb = _crayon(rgb, shape, r, [
            (cx, base - hr * 3.1, cx - hr * 1.7, base - hr * 2.3),
            (cx, base - hr * 3.1, cx + hr * 1.7, base - hr * 2.3)], col, 0.7, (2.2, 3.6))
    # 牵手连线
    rgb = _crayon(rgb, shape, r, [
        (W * 0.30 + W * 0.045 * 1.7, H * 0.80 - W * 0.045 * 2.3,
         W * 0.50 - W * 0.045 * 1.7, H * 0.80 - W * 0.045 * 2.3),
        (W * 0.50 + W * 0.045 * 1.7, H * 0.80 - W * 0.045 * 2.3,
         W * 0.70 - W * 0.045 * 1.7, H * 0.82 - W * 0.045 * 2.3)], "#6a5a3a", 0.6, (1.5, 2.5))
    # 几笔歪斜的云和鸟
    for _ in range(3):
        y = r.uniform(H * 0.08, H * 0.22)
        x = r.uniform(W * 0.10, W * 0.60)
        rgb = _crayon(rgb, shape, r, [(x, y, x + W * 0.06, y + r.normal(0, 2))],
                      "#7a9ab8", 0.45, (2, 3.5))
    # 纸的做旧：折痕、卷边、胶带印、针孔
    crease = _crease(shape, r, n=2, width=0.004, dark=0.12)
    rgb *= (1.0 - 0.10 * crease)[..., None]
    edge = A.border_dist(shape, 0, 0)
    edge_m = 1.0 - A.smoothstep(edge / (W * 0.03))
    rgb *= (1.0 - 0.18 * edge_m)[..., None]
    rgb += (0.03 * np.roll(edge_m, 4, axis=0))[..., None]
    for (tx, ty) in ((W * 0.05, H * 0.05), (W * 0.95, H * 0.06)):
        tape = _pil_mask(shape, lambda d: d.rectangle(
            [tx - W * 0.05, ty - H * 0.02, tx + W * 0.05, ty + H * 0.02], fill=255))
        rgb = A.over(rgb, A.hexc("#c9b878"), A.blur(tape, 2.0), 0.35)
    pinch = A.blobs(shape, [(H * 0.04, W * 0.5, W * 0.012, 1.0)], feather=1.5)
    rgb = A.over(rgb, A.hexc("#5a5038"), pinch, 0.7)
    rgb = _post(rgb, r, 0.024, 0.05, vignette=0.22)
    return _down(rgb, w, h)


# ================================================================ 5 1999 年挂历

def build_calendar(w, h):
    W, H = _work(w, h)
    shape = (H, W)
    r = A.rng("calendar")
    yy, xx = A.coords(shape)
    rgb = _paper_base(shape, r, "#d6c8a4", mottle=0.09, fiber=0.08, foxing=16)

    # 顶部挂孔 + 阴影
    hole = _ellipse_mask(shape, W * 0.5, H * 0.018, W * 0.035, H * 0.012,
                         feather=1.2)
    rgb = A.over(rgb, A.hexc("#e8e0c8"), hole, 0.4)
    hole_dark = _ellipse_mask(shape, W * 0.5, H * 0.018, W * 0.018, H * 0.008,
                              feather=1.0)
    rgb = A.over(rgb, A.hexc("#2a241c"), hole_dark, 0.9)

    # 标题：1999 年 三月
    title = _text_block(shape, ["1999"], A.FONT_HEI, W * 0.18,
                        W * 0.5, H * 0.075, H * 0.10)
    title2 = _text_block(shape, ["年  三  月"], A.FONT_SONG, W * 0.095,
                         W * 0.5, H * 0.135, H * 0.08)
    rgb = A.over(rgb, A.hexc("#8f2f26"), title, 0.92)
    rgb = A.over(rgb, A.hexc("#2f2a22"), title2, 0.9)
    # 红色细线
    line = _pil_mask(shape, lambda d: d.rectangle(
        [W * 0.10, H * 0.175, W * 0.90, H * 0.181], fill=255))
    rgb = A.over(rgb, A.hexc("#a83a2e"), line, 0.8)

    # 星期行
    week = _text_block(shape, ["日  一  二  三  四  五  六"], A.FONT_SONG,
                       W * 0.060, W * 0.5, H * 0.215, H * 0.05)
    rgb = A.over(rgb, A.hexc("#6f2f28"), week, 0.85)

    # 日期网格：1999-03-01 是星期一
    col_w = W / 7.0
    row_h = H * 0.062
    y0 = H * 0.255
    # 网格线
    for c in range(1, 7):
        x = W * 0.04 + (W * 0.92) * c / 7.0
        m = _pil_mask(shape, lambda d, x=x: d.line(
            [(x, y0 - H * 0.025), (x, y0 + row_h * 5.2)], fill=255, width=max(1, int(W * 0.002))))
        rgb *= (1.0 - 0.10 * m)[..., None]
    for rr in range(7):
        y = y0 + rr * row_h
        m = _pil_mask(shape, lambda d, y=y: d.line(
            [(W * 0.04, y), (W * 0.96, y)], fill=255, width=max(1, int(W * 0.002))))
        rgb *= (1.0 - 0.10 * m)[..., None]
    # 数字（3 月 1 日 = 周一 -> 第二列）
    day = 1
    circle_c = None
    for row in range(5):
        for col in range(7):
            if row == 0 and col == 0:
                continue
            if day > 31:
                break
            cx = W * 0.04 + (col + 0.5) * (W * 0.92) / 7.0
            cy = y0 + (row + 0.5) * row_h
            txt = A.text_mask(str(day), A.FONT_SONG, W * 0.050, shape,
                              center=(cx, cy))
            colr = "#2c2820" if day not in (12,) else "#8f2f26"
            rgb = A.over(rgb, A.hexc(colr), txt, 0.9)
            if day == 12:
                circle_c = (cx, cy)
            day += 1
    # 红笔圈出 12 日（手绘感：多段抖动圆）
    if circle_c:
        cx, cy = circle_c
        rr = W * 0.036
        pts = []
        for k in range(19):
            a = k / 18 * math.pi * 2
            jr = rr * (1.0 + r.normal(0, 0.045))
            pts.append((cx + math.cos(a) * jr * 0.95,
                        cy + math.sin(a) * jr * 0.85))
        cm = A.polyline_mask(shape, pts, W * 0.006, feather=1.2)
        rgb = A.over(rgb, A.hexc("#a8332a"), cm, 0.85)
    # 红笔手写小字（竖排）：早点回家
    hand = A.vtext_mask("早点回家", A.FONT_KAI, W * 0.105, shape,
                        center=(W * 0.76, H * 0.775), char_gap=1.10)
    hand = _wear_text(hand, r, wear=0.30, pit=0.35)
    rgb = A.over(rgb, A.hexc("#8a2620"), hand, 0.9)
    # 铅笔小字 3.12
    pencil = A.text_mask("3.12", A.FONT_SONG, W * 0.034, shape,
                         center=(W * 0.24, H * 0.79))
    rgb = A.over(rgb, A.hexc("#5a554a"), pencil, 0.55)
    # 做旧：折痕、角落起翘、污渍
    crease = _crease(shape, r, n=2, width=0.006, dark=0.12)
    rgb *= (1.0 - 0.10 * crease)[..., None]
    edge = A.border_dist(shape, 0, 0)
    rgb *= (1.0 - 0.16 * (1 - A.smoothstep(edge / (W * 0.025))))[..., None]
    stain = A.blobs(shape, [(r.uniform(0, H), r.uniform(0, W), r.uniform(5, 20),
                             r.uniform(0.2, 0.5)) for _ in range(16)], feather=5)
    rgb = A.over(rgb, A.hexc("#8a6f40"), stain, 0.22)
    rgb = _post(rgb, r, 0.022, 0.04, vignette=0.22)
    return _down(rgb, w, h)


# ================================================================ 6 通知板

def _notice_sheet(size, r, title, lines, title_font=A.FONT_HEI,
                  body_font=A.FONT_SONG, stamp=None, title_color="#2a2620",
                  body_color="#33302a", paper="#e0d9c2"):
    W, H = size
    rng = A.rng(f"notice_{title}_{r.integers(0, 999999)}")
    rgb = _paper_base((H, W), rng, paper, mottle=0.05, fiber=0.05, foxing=8)
    shape = (H, W)
    tm = A.text_mask(title, title_font, W * 0.115, shape,
                     center=(W * 0.5, H * 0.12), stroke_width=1)
    rgb = A.over(rgb, A.hexc(title_color), tm, 0.9)
    m = np.zeros(shape[:2], np.float32)
    y = H * 0.25
    size_body = W * 0.052
    for line in lines:
        m = np.maximum(m, A.text_mask(line, body_font, size_body, shape,
                                      center=(W * 0.5, y)))
        y += size_body * 1.55
    rgb = A.over(rgb, A.hexc(body_color), _wear_text(m, rng, 0.12, 0.2), 0.9)
    if stamp:
        sc = _ellipse_mask(shape, W * 0.72, H * 0.82, W * 0.14, W * 0.055,
                           angle=-0.3, feather=2.0)
        ring = np.clip(sc - _ellipse_mask(shape, W * 0.72, H * 0.82,
                                          W * 0.125, W * 0.043, angle=-0.3,
                                          feather=2.0), 0, 1)
        rgb = A.over(rgb, A.hexc("#a83a30"), ring * 0.8, 0.55)
        st = A.text_mask(stamp, A.FONT_HEI, W * 0.05, shape,
                         center=(W * 0.72, H * 0.82))
        rgb = A.over(rgb, A.hexc("#a83a30"), st, 0.5)
    edge = A.border_dist(shape, 0, 0)
    rgb *= (1.0 - 0.10 * (1 - A.smoothstep(edge / (W * 0.02))))[..., None]
    rng2 = A.rng("notice_sheet_grain")
    rgb = A.grain(np.clip(rgb, 0, 1), rng2, 0.02, 0.2)
    return rgb


def build_notice_board(w, h):
    W, H = _work(w, h)
    shape = (H, W)
    r = A.rng("notice_board")
    yy, xx = A.coords(shape)
    # 软木板底
    rgb = A.mix(A.hexc("#5d4632")[None, None], A.hexc("#79603f")[None, None],
                A.fbm(shape, 3, 5, r)[..., None])
    cork = A.pnoise(shape, (260, 260), r)
    rgb *= (0.82 + 0.30 * cork)[..., None]
    fib = A.fbm(shape, 0, 3, r, aniso=(14, 150))
    rgb *= (0.92 + 0.14 * fib)[..., None]
    # 边框
    edge = A.border_dist(shape, W * 0.018, H * 0.03)
    frame = 1.0 - A.smoothstep(edge / 3.0)
    rgb = A.over(rgb, A.hexc("#3a2a1d"), frame, 0.85)
    rgb = A.over(rgb, A.hexc("#8a7354"),
                 np.clip(A.blur(frame, 2.0, periodic=False) - frame, 0, 1), 0.35)

    # 各张纸：先各自画好 → 旋转 → 贴到板子上
    canvas = A.to_img(np.clip(rgb, 0, 1))
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    layers = []

    def add_sheet(cx, cy, sw, sh, angle, title, lines, stamp=None, paper="#e0d9c2"):
        sheet = _notice_sheet((sw, sh), r, title, lines, stamp=stamp, paper=paper)
        im = A.to_img(np.clip(sheet, 0, 1)).convert("RGBA")
        im = im.rotate(angle, expand=True, resample=Image.BICUBIC)
        x = int(cx * W - im.width / 2)
        y = int(cy * H - im.height / 2)
        layers.append((im, x, y))

    add_sheet(0.27, 0.50, int(W * 0.30), int(H * 0.72), 2.0,
              "停水通知",
              ["因地下管道维修", "3月14日 8:00—18:00", "全楼停水", "请提前储水",
               "物业办公室 3.10"], stamp="物业")
    add_sheet(0.57, 0.62, int(W * 0.24), int(H * 0.50), -2.5,
              "水费通知单",
              ["户号 503", "用水 8.5 吨", "金额 12.60 元", "月底前交纳"], stamp="已收")
    add_sheet(0.80, 0.32, int(W * 0.24), int(H * 0.42), 1.5,
              "通  知",
              ["楼道禁止堆放杂物", "请各户自行清理", "    居委会"])
    add_sheet(0.79, 0.75, int(W * 0.22), int(H * 0.32), -1.2,
              "停电通知",
              ["3月18日 7:00—17:00", "线路检修停电"])

    # 先画阴影，再贴纸
    d = ImageDraw.Draw(shadow)
    for im, x, y in layers:
        d.rectangle([x + 6, y + 7, x + im.width + 8, y + im.height + 9],
                    fill=(0, 0, 0, 90))
    shadow = shadow.filter(ImageFilter.GaussianBlur(5))
    canvas = canvas.convert("RGBA")
    canvas = Image.alpha_composite(canvas, shadow)
    for im, x, y in layers:
        canvas.alpha_composite(im, (x, y))
    rgb = np.asarray(canvas.convert("RGB"), np.float32) / 255.0

    # 胶带、图钉、灰尘
    for (tx, ty, ang) in ((W * 0.15, H * 0.16, 0.2), (W * 0.42, H * 0.13, -0.3),
                          (W * 0.68, H * 0.87, 0.1), (W * 0.90, H * 0.50, -0.2)):
        tw, th = W * 0.055, H * 0.022
        ca, sa = math.cos(ang), math.sin(ang)
        pts = []
        for (sx, sy) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            x = tx + (sx * tw * ca - sy * th * sa)
            y = ty + (sx * tw * sa + sy * th * ca)
            pts.append((x, y))
        tape = _pil_mask(shape, lambda d, pts=pts: d.polygon(pts, fill=255))
        rgb = A.over(rgb, A.hexc("#c9b06a"), A.blur(tape, 1.2), 0.45)
    for (px, py) in ((W * 0.18, H * 0.25), (W * 0.49, H * 0.30),
                     (W * 0.74, H * 0.18), (W * 0.66, H * 0.58)):
        pin = _ellipse_mask(shape, px, py, W * 0.010, W * 0.010, feather=1.0)
        rgb = A.over(rgb, A.hexc("#2a2624"), pin, 0.9)
        hi = _ellipse_mask(shape, px - W * 0.003, py - W * 0.003,
                           W * 0.004, W * 0.004, feather=0.8)
        rgb = A.over(rgb, A.hexc("#cfc9b8"), hi, 0.8)
    dust = A.fbm(shape, 7, 4, r)
    rgb *= (0.94 + 0.10 * dust)[..., None]
    vg = A.vignette_mask(shape, 0.35, 1.7)
    rgb *= vg[..., None]
    rgb = _post(rgb, r, 0.02, 0.05)
    return _down(rgb, w, h)


# ================================================================ 7 褪色对联

def build_couplet(w, h):
    W, H = _work(w, h)
    shape = (H, W)
    r = A.rng("couplet")
    yy, xx = A.coords(shape)
    # 红纸（已褪成砖红/粉）
    rgb = A.mix(A.hexc("#8f3a30")[None, None], A.hexc("#b0584a")[None, None],
                A.fbm(shape, 3, 5, r)[..., None])
    paper_fib = A.fbm(shape, 0, 4, r, aniso=(10, 120))
    rgb *= (0.90 + 0.16 * paper_fib)[..., None]
    # 竖向纸纹
    rgb *= (0.94 + 0.10 * (0.5 + 0.5 * np.cos(2 * np.pi * xx / W * 9.0)))[..., None]
    # 金色大字（竖排七言）
    text = "天增岁月人增寿"
    chars = list(text)
    step = H * 0.112
    y0 = H * 0.09
    mask = np.zeros(shape, np.float32)
    for i, ch in enumerate(chars):
        cy = y0 + i * step
        mask = np.maximum(mask, A.text_mask(ch, A.FONT_KAI, W * 0.30, shape,
                                             center=(W * 0.5, cy),
                                             stroke_width=int(W * 0.008)))
    mask = _wear_text(mask, r, wear=0.20, pit=0.45)
    # 金字的暗边 + 金色主体 + 高光
    edge = np.clip(np.roll(np.roll(mask, 2, axis=0), 2, axis=1) - mask, 0, 1)
    rgb = A.over(rgb, A.hexc("#5a2118"), edge, 0.55)
    gold = A.mix(A.hexc("#c79a4e")[None, None], A.hexc("#e6c77a")[None, None],
                 A.fbm(shape, 8, 4, r)[..., None])
    rgb = A.mix(rgb, gold, mask * 0.92)
    # 金粉磨损：随机漏出红纸
    flake = A.smoothstep((A.fbm(shape, 14, 4, r) - 0.60) / 0.08) * mask
    rgb = A.over(rgb, A.hexc("#a8503f"), flake, 0.45)
    # 上下端破损、胶带痕、污渍
    tear_top = A.blobs(shape, [(H * 0.005, W * 0.35, W * 0.22, 1.0),
                               (H * 0.01, W * 0.75, W * 0.16, 1.0)], feather=4)
    rgb = A.over(rgb, A.hexc("#d8c9a8"), tear_top, 0.45)
    tear_bot = A.blobs(shape, [(H * 0.995, W * 0.60, W * 0.18, 1.0)], feather=5)
    rgb = A.over(rgb, A.hexc("#cdbd9c"), tear_bot, 0.4)
    stain = A.blobs(shape, [(r.uniform(0, H), r.uniform(0, W), r.uniform(6, 22),
                             r.uniform(0.15, 0.4)) for _ in range(18)], feather=5)
    rgb = A.over(rgb, A.hexc("#7a3a2a"), stain, 0.25)
    crease = _crease(shape, r, n=3, width=0.004, dark=0.12)
    rgb *= (1.0 - 0.10 * crease)[..., None]
    # 小印章（底部）
    seal = _pil_mask(shape, lambda d: d.rectangle(
        [W * 0.36, H * 0.915, W * 0.64, H * 0.965], fill=255))
    seal_in = _pil_mask(shape, lambda d: d.rectangle(
        [W * 0.38, H * 0.922, W * 0.62, H * 0.958], fill=255))
    rgb = A.over(rgb, A.hexc("#a52a24"), seal, 0.7)
    rgb = A.over(rgb, A.hexc("#e8dcc0"),
                 _wear_text(seal - seal_in, r, 0.15, 0.2), 0.5)
    edge = A.border_dist(shape, 0, 0)
    rgb *= (1.0 - 0.18 * (1 - A.smoothstep(edge / (W * 0.03))))[..., None]
    rgb = _post(rgb, r, 0.022, 0.05, vignette=0.2)
    return _down(rgb, w, h)


# ================================================================ 8 澡堂宣传画/安全须知

def build_bath_poster(w, h):
    W, H = _work(w, h)
    shape = (H, W)
    r = A.rng("bath_poster")
    yy, xx = A.coords(shape)
    rgb = _paper_base(shape, r, "#e2d5b0", mottle=0.06, fiber=0.05, foxing=10)
    # 蓝色边框
    frame = 1.0 - A.smoothstep(A.border_dist(shape, W * 0.022, H * 0.018)
                               / (W * 0.006))
    rgb = A.over(rgb, A.hexc("#2e5570"), frame, 0.85)
    inner = 1.0 - A.smoothstep(A.border_dist(shape, W * 0.040, H * 0.030)
                               / (W * 0.003))
    rgb = A.over(rgb, A.hexc("#8a6a3a"), inner, 0.35)
    # 标题
    title = _text_block(shape, ["浴池安全须知"], A.FONT_HEI, W * 0.115,
                        W * 0.5, H * 0.085, H * 0.1)
    rgb = A.over(rgb, A.hexc("#2e5570"), title, 0.92)
    uline = _pil_mask(shape, lambda d: d.rectangle(
        [W * 0.22, H * 0.128, W * 0.78, H * 0.133], fill=255))
    rgb = A.over(rgb, A.hexc("#a83a2e"), uline, 0.8)
    # 插画区：浅青绿底 + 瓷砖格 + 蒸汽 + 红毛巾 + 滑倒警示
    ill = _pil_mask(shape, lambda d: d.rounded_rectangle(
        [W * 0.07, H * 0.16, W * 0.93, H * 0.55], radius=W * 0.01, fill=255))
    rgb = A.over(rgb, A.hexc("#b8cfc2"), ill, 0.85)
    # 瓷砖格
    tilemask = np.zeros(shape, np.float32)
    for i in range(1, 6):
        x = W * 0.07 + (W * 0.86) * i / 6.0
        tilemask = np.maximum(tilemask, _pil_mask(shape, lambda d, x=x: d.line(
            [(x, H * 0.16), (x, H * 0.55)], fill=255, width=max(1, int(W * 0.0025)))))
    for j in range(1, 4):
        y = H * 0.16 + (H * 0.39) * j / 4.0
        tilemask = np.maximum(tilemask, _pil_mask(shape, lambda d, y=y: d.line(
            [(W * 0.07, y), (W * 0.93, y)], fill=255, width=max(1, int(W * 0.0025)))))
    rgb = A.over(rgb, A.hexc("#6f8c7e"), tilemask * ill, 0.5)
    # 蒸汽（白色软团）
    steam = A.fbm(shape, 4, 5, r)
    steam_m = A.smoothstep((steam - 0.52) / 0.2) * ill
    rgb = A.over(rgb, A.hexc("#eef2ea"), A.blur(steam_m, 8.0, periodic=False), 0.5)
    # 红毛巾挂在钩子上
    hook_x, hook_y = W * 0.20, H * 0.245
    rgb = A.over(rgb, A.hexc("#4a4038"), _ellipse_mask(shape, hook_x, hook_y,
                                                       W * 0.012, W * 0.012), 0.8)
    towel = _pil_mask(shape, lambda d: d.polygon([
        (hook_x - W * 0.040, hook_y + H * 0.012),
        (hook_x + W * 0.022, hook_y + H * 0.015),
        (hook_x + W * 0.040, hook_y + H * 0.075),
        (hook_x + W * 0.020, hook_y + H * 0.145),
        (hook_x - W * 0.012, hook_y + H * 0.120),
        (hook_x - W * 0.048, hook_y + H * 0.150)], fill=255))
    rgb = A.over(rgb, A.hexc("#a8443c"), A.blur(towel, 1.2), 0.88)
    for k in range(3):
        fx = hook_x - W * 0.030 + k * W * 0.024
        fold = _pil_mask(shape, lambda d, fx=fx: d.line(
            [(fx, hook_y + H * 0.02), (fx - W * 0.006, hook_y + H * 0.14)],
            fill=255, width=max(1, int(W * 0.004))))
        rgb = A.over(rgb, A.hexc("#7a2f2a"), fold * 0.35, 0.55)
    # 蒸汽更明显
    rgb = A.over(rgb, A.hexc("#eef2ea"),
                 A.blur(A.smoothstep((A.fbm(shape, 6, 5, r) - 0.58) / 0.16)
                        * ill, 5.0, periodic=False), 0.55)
    # 长凳 + 水桶
    bench = _pil_mask(shape, lambda d: d.rectangle(
        [W * 0.60, H * 0.47, W * 0.90, H * 0.495], fill=255))
    rgb = A.over(rgb, A.hexc("#6b4a32"), bench * ill, 0.85)
    for bx in (0.63, 0.86):
        leg = _pil_mask(shape, lambda d, bx=bx: d.rectangle(
            [W * bx, H * 0.495, W * (bx + 0.015), H * 0.55], fill=255))
        rgb = A.over(rgb, A.hexc("#4f3826"), leg * ill, 0.8)
    bucket = _ellipse_mask(shape, W * 0.55, H * 0.515, W * 0.035, H * 0.022,
                           feather=1.5) * ill
    rgb = A.over(rgb, A.hexc("#7a8a7e"), bucket, 0.8)
    # 黄色警告三角 + 「滑」
    tri = _pil_mask(shape, lambda d: d.polygon([
        (W * 0.69, H * 0.49), (W * 0.60, H * 0.33), (W * 0.78, H * 0.33)], fill=255))
    rgb = A.over(rgb, A.hexc("#d9a83a"), tri, 0.9)
    tri_line = np.clip(tri - _pil_mask(shape, lambda d: d.polygon([
        (W * 0.685, H * 0.465), (W * 0.615, H * 0.345), (W * 0.765, H * 0.345)],
        fill=255)), 0, 1)
    rgb = A.over(rgb, A.hexc("#2a2620"), tri_line, 0.85)
    hua = A.text_mask("滑", A.FONT_HEI, W * 0.062, shape,
                      center=(W * 0.692, H * 0.418))
    rgb = A.over(rgb, A.hexc("#2a2620"), hua, 0.9)
    # 注意事项列表
    rules_y = H * 0.615
    rules = ["一、小心地滑，切勿奔跑",
             "二、贵重物品请交柜台保管",
             "三、高血压、心脏病患者慎入",
             "四、请勿在池内搓洗、追逐",
             "五、节约用水，爱护公物"]
    size_r = W * 0.052
    for i, line in enumerate(rules):
        m = A.text_mask(line, A.FONT_SONG, size_r, shape,
                        center=(W * 0.5, rules_y + i * size_r * 1.7))
        rgb = A.over(rgb, A.hexc("#2c2820"), m, 0.88)
    # 落款
    foot = A.text_mask("国营向阳浴池  宣", A.FONT_SONG, W * 0.042, shape,
                       center=(W * 0.5, H * 0.945))
    rgb = A.over(rgb, A.hexc("#5a3028"), foot, 0.8)
    seal = _pil_mask(shape, lambda d: d.rectangle(
        [W * 0.80, H * 0.925, W * 0.87, H * 0.958], fill=255))
    rgb = A.over(rgb, A.hexc("#a52a24"), seal, 0.55)
    # 做旧
    stain = A.blobs(shape, [(r.uniform(0, H), r.uniform(0, W), r.uniform(6, 26),
                             r.uniform(0.15, 0.4)) for _ in range(18)], feather=6)
    rgb = A.over(rgb, A.hexc("#8a6f40"), stain, 0.2)
    crease = _crease(shape, r, n=3, width=0.004, dark=0.10)
    rgb *= (1.0 - 0.08 * crease)[..., None]
    rgb *= (0.92 + 0.10 * A.fbm(shape, 5, 4, r))[..., None]
    edge = A.border_dist(shape, 0, 0)
    rgb *= (1.0 - 0.22 * (1 - A.smoothstep(edge / (W * 0.025))))[..., None]
    rgb = _post(rgb, r, 0.024, 0.10, vignette=0.45)
    return _down(rgb, w, h)


# ================================================================ 9 澡堂票价/营业时间牌

def build_bath_notice(w, h):
    W, H = _work(w, h)
    shape = (H, W)
    r = A.rng("bath_notice")
    yy, xx = A.coords(shape)
    # 深绿珐琅底
    rgb = A.mix(A.hexc("#2c453d")[None, None], A.hexc("#3d5a4e")[None, None],
                A.fbm(shape, 3, 4, r)[..., None])
    rgb *= (0.92 + 0.12 * A.pnoise(shape, (180, 180), r))[..., None]
    # 奶白边框
    border = 1.0 - A.smoothstep(A.border_dist(shape, W * 0.028, H * 0.045)
                                / (W * 0.004))
    rgb = A.over(rgb, A.hexc("#cfc7ad"), border, 0.85)
    inner = 1.0 - A.smoothstep(A.border_dist(shape, W * 0.042, H * 0.065)
                               / (W * 0.002))
    rgb = A.over(rgb, A.hexc("#5a6a5c"), inner, 0.4)
    # 标题
    title = A.text_mask("票 价 表", A.FONT_HEI, W * 0.070, shape,
                        center=(W * 0.30, H * 0.19))
    rgb = A.over(rgb, A.hexc("#e0d8bc"), title, 0.92)
    # 左右分隔线
    sep = _pil_mask(shape, lambda d: d.line(
        [(W * 0.58, H * 0.13), (W * 0.58, H * 0.90)], fill=255,
        width=max(1, int(W * 0.003))))
    rgb = A.over(rgb, A.hexc("#cfc7ad"), sep, 0.4)
    # 左侧票价行
    rows = [("男 浴", "2.00 元"), ("女 浴", "2.00 元"), ("盆 塘", "3.50 元")]
    y = H * 0.36
    for name, price in rows:
        m1 = A.text_mask(name, A.FONT_HEI, W * 0.048, shape,
                         center=(W * 0.23, y))
        m2 = A.text_mask(price, A.FONT_SONG, W * 0.044, shape,
                         center=(W * 0.45, y))
        rgb = A.over(rgb, A.hexc("#e0d8bc"), m1, 0.9)
        rgb = A.over(rgb, A.hexc("#e0d8bc"), m2, 0.9)
        y += H * 0.17
    # 涨价：红笔划掉盆塘价格 + 手写 4.00
    cross = _pil_mask(shape, lambda d: d.line(
        [(W * 0.35, H * 0.68), (W * 0.53, H * 0.72)], fill=255,
        width=max(2, int(W * 0.006))))
    rgb = A.over(rgb, A.hexc("#a8332a"), cross, 0.8)
    newp = A.text_mask("4.00 元", A.FONT_KAI, W * 0.050, shape,
                       center=(W * 0.455, H * 0.755))
    newp = _wear_text(newp, r, wear=0.2, pit=0.2)
    rgb = A.over(rgb, A.hexc("#c56a5a"), newp, 0.85)
    # 右侧营业时间
    t2 = A.text_mask("营业时间", A.FONT_HEI, W * 0.044, shape,
                     center=(W * 0.79, H * 0.24))
    rgb = A.over(rgb, A.hexc("#e0d8bc"), t2, 0.9)
    times = ["早 6:00 — 晚 22:00", "节假日照常", "锅炉检修另行通知"]
    y = H * 0.40
    for line in times:
        m = A.text_mask(line, A.FONT_SONG, W * 0.033, shape,
                        center=(W * 0.79, y))
        rgb = A.over(rgb, A.hexc("#d8d0b4"), m, 0.85)
        y += H * 0.115
    foot = A.text_mask("国 营 向 阳 浴 池", A.FONT_SONG, W * 0.028, shape,
                       center=(W * 0.79, H * 0.83))
    rgb = A.over(rgb, A.hexc("#c9c1a6"), foot, 0.8)
    # 珐琅做旧：裂纹、掉漆、锈、螺丝
    crack = A.smoothstep((A.ridged(shape, 9, 3, r) - 0.988) / 0.008)
    rgb = A.over(rgb, A.hexc("#7a8474"), crack, 0.35)
    chip = A.smoothstep((A.fbm(shape, 6, 4, r) - 0.66) / 0.04)
    rgb = A.over(rgb, A.hexc("#6b5230"), chip, 0.5)
    rust = A.smoothstep((A.fbm(shape, 0, 4, r, aniso=(50, 4)) - 0.72) / 0.08)
    rust *= (yy / H) ** 0.7
    rgb = A.over(rgb, A.hexc("#8a4a24"), rust, 0.45)
    for (sx, sy) in ((W * 0.05, H * 0.08), (W * 0.95, H * 0.08),
                     (W * 0.05, H * 0.92), (W * 0.95, H * 0.92)):
        screw = _ellipse_mask(shape, sx, sy, W * 0.014, W * 0.020, feather=1.0)
        rgb = A.over(rgb, A.hexc("#8f8a76"), screw, 0.85)
        slot = _pil_mask(shape, lambda d, sx=sx, sy=sy: d.line(
            [(sx - W * 0.010, sy), (sx + W * 0.010, sy)], fill=255,
            width=max(1, int(W * 0.002))))
        rgb = A.over(rgb, A.hexc("#3f3a30"), slot, 0.7)
    dust = A.smoothstep((A.pnoise(shape, (250, 250), r) - 0.68) / 0.1)
    rgb = A.over(rgb, A.hexc("#8a7a5c"), dust, 0.22)
    vg = A.vignette_mask(shape, 0.38, 1.8)
    rgb *= vg[..., None]
    rgb = _post(rgb, r, 0.022, 0.05)
    return _down(rgb, w, h)


# ================================================================ 10 旧澡票

def build_bath_ticket(w, h):
    W, H = _work(w, h)
    shape = (H, W)
    r = A.rng("bath_ticket")
    yy, xx = A.coords(shape)
    # 浅蓝绿薄纸
    rgb = _paper_base(shape, r, "#c6d3ce", mottle=0.06, fiber=0.06, foxing=8)
    # 边框
    border = _pil_mask(shape, lambda d: d.rectangle(
        [W * 0.03, H * 0.06, W * 0.97, H * 0.94], outline=255,
        width=max(1, int(W * 0.004))))
    rgb = A.over(rgb, A.hexc("#3f6070"), border, 0.7)
    # 撕线（左侧存根）
    perf = np.zeros(shape, np.float32)
    for k in range(14):
        y = H * (0.10 + k * 0.058)
        perf = np.maximum(perf, _ellipse_mask(shape, W * 0.155, y,
                                              W * 0.006, H * 0.008, feather=1.0))
    rgb = A.over(rgb, A.hexc("#7a8a86"), perf, 0.8)
    stub = A.text_mask("存根", A.FONT_SONG, W * 0.040, shape,
                       center=(W * 0.09, H * 0.30))
    rgb = A.over(rgb, A.hexc("#3f6070"), stub, 0.75)
    no = A.text_mask("No.047213", A.FONT_SONG, W * 0.026, shape,
                     center=(W * 0.09, H * 0.72))
    rgb = A.over(rgb, A.hexc("#3f6070"), no, 0.75)
    # 主体文字
    head = A.text_mask("向阳浴池", A.FONT_HEI, W * 0.052, shape,
                       center=(W * 0.55, H * 0.20))
    rgb = A.over(rgb, A.hexc("#2f4a56"), head, 0.9)
    big = A.text_mask("澡  票", A.FONT_HEI, W * 0.095, shape,
                      center=(W * 0.55, H * 0.41))
    rgb = A.over(rgb, A.hexc("#2f4a56"), big, 0.92)
    price = A.text_mask("贰 元", A.FONT_SONG, W * 0.085, shape,
                        center=(W * 0.55, H * 0.61))
    rgb = A.over(rgb, A.hexc("#a8332a"), price, 0.85)
    small = _text_block(shape, ["大池 · 男部", "当日有效  请勿遗失"],
                        A.FONT_SONG, W * 0.029, W * 0.55, H * 0.735, H * 0.085)
    rgb = A.over(rgb, A.hexc("#4a5a5c"), small, 0.8)
    # 红色圆章（盖一半）
    stamp = _ellipse_mask(shape, W * 0.80, H * 0.36, W * 0.105, W * 0.13,
                          angle=0.2, feather=2.0)
    ring = np.clip(stamp - _ellipse_mask(shape, W * 0.80, H * 0.36,
                                         W * 0.092, W * 0.114, angle=0.2,
                                         feather=2.0), 0, 1)
    rgb = A.over(rgb, A.hexc("#b03a30"), ring, 0.55)
    st = A.text_mask("99.3", A.FONT_HEI, W * 0.034, shape,
                     center=(W * 0.80, H * 0.36))
    rgb = A.over(rgb, A.hexc("#b03a30"), st, 0.5)
    # 手写日期
    date = A.text_mask("1999.3.12", A.FONT_KAI, W * 0.028, shape,
                       center=(W * 0.42, H * 0.905))
    rgb = A.over(rgb, A.hexc("#3a3a38"), date, 0.6)
    # 做旧：折痕、污渍、边缘磨损
    crease = _crease(shape, r, n=2, width=0.005, dark=0.12)
    rgb *= (1.0 - 0.10 * crease)[..., None]
    stain = A.blobs(shape, [(r.uniform(0, H), r.uniform(0, W), r.uniform(4, 16),
                             r.uniform(0.15, 0.4)) for _ in range(10)], feather=4)
    rgb = A.over(rgb, A.hexc("#8a7448"), stain, 0.22)
    edge = A.border_dist(shape, 0, 0)
    rgb *= (1.0 - 0.18 * (1 - A.smoothstep(edge / (W * 0.02))))[..., None]
    rgb = _post(rgb, r, 0.022, 0.04, vignette=0.2)
    return _down(rgb, w, h)


# ================================================================ 11 镜面裂纹（RGBA）

def build_mirror_crack(w, h):
    W, H = _work(w, h)
    shape = (H, W)
    r = A.rng("mirror_crack")
    ox, oy = W * 0.44, H * 0.40
    lines = np.zeros(shape, np.float32)

    def add_crack(x0, y0, ang, length, width, depth=0, wobble=0.30):
        nonlocal lines
        pts = [(x0, y0)]
        a = ang
        d = 0.0
        n = int(r.integers(6, 13))
        for _ in range(n):
            a += r.normal(0, wobble)        # 玻璃裂的折角
            d += length / n * r.uniform(0.45, 1.55)
            pts.append((x0 + math.cos(a) * d, y0 + math.sin(a) * d))
        lines = np.maximum(lines, A.polyline_mask(shape, pts, width, feather=0.8))
        return pts, a

    # 主放射裂纹 + 分叉（角度均匀 + 少量折角，像玻璃不像树枝）
    for k in range(18):
        a0 = k / 18.0 * math.pi * 2 + r.normal(0, 0.09)
        L = W * r.uniform(0.26, 0.48)
        pts, a_end = add_crack(ox, oy, a0, L, W * r.uniform(0.0012, 0.0022),
                               wobble=0.16)
        for _ in range(int(r.integers(1, 3))):
            idx = int(r.integers(1, max(2, len(pts) - 1)))
            bx, by = pts[idx]
            add_crack(bx, by, a_end + r.normal(0, 0.7),
                      W * r.uniform(0.04, 0.15), W * r.uniform(0.0009, 0.0016),
                      1, wobble=0.40)
    # 冲击点附近的细碎裂纹
    for _ in range(34):
        a0 = r.uniform(0, math.pi * 2)
        d0 = r.uniform(W * 0.012, W * 0.11)
        x = ox + math.cos(a0) * d0
        y = oy + math.sin(a0) * d0
        add_crack(x, y, r.uniform(0, math.pi * 2),
                  W * r.uniform(0.012, 0.055), W * 0.0010, 2, wobble=0.5)
    # 断续的同心碎裂环
    for ring_i in range(1, 4):
        rr = W * 0.055 * ring_i * r.uniform(0.85, 1.22)
        start = r.uniform(0, math.pi * 2)
        span = r.uniform(0.9, 2.6)
        pts = []
        for i in range(16):
            a = start + span * i / 15.0
            jr = rr * (1.0 + r.normal(0, 0.03))
            pts.append((ox + math.cos(a) * jr, oy + math.sin(a) * jr))
        lines = np.maximum(lines, A.polyline_mask(shape, pts, W * 0.0015,
                                                  feather=0.8))
    # 中心的碎玻璃渣
    shards = A.blobs(shape, [(oy + r.normal(0, W * 0.03),
                              ox + r.normal(0, W * 0.03),
                              W * r.uniform(0.002, 0.010), 1.0)
                             for _ in range(18)], feather=1.0)
    lines = np.maximum(lines, shards * 0.9)

    # 暗边（玻璃断面的折射阴影）+ 亮芯 + 微光
    dark = np.roll(np.roll(lines, 1, axis=0), 2, axis=1)
    dark = np.clip(dark - lines * 0.55, 0, 1)
    glow = A.blur(lines, 2.4, periodic=False)
    haze_d = np.sqrt((np.arange(W)[None, :] - ox) ** 2 +
                     (np.arange(H)[:, None] - oy) ** 2) / (W * 0.12)
    haze = np.exp(-haze_d ** 2) * 0.65
    rgb = np.zeros((H, W, 3), np.float32)
    rgb = A.mix(rgb, A.hexc("#556a6a")[None, None] *
                np.ones((H, W, 1), np.float32), np.clip(dark * 0.7, 0, 1))
    rgb = A.mix(rgb, A.hexc("#eef7f3")[None, None] *
                np.ones((H, W, 1), np.float32), np.clip(lines * 0.98, 0, 1))
    rgb = A.mix(rgb, A.hexc("#a9bdba")[None, None] *
                np.ones((H, W, 1), np.float32), np.clip(glow * 0.26, 0, 1) * (1 - lines))
    rgb = A.mix(rgb, A.hexc("#c6d2ce")[None, None] *
                np.ones((H, W, 1), np.float32), np.clip(haze, 0, 1) * 0.07)
    alpha = np.clip(lines * 0.92 + glow * 0.22 + dark * 0.38 + haze * 0.06, 0, 1)
    # 量化颜色/alpha，减小透明 PNG 体积（锁在预算内）
    rgb = np.round(np.clip(rgb, 0, 1) * 31) / 31
    alpha = np.round(np.clip(alpha, 0, 1) * 47) / 47
    rgba = np.dstack([rgb, alpha * 0.96])
    return _down(rgba, w, h)


# ================================================================ 12 水汽手印（RGBA）

def build_handprint(w, h):
    W, H = _work(w, h)
    shape = (H, W)
    r = A.rng("handprint")
    cx, cy = W * 0.50, H * 0.60
    palm = _ellipse_mask(shape, cx, cy, W * 0.132, H * 0.152, feather=2.2)
    wrist = _pil_mask(shape, lambda d: d.rounded_rectangle(
        [cx - W * 0.080, cy + H * 0.09, cx + W * 0.080, cy + H * 0.29],
        radius=int(W * 0.045), fill=255))
    fingers = np.zeros(shape, np.float32)
    finger_defs = [
        (cx - W * 0.105, cy - H * 0.085, cx - W * 0.150, cy - H * 0.300, W * 0.047),
        (cx - W * 0.038, cy - H * 0.120, cx - W * 0.052, cy - H * 0.355, W * 0.049),
        (cx + W * 0.030, cy - H * 0.120, cx + W * 0.043, cy - H * 0.345, W * 0.049),
        (cx + W * 0.098, cy - H * 0.100, cx + W * 0.142, cy - H * 0.300, W * 0.046),
        # 拇指
        (cx + W * 0.125, cy + H * 0.005, cx + W * 0.245, cy - H * 0.070, W * 0.052),
    ]
    for (x0, y0, x1, y1, fw) in finger_defs:
        fingers = np.maximum(fingers, _pil_mask(
            shape, lambda d, x0=x0, y0=y0, x1=x1, y1=y1, fw=fw: d.line(
                [(x0, y0), (x1, y1)], fill=255, width=int(fw))))
        fingers = np.maximum(fingers, _ellipse_mask(
            shape, x1, y1, fw * 0.52, fw * 0.52, feather=1.4))
    hand = np.maximum.reduce([palm, wrist, fingers])
    hand = A.blur(hand, 2.0, periodic=False)
    hand = A.smoothstep(hand / 0.70)
    # 手指擦痕：指尖方向的水汽被抹开（更清楚）
    streaks = np.zeros(shape, np.float32)
    for (x0, y0, x1, y1, fw) in finger_defs[:4]:
        streaks = np.maximum(streaks, _pil_mask(
            shape, lambda d, x0=x0, y0=y0, x1=x1, y1=y1, fw=fw: d.line(
                [(x0, y0), (x1, y1)], fill=255, width=max(2, int(fw * 0.30)))))
    # 掌心擦痕（手掌按上去时中心更亮/更清楚）
    streaks = np.maximum(streaks, _ellipse_mask(shape, cx, cy,
                                                W * 0.08, H * 0.09, feather=4.0))
    streaks = A.blur(streaks, 2.5, periodic=False)
    # 水汽浓度：中心薄、边缘厚，带细颗粒
    fog = A.fbm(shape, 5, 4, r)
    fine = A.pnoise(shape, (300, 300), r)
    alpha = hand * (0.20 + 0.32 * fog + 0.10 * fine)
    alpha = np.maximum(alpha, streaks * hand * 0.42)
    alpha *= 0.95
    # 向下流的水痕
    drips = np.zeros(shape, np.float32)
    for _ in range(18):
        x0 = r.uniform(cx - W * 0.20, cx + W * 0.20)
        y0 = r.uniform(cy + H * 0.12, cy + H * 0.22)
        L = r.uniform(H * 0.04, H * 0.16)
        wdt = r.uniform(W * 0.004, W * 0.011)
        yrel = np.clip((np.arange(H)[:, None] - y0) / L, 0, 1)
        d = np.exp(-((np.arange(W)[None, :] - x0) / wdt) ** 2) * \
            (1 - yrel) * (yrel > 0)
        drips = np.maximum(drips, d.astype(np.float32))
    alpha = np.clip(alpha + drips * 0.20, 0, 0.92)
    # 散落小水珠
    drops = A.blobs(shape, [(r.uniform(0, H), r.uniform(0, W),
                             r.uniform(1.0, 3.2), r.uniform(0.25, 0.55))
                            for _ in range(46)], feather=1.2)
    alpha = np.clip(alpha + drops * 0.28, 0, 0.95)
    # 手印边缘：污手印更灰更脏
    rim = np.clip(A.blur(hand, 5.0, periodic=False) - hand, 0, 1)
    col = A.mix(A.hexc("#dfe5e0")[None, None], A.hexc("#b7c1ba")[None, None],
                fog[..., None])
    col = A.mix(col, A.hexc("#8d988f")[None, None], (1 - hand)[..., None] * 0.28)
    col = A.mix(col, A.hexc("#a8b2aa")[None, None], rim[..., None] * 0.6)
    rgba = np.dstack([np.broadcast_to(col, (H, W, 3)).astype(np.float32), alpha])
    return _down(rgba, w, h)


# ================================================================ 清单 / manifest / 自检

from PIL import ImageFilter  # noqa: E402,F401  （notice_board 阴影用，已在上方导入）

SPECS = [
    dict(key="MAT_photo_family_1", file="photo_family_1.jpg", w=256, h=256,
         fn=build_photo_family_1, tint="#fff6e8", transparent=False,
         desc="家庭合影（父母+孩子，室内，褪色，人脸模糊）"),
    dict(key="MAT_photo_family_2", file="photo_family_2.jpg", w=128, h=256,
         fn=build_photo_family_2, tint="#f6eedd", transparent=False,
         desc="母亲与孩子旧照（竖幅，黑白偏棕）"),
    dict(key="MAT_photo_family_3", file="photo_family_3.jpg", w=256, h=256,
         fn=build_photo_family_3, tint="#fff2e0", transparent=False,
         desc="年轻时的合影/结婚照（褪色，红花）"),
    dict(key="MAT_child_drawing", file="child_drawing.jpg", w=256, h=256,
         fn=build_child_drawing, tint="#f6f0e0", transparent=False,
         desc="孩子蜡笔画：房子与三个人，纸边卷曲"),
    dict(key="MAT_calendar", file="calendar_1999.jpg", w=128, h=256,
         fn=build_calendar, tint="#f4ecd6", transparent=False,
         desc="1999 年 3 月挂历，12 日红圈 + 手写“早点回家”"),
    dict(key="MAT_notice_board", file="notice_board.jpg", w=512, h=256,
         fn=build_notice_board, tint="#ffffff", transparent=False,
         desc="小区通知板：停水/水费/居委会/停电通知拼贴"),
    dict(key="MAT_couplet", file="couplet.jpg", w=128, h=512,
         fn=build_couplet, tint="#f2e0d4", transparent=False,
         desc="褪色红纸对联（金字竖排“天增岁月人增寿”）"),
    dict(key="MAT_bath_poster", file="bath_poster.jpg", w=256, h=512,
         fn=build_bath_poster, tint="#f6ecd6", transparent=False,
         desc="九十年代澡堂安全须知宣传画"),
    dict(key="MAT_bath_notice", file="bath_notice.jpg", w=512, h=256,
         fn=build_bath_notice, tint="#ffffff", transparent=False,
         desc="澡堂票价/营业时间牌（珐琅，红笔改价）"),
    dict(key="MAT_bath_ticket", file="bath_ticket.jpg", w=256, h=128,
         fn=build_bath_ticket, tint="#f8f4e8", transparent=False,
         desc="旧澡票（贰元，红章，存根）"),
    dict(key="MAT_mirror_crack", file="mirror_crack.png", w=512, h=512,
         fn=build_mirror_crack, tint="#ffffff", transparent=True,
         desc="镜面裂纹（RGBA 透明叠加）"),
    dict(key="MAT_handprint", file="handprint.png", w=256, h=256,
         fn=build_handprint, tint="#ffffff", transparent=True,
         desc="水汽手印（RGBA 透明叠加）"),
]

MANIFEST_ENTRY_KEYS = ("file", "colorSpace", "tint", "emissive")
LEGACY_KEYS = [
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
]


def build_one(spec):
    arr = spec["fn"](spec["w"], spec["h"])
    path = A.TEX_DIR / spec["file"]
    if spec["transparent"]:
        if arr.shape[2] != 4:
            raise SystemExit(f"{spec['key']}: 期望 RGBA，得到 {arr.shape}")
        A.save_png(arr[..., :3], path, alpha=arr[..., 3])
    else:
        if arr.shape[0] != spec["h"] or arr.shape[1] != spec["w"]:
            raise SystemExit(f"{spec['key']}: 尺寸 {arr.shape[1]}x{arr.shape[0]} "
                             f"!= {spec['w']}x{spec['h']}")
        A.save_jpg(arr, path, quality=88)
    return path.stat().st_size


def update_manifest():
    path = A.TEX_DIR / "manifest.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    mats = data["materials"]
    for spec in SPECS:
        entry = {
            "file": spec["file"],
            "colorSpace": "srgb",
            "tint": spec["tint"],
            "emissive": None,
        }
        if spec["transparent"]:
            entry["transparent"] = True
        mats[spec["key"]] = entry
    A.write_json(path, data)
    return len(mats)


def build_verify(new_sizes):
    lines = []
    ok = True
    man = json.loads((A.TEX_DIR / "manifest.json").read_text(encoding="utf-8"))
    mats = man["materials"]
    lines.append("《三更》v1.0.2 叙事贴图自检报告（v1.0.2-verify.txt）")
    lines.append("=" * 78)
    lines.append(f"生成脚本: tools/art/build_v102_textures.py（固定 seed {A.SEED}，"
                 f"numpy {np.__version__}, Pillow {Image.__version__}）")
    lines.append(f"新增材质: {len(SPECS)} 个；预算 ≤ 500 KB；"
                 f"现有 legacy 材质保留 {len(LEGACY_KEYS)} 条")
    lines.append("")
    lines.append(f"{'KEY':<22}{'FILE':<22}{'SIZE':>10}{'BYTES':>9}  "
                 f"{'FORMAT':<7}{'MANIFEST':>9}  STATUS")
    total = 0
    missing_manifest = []
    for spec in SPECS:
        key = spec["key"]
        f = A.TEX_DIR / spec["file"]
        problems = []
        if not f.exists():
            problems.append("文件缺失")
            size = 0
            fmt = "--"
        else:
            size = f.stat().st_size
            total += size
            with Image.open(f) as im:
                w, h = im.size
                mode = im.mode
            if (w, h) != (spec["w"], spec["h"]):
                problems.append(f"尺寸{w}x{h}")
            if spec["transparent"]:
                fmt = "PNG-a"
                if mode != "RGBA":
                    problems.append(f"模式{mode}")
            else:
                fmt = "JPEG"
                if mode != "RGB":
                    problems.append(f"模式{mode}")
        entry = mats.get(key)
        if entry is None:
            missing_manifest.append(key)
            problems.append("manifest 缺失")
            man_ok = "NO"
        else:
            man_ok = "OK"
            if entry.get("file") != spec["file"]:
                problems.append("manifest 文件名不一致")
            if bool(entry.get("transparent")) != spec["transparent"]:
                problems.append("transparent 不一致")
        status = "OK" if not problems else "FAIL: " + ", ".join(problems)
        if problems:
            ok = False
        lines.append(f"{key:<22}{spec['file']:<22}{f'{size/1024:8.1f}KB':>10}"
                     f"{size:>9}  {fmt:<7}{man_ok:>9}  {status}")
    lines.append("")
    lines.append("---- 预算 ----")
    lines.append(f"新增总字节: {total} ({total/1024:.1f} KB) / 上限 {NEW_BUDGET/1024:.0f} KB")
    if total > NEW_BUDGET:
        lines.append("[FAIL] 新增素材超过 500KB")
        ok = False
    else:
        lines.append("[OK] 新增素材在 500KB 以内")
    lines.append("")
    lines.append("---- legacy 材质保留 ----")
    missing_legacy = [k for k in LEGACY_KEYS if k not in mats]
    if missing_legacy:
        lines.append("[FAIL] 丢失旧键名: " + ", ".join(missing_legacy))
        ok = False
    else:
        lines.append(f"[OK] 原有 {len(LEGACY_KEYS)} 个 MAT_* 键名全部保留（manifest 共 {len(mats)} 条）")
    lines.append("")
    lines.append("---- 文件唯一性 ----")
    files = [s["file"] for s in SPECS]
    if len(files) != len(set(files)):
        lines.append("[FAIL] 文件名重复")
        ok = False
    else:
        lines.append("[OK] 新增文件名无重复")
    legacy_files = {mats[k]["file"] for k in LEGACY_KEYS if k in mats}
    clash = [f for f in files if f in legacy_files]
    if clash:
        lines.append("[FAIL] 与旧文件名冲突: " + ", ".join(clash))
        ok = False
    else:
        lines.append("[OK] 与旧文件名无冲突")
    lines.append("")
    lines.append("=" * 78)
    lines.append("V102 VERIFY OK" if ok else "V102 VERIFY FAIL")
    report = A.REPORT_DIR / "v1.0.2-verify.txt"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return ok, "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()
    if args.list:
        for s in SPECS:
            print(f"{s['key']:<22}{s['w']}x{s['h']:<4}"
                  f"{'PNG' if s['transparent'] else 'JPEG':<5}{s['file']}")
        print(f"共 {len(SPECS)} 个新增材质")
        return
    only = [x.strip() for x in args.only.split(",") if x.strip()]
    specs = [s for s in SPECS if not only or s["key"] in only]
    unknown = [k for k in only if k not in {s["key"] for s in SPECS}]
    if unknown:
        raise SystemExit("未知键名: " + ", ".join(unknown))
    print(f"生成 {len(specs)} 张 v1.0.2 叙事贴图 -> {A.TEX_DIR}")
    new_sizes = {}
    import time
    for s in specs:
        t0 = time.time()
        size = build_one(s)
        new_sizes[s["key"]] = size
        print(f"  {s['key']:<22}{s['w']:>4}x{s['h']:<4}{size/1024:8.1f} KB  "
              f"{time.time()-t0:5.2f}s  {s['file']}")
    n = update_manifest()
    print(f"manifest.json 已追加：materials 共 {n} 条")
    if only:
        print("（--only 模式：跳过完整自检；请在全量生成后跑一次不带参数的脚本）")
        return
    ok, text = build_verify(new_sizes)
    print(text)
    print("V102 VERIFY OK" if ok else "V102 VERIFY FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
