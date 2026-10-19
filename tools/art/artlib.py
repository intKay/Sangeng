"""artlib —— 《三更》程序化美术公共库。

全部图像由 numpy + Pillow 生成；固定随机种子（每个材质独立派生，见 rng()）。
不读取任何外部图片；只使用 Windows 自带中文字体文件。

主要能力：
  * 周期性（无缝）值噪声 / fBm / 各向异性噪声；
  * 周期性模糊（FFT 高斯）与普通模糊（边缘 pad）；
  * 轮胎状（torus）分布的斑点、椭圆、折线笔触 —— 所有 tiled 贴图保持无缝；
  * 文字蒙版（横排/竖排，楷体/黑体/宋体/雅黑）；
  * 贴图采样（供海报透视采样）；
  * JPEG/PNG 保存、缩小、颗粒、暗角等收尾工具。
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------- 路径与常量

HORROR_DIR = Path(__file__).resolve().parents[2]          # horror-demos/
PROJECT_DIR = HORROR_DIR.parent                            # 文艺漫游/
TEX_DIR = HORROR_DIR / "assets" / "textures"
ART_DIR = HORROR_DIR / "assets" / "art"
REPORT_DIR = HORROR_DIR / "reports" / "art"

SEED = 20261018

FONT_KAI = r"C:\Windows\Fonts\simkai.ttf"     # 楷体：手写招牌、印章
FONT_SONG = r"C:\Windows\Fonts\simsun.ttc"    # 宋体：表盘、纸面
FONT_HEI = r"C:\Windows\Fonts\simhei.ttf"     # 黑体：门牌、雕版
FONT_YAHEI = r"C:\Windows\Fonts\msyh.ttc"     # 雅黑：联系表标注

# 统一材质清单（键名 -> 文件名/尺寸/是否平铺）由 build_textures 读取，此处只放工具。


# ---------------------------------------------------------------- 随机与噪声

def rng(name: str) -> np.random.Generator:
    """按名字派生稳定随机数发生器（跨进程/跨机器稳定）。"""
    h = hashlib.md5(f"sangeng-art::{SEED}::{name}".encode("utf-8")).hexdigest()
    return np.random.default_rng(int(h[:16], 16))


def rng_int(name: str) -> int:
    h = hashlib.md5(f"sangeng-int::{SEED}::{name}".encode("utf-8")).hexdigest()
    return int(h[:8], 16)


def smoothstep(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def coords(shape):
    """返回 (yy, xx) 像素坐标网格，float32。"""
    h, w = shape[:2]
    yy = np.arange(h, dtype=np.float32)[:, None]
    xx = np.arange(w, dtype=np.float32)[None, :]
    return yy, xx


def pnoise(shape, cells=4, rng_=None):
    """周期性（无缝）二维值噪声。cells 可为 int 或 (cy, cx)，输出 0..1。"""
    if rng_ is None:
        rng_ = np.random.default_rng(0)
    h, w = shape[:2]
    if isinstance(cells, (tuple, list)):
        cy, cx = int(cells[0]), int(cells[1])
    else:
        cy = cx = int(cells)
    cy = max(1, cy)
    cx = max(1, cx)
    g = rng_.random((cy, cx))
    ys = (np.arange(h, dtype=np.float64) * cy / h)
    xs = (np.arange(w, dtype=np.float64) * cx / w)
    y0 = np.floor(ys).astype(int)
    x0 = np.floor(xs).astype(int)
    fy = smoothstep(ys - y0)
    fx = smoothstep(xs - x0)
    y0m = y0 % cy
    x0m = x0 % cx
    y1m = (y0 + 1) % cy
    x1m = (x0 + 1) % cx
    g00 = g[np.ix_(y0m, x0m)]
    g01 = g[np.ix_(y0m, x1m)]
    g10 = g[np.ix_(y1m, x0m)]
    g11 = g[np.ix_(y1m, x1m)]
    fyv = fy[:, None]
    fxv = fx[None, :]
    top = g00 * (1 - fxv) + g01 * fxv
    bot = g10 * (1 - fxv) + g11 * fxv
    return top * (1 - fyv) + bot * fyv


def fbm(shape, cells=4, octaves=5, rng_=None, persistence=0.5, aniso=None):
    """周期 fBm，输出大致 0..1。aniso=(cy,cx) 时为各向异性（拉伸）噪声。"""
    if rng_ is None:
        rng_ = np.random.default_rng(0)
    if aniso is not None:
        cy, cx = aniso
    elif isinstance(cells, (tuple, list)):
        cy, cx = cells
    else:
        cy = cx = cells
    total = np.zeros(shape[:2], np.float64)
    norm = 0.0
    amp = 1.0
    for o in range(octaves):
        total += amp * pnoise(shape, (max(1, int(round(cy))), max(1, int(round(cx)))), rng_)
        norm += amp
        amp *= persistence
        cy *= 2
        cx *= 2
    return total / norm


def ridged(shape, cells=4, octaves=4, rng_=None):
    """脊状噪声（适合裂纹/树皮/水痕）。输出 0..1，亮线在 1 附近。"""
    f = fbm(shape, cells, octaves, rng_)
    return 1.0 - np.abs(f * 2.0 - 1.0)


def blur(arr, sigma, periodic=False):
    """高斯模糊。periodic=True 用频域（严格无缝）；否则 reflect padding。"""
    if sigma <= 0.05:
        return np.asarray(arr, dtype=np.float64)
    a = np.asarray(arr, dtype=np.float64)
    h, w = a.shape[:2]
    pad = 0 if periodic else int(math.ceil(3 * sigma))
    if pad:
        pw = [(pad, pad), (pad, pad)] + ([(0, 0)] if a.ndim == 3 else [])
        a = np.pad(a, pw, mode="reflect")
        h, w = a.shape[:2]
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.fftfreq(w)[None, :]
    filt = np.exp(-2.0 * (np.pi ** 2) * (sigma ** 2) * (fy ** 2 + fx ** 2))
    if a.ndim == 3:
        filt = filt[..., None]
    out = np.fft.ifft2(np.fft.fft2(a, axes=(0, 1)) * filt, axes=(0, 1)).real
    if pad:
        out = out[pad:pad + (h - 2 * pad), pad:pad + (w - 2 * pad)]
    return out


def torus_delta(yy, xx, cy, cx, h, w):
    """返回相对 (cy,cx) 的环形最小位移 (dy, dx)。"""
    dy = (yy - cy + h * 0.5) % h - h * 0.5
    dx = (xx - cx + w * 0.5) % w - w * 0.5
    return dy, dx


def blobs(shape, specs, feather=2.0):
    """环形空间中的柔边圆斑叠加（取最大值）。specs: (cy, cx, r, peak)。"""
    h, w = shape[:2]
    yy, xx = coords(shape)
    out = np.zeros((h, w), np.float32)
    for cy, cx, r, peak in specs:
        dy, dx = torus_delta(yy, xx, cy, cx, h, w)
        d = np.sqrt(dy * dy + dx * dx)
        m = smoothstep((r - d) / max(feather, 1e-3))
        out = np.maximum(out, (m * peak).astype(np.float32))
    return out


def ellipses(shape, specs, feather=2.0):
    """环形空间中被旋转的椭圆斑。specs: (cy, cx, ry, rx, angle, peak)。"""
    h, w = shape[:2]
    yy, xx = coords(shape)
    out = np.zeros((h, w), np.float32)
    for cy, cx, ry, rx, ang, peak in specs:
        dy, dx = torus_delta(yy, xx, cy, cx, h, w)
        ca, sa = math.cos(ang), math.sin(ang)
        u = dx * ca + dy * sa
        v = -dx * sa + dy * ca
        d = np.sqrt((u / max(rx, 1e-3)) ** 2 + (v / max(ry, 1e-3)) ** 2)
        m = smoothstep((1.0 - d) * min(rx, ry) / max(feather, 1e-3))
        out = np.maximum(out, (m * peak).astype(np.float32))
    return out


def polyline_mask(shape, pts, width, feather=1.2):
    """环形空间折线笔触蒙版（0..1）。pts: [(x, y), ...] 像素坐标。"""
    h, w = shape[:2]
    yy, xx = coords(shape)
    out = np.zeros((h, w), np.float32)
    half = max(width, 0.6) * 0.5
    for (p0, p1) in zip(pts[:-1], pts[1:]):
        x0, y0 = p0
        x1, y1 = p1
        dxs = (xx - x0 + w * 0.5) % w - w * 0.5
        dys = (yy - y0 + h * 0.5) % h - h * 0.5
        ux, uy = x1 - x0, y1 - y0
        ll = ux * ux + uy * uy
        if ll < 1e-6:
            d = np.sqrt(dxs * dxs + dys * dys)
        else:
            t = np.clip((dxs * ux + dys * uy) / ll, 0.0, 1.0)
            d = np.sqrt((dxs - t * ux) ** 2 + (dys - t * uy) ** 2)
        m = smoothstep((half + feather - d) / max(feather, 1e-3))
        out = np.maximum(out, m.astype(np.float32))
    return out


def seg_mask(shape, segments, feather=0.9):
    """一批短线段（草叶/毛发）蒙版。segments: [(x0,y0,x1,y1,width), ...]"""
    h, w = shape[:2]
    yy, xx = coords(shape)
    out = np.zeros((h, w), np.float32)
    for (x0, y0, x1, y1, width) in segments:
        dxs = (xx - x0 + w * 0.5) % w - w * 0.5
        dys = (yy - y0 + h * 0.5) % h - h * 0.5
        ux, uy = x1 - x0, y1 - y0
        ll = ux * ux + uy * uy
        if ll < 1e-6:
            d = np.sqrt(dxs * dxs + dys * dys)
        else:
            t = np.clip((dxs * ux + dys * uy) / ll, 0.0, 1.0)
            d = np.sqrt((dxs - t * ux) ** 2 + (dys - t * uy) ** 2)
        half = max(width, 0.6) * 0.5
        m = smoothstep((half + feather - d) / max(feather, 1e-3))
        out = np.maximum(out, m.astype(np.float32))
    return out


# ---------------------------------------------------------------- 颜色工具

def hexc(h: str) -> np.ndarray:
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)], dtype=np.float32)


def mix(a, b, t):
    t = np.asarray(t, dtype=np.float32)
    if t.ndim == 2:
        t = t[..., None]
    return a * (1.0 - t) + b * t


def over(base, color, mask, strength=1.0):
    """把颜色 color 按 mask*strength 覆盖到 base（float RGB）。"""
    m = np.clip(np.asarray(mask, dtype=np.float32) * strength, 0.0, 1.0)
    if m.ndim == 2:
        m = m[..., None]
    c = np.asarray(color, dtype=np.float32)
    return base * (1.0 - m) + c * m


def ramp(field, stops, colors):
    """按 stops 位置把 0..1 场映射到 RGB 渐变。colors: [(r,g,b), ...]"""
    f = np.clip(np.asarray(field, dtype=np.float32), 0.0, 1.0)
    cols = np.array(colors, dtype=np.float32)
    out = np.empty(f.shape + (3,), np.float32)
    for ch in range(3):
        out[..., ch] = np.interp(f, stops, cols[:, ch]).astype(np.float32)
    return out


def desaturate(rgb, amount=0.25):
    lum = (rgb @ np.array([0.299, 0.587, 0.114], np.float32))[..., None]
    return mix(rgb, np.repeat(lum, 3, axis=-1), amount)


def brighten_contrast(rgb, brightness=0.0, contrast=1.0):
    out = (rgb - 0.5) * contrast + 0.5 + brightness
    return np.clip(out, 0.0, 1.0)


def grain(rgb, rng_, amount=0.02, chroma=0.25, periodic=True):
    """颗粒：亮度噪声为主 + 少量色度噪声。periodic 时噪声本身无结构。"""
    h, w = rgb.shape[:2]
    lum = rng_.normal(0.0, 1.0, (h, w)).astype(np.float32)
    lum = blur(lum, 0.55, periodic=False)
    lum = lum / (np.std(lum) + 1e-6)
    out = rgb + lum[..., None] * amount
    if chroma > 0:
        cr = rng_.normal(0.0, 1.0, (h, w, 3)).astype(np.float32)
        cr = blur(cr, 0.7, periodic=False)
        cr = cr / (np.std(cr) + 1e-6)
        out = out + cr * (amount * chroma)
    return np.clip(out, 0.0, 1.0)


def vignette_mask(shape, strength=0.5, power=2.2, cx=0.5, cy=0.5):
    h, w = shape[:2]
    yy, xx = coords(shape)
    nx = (xx / (w - 1) - cx) / 0.72
    ny = (yy / (h - 1) - cy) / 0.72
    r = np.sqrt(nx * nx + ny * ny)
    return 1.0 - strength * np.clip(r, 0, 1.4) ** power


def border_dist(shape, inset_x, inset_y=None):
    """到矩形内边界的有符号距离（内部为正，像素）。inset_y 默认同 inset_x。"""
    h, w = shape[:2]
    if inset_y is None:
        inset_y = inset_x
    yy, xx = coords(shape)
    dx = np.minimum(xx - inset_x, (w - inset_x) - xx)
    dy = np.minimum(yy - inset_y, (h - inset_y) - yy)
    return np.minimum(dx, dy)


# ---------------------------------------------------------------- 文字

_FONT_CACHE: dict = {}


def get_font(path: str, size: int) -> ImageFont.FreeTypeFont:
    key = (path, size)
    if key not in _FONT_CACHE:
        _FONT_CACHE[key] = ImageFont.truetype(path, size)
    return _FONT_CACHE[key]


def text_mask(text, font_path, size, shape, center=None, spacing=1.0,
              anchor="mm", stroke_width=0, tracking=0):
    """单行文字蒙版（0..1）。center 为 (x, y) 像素；默认画布中心。"""
    h, w = shape[:2]
    img = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(img)
    font = get_font(font_path, int(size))
    cx, cy = center if center is not None else (w * 0.5, h * 0.5)
    if tracking:
        # 手动逐字排版（用于横招牌的疏密调节）
        total = 0
        widths = []
        for ch in text:
            bb = d.textbbox((0, 0), ch, font=font, stroke_width=stroke_width)
            wch = bb[2] - bb[0]
            widths.append(wch)
            total += wch + tracking
        total -= tracking
        x = cx - total * 0.5
        for ch, wch in zip(text, widths):
            d.text((x, cy), ch, font=font, fill=255, anchor="lm",
                   stroke_width=stroke_width)
            x += wch + tracking
    else:
        d.text((cx, cy), text, font=font, fill=255, anchor=anchor,
               stroke_width=stroke_width)
    return np.asarray(img, dtype=np.float32) / 255.0


def vtext_mask(chars, font_path, size, shape, center=None, char_gap=1.12,
               stroke_width=0):
    """竖排文字蒙版；chars 为字符串，逐字居中排列。"""
    h, w = shape[:2]
    img = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(img)
    font = get_font(font_path, int(size))
    cx, cy = center if center is not None else (w * 0.5, h * 0.5)
    step = size * char_gap
    y0 = cy - step * (len(chars) - 1) * 0.5
    for i, ch in enumerate(chars):
        d.text((cx, y0 + i * step), ch, font=font, fill=255, anchor="mm",
               stroke_width=stroke_width)
    return np.asarray(img, dtype=np.float32) / 255.0


# ---------------------------------------------------------------- 图像/保存

def to_img(arr, mode="RGB", alpha=None):
    """float RGB(A) -> PIL。alpha 单独给时拼成 RGBA。"""
    a = np.clip(arr, 0.0, 1.0)
    if alpha is not None:
        rgb8 = (a[..., :3] * 255.0 + 0.5).astype(np.uint8)
        al8 = np.clip(alpha, 0.0, 1.0)
        if al8.ndim == 3:
            al8 = al8[..., 0]
        al8 = (al8 * 255.0 + 0.5).astype(np.uint8)
        return Image.fromarray(np.dstack([rgb8, al8]), "RGBA")
    return Image.fromarray((a * 255.0 + 0.5).astype(np.uint8), mode)


def resize_arr(arr, w, h):
    """高质量缩小（RGB / 灰度 / RGBA）。"""
    a = np.asarray(arr, dtype=np.float32)
    if a.ndim == 3 and a.shape[2] == 4:
        rgb = Image.fromarray((np.clip(a[..., :3], 0, 1) * 255 + 0.5).astype(np.uint8), "RGB")
        al = Image.fromarray((np.clip(a[..., 3], 0, 1) * 255 + 0.5).astype(np.uint8), "L")
        rgb = rgb.resize((w, h), Image.LANCZOS)
        al = al.resize((w, h), Image.LANCZOS)
        return np.dstack([np.asarray(rgb, np.float32) / 255.0,
                          np.asarray(al, np.float32) / 255.0])
    if a.ndim == 2:
        im = Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8), "L")
        return np.asarray(im.resize((w, h), Image.LANCZOS), np.float32) / 255.0
    im = Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8), "RGB")
    return np.asarray(im.resize((w, h), Image.LANCZOS), np.float32) / 255.0


def downscale_tiled(arr, w, h, ss, k=8):
    """周期性（无缝）缩小：先环形 pad 再缩放，避免边缘被 clamp 出接缝。"""
    if ss == 1:
        return arr
    a = np.asarray(arr, np.float32)
    if a.ndim == 3 and a.shape[2] == 4:
        rgb = downscale_tiled(a[..., :3], w, h, ss, k)
        al = downscale_tiled(a[..., 3], w, h, ss, k)
        return np.dstack([rgb, al])
    H, W = a.shape[:2]
    ys = np.arange(-k, H + k) % H
    xs = np.arange(-k, W + k) % W
    if a.ndim == 3:
        padded = a[np.ix_(ys, xs)]
    else:
        padded = a[np.ix_(ys, xs)]
    ow = int(round(w * (W + 2 * k) / W))
    oh = int(round(h * (H + 2 * k) / H))
    res = resize_arr(padded, ow, oh)
    ox = (ow - w) // 2
    oy = (oh - h) // 2
    return res[oy:oy + h, ox:ox + w]


def downscale(rgb, w, h, ss):
    """把 ss 倍工作图缩回目标尺寸（ss=1 时原样返回）。"""
    if ss == 1:
        return rgb
    return resize_arr(rgb, w, h)


def save_jpg(arr, path: Path, quality=88):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    im = to_img(arr, "RGB")
    im.save(path, "JPEG", quality=quality, optimize=True, progressive=False)


def save_png(arr, path: Path, alpha=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    im = to_img(arr, "RGB", alpha=alpha)
    im.save(path, "PNG", optimize=True)


# ---------------------------------------------------------------- 贴图采样（海报用）

_TEX_CACHE: dict = {}


def load_tex(path):
    path = Path(path)
    key = str(path)
    if key not in _TEX_CACHE:
        im = Image.open(path).convert("RGB")
        _TEX_CACHE[key] = np.asarray(im, np.float32) / 255.0
    return _TEX_CACHE[key]


def sample(tex, u, v, wrap=True):
    """双线性采样。u,v 可为任意形状数组（0..1）；wrap=True 周期性。"""
    h, w = tex.shape[:2]
    u = np.asarray(u, np.float32)
    v = np.asarray(v, np.float32)
    if wrap:
        x = (u % 1.0) * w
        y = (v % 1.0) * h
        x0 = np.floor(x).astype(np.int64) % w
        y0 = np.floor(y).astype(np.int64) % h
        x1 = (x0 + 1) % w
        y1 = (y0 + 1) % h
    else:
        x = np.clip(u, 0, 1) * (w - 1)
        y = np.clip(v, 0, 1) * (h - 1)
        x0 = np.floor(x).astype(np.int64)
        y0 = np.floor(y).astype(np.int64)
        x1 = np.clip(x0 + 1, 0, w - 1)
        y1 = np.clip(y0 + 1, 0, h - 1)
    fx = (x - x0)[..., None].astype(np.float32)
    fy = (y - y0)[..., None].astype(np.float32)
    c00 = tex[y0, x0]
    c01 = tex[y0, x1]
    c10 = tex[y1, x0]
    c11 = tex[y1, x1]
    return (c00 * (1 - fx) + c01 * fx) * (1 - fy) + (c10 * (1 - fx) + c11 * fx) * fy


# ---------------------------------------------------------------- 渐变/场工具

def gradient_v(h, w, stops, colors):
    """竖直渐变（0 上、1 下）。"""
    t = np.linspace(0.0, 1.0, h, dtype=np.float32)
    cols = np.array(colors, np.float32)
    out = np.empty((h, w, 3), np.float32)
    for ch in range(3):
        out[..., ch] = np.interp(t, stops, cols[:, ch])[:, None]
    return out


def radial_field(shape, cx, cy, radius, periodic=False):
    h, w = shape[:2]
    yy, xx = coords(shape)
    if periodic:
        dy, dx = torus_delta(yy, xx, cy, cx, h, w)
    else:
        dy = yy - cy
        dx = xx - cx
    return np.sqrt(dy * dy + dx * dx) / max(radius, 1e-3)


def hexlist(hexes):
    return [hexc(h) for h in hexes]


def write_json(path: Path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def md5_file(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()
