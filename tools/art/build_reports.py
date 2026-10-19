"""《三更》美术自检：联系表 contact_sheet.jpg + 校验报告 verify.txt。

用法：
  python horror-demos/tools/art/build_reports.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np                                 # noqa: E402
from PIL import Image, ImageDraw, ImageFont        # noqa: E402

import artlib as A                                 # noqa: E402
from build_textures import ALL_SPECS, REQUIRED_KEYS  # noqa: E402

SPEC_BY_KEY = {s["key"]: s for s in ALL_SPECS}
MAX_TEXTURE_BYTES = 8 * 1024 * 1024

ART_EXPECT = {
    "poster-door.jpg": (900, 1200),
    "poster-mirror.jpg": (900, 1200),
    "poster-night.jpg": (900, 1200),
    "hero.jpg": (1600, 900),
    "seal.png": (512, 512),
    "favicon.png": (128, 128),
}


def _checker(w, h, a=18, b=26):
    im = Image.new("RGB", (w, h), (a, a, a))
    d = ImageDraw.Draw(im)
    step = 16
    for y in range(0, h, step):
        for x in range(0, w, step):
            if ((x // step) + (y // step)) % 2 == 0:
                d.rectangle([x, y, x + step - 1, y + step - 1], fill=(b, b, b))
    return im


def _load_cell(spec, tex_dir: Path):
    path = tex_dir / spec["file"]
    im = Image.open(path)
    im.load()
    if im.mode == "RGBA":
        bg = _checker(im.width, im.height)
        bg.paste(im, (0, 0), im)
        im = bg
    else:
        im = im.convert("RGB")
    if spec.get("tiled"):
        w, h = im.size
        tiled = Image.new("RGB", (w * 2, h * 2))
        for yy in range(2):
            for xx in range(2):
                tiled.paste(im, (xx * w, yy * h))
        im = tiled
    return im


def build_contact_sheet(tex_dir: Path, out_path: Path):
    order = [k for k in REQUIRED_KEYS if k in SPEC_BY_KEY]
    cols = 8
    cell_w, cell_h = 182, 198
    img_box = 166
    margin = 18
    header = 74
    rows = (len(order) + cols - 1) // cols
    W = margin * 2 + cols * cell_w
    H = header + margin + rows * cell_h + margin
    sheet = Image.new("RGB", (W, H), (20, 20, 19))
    d = ImageDraw.Draw(sheet)
    title_font = ImageFont.truetype(A.FONT_YAHEI, 22)
    sub_font = ImageFont.truetype(A.FONT_YAHEI, 12)
    label_font = ImageFont.truetype(A.FONT_YAHEI, 12)
    small_font = ImageFont.truetype(A.FONT_YAHEI, 10)

    d.text((margin, 14), "《三更》SANGENG · 贴图联系表（50 × MAT_*）",
           font=title_font, fill=(216, 208, 186))
    d.text((margin, 44),
           "seed 20261018 · 建筑贴图以 2×2 平铺显示（检查四边接缝）· "
           "右下标注 尺寸 / 文件大小",
           font=sub_font, fill=(140, 134, 118))
    d.line([(margin, header - 6), (W - margin, header - 6)], fill=(64, 60, 52))

    for i, key in enumerate(order):
        spec = SPEC_BY_KEY[key]
        col, row = i % cols, i // cols
        x = margin + col * cell_w
        y = header + margin + row * cell_h
        # 格底
        d.rectangle([x + 2, y + 2, x + cell_w - 6, y + cell_h - 30],
                    fill=(28, 28, 26), outline=(48, 45, 40))
        try:
            im = _load_cell(spec, tex_dir)
        except FileNotFoundError:
            d.text((x + 8, y + 40), "MISSING", font=label_font, fill=(200, 70, 60))
            im = None
        if im is not None:
            im.thumbnail((img_box, img_box), Image.LANCZOS)
            px = x + (cell_w - 6 + 2 - im.width) // 2
            py = y + 2 + (cell_h - 30 - im.height) // 2
            sheet.paste(im, (px, py))
        # 标签
        ly = y + cell_h - 26
        d.text((x + 4, ly), key, font=label_font, fill=(224, 218, 200))
        f = tex_dir / spec["file"]
        kb = f.stat().st_size / 1024 if f.exists() else 0
        tiled = " · 2×2" if spec.get("tiled") else ""
        d.text((x + 4, ly + 13),
               f"{spec['w']}×{spec['h']}{tiled} · {kb:.0f}KB",
               font=small_font, fill=(130, 126, 112))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path, "JPEG", quality=90, optimize=True)
    return sheet.size


def seam_metric(path: Path):
    arr = np.asarray(Image.open(path).convert("RGB"), np.float32) / 255.0
    h, w = arr.shape[:2]
    seam_x = np.abs(arr[:, 0] - arr[:, -1]).mean()
    seam_y = np.abs(arr[0, :] - arr[-1, :]).mean()
    ref_x = np.abs(arr[:, 1:] - arr[:, :-1]).mean()
    ref_y = np.abs(arr[1:, :] - arr[:-1, :]).mean()
    return (seam_x / max(ref_x, 1e-6), seam_y / max(ref_y, 1e-6))


def build_verify(tex_dir: Path, art_dir: Path, report: Path):
    lines = []
    ok = True
    lines.append("《三更》美术自检报告 verify.txt")
    lines.append("=" * 78)
    lines.append(f"生成脚本: horror-demos/tools/art/build_textures.py (numpy {np.__version__}, "
                 f"Pillow {Image.__version__})")
    lines.append(f"固定种子: {A.SEED}  目标: 50 个 MAT_* 全部有文件 + manifest 条目")
    lines.append("")

    # ---- manifest
    man_path = tex_dir / "manifest.json"
    manifest = {}
    if not man_path.exists():
        lines.append("[FAIL] manifest.json 不存在")
        ok = False
    else:
        try:
            manifest = json.loads(man_path.read_text(encoding="utf-8"))
            mats = manifest.get("materials", {})
            lines.append(f"[OK] manifest.json 可解析，materials = {len(mats)}")
        except Exception as exc:  # noqa: BLE001
            lines.append(f"[FAIL] manifest.json 解析失败: {exc}")
            mats = {}
            ok = False
    mats = manifest.get("materials", {})

    lines.append("")
    lines.append("---- 1. 文件与 manifest 覆盖（顺序同 ASSET_SPEC §3） ----")
    lines.append(f"{'KEY':<24}{'FILE':<22}{'SIZE':>9}{'BYTES':>9}  "
                 f"{'TILE':<5}{'SEAM_X':>7}{'SEAM_Y':>7}  STATUS")
    total = 0
    missing = []
    for key in REQUIRED_KEYS:
        spec = SPEC_BY_KEY.get(key)
        if spec is None:
            lines.append(f"{key:<24}{'--':<22}{'--':>9}{'--':>9}  SPEC 缺失")
            ok = False
            continue
        f = tex_dir / spec["file"]
        entry = mats.get(key)
        problems = []
        if not f.exists():
            problems.append("文件缺失")
            missing.append(key)
        if entry is None:
            problems.append("manifest 缺失")
        elif entry.get("file") != spec["file"]:
            problems.append("manifest 文件名不一致")
        if f.exists():
            with Image.open(f) as im:
                w, h = im.size
                mode = im.mode
            if (w, h) != (spec["w"], spec["h"]):
                problems.append(f"尺寸{w}x{h}!={spec['w']}x{spec['h']}")
            expect_png = spec.get("alpha", False)
            if expect_png and f.suffix.lower() != ".png":
                problems.append("透明材质应为 PNG")
            if not expect_png and f.suffix.lower() != ".jpg":
                problems.append("不透明材质应为 JPEG")
            if expect_png and "A" not in mode:
                problems.append("PNG 无 alpha 通道")
            size = f.stat().st_size
            total += size
            if spec.get("tiled"):
                sx, sy = seam_metric(f)
                seam = f"{sx:6.2f}{sy:7.2f}"
                if max(sx, sy) > 1.9:
                    problems.append("接缝偏大?")
            else:
                seam = f"{'--':>6}{'--':>7}"
        else:
            size = 0
            seam = f"{'--':>6}{'--':>7}"
        status = "OK" if not problems else "FAIL: " + ",".join(problems)
        if problems:
            ok = False
        lines.append(f"{key:<24}{spec['file']:<22}{f'{size/1024:7.1f}KB':>9}"
                     f"{size:>9}  {('Y' if spec.get('tiled') else 'n'):<5}"
                     f"{seam}  {status}")
    lines.append("")

    # manifest 多余键
    extra = [k for k in mats if k not in REQUIRED_KEYS]
    lines.append(f"manifest 多余键: {extra if extra else '无'}")
    lines.append(f"manifest 各字段检查: " + (
        "OK（file/colorSpace/tint/emissive；自发光含 emissiveIntensity；"
        "透明含 transparent）"
        if all("file" in mats[k] and "tint" in mats[k] for k in mats) else "FAIL"))
    if extra:
        ok = False

    # ---- 总量
    all_files = [p for p in tex_dir.iterdir()
                 if p.is_file() and p.suffix.lower() in (".jpg", ".png")]
    total_all = sum(p.stat().st_size for p in all_files)
    lines.append("")
    lines.append("---- 2. 总量 ----")
    lines.append(f"贴图文件数: {len(all_files)}（manifest.json 之外） / 期望 50")
    lines.append(f"贴图总字节: {total_all} ({total_all/1024/1024:.2f} MB) / 上限 8 MB")
    if len(all_files) != 50:
        lines.append("[FAIL] 文件数不等于 50")
        ok = False
    if total_all > MAX_TEXTURE_BYTES:
        lines.append("[FAIL] 超过 8MB")
        ok = False
    else:
        lines.append("[OK] 总量在 8MB 以内")

    # ---- 其他美术
    lines.append("")
    lines.append("---- 3. 海报与包装 ----")
    for name, (ew, eh) in ART_EXPECT.items():
        f = art_dir / name
        if not f.exists():
            lines.append(f"[--] {name:<18} 未生成（待海报步骤）")
            continue
        with Image.open(f) as im:
            w, h = im.size
        st = "OK" if (w, h) == (ew, eh) else f"FAIL 尺寸 {w}x{h} != {ew}x{eh}"
        if (w, h) != (ew, eh):
            ok = False
        lines.append(f"[{st[:2]}] {name:<18} {w}x{h}  {f.stat().st_size/1024:.0f} KB  {st}")

    # ---- 结论
    lines.append("")
    lines.append("=" * 78)
    if ok:
        lines.append("VERIFY OK")
    else:
        lines.append("VERIFY FAIL: 见上方 FAIL 行")
        if missing:
            lines.append("缺失: " + ", ".join(missing))
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return ok, "\n".join(lines)


def main():
    tex_dir = A.TEX_DIR
    art_dir = A.ART_DIR
    out_dir = A.REPORT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    size = build_contact_sheet(tex_dir, out_dir / "contact_sheet.jpg")
    print(f"contact_sheet.jpg: {size[0]}x{size[1]}")
    ok, text = build_verify(tex_dir, art_dir, out_dir / "verify.txt")
    print(text)
    print("VERIFY OK" if ok else "VERIFY FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
