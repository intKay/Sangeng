"""《三更》贴图生成入口：生成 assets/textures/ 下全部 MAT_* 贴图 + manifest.json。

用法（在仓库根目录）：
  python horror-demos/tools/art/build_textures.py                # 全部
  python horror-demos/tools/art/build_textures.py --only MAT_wallpaper,MAT_tile_green
  python horror-demos/tools/art/build_textures.py --list
  python horror-demos/tools/art/build_textures.py --no-manifest  # 只出图，便于迭代

固定 seed（artlib.SEED），可重复生成一致结果。禁止外部图片素材。
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

# 允许以脚本方式运行（把同目录加入 sys.path）
sys.path.insert(0, str(Path(__file__).resolve().parent))

import artlib as A                      # noqa: E402
import textures_surfaces as T1          # noqa: E402
import textures_props as T2             # noqa: E402

ALL_SPECS = T1.SPECS + T2.SPECS

# 硬性要求：ASSET_SPEC §3 的全部键名（顺序即文档顺序）
REQUIRED_KEYS = """
MAT_wallpaper MAT_wallpaper_dark MAT_plaster MAT_wood_floor MAT_wood_door
MAT_wood_dark MAT_wood_pale MAT_paint_ceiling MAT_concrete MAT_tile_green
MAT_tile_white MAT_tile_floor MAT_metal_locker MAT_metal_rust MAT_glass_dirty
MAT_window_night MAT_curtain MAT_fabric_red MAT_fabric_white MAT_fabric_blue
MAT_paper MAT_photo MAT_tv_static MAT_lamp_tube MAT_lamp_warm MAT_lantern_paper
MAT_soil MAT_grass MAT_bark MAT_leaves MAT_stone MAT_shrine_wood MAT_sign_night_1
MAT_sign_night_2 MAT_sign_bath MAT_shrine_tablet MAT_door_number_501
MAT_door_number_502 MAT_door_number_503 MAT_door_number_504 MAT_clock_face
MAT_mirror_grime MAT_stain_mold MAT_stain_water MAT_entity_white MAT_entity_hair
MAT_entity_face MAT_red_cloth MAT_paper_money MAT_steam
""".split()


def check_specs():
    keys = [s["key"] for s in ALL_SPECS]
    files = [s["file"] for s in ALL_SPECS]
    problems = []
    if len(keys) != len(set(keys)):
        problems.append("重复的 key")
    if len(files) != len(set(files)):
        problems.append("重复的文件名")
    missing = [k for k in REQUIRED_KEYS if k not in keys]
    extra = [k for k in keys if k not in REQUIRED_KEYS]
    if missing:
        problems.append("缺少键名: " + ", ".join(missing))
    if extra:
        problems.append("多余键名: " + ", ".join(extra))
    if problems:
        raise SystemExit("SPEC 校验失败: " + "; ".join(problems))
    return keys


def build_one(spec, out_dir: Path):
    t0 = time.time()
    w, h = spec["w"], spec["h"]
    alpha = spec.get("alpha", False)
    arr = spec["fn"](w, h)
    file_path = out_dir / spec["file"]
    if alpha:
        if arr.shape[2] != 4:
            raise SystemExit(f"{spec['key']}: 期望 RGBA 输出，得到 {arr.shape}")
        A.save_png(arr[..., :3], file_path, alpha=arr[..., 3])
    else:
        if arr.shape[0] != h or arr.shape[1] != w:
            raise SystemExit(f"{spec['key']}: 尺寸 {arr.shape[1]}x{arr.shape[0]} "
                             f"!= {w}x{h}")
        A.save_jpg(arr, file_path, quality=88)
    dt = time.time() - t0
    size = file_path.stat().st_size
    print(f"  {spec['key']:<22} {w:>3}x{h:<3} {size/1024:6.1f} KB  {dt:5.2f}s  "
          f"{spec['file']}")
    return size


def make_manifest(entries):
    materials = {}
    for spec in ALL_SPECS:
        entry = {
            "file": spec["file"],
            "colorSpace": "srgb",
            "tint": spec.get("tint", "#ffffff"),
            "emissive": spec.get("emissive"),
        }
        if spec.get("emissive"):
            entry["emissiveIntensity"] = spec.get("emissiveIntensity", 1.0)
        if spec.get("transparent"):
            entry["transparent"] = True
        materials[spec["key"]] = entry
    return {"materials": materials}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="逗号分隔的键名，只重建这些")
    ap.add_argument("--list", action="store_true", help="列出全部材质")
    ap.add_argument("--no-manifest", action="store_true", help="不写 manifest")
    ap.add_argument("--out", default=str(A.TEX_DIR), help="输出目录")
    args = ap.parse_args()

    check_specs()
    if args.list:
        for s in ALL_SPECS:
            print(f"{s['key']:<24} {s['w']}x{s['h']:<4} tiled={str(s['tiled']):<5} "
                  f"{s['file']}")
        print(f"共 {len(ALL_SPECS)} 个材质")
        return

    selected = [s.strip() for s in args.only.split(",") if s.strip()]
    if selected:
        unknown = [k for k in selected if k not in {s["key"] for s in ALL_SPECS}]
        if unknown:
            raise SystemExit("未知键名: " + ", ".join(unknown))
        specs = [s for s in ALL_SPECS if s["key"] in selected]
    else:
        specs = ALL_SPECS

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    # 清掉旧的 manifest 由本脚本重写，不删除其它文件以免误删
    print(f"生成 {len(specs)} 张贴图 -> {out_dir}")
    total = 0
    for spec in specs:
        total += build_one(spec, out_dir)

    if not args.no_manifest:
        manifest = make_manifest(specs)
        A.write_json(out_dir / "manifest.json", manifest)
        print(f"manifest.json: {len(manifest['materials'])} 个材质 -> "
              f"{out_dir / 'manifest.json'}")
    print(f"本次输出 {total/1024/1024:.2f} MB")
    # 目录总量
    all_files = sorted(p for p in out_dir.iterdir() if p.is_file())
    total_all = sum(p.stat().st_size for p in all_files)
    print(f"目录合计 {len(all_files)} 文件 {total_all/1024/1024:.2f} MB "
          f"(<= 8MB 要求)")


if __name__ == "__main__":
    main()
