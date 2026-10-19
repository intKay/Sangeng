"""《三更》海报与包装生成：poster-door / poster-mirror / poster-night、
hero.jpg、seal.png、favicon.png。

海报全部由 numpy + Pillow 程序化绘制，透视面用真实采样已生成的 MAT_* 贴图；
固定 seed，可重跑复现。海报上不写标题文字（标题由 HTML 叠加），只有画面与日期戳。
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np                                      # noqa: E402
from PIL import Image, ImageDraw, ImageFont             # noqa: E402

import artlib as A                                      # noqa: E402

PW, PH = 900, 1200


# ---------------------------------------------------------------- 基础工具

def _img(name):
    """读取贴图（RGB float0..1），带缓存。"""
    return A.load_tex(A.TEX_DIR / name)


def _img_rgba(name):
    im = Image.open(A.TEX_DIR / name).convert("RGBA")
    return np.asarray(im, np.float32) / 255.0


def _samp(name, u, v, wrap=True):
    return A.sample(_img(name), u, v, wrap=wrap)


def _samp_alpha(name, u, v):
    """采样 RGBA 贴图的 alpha（用重复 3 通道绕过 A.sample 的 RGB 假设）。"""
    rgba = _img_rgba(name)
    a3 = np.repeat(rgba[..., 3:4], 3, axis=2)
    return A.sample(a3, u, v, wrap=True)[..., 0]


def _grid(w, h):
    return np.mgrid[0:h, 0:w].astype(np.float32)


def _figure_mask(shape, cx, cy, height, kind="adult"):
    """站立人形蒙版（脚底在 cy，身高 height）。kind: adult / paper。"""
    h, w = shape
    im = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(im)
    if kind == "paper":
        head_r = height * 0.062
        head_cy = cy - height + head_r * 1.05
        hx = cx + height * 0.012
    else:
        head_r = height * 0.068
        head_cy = cy - height + head_r * 1.05
        hx = cx
    d.ellipse([hx - head_r, head_cy - head_r * 1.04,
               hx + head_r, head_cy + head_r * 1.04], fill=255)
    neck_top = head_cy + head_r * 0.8
    shoulder = neck_top + height * 0.055
    hip = cy - height * 0.46
    sw = height * (0.155 if kind == "paper" else 0.145)
    # 躯干
    d.polygon([(hx - head_r * 0.55, neck_top), (hx + head_r * 0.55, neck_top),
               (hx + sw, shoulder), (hx + sw * 0.85, hip),
               (hx - sw * 0.85, hip), (hx - sw, shoulder)], fill=255)
    # 手臂（自然下垂，略微外张）
    arm_w = height * 0.036
    for side in (-1, 1):
        ax = hx + side * sw * 0.95
        ay = shoulder + height * 0.01
        bx = hx + side * (sw * 1.12 if kind == "paper" else sw * 0.95)
        by = cy - height * 0.20
        d.line([(ax, ay), (bx, by)], fill=255, width=max(2, int(arm_w)))
        d.ellipse([bx - arm_w * 0.55, by - arm_w * 0.6,
                   bx + arm_w * 0.55, by + arm_w * 0.6], fill=255)
    # 腿
    leg_w = height * 0.052
    for side in (-1, 1):
        lx = hx + side * height * 0.045
        d.line([(lx, hip), (hx + side * height * 0.075, cy - height * 0.02)],
               fill=255, width=max(2, int(leg_w)))
        d.ellipse([hx + side * height * 0.075 - leg_w * 0.6, cy - height * 0.045,
                   hx + side * height * 0.075 + leg_w * 0.6, cy], fill=255)
    return np.asarray(im, np.float32) / 255.0


def _blur_mask(mask, sigma, periodic=False):
    return A.blur(mask, sigma, periodic=periodic)


def _over_screen(col, color, mask, strength=1.0):
    return A.over(col, np.asarray(color, np.float32), mask, strength)


def _grain_final(col, r, amount=0.04, chroma=0.3):
    return A.grain(np.clip(col, 0, 1), r, amount, chroma)


def _scanlines(col, strength=0.03):
    h = col.shape[0]
    scan = 1.0 - strength * ((np.arange(h) % 2) == 0)[:, None].astype(np.float32)
    return col * scan[..., None]


def _scratches(col, r, count=12, color="#d8d2c0", alpha=0.18):
    h, w = col.shape[:2]
    segs = [(r.uniform(0, w), r.uniform(0, h), r.uniform(0, w), r.uniform(0, h),
             r.uniform(0.5, 1.3)) for _ in range(count)]
    m = A.seg_mask((h, w), segs, feather=0.8)
    return A.over(col, A.hexc(color), m, alpha)


def _dust_specks(col, r, count=60, bright=0.10):
    h, w = col.shape[:2]
    specs = [(r.uniform(0, h), r.uniform(0, w), r.uniform(0.6, 2.2),
              r.uniform(0.3, 1.0)) for _ in range(count)]
    m = A.blobs((h, w), specs, feather=1.2)
    return A.over(col, A.hexc("#cfcbb8"), m, bright)


def _save(col, name, quality=90):
    A.save_jpg(np.clip(col, 0, 1), A.ART_DIR / name, quality=quality)
    print(f"  {name}  {col.shape[1]}x{col.shape[0]}  "
          f"{(A.ART_DIR / name).stat().st_size/1024:.0f} KB")


def _date_stamp(img: Image.Image, text: str, xy, size=21, color=(196, 122, 56)):
    """橙色日期戳（模拟一次性相机日期打印）。"""
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype(A.FONT_SONG, size)
    x, y = xy
    d.text((x + 1, y + 1), text, font=font, fill=(40, 24, 10))
    d.text((x, y), text, font=font, fill=color)
    return img


# ================================================================ 海报一：门后
def poster_door():
    W, H = PW, PH
    r = A.rng("poster_door")
    yy, xx = _grid(W, H)
    cx, cy = W * 0.50, H * 0.455
    f = 610.0
    ycam, halfw, ceilh, D = 1.55, 1.1, 2.7, 8.6
    u = xx - cx
    v = yy - cy

    # ---- 透视面参数
    d_floor = ycam * f / np.maximum(v, 1e-2)
    x_floor = u * d_floor / f
    m_floor = (v > 0) & (np.abs(x_floor) <= halfw) & (d_floor <= D)

    d_ceil = (ceilh - ycam) * f / np.maximum(-v, 1e-2)
    x_ceil = u * d_ceil / f
    m_ceil = (v < 0) & (np.abs(x_ceil) <= halfw) & (d_ceil <= D)

    d_r = halfw * f / np.maximum(u, 1e-2)
    y_r = ycam - v * d_r / f
    m_r = (u > 0) & (y_r >= 0) & (y_r <= ceilh) & (d_r <= D)

    d_l = halfw * f / np.maximum(-u, 1e-2)
    y_l = ycam - v * d_l / f
    m_l = (u < 0) & (y_l >= 0) & (y_l <= ceilh) & (d_l <= D)

    x_end = u * D / f
    y_end = ycam - v * D / f
    m_end = (np.abs(x_end) <= halfw) & (y_end >= 0) & (y_end <= ceilh)

    # ---- 材质采样
    floor_alb = _samp("tile_floor.jpg", x_floor / 2.0, d_floor / 2.0)
    ceil_alb = _samp("paint_ceiling.jpg", x_ceil / 2.0, d_ceil / 2.0)
    wall_alb = np.where(m_r[..., None],
                        _samp("wallpaper_old_dark.jpg", d_r / 2.0, y_r / 2.0),
                        _samp("wallpaper_old_dark.jpg", d_l / 2.0, y_l / 2.0))
    y_wall = np.where(m_r, y_r, y_l)
    d_wall = np.where(m_r, d_r, d_l)
    # 墙裙（1m 以下深绿漆）
    band = A.smoothstep((1.02 - y_wall) / 0.07)
    band_tex = _samp("concrete.jpg", d_wall / 2.0, y_wall / 2.0) * \
        np.array([0.42, 0.55, 0.46], np.float32)
    wall_alb = A.mix(wall_alb, band_tex, band * 0.85)
    # 墙裙分界线
    line = np.exp(-((y_wall - 1.04) / 0.012) ** 2)
    wall_alb = A.over(wall_alb, A.hexc("#20291f"), line, 0.6)
    # 墙面霉斑/水渍（贴花采样）
    mold_a = _samp_alpha("stain_mold.png", d_wall / 3.0, y_wall / 3.0)
    wall_alb = A.over(wall_alb, A.hexc("#26301f"), mold_a, 0.60)
    water_a = _samp_alpha("stain_water.png", d_wall / 2.3 + 0.3, y_wall / 2.3)
    wall_alb = A.over(wall_alb, A.hexc("#8b6f38"), water_a, 0.35)
    # 墙面竖向污痕
    grime = A.fbm((H, W), 0, 3, r, aniso=(40, 2))
    wall_alb *= (0.85 + 0.25 * grime)[..., None]

    # 侧门（走廊两边的住户门）
    door_defs = [("R", 4.6), ("L", 3.2), ("L", 6.5), ("R", 7.7)]
    for side, dc in door_defs:
        on = m_r if side == "R" else m_l
        dw = d_r if side == "R" else d_l
        yw = y_r if side == "R" else y_l
        in_door = on & (np.abs(dw - dc) <= 0.46) & (yw <= 2.06)
        door_uv_u = (dw - dc + 0.46) / 0.92
        door_uv_v = yw / 2.06
        door_alb = _samp("wood_door.jpg", door_uv_u, door_uv_v)
        # 门框
        frame = in_door & ((np.abs(dw - dc) > 0.40) | (yw > 1.98))
        wall_alb = np.where(in_door[..., None], door_alb, wall_alb)
        wall_alb = A.over(wall_alb, A.hexc("#33291f"), frame, 0.5)
        # 门牌（小亮点）
        plate = in_door & (yw > 1.38) & (yw < 1.62) & \
            (np.abs(dw - dc) < 0.09)
        wall_alb = A.over(wall_alb, A.hexc("#b7b09b"), plate, 0.8)

    # 尽头墙 + 门
    end_alb = _samp("wallpaper_old_dark.jpg", x_end / 2.0, y_end / 2.0)
    in_end_door = m_end & (np.abs(x_end) <= 0.45) & (y_end <= 2.05)
    end_door_alb = _samp("wood_door.jpg", x_end / 0.90 + 0.5, y_end / 2.05)
    end_frame = (m_end & (np.abs(x_end) <= 0.54) &
                 (((np.abs(x_end) - 0.45) ** 2 < 0.004) |
                  ((y_end > 2.05) & (y_end < 2.14))))
    end_alb = np.where(in_end_door[..., None], end_door_alb, end_alb)
    end_alb = A.over(end_alb, A.hexc("#2e2419"), end_frame, 0.6)
    # 门板压线
    panel = in_end_door & ((np.abs(x_end) - 0.33) ** 2 < 0.0015) | \
        (in_end_door & (np.abs(y_end - 1.15) < 0.02))
    end_alb = A.over(end_alb, A.hexc("#3d2a1f"), panel, 0.35)

    # ---- 合成 albedo
    alb = np.where(m_end[..., None], end_alb,
                   np.where(m_ceil[..., None], ceil_alb,
                            np.where((m_r | m_l)[..., None], wall_alb,
                                     floor_alb)))
    alb = np.where(m_ceil[..., None], alb * 0.80, alb)
    # 地面拼缝磨损（砖块网格线）
    floor_line = np.minimum((d_floor / 2.0) % 1.0, 1 - (d_floor / 2.0) % 1.0)
    floor_line = np.minimum(floor_line, np.minimum(
        (x_floor / 2.0 + 0.5) % 1.0, 1 - (x_floor / 2.0 + 0.5) % 1.0))
    alb *= (1.0 - 0.18 * A.smoothstep((0.02 - floor_line) / 0.02))[..., None]

    # ---- 世界坐标（用于光照）
    px = np.where(m_end, x_end,
                  np.where(m_r, halfw,
                           np.where(m_l, -halfw,
                                    np.where(m_ceil, x_ceil, x_floor))))
    py = np.where(m_end, y_end,
                  np.where(m_r, y_r,
                           np.where(m_l, y_l,
                                    np.where(m_ceil, ceilh, 0.0))))
    pd = np.where(m_end, D,
                  np.where(m_r, d_r,
                           np.where(m_l, d_l,
                                    np.where(m_ceil, d_ceil, d_floor))))

    # ---- 光照
    # 灯光是乘在 albedo 上的（否则会被均匀光洗掉材质细节）
    light = np.zeros((H, W, 3), np.float32)
    light += np.array([0.082, 0.100, 0.090], np.float32)[None, None]
    tube_col = np.array([0.74, 0.98, 0.84], np.float32)
    for ld, inten in ((1.9, 1.0), (4.3, 0.92), (6.7, 0.80)):
        dist2 = px * px + (py - 2.52) ** 2 + (pd - ld) ** 2
        light += tube_col[None, None] * (inten * 0.92 / (1.0 + dist2 * 0.36))[..., None]
    # 门后暖光
    dist2w = px * px + (py - 0.95) ** 2 + (pd - (D - 0.08)) ** 2
    warm = 0.70 / (1.0 + dist2w * 1.40)
    light += np.array([1.0, 0.55, 0.26], np.float32)[None, None] * warm[..., None]
    # 远处一点点冷色反射
    light += np.array([0.05, 0.06, 0.065], np.float32)[None, None] * \
        np.exp(-((pd - D) / 2.5) ** 2)[..., None]
    col = alb * light

    # ---- 雾
    fog = np.clip(1.0 - np.exp(-(pd / 12.0) ** 2), 0, 0.88) * 0.82
    fog_col = np.array([0.036, 0.046, 0.042], np.float32)
    col = col * (1 - fog[..., None]) + fog_col[None, None] * fog[..., None]

    # ---- 门缝透光（屏幕空间）
    hw_px = 0.45 * f / D
    y_bot = cy + ycam * f / D
    y_top = cy - (2.05 - ycam) * f / D
    dx = np.maximum(np.maximum(cx - hw_px - xx, xx - (cx + hw_px)), 0)
    dy = np.maximum(np.maximum(y_top - yy, yy - y_bot), 0)
    edge = np.sqrt(dx * dx + dy * dy)
    warm_col = np.array([1.0, 0.64, 0.32], np.float32)
    glow = np.exp(-(edge / 3.0) ** 2) * 0.62 + np.exp(-(edge / 26.0) ** 2) * 0.20
    col += glow[..., None] * warm_col[None, None]
    slit = np.exp(-((xx - cx) / (hw_px * 1.05)) ** 8) * \
        np.exp(-((yy - y_bot) / 2.4) ** 2)
    col += slit[..., None] * warm_col[None, None] * 0.55
    halo = np.exp(-(edge / 95.0) ** 2) * 0.14
    col += halo[..., None] * warm_col[None, None]

    # ---- 顶灯（天花上的日光灯盒，光晕）
    for ld, inten in ((1.9, 1.0), (4.3, 0.8), (6.7, 0.6)):
        sy = cy - (2.58 - ycam) * f / ld
        sx = cx
        d2 = (xx - sx) ** 2 + (yy - sy) ** 2
        g = inten * np.exp(-d2 / (2 * (10.0 ** 2))) * 0.45
        col += g[..., None] * np.array([0.80, 0.97, 0.88], np.float32)[None, None]
        bar = inten * np.exp(-((yy - sy) / 1.6) ** 2) * \
            np.exp(-((xx - sx) / (22.0 * inten + 6)) ** 2) * 0.65
        col += bar[..., None] * np.array([0.88, 1.0, 0.94], np.float32)[None, None]

    # ---- 尘埃/光点
    col = _dust_specks(col, r, 90, 0.10)

    # ---- 调色与后处理
    col = A.desaturate(col, 0.24)
    col *= np.array([1.03, 0.97, 0.99], np.float32)[None, None]
    col = np.clip(col, 0, 1)
    col = _grain_final(col, r, 0.042, 0.32)
    col = _scanlines(col, 0.025)
    col = _scratches(col, r, 14, "#c9c4b0", 0.16)
    col = col * A.vignette_mask((H, W), 0.62, 1.6)[..., None]
    col = np.clip(col, 0, 1)
    img = A.to_img(col)
    img = _date_stamp(img, "98 03 12", (W - 186, H - 64), 20, (198, 124, 58))
    img.save(A.ART_DIR / "poster-door.jpg", "JPEG", quality=90, optimize=True)
    print(f"  poster-door.jpg  900x1200  "
          f"{(A.ART_DIR / 'poster-door.jpg').stat().st_size/1024:.0f} KB")
    return img


# ================================================================ 海报二：镜中
def poster_mirror():
    W, H = PW, PH
    r = A.rng("poster_mirror")
    yy, xx = _grid(W, H)

    # ---- 背景：绿瓷砖 + 上部白灰墙
    tile_alb = _samp("tile_green.jpg", xx / W * 3.2, yy / H * 4.2)
    plaster_alb = _samp("plaster.jpg", xx / W * 2.2, yy / H * 2.0)
    edge = 0.155 * H + 5.0 * A.fbm((H, W), 8, 3, r)
    top_mask = A.smoothstep((edge - yy) / 6.0)
    col = A.mix(tile_alb, plaster_alb, top_mask)
    # 瓷砖顶部的压条
    trim = np.exp(-((yy - edge) / (H * 0.006)) ** 2)
    col = A.over(col, A.hexc("#4a5748"), trim, 0.75)
    # 墙面光照（顶部两支日光灯）
    wall_light = 0.42 + 0.34 * np.exp(-((yy - 0.03 * H) / (0.30 * H)) ** 2) + \
        0.18 * np.exp(-((xx - 0.24 * W) / (0.25 * W)) ** 2
                      - ((yy - 0.05 * H) / (0.20 * H)) ** 2) + \
        0.16 * np.exp(-((xx - 0.74 * W) / (0.22 * W)) ** 2
                      - ((yy - 0.04 * H) / (0.18 * H)) ** 2)
    col *= wall_light[..., None]
    # 墙面污渍/霉
    mold_a = _samp_alpha("stain_mold.png", xx / W * 2.0 + 0.2, yy / H * 2.2)
    col = A.over(col, A.hexc("#26301f"), mold_a, 0.55)
    water_a = _samp_alpha("stain_water.png", xx / W * 1.7, yy / H * 2.4)
    col = A.over(col, A.hexc("#8b6f38"), water_a, 0.30)
    # 底部更脏
    bottom_grime = A.smoothstep((yy - 0.78 * H) / (0.22 * H))
    col *= (1.0 - 0.35 * bottom_grime)[..., None]

    # ---- 镜框
    mx0, mx1 = int(W * 0.075), int(W * 0.925)
    my0, my1 = int(H * 0.215), int(H * 0.505)
    frame_w = 13
    # 镜框外投影
    d_out = A.border_dist((H, W), mx0, my0)
    # 用矩形距离场：内部为正
    ddx = np.minimum(xx - mx0, mx1 - xx)
    ddy = np.minimum(yy - my0, my1 - yy)
    drect = np.minimum(ddx, ddy)
    shadow = np.exp(-((drect + 16) / 16.0) ** 2) * (drect < 0) * 0.55
    col *= (1.0 - shadow)[..., None]
    # 镜框（深绿灰金属/木）
    frame_mask = (drect >= 0) & (drect <= frame_w)
    frame_alb = 0.5 + 0.5 * A.fbm((H, W), 4, 4, r)
    frame_col = np.array([0.19, 0.22, 0.19], np.float32)[None, None] * \
        (0.8 + 0.5 * frame_alb[..., None])
    col = np.where(frame_mask[..., None], frame_col, col)
    # 框的内外亮边
    frame_hi = np.exp(-((drect - frame_w) / 2.0) ** 2) * (drect < frame_w + 3)
    col += frame_hi[..., None] * np.array([0.10, 0.12, 0.10], np.float32)

    # ---- 镜面
    mir_mask = (xx > mx0 + frame_w) & (xx < mx1 - frame_w) & \
               (yy > my0 + frame_w) & (yy < my1 - frame_w)
    mir_w = mx1 - mx0 - 2 * frame_w
    mir_h = my1 - my0 - 2 * frame_w
    mu = (xx - (mx0 + frame_w)) / mir_w
    mv = (yy - (my0 + frame_w)) / mir_h
    # 反射的瓷砖（略暗、偏青）
    refl = _samp("tile_green.jpg", mu * 1.15, mv * 1.05)
    refl = A.mix(refl, A.hexc("#3a5550"), 0.45)
    refl *= 0.86
    # 反射的日光灯（顶部亮带）
    refl += (0.55 * np.exp(-((mv - 0.10) / 0.045) ** 2) *
             (0.55 + 0.45 * np.exp(-((mu - 0.33) / 0.16) ** 2))
             )[..., None] * np.array([0.75, 0.95, 0.86], np.float32)
    refl += (0.35 * np.exp(-((mv - 0.06) / 0.03) ** 2) *
             np.exp(-((mu - 0.72) / 0.14) ** 2))[..., None] * \
        np.array([0.6, 0.8, 0.72], np.float32)
    # 反射里更衣柜的暗块（下方）
    for i in range(6):
        x0 = 0.06 + i * 0.15
        locker = A.smoothstep((mu - x0) / 0.006) * \
            A.smoothstep((x0 + 0.13 - mu) / 0.006) * \
            A.smoothstep((mv - 0.55) / 0.02)
        refl = A.over(refl, A.hexc("#2b3a36"), locker, 0.55)
        refl = A.over(refl, A.hexc("#1d2825"),
                      locker * np.exp(-((mu - (x0 + 0.065)) / 0.005) ** 2), 0.5)
    # 反射的地面
    floor_ref = A.smoothstep((mv - 0.86) / 0.03)
    refl = A.over(refl, A.hexc("#3c4a42"), floor_ref, 0.4)
    # 镜中模糊人形
    fig = _figure_mask((H, W), W * 0.0 + (mx0 + frame_w) + mir_w * 0.56,
                       my0 + frame_w + mir_h * 0.97, mir_h * 0.72, kind="adult")
    fig = _blur_mask(fig, 7.0)
    fig *= (0.68 + 0.32 * A.fbm((H, W), 5, 3, r))
    refl = A.over(refl, A.hexc("#cfd2c4"), fig, 0.62)
    # 人形边缘模糊/冷光
    fig_edge = np.clip(A.blur(fig, 12.0) - fig, 0, 1)
    refl = A.over(refl, A.hexc("#8ea7a0"), fig_edge, 0.30)
    # 镜面水汽/污渍
    mg = _img_rgba("mirror_grime.png")
    mg_rgb = A.sample(mg[..., :3], mu, mv)
    mg_a = A.sample(np.repeat(mg[..., 3:4], 3, axis=2), mu, mv)[..., 0]
    refl = A.mix(refl, mg_rgb, np.clip(mg_a, 0, 1))
    # 镜面整体反光条
    glare = 0.16 * np.exp(-((mu + mv * 0.7 - 0.55) / 0.22) ** 2)
    refl += glare[..., None] * np.array([0.8, 0.9, 0.82], np.float32)
    col = np.where(mir_mask[..., None], refl, col)
    # 镜面底部冷凝水珠
    for _ in range(26):
        bx = r.uniform(mx0 + frame_w, mx1 - frame_w)
        by = r.uniform(my1 - frame_w - 20, my1 - frame_w)
        rad = r.uniform(1.2, 3.0)
        d2 = (xx - bx) ** 2 + (yy - by) ** 2
        drop = np.exp(-d2 / (rad * rad))
        col += (drop * 0.25)[..., None] * np.array([0.8, 0.9, 0.85], np.float32)

    # ---- 镜台与水盆
    counter_y = 0.585 * H
    counter_shadow = np.exp(-((yy - counter_y) / 18.0) ** 2)
    col *= (1.0 - 0.5 * counter_shadow * (yy > counter_y))[..., None]
    basin = A.smoothstep((yy - counter_y - 8) / 30.0) * \
        A.smoothstep((0.93 * H - yy) / 30.0)
    basin_col = A.hexc("#5f6a5f")
    for bx in (0.28, 0.50, 0.72):
        bxc = bx * W
        d2 = ((xx - bxc) / (0.10 * W)) ** 2 + ((yy - (counter_y + 52)) / 34.0) ** 2
        bowl = np.exp(-d2)
        col = A.over(col, basin_col, bowl * basin, 0.55)
        col = A.over(col, A.hexc("#2f3a34"), np.exp(-((d2 - 0.72) / 0.10) ** 2) * basin, 0.4)
        # 水龙头
        fau = np.exp(-(((xx - bxc) / 5.0) ** 2 + ((yy - (counter_y + 12)) / 22.0) ** 2))
        col = A.over(col, A.hexc("#8b8f7e"), fau * basin, 0.7)

    # ---- 前景红毛巾（搭在洗手台边缘/挂钩上，垂下来）
    towel_mask = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(towel_mask)
    # 上缘被台面压住，往下垂，下缘被水汽打湿呈波浪
    top_y = H * 0.665
    left, right = W * 0.035, W * 0.30
    pts = [(left, top_y), (right, top_y + H * 0.010)]
    for k in range(9):
        t = 1.0 - k / 8.0
        x = left + (right - left) * t
        y = H * 1.02 - (H * 0.035) * math.sin(t * math.pi * 2.2 + 0.6) - H * 0.01 * k
        pts.append((x, y))
    d.polygon(pts, fill=255)
    tm = np.asarray(towel_mask, np.float32) / 255.0
    tm = A.blur(tm, 3.0)
    # 毛巾自身的布纹 + 垂褶阴影
    towel_alb = _samp("fabric_red.jpg", xx / W * 1.1 + 0.2, yy / H * 1.3)
    fold_phase = 2 * np.pi * (xx / W * 5.0 + 0.22 * A.fbm((H, W), 3, 3, r))
    folds = (0.5 + 0.5 * np.cos(fold_phase)) ** 1.7
    vertical = 0.42 + 0.58 * np.clip((yy - top_y) / (0.32 * H), 0, 1)
    towel_col = towel_alb * (0.40 + 0.95 * folds)[..., None] * vertical[..., None]
    # 布褶的细阴影
    crease = A.smoothstep((A.fbm((H, W), 0, 4, r, aniso=(40, 3)) - 0.58) / 0.2)
    towel_col *= (1.0 - 0.28 * crease)[..., None]
    # 顶部被台面压住的暗边 + 底边湿暗
    edge_shadow = np.exp(-((yy - top_y) / (H * 0.010)) ** 2) * (tm > 0.2)
    towel_col *= (1.0 - 0.55 * edge_shadow)[..., None]
    wet_hem = A.smoothstep((yy - (H * 0.90)) / (H * 0.08))
    towel_col *= (1.0 - 0.30 * wet_hem)[..., None]
    # 布边略暗
    rim = np.clip(A.blur(tm, 5.0) - tm, 0, 1)
    towel_col *= (1.0 - 0.45 * rim)[..., None]
    towel_col = towel_col * (0.60 + 0.50 * wall_light[..., None]) * 1.15
    # 右侧浴池暖光落在布上
    towel_col += (0.18 * np.exp(-((xx - 0.85 * W) / (0.45 * W)) ** 2))[..., None] * \
        np.array([0.9, 0.55, 0.32], np.float32)
    col = A.mix(col, towel_col, tm * 0.95)
    # 台面压住处的高光
    top_hi = np.exp(-((yy - top_y) / (H * 0.006)) ** 2) * tm
    col += (top_hi * 0.12)[..., None] * np.array([0.9, 0.78, 0.66], np.float32)
    # 毛巾下的阴影
    sh = np.clip(A.blur(tm, 16.0) - tm, 0, 1)
    col *= (1.0 - 0.5 * sh)[..., None]

    # ---- 水汽
    steam_rgba = _img_rgba("steam.png")
    su = xx / W * 1.6 - 0.2
    sv = yy / H * 1.9 - 0.6
    steam_rgb = A.sample(steam_rgba[..., :3], su, sv)
    steam_a = A.sample(np.repeat(steam_rgba[..., 3:4], 3, axis=2), su, sv)[..., 0]
    steam_a *= A.smoothstep((yy - 0.46 * H) / (0.4 * H)) * 0.50
    col = A.mix(col, np.clip(steam_rgb * 0.95, 0, 1), np.clip(steam_a, 0, 1))

    # ---- 门缝暖光（画面右侧，浴池方向）
    warm = np.exp(-((xx - 1.02 * W) / (0.18 * W)) ** 2) * \
        A.smoothstep((yy - 0.25 * H) / (0.5 * H))
    col += warm[..., None] * np.array([0.50, 0.28, 0.12], np.float32)

    # ---- 调色/后处理
    col = A.desaturate(col, 0.18)
    col = np.clip(col, 0, 1)
    col = _grain_final(col, r, 0.045, 0.35)
    col = _scanlines(col, 0.02)
    col = _scratches(col, r, 10, "#c9c4b0", 0.14)
    col = col * A.vignette_mask((H, W), 0.60, 1.6)[..., None]
    col = np.clip(col, 0, 1)
    img = A.to_img(col)
    img = _date_stamp(img, "98 07 04", (W - 186, H - 64), 20, (198, 124, 58))
    img.save(A.ART_DIR / "poster-mirror.jpg", "JPEG", quality=90, optimize=True)
    print(f"  poster-mirror.jpg  900x1200  "
          f"{(A.ART_DIR / 'poster-mirror.jpg').stat().st_size/1024:.0f} KB")
    return img


# ================================================================ 海报三：夜路
def poster_night():
    W, H = PW, PH
    r = A.rng("poster_night")
    yy, xx = _grid(W, H)
    horizon = 0.525 * H
    f = 640.0
    ycam = 1.55

    # ---- 天空
    col = A.gradient_v(H, W, [0.0, 0.35, 0.52, 0.70, 1.0],
                       [A.hexc("#04080f"), A.hexc("#08131c"),
                        A.hexc("#14222c"), A.hexc("#1b2a34"),
                        A.hexc("#24343a")])
    # 月亮
    moon_x, moon_y, moon_r = 0.72 * W, 0.175 * H, 34.0
    dm = np.sqrt((xx - moon_x) ** 2 + (yy - moon_y) ** 2)
    col += np.exp(-(dm / (moon_r * 7.0)) ** 2)[..., None] * \
        np.array([0.11, 0.14, 0.16], np.float32)
    col += np.exp(-(dm / (moon_r * 2.4)) ** 2)[..., None] * \
        np.array([0.16, 0.20, 0.22], np.float32)
    col += A.smoothstep((moon_r * 1.02 - dm) / 2.0)[..., None] * \
        np.array([0.66, 0.72, 0.73], np.float32)
    # 月面：石纹理 + 一侧阴影
    moon_tex = _samp("stone.jpg", (xx - moon_x) / (moon_r * 6) + 0.5,
                     (yy - moon_y) / (moon_r * 6) + 0.5)
    moon_mask = A.smoothstep((moon_r * 1.02 - dm) / 2.0)
    col = A.over(col, moon_tex * 0.85, moon_mask, 0.55)
    shade_side = A.smoothstep(((xx - moon_x) / moon_r * 0.55 + 0.35)
                              / 0.6) * moon_mask
    col = A.over(col, A.hexc("#5d6668"), shade_side * 0.55, 0.5)
    # 地平线附近的雾气亮带
    col += (0.10 * np.exp(-((yy - horizon) / (0.06 * H)) ** 2))[..., None] * \
        np.array([0.45, 0.55, 0.60], np.float32)
    # 云
    cloud = A.fbm((H, W), 0, 4, r, aniso=(5, 16))
    cloud_mask = A.smoothstep((cloud - 0.48) / 0.18) * \
        (yy < horizon + 20) * (yy > 0.06 * H)
    col = A.mix(col, np.array([0.075, 0.105, 0.13], np.float32)[None, None],
                cloud_mask * 0.55)
    # 星
    stars = A.blobs((H, W), [(r.uniform(0, 0.44 * H), r.uniform(0, W),
                              r.uniform(0.8, 2.2), r.uniform(0.35, 1.0))
                             for _ in range(64)], feather=1.0)
    col += stars[..., None] * np.array([0.62, 0.70, 0.70], np.float32) * 0.75

    # ---- 远景：树线、村子灯光
    tree_line = horizon + 6.0 * A.fbm((H, W), 3, 4, r, aniso=(2, 18))
    tree_mask = ((yy >= tree_line) & (yy < horizon + 60) &
                 (A.smoothstep((A.fbm((H, W), 2, 4, r, aniso=(2, 14)) - 0.35)
                               / 0.2) > 0.5))
    col = A.mix(col, np.array([0.030, 0.045, 0.048], np.float32)[None, None],
                tree_mask * 0.92)
    for lx, ly, li in ((0.14, 0.545, 1.0), (0.19, 0.552, 0.7), (0.27, 0.560, 0.8),
                       (0.62, 0.548, 0.6), (0.83, 0.556, 0.9)):
        d2 = (xx - lx * W) ** 2 + (yy - ly * H) ** 2
        g = np.exp(-d2 / (2 * 4.0 ** 2)) * li
        col += g[..., None] * np.array([1.0, 0.62, 0.28], np.float32) * 0.9
        col += (np.exp(-d2 / (2 * 16.0 ** 2)) * li * 0.18)[..., None] * \
            np.array([1.0, 0.55, 0.25], np.float32)

    # ---- 土路透视
    cx = W * 0.50
    u = xx - cx
    v = yy - horizon
    d_road = ycam * f / np.maximum(v, 1e-2)
    x_road = u * d_road / f
    curve = 0.9 * np.sin(d_road / 22.0)
    xr = x_road - curve
    road_mask = (v > 0) & (np.abs(xr) <= 1.65) & (d_road <= 140)
    edge_mask = (v > 0) & (np.abs(xr) > 1.65) & (np.abs(xr) <= 2.4) & (d_road <= 140)
    grass_mask = (v > 0) & (np.abs(xr) > 2.4) & (d_road <= 140)

    road_alb = _samp("soil.jpg", (xr + 1.65) / 2.0, d_road / 2.0)
    edge_alb = _samp("soil.jpg", xr / 2.0 + 0.1, d_road / 2.3) * 0.75
    grass_alb = _samp("grass.jpg", (xr - 2.4) / 2.0, d_road / 2.4) * 0.85
    # 路面上的车辙压暗
    rut = np.exp(-((np.abs(xr) - 0.55) / 0.22) ** 2)
    road_alb *= (1.0 - 0.25 * rut)[..., None]

    alb = np.where(road_mask[..., None], road_alb,
                   np.where(edge_mask[..., None], edge_alb,
                            np.where(grass_mask[..., None], grass_alb, col)))

    # ---- 地面光照（月光 + 灯笼暖光）
    ground = (v > 0)
    light = 0.44 + 0.12 * np.exp(-((x_road) / 3.0) ** 2)
    # 灯笼位置与光晕
    lantern_d = 28.0
    lantern_x = curve_l = 0.9 * math.sin(lantern_d / 22.0) + 1.85
    ldist2 = (x_road - lantern_x) ** 2 + (d_road - lantern_d) ** 2
    light = light + 3.2 / (1.0 + ldist2 * 0.55)
    alb *= light[..., None]
    # 雾气：越远越蓝白，地面雾更重
    fog = 1.0 - np.exp(-(d_road / 17.0) ** 1.6)
    fog = np.clip(fog, 0, 0.96)
    fog_col = np.array([0.135, 0.175, 0.195], np.float32)
    ground_col = alb * (1 - fog[..., None]) + fog_col[None, None] * fog[..., None]
    col = np.where(ground[..., None], ground_col, col)
    # 远处草丛/雾气过渡
    far_ground = ground & (d_road > 40)
    col = A.mix(col, fog_col[None, None],
                (A.smoothstep((d_road - 40) / 60.0) * 0.65)[..., None] *
                ground[..., None])

    # ---- 灯笼（远处一点红灯笼）
    sx = cx + lantern_x * f / lantern_d
    sy = horizon + (ycam - 1.35) * f / lantern_d * -1.0
    sy = horizon - (1.35 - ycam) * f / lantern_d
    d2 = (xx - sx) ** 2 + (yy - sy) ** 2
    col += np.exp(-d2 / (2 * 3.0 ** 2))[..., None] * \
        np.array([1.0, 0.62, 0.30], np.float32) * 1.35
    col += np.exp(-d2 / (2 * 11.0 ** 2))[..., None] * \
        np.array([1.0, 0.42, 0.16], np.float32) * 0.7
    col += np.exp(-d2 / (2 * 38.0 ** 2))[..., None] * \
        np.array([0.55, 0.24, 0.10], np.float32) * 0.35
    # 灯笼本体（小红点 + 竹骨竖纹）
    lh, lw = 20.0, 12.0
    body = np.exp(-(((xx - sx) / lw) ** 2 + ((yy - sy) / lh) ** 2) ** 2)
    rib = 0.6 + 0.4 * np.abs(np.cos((xx - sx) / lw * math.pi * 2.0))
    col = A.over(col, np.array([0.85, 0.28, 0.16], np.float32), body, 0.85)
    col += (body * (1 - rib) * 0.25)[..., None] * \
        np.array([0.6, 0.2, 0.1], np.float32)

    # 灯笼的木杆剪影
    pole_pts = [(sx - 5, sy + 8), (sx - 6, sy + 60)]
    pm = A.seg_mask((H, W), [(sx - 5, sy + 10, sx - 7, sy + 72, 3.0)], 0.8)
    col = A.mix(col, np.array([0.03, 0.035, 0.03], np.float32)[None, None],
                pm[..., None] * 0.7)

    # ---- 纸人（路边白色轮廓）
    pman_d = 10.5
    pman_x = 0.9 * math.sin(pman_d / 22.0) + 2.25
    px_s = cx + pman_x * f / pman_d
    py_s = horizon + (ycam - 0.0) * f / pman_d
    ph = 1.72 * f / pman_d
    fig = _figure_mask((H, W), px_s, py_s, ph, kind="paper")
    fig = A.blur(fig, 1.4)
    fig *= 0.86 + 0.14 * A.fbm((H, W), 6, 3, r)
    # 纸人颜色受雾影响
    fig_col = np.array([0.62, 0.62, 0.57], np.float32)
    col = A.over(col, fig_col, fig, 0.88)
    # 纸人的墨线眼（两点）
    for ex in (px_s - ph * 0.035, px_s + ph * 0.035):
        d2e = (xx - ex) ** 2 + (yy - (py_s - ph + ph * 0.115)) ** 2
        col = A.over(col, A.hexc("#15130f"),
                     np.exp(-d2e / (2 * (ph * 0.012) ** 2)), 0.9)
    # 纸人脚下的暗影
    shadow_ell = np.exp(-(((xx - px_s) / (ph * 0.22)) ** 2 +
                          ((yy - py_s) / (ph * 0.05)) ** 2))
    col *= (1.0 - 0.35 * shadow_ell)[..., None]

    # ---- 电线杆与电线
    def pole(sx_, ground_y, top_y, width, alpha=0.9):
        nonlocal col
        d_pole = np.abs(xx - sx_)
        m = (d_pole < width) & (yy >= top_y) & (yy <= ground_y)
        col = A.mix(col, np.array([0.025, 0.035, 0.038], np.float32)[None, None],
                    m[..., None] * alpha)
        arm = (np.abs(yy - (top_y + (ground_y - top_y) * 0.12)) < 2.0) & \
            (d_pole < width * 6)
        col = A.mix(col, np.array([0.025, 0.035, 0.038], np.float32)[None, None],
                    arm[..., None] * alpha)
        return top_y + (ground_y - top_y) * 0.12

    # 两根电线杆（近处左侧、远处右侧）
    arm_l = pole(W * 0.10, H * 0.98, H * 0.30, 4.0)
    arm_r = pole(W * 0.84, H * 0.60, H * 0.44, 2.2)
    # 电线：悬链线近似
    for dyoff, colr in ((-8, 0.4), (0, 0.5), (8, 0.4)):
        pts = []
        for t in np.linspace(0, 1, 40):
            x = W * 0.10 + (W * 0.84 - W * 0.10) * t
            sag = 26.0 * math.sin(math.pi * t)
            y = (arm_l + dyoff) + ((arm_r + dyoff) - (arm_l + dyoff)) * t + sag
            pts.append((x, y))
        m = np.zeros((H, W), np.float32)
        for (p0, p1) in zip(pts[:-1], pts[1:]):
            m = np.maximum(m, A.seg_mask((H, W), [(p0[0], p0[1], p1[0], p1[1], 1.2)], 0.7))
        col = A.mix(col, np.array([0.02, 0.03, 0.032], np.float32)[None, None],
                    m[..., None] * colr)

    # ---- 树木剪影（两侧近景）
    def tree(cxs, base_y, height, spread, alpha=0.95):
        nonlocal col
        im = Image.new("L", (W, H), 0)
        d = ImageDraw.Draw(im)
        trunk_w = max(2, height * 0.022)
        d.rectangle([cxs - trunk_w / 2, base_y - height * 0.62,
                     cxs + trunk_w / 2, base_y], fill=255)
        rr = np.random.default_rng(int(cxs * 7 + height))
        # 枝干
        for _ in range(9):
            bx = cxs + rr.normal(0, spread * 0.22)
            by = base_y - height * rr.uniform(0.45, 0.80)
            d.line([(cxs, base_y - height * 0.45), (bx, by)], fill=255,
                   width=max(1, int(trunk_w * 0.5)))
        # 碎树冠
        for _ in range(30):
            bx = cxs + rr.normal(0, spread * 0.42)
            by = base_y - height * rr.uniform(0.60, 0.99)
            br = height * rr.uniform(0.045, 0.13)
            d.ellipse([bx - br * 1.5, by - br * 1.1, bx + br * 1.5, by + br * 1.1],
                      fill=255)
        m = np.asarray(im, np.float32) / 255.0
        tex = _samp("leaves.jpg", (xx - cxs) / (spread * 2) + 0.5,
                    (yy - (base_y - height * 0.7)) / (height * 1.2) + 0.5)
        tc = A.mix(np.array([0.015, 0.022, 0.024], np.float32)[None, None],
                   tex * 0.16, 0.30)
        col = A.mix(col, tc, m[..., None] * alpha)

    tree(W * 0.005, H * 1.04, H * 0.46, W * 0.14)
    tree(W * 0.995, H * 0.72, H * 0.32, W * 0.11)

    # ---- 草地前景剪影（只在路两侧）
    segs = []
    for _ in range(150):
        if r.random() < 0.5:
            gx = r.uniform(-W * 0.02, W * 0.30)
        else:
            gx = r.uniform(W * 0.72, W * 1.02)
        gy = r.uniform(H * 0.76, H * 1.02)
        L = r.uniform(24, 85)
        segs.append((gx, gy, gx + r.normal(0, 14), gy - L, r.uniform(1.5, 3.8)))
    gm = A.seg_mask((H, W), segs, feather=0.8)
    col = A.mix(col, np.array([0.02, 0.028, 0.022], np.float32)[None, None],
                gm[..., None] * 0.75)

    # ---- 路边的纸钱
    money_tex = _img("paper_money.jpg")
    for k in range(5):
        dd = 2.4 + k * 1.7
        mx = 0.9 * math.sin(dd / 22.0) + r.uniform(-1.3, 1.3)
        mxs = cx + mx * f / dd
        mys = horizon + ycam * f / dd
        size_m = 0.09
        sw = max(3, int(size_m * f / dd))
        m = np.asarray(Image.fromarray((money_tex * 255).astype(np.uint8)).resize(
            (sw * 2, sw)), np.float32) / 255.0
        x0, y0 = int(mxs - sw), int(mys - sw * 0.5)
        x1, y1 = x0 + sw * 2, y0 + sw
        if x0 < 0 or x1 >= W or y0 < 0 or y1 >= H:
            continue
        sub = col[y0:y1, x0:x1]
        col[y0:y1, x0:x1] = sub * 0.62 + m * 0.38

    # ---- 后处理
    col = A.desaturate(col, 0.12)
    col = A.mix(col, A.hexc("#0a1418")[None, None], 0.12)
    col = np.clip(col, 0, 1)
    col = _grain_final(col, r, 0.05, 0.35)
    col = _scanlines(col, 0.02)
    col = _scratches(col, r, 10, "#c9c4b0", 0.12)
    col = col * A.vignette_mask((H, W), 0.58, 1.55)[..., None]
    col = np.clip(col, 0, 1)
    img = A.to_img(col)
    img = _date_stamp(img, "98 11 21", (W - 186, H - 64), 20, (198, 124, 58))
    img.save(A.ART_DIR / "poster-night.jpg", "JPEG", quality=90, optimize=True)
    print(f"  poster-night.jpg  900x1200  "
          f"{(A.ART_DIR / 'poster-night.jpg').stat().st_size/1024:.0f} KB")
    return img


# ================================================================ 入口 hero
def build_hero():
    W, H = 1600, 900
    posters = [Image.open(A.ART_DIR / n).convert("RGB")
               for n in ("poster-door.jpg", "poster-mirror.jpg", "poster-night.jpg")]
    canvas = Image.new("RGB", (W, H), (8, 8, 8))
    # 每张海报取中间 534x900 条带，重度模糊后拼接
    seg = 3
    seg_w = W // seg + 40
    arr = np.zeros((H, W, 3), np.float32)
    weight = np.zeros((H, W, 1), np.float32)
    for i, im in enumerate(posters):
        iw, ih = im.size
        crop_w = int(iw * (seg_w / (H * iw / ih)))
        crop_w = min(crop_w, iw)
        left = (iw - crop_w) // 2
        crop = im.crop((left, 0, left + crop_w, ih)).resize((seg_w, H), Image.LANCZOS)
        ca = np.asarray(crop, np.float32) / 255.0
        ca = A.blur(ca, 5.0, periodic=False)
        ca = np.clip(ca ** 0.82 * 1.35, 0, 1)
        x0 = i * (W // seg) - 20
        x1 = x0 + seg_w
        x0c, x1c = max(0, x0), min(W, x1)
        w = np.ones((1, x1c - x0c, 1), np.float32)
        if i > 0:
            ramp = np.linspace(0, 1, 70, dtype=np.float32)
            w[:, :70] = np.minimum(w[:, :70], ramp[None, :, None])
        if i < seg - 1:
            ramp = np.linspace(1, 0, 70, dtype=np.float32)
            w[:, -70:] = np.minimum(w[:, -70:], ramp[None, :, None])
        arr[:, x0c:x1c] += ca[:, (x0c - x0):(x1c - x0)] * w
        weight[:, x0c:x1c] += w
    arr = arr / np.maximum(weight, 1e-4)
    # 整体压暗、冷调、去饱和
    arr = A.mix(arr, A.hexc("#0a0d0c")[None, None], 0.24)
    arr = A.desaturate(arr, 0.25)
    arr = arr * np.array([0.88, 0.96, 0.94], np.float32)[None, None]
    r = A.rng("hero")
    arr = _grain_final(arr, r, 0.035, 0.3)
    arr = arr * A.vignette_mask((H, W), 0.58, 1.4, cx=0.5, cy=0.46)[..., None]
    arr = np.clip(arr, 0, 1)
    A.save_jpg(arr, A.ART_DIR / "hero.jpg", quality=88)
    print(f"  hero.jpg  1600x900  "
          f"{(A.ART_DIR / 'hero.jpg').stat().st_size/1024:.0f} KB")


# ================================================================ 印章 / favicon
def _seal_mask(W, H, r, margin=34, chip=0.55):
    """做旧方印蒙版：粗糙边缘、缺角、印泥不匀。"""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    m = np.ones((H, W), np.float32)
    m[(xx < margin) | (xx > W - margin) | (yy < margin) | (yy > H - margin)] = 0
    # 边缘起伏
    edge_n = A.fbm((H, W), 8, 4, r)
    inner = np.minimum.reduce([xx - margin, (W - margin) - xx,
                               yy - margin, (H - margin) - yy])
    m = A.smoothstep(inner / 5.0)
    # 缺角与崩边
    chips = (A.smoothstep((A.fbm((H, W), 6, 4, r) - 0.62) / 0.05) *
             (inner < 26)).astype(np.float32)
    m *= (1.0 - chips)
    # 印泥不匀：随机斑驳 + 缺墨
    m *= (0.68 + 0.32 * A.fbm((H, W), 12, 4, r))
    lack = A.smoothstep((A.fbm((H, W), 9, 4, r) - 0.70) / 0.05)
    m *= (1.0 - 0.65 * lack)
    return np.clip(m, 0, 1)


def build_seal():
    W = H = 512
    r = A.rng("seal")
    mask = _seal_mask(W, H, r, margin=40)
    # 篆意（用楷体加粗放大，再做轻微歪斜/断笔）
    chars = "三更"
    size = int(W * 0.30)
    tm = np.zeros((H, W), np.float32)
    for i, ch in enumerate(chars):
        lm = A.text_mask(ch, A.FONT_KAI, size,
                         (H, W), center=(W * 0.5, H * (0.30 + i * 0.40)),
                         stroke_width=3)
        tm = np.maximum(tm, lm)
    # 字的斑驳（印泥未盖到）
    tm *= (0.52 + 0.48 * A.fbm((H, W), 14, 4, r))
    tm = A.smoothstep((tm - 0.34) / 0.44)
    # 白文：字从印面挖掉
    alpha = mask * (1.0 - tm * 0.97)
    # 印面颜色：红的深浅不匀 + 边缘更浓
    fill = A.mix(A.hexc("#a52a24")[None, None], A.hexc("#7f1d1a")[None, None],
                  A.fbm((H, W), 7, 5, r)[..., None])
    fill = A.over(fill, A.hexc("#c0473c"),
                  0.5 * A.fbm((H, W), 20, 4, r), 0.35)
    fill = A.grain(fill, r, 0.03, 0.3)
    A.save_png(fill, A.ART_DIR / "seal.png", alpha=alpha)
    print(f"  seal.png  512x512  "
          f"{(A.ART_DIR / 'seal.png').stat().st_size/1024:.0f} KB")


def build_favicon():
    W = H = 128
    r = A.rng("favicon")
    margin = 11
    mask = _seal_mask(W, H, r, margin=margin, chip=0.5)
    size = int(W * 0.62)
    tm = A.text_mask("三", A.FONT_HEI, size, (H, W), center=(W * 0.5, H * 0.5),
                     stroke_width=1)
    tm *= (0.75 + 0.25 * A.fbm((H, W), 10, 4, r))
    tm = A.smoothstep((tm - 0.3) / 0.6)
    alpha = mask * (1.0 - tm * 0.98)
    fill = A.mix(A.hexc("#a52a24")[None, None], A.hexc("#8a211c")[None, None],
                 A.fbm((H, W), 6, 4, r)[..., None])
    # 黑底（不透明 PNG：黑色底 + 红印，字为黑色镂空）
    rgb = fill * alpha[..., None]
    A.save_png(np.clip(rgb, 0, 1), A.ART_DIR / "favicon.png")
    print(f"  favicon.png  128x128  "
          f"{(A.ART_DIR / 'favicon.png').stat().st_size/1024:.0f} KB")


# ================================================================ 入口
def main():
    A.ART_DIR.mkdir(parents=True, exist_ok=True)
    print("生成海报与包装 ...")
    poster_door()
    poster_mirror()
    poster_night()
    build_hero()
    build_seal()
    build_favicon()
    print("完成。")


if __name__ == "__main__":
    main()
