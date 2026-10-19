"""verify.py — 音频资产自检，输出 reports/audio/verify.txt（+ 波形图 PNG）。

检查项
1. manifest JSON 可解析、字段完整；
2. manifest 引用的文件全部存在，且无未引用孤儿文件；
3. ffprobe: codec=vorbis / 采样率 44100 / 声道（音乐环境=2，音效UI=1）/ 时长；
4. 解码后实测：峰值 ≤ -1 dBFS；音乐环境 RMS 约 -22~-18；SFX 峰值 -3~-1；UI 轻；
5. 循环素材接缝：jump_rel = |x0-x[-1]| / rms(diff)，< 6 视为听不出接缝；
6. 汇总文件数、总时长、分组统计。

用法: python verify.py [door|mirror|nightroad|all] [--png]
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import synth as S  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
ASSETS = os.path.join(ROOT, "assets", "audio")
REPORT_DIR = os.path.join(ROOT, "reports", "audio")
SHARED_MANIFEST = "shared/manifest.json"
GAME_MANIFESTS = {
    "door": "door/manifest.json",
    "mirror": "mirror/manifest.json",
    "nightroad": "nightroad/manifest.json",
}

MUSIC_DUR = {
    "door/music/main.ogg": 60.0, "door/music/tension.ogg": 45.0,
    "door/music/ending.ogg": 40.0,
    "mirror/music/main.ogg": 60.0, "mirror/music/tension.ogg": 45.0,
    "mirror/music/ending.ogg": 35.0,
    "nightroad/music/main.ogg": 60.0, "nightroad/music/tension.ogg": 45.0,
    "nightroad/music/ending.ogg": 40.0,
}
AMB_DUR = {
    "door/ambience/corridor_hum.ogg": 30.0, "door/ambience/room_tone.ogg": 30.0,
    "door/ambience/rain_window.ogg": 30.0, "door/ambience/tv_static.ogg": 15.0,
    "mirror/ambience/fluorescent_buzz.ogg": 20.0,
    "mirror/ambience/water_drip.ogg": 30.0,
    "mirror/ambience/distant_water.ogg": 30.0,
    "mirror/ambience/steam_hiss.ogg": 15.0,
    "nightroad/ambience/wind_field.ogg": 30.0,
    "nightroad/ambience/insects.ogg": 30.0,
    "nightroad/ambience/night_room_tone.ogg": 30.0,
    "nightroad/ambience/distant_dog.ogg": 12.0,
}
LOOP_DUR = {
    "door/sfx/clock_tick.ogg": 2.0,
    "mirror/sfx/clock_tick.ogg": 2.0,
    "door/sfx/heartbeat.ogg": 10.0,
    "mirror/sfx/heartbeat.ogg": 10.0,
    "nightroad/sfx/heartbeat.ogg": 10.0,
    "door/sfx/breath.ogg": 8.0,
    "nightroad/sfx/breath.ogg": 8.0,
    "door/sfx/entity_breath.ogg": 10.0,
    "mirror/sfx/doppel_breath.ogg": 8.0,
    "mirror/sfx/water_stream.ogg": 10.0,
    "mirror/sfx/radio_static.ogg": 8.0,
}


# ------------------------------------------------------------ helpers -----
def collect_manifest_entries(manifest, base):
    """遍历 manifest，返回 [(entry_key, abs_path, rel_path, loop, category)]。"""
    out = []
    for cat in ("music", "ambience", "sfx", "ui"):
        section = manifest.get(cat) or {}
        for key, ent in section.items():
            paths = []
            if "file" in ent:
                paths = [ent["file"]]
            elif "files" in ent:
                paths = list(ent["files"])
            for rel in paths:
                rel_norm = os.path.normpath(os.path.join(base, rel)).replace("\\", "/")
                out.append({
                    "key": f"{cat}.{key}",
                    "category": cat,
                    "loop": bool(ent.get("loop", False)),
                    "abs": os.path.join(ASSETS, rel_norm),
                    "rel": rel_norm,
                    "volume": ent.get("volume"),
                })
    return out


def decode_stats(path):
    x = S.decode_f32(path)
    mono = x.mean(axis=0)
    peak = S.peak_db(x)
    rms = S.rms_db(x)
    dc = float(np.mean(mono))
    seam = S.seam_metrics(x)
    return {
        "peak": peak, "rms": rms, "dc": dc,
        "jump_rel": seam[0], "slope_rel": seam[1],
        "nch": x.shape[0], "nsamp": x.shape[1],
    }


def fmt_db(v):
    return f"{v:7.2f}"


class Report:
    def __init__(self):
        self.lines = []
        self.fails = []
        self.warns = []

    def add(self, s=""):
        self.lines.append(s)

    def check(self, ok, msg, level="FAIL"):
        if not ok:
            (self.fails if level == "FAIL" else self.warns).append(msg)
        return ok


def main(argv):
    group = argv[1] if len(argv) > 1 and not argv[1].startswith("--") else "all"
    make_png = "--png" in argv or group == "all"
    groups = list(GAME_MANIFESTS) if group == "all" else [group]
    rep = Report()

    # ---- environment
    import platform
    rep.add("《三更》音频资产自检报告")
    rep.add("=" * 78)
    rep.add(f"生成时间(本地): 见文件修改时间；环境 python {platform.python_version()} / "
            f"numpy {np.__version__} / ffmpeg(libvorbis)")
    rep.add(f"资产根目录: {os.path.relpath(ASSETS, ROOT)}")
    rep.add("")

    # ---- load manifests
    manifests = {}
    all_entries = []
    for g in groups:
        rel_m = GAME_MANIFESTS[g]
        path = os.path.join(ASSETS, rel_m)
        rep.add(f"[manifest] {rel_m}")
        if not os.path.exists(path):
            rep.check(False, f"缺少 manifest: {rel_m}")
            continue
        with open(path, encoding="utf-8") as f:
            man = json.load(f)
        manifests[g] = man
        rep.check(man.get("id") == g, f"{rel_m}: id 应为 {g}")
        for cat in ("music", "ambience", "sfx", "ui"):
            rep.check(cat in man and isinstance(man[cat], dict),
                      f"{rel_m}: 缺少 {cat} 段")
        entries = collect_manifest_entries(man, os.path.dirname(rel_m))
        all_entries.extend(entries)
        rep.add(f"           categories={list(man.keys())} 条目={len(entries)}")
    # shared manifest
    spath = os.path.join(ASSETS, SHARED_MANIFEST)
    rep.add(f"[manifest] {SHARED_MANIFEST}")
    if os.path.exists(spath):
        with open(spath, encoding="utf-8") as f:
            sman = json.load(f)
        sentries = collect_manifest_entries(sman, os.path.dirname(SHARED_MANIFEST))
        all_entries.extend(sentries)
        rep.add(f"           ui 条目={len(sentries)}")
    else:
        rep.check(False, f"缺少 manifest: {SHARED_MANIFEST}")
    rep.add("")

    # ---- manifest file existence
    rep.add("1) manifest 引用检查")
    rep.add("-" * 78)
    seen = set()
    uniq_entries = []
    for e in all_entries:
        if e["rel"] in seen:
            continue
        seen.add(e["rel"])
        uniq_entries.append(e)
    all_entries = uniq_entries
    for e in all_entries:
        exists = os.path.isfile(e["abs"])
        rep.check(exists, f"manifest 引用文件不存在: {e['rel']} ({e['key']})")
        if not exists:
            rep.add(f"  MISSING {e['rel']}  ({e['key']})")
    rep.add(f"  引用文件 {len(seen)} 个，缺失 {sum(1 for e in all_entries if not os.path.isfile(e['abs']))} 个")

    # orphan check within group dirs
    orphans = []
    for g in groups:
        for dirpath, _dirnames, fnames in os.walk(os.path.join(ASSETS, g)):
            for fn in fnames:
                if not fn.endswith(".ogg"):
                    continue
                rel = os.path.relpath(os.path.join(dirpath, fn), ASSETS).replace("\\", "/")
                if rel not in seen:
                    orphans.append(rel)
    if group != "all":
        for dirpath, _d, fnames in os.walk(os.path.join(ASSETS, "shared")):
            for fn in fnames:
                if fn.endswith(".ogg"):
                    rel = os.path.relpath(os.path.join(dirpath, fn), ASSETS).replace("\\", "/")
                    if rel not in seen:
                        orphans.append(rel)
    rep.check(not orphans, f"存在未被 manifest 引用的文件: {orphans}", "WARN")
    for o in orphans:
        rep.add(f"  ORPHAN {o}")
    rep.add("")

    # ---- per file audio checks
    rep.add("2) 逐文件检查（ffprobe + 解码实测）")
    rep.add("-" * 78)
    hdr = (f"{'文件':44s} {'时长':>6s} {'sr':>6s} {'ch':>2s} "
           f"{'峰值':>7s} {'RMS':>7s} {'接缝':>6s} 判定")
    rep.add(hdr)
    total_dur = 0.0
    n_files = 0
    peaks = []
    loop_jumps = []
    rms_music = []
    rms_amb = []
    peak_sfx = []
    for e in all_entries:
        rel = e["rel"]
        p = e["abs"]
        if not os.path.isfile(p):
            continue
        info = S.ffprobe(p)
        n_files += 1
        dur = info.get("duration", 0.0)
        total_dur += dur
        sr = info.get("sample_rate", 0)
        ch = info.get("channels", 0)
        stats = decode_stats(p)
        cat = e["category"]
        stereo_expected = cat in ("music", "ambience")
        problems = []
        if info.get("codec") != "vorbis":
            problems.append("codec")
        if sr != 44100:
            problems.append(f"sr={sr}")
        if stereo_expected and ch != 2:
            problems.append(f"ch={ch}(应2)")
        if not stereo_expected and ch != 1:
            problems.append(f"ch={ch}(应1)")
        # duration expectation
        exp = MUSIC_DUR.get(rel) or AMB_DUR.get(rel) or LOOP_DUR.get(rel)
        if exp is not None:
            tol = 0.10 if rel in AMB_DUR else 0.03
            if abs(dur - exp) > tol:
                problems.append(f"dur={dur:.2f}/应{exp}")
        else:
            if dur > 12.0:
                problems.append(f"dur={dur:.2f}(过长)")
            if dur < 0.04:
                problems.append(f"dur={dur:.3f}(过短)")
        # peak: 所有文件 ≤ -1 dBFS
        if stats["peak"] > -1.0:
            problems.append(f"peak={stats['peak']:.2f}>-1")
        # loudness ranges
        if cat in ("music",):
            rms_music.append(stats["rms"])
            if not (-23.0 <= stats["rms"] <= -17.0):
                problems.append(f"rms={stats['rms']:.1f}")
        elif cat == "ambience":
            rms_amb.append(stats["rms"])
            if not (-23.5 <= stats["rms"] <= -17.0):
                problems.append(f"rms={stats['rms']:.1f}")
        elif cat == "sfx":
            peak_sfx.append(stats["peak"])
            if not (-3.6 <= stats["peak"] <= -0.9):
                problems.append(f"peak={stats['peak']:.2f}")
        # loops seam
        if e["loop"]:
            j = stats["jump_rel"]
            loop_jumps.append((rel, j))
            if j >= 6.0:
                problems.append(f"seam={j:.2f}")
        peaks.append(stats["peak"])
        status = "OK" if not problems else "FAIL " + ",".join(problems)
        rep.check(not problems, f"{rel}: {status}")
        rep.add(f"{rel:44s} {dur:6.2f} {sr:6d} {ch:2d} "
                f"{fmt_db(stats['peak'])} {fmt_db(stats['rms'])} "
                f"{stats['jump_rel'] if e['loop'] else 0.0:6.2f} {status}")
    rep.add("")

    # ---- summary
    rep.add("3) 汇总")
    rep.add("-" * 78)
    rep.add(f"  文件数: {n_files}，总时长: {total_dur:.1f}s "
            f"({total_dur/60:.1f} min)")
    rep.add(f"  峰值范围: {min(peaks):.2f} ~ {max(peaks):.2f} dBFS（上限 -1）")
    if rms_music:
        rep.add(f"  音乐 RMS: {min(rms_music):.2f} ~ {max(rms_music):.2f} dBFS")
    if rms_amb:
        rep.add(f"  环境 RMS: {min(rms_amb):.2f} ~ {max(rms_amb):.2f} dBFS")
    if peak_sfx:
        rep.add(f"  音效峰值: {min(peak_sfx):.2f} ~ {max(peak_sfx):.2f} dBFS")
    if loop_jumps:
        worst = max(loop_jumps, key=lambda t: t[1])
        rep.add(f"  循环接缝 jump_rel: 平均 {np.mean([j for _, j in loop_jumps]):.2f}，"
                f"最差 {worst[0]} = {worst[1]:.2f}（<6 视为听不出）")
    per_group = {}
    for e in all_entries:
        g = e["rel"].split("/")[0]
        per_group[g] = per_group.get(g, 0) + (1 if os.path.isfile(e["abs"]) else 0)
    rep.add("  分组文件数: " + "，".join(f"{k}={v}" for k, v in sorted(per_group.items())))
    rep.add("")

    # ---- verdict
    n_fail = len([f for f in rep.fails])
    rep.add("4) 结论")
    rep.add("-" * 78)
    if n_fail == 0:
        rep.add(f"  PASS — 全部 {n_files} 个文件通过格式/响度/循环接缝检查；"
                f"manifest 引用完整，无缺失。")
    else:
        rep.add(f"  FAIL — {n_fail} 项不达标：")
        for f in rep.fails[:80]:
            rep.add(f"    - {f}")
    if rep.warns:
        rep.add(f"  WARN {len(rep.warns)} 项：")
        for w in rep.warns[:40]:
            rep.add(f"    - {w}")
    rep.add("")

    os.makedirs(REPORT_DIR, exist_ok=True)
    out_txt = os.path.join(REPORT_DIR, "verify.txt")
    with open(out_txt, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(rep.lines))
    print("\n".join(rep.lines[-14:]))
    print(f"\n[verify] 报告写入 {os.path.relpath(out_txt, ROOT)}")

    if make_png:
        try:
            make_waveforms()
        except Exception as exc:  # noqa: BLE001
            print(f"[verify] waveform png skipped: {exc}")
    return 0 if n_fail == 0 else 1


# ----------------------------------------------------------- waveform -----
def _envelope(x, width):
    """把信号压成每列 min/max 包络。"""
    n = x.shape[-1]
    if n < width:
        x = np.pad(x, (0, width - n))
        n = width
    edges = np.linspace(0, n, width + 1).astype(int)
    lo = np.zeros(width)
    hi = np.zeros(width)
    for i in range(width):
        seg = x[edges[i]:max(edges[i] + 1, edges[i + 1])]
        lo[i] = seg.min()
        hi[i] = seg.max()
    return lo, hi


def make_waveforms():
    from PIL import Image, ImageDraw

    def sheet(files, out_png, cols=3, cell=(640, 200), title=""):
        rows = (len(files) + cols - 1) // cols
        W, H = cell[0] * cols, cell[1] * rows + 30
        img = Image.new("RGB", (W, H), (16, 16, 20))
        dr = ImageDraw.Draw(img)
        dr.text((8, 8), title, fill=(200, 190, 170))
        for idx, rel in enumerate(files):
            path = os.path.join(ASSETS, rel)
            if not os.path.exists(path):
                continue
            r, c = divmod(idx, cols)
            ox, oy = c * cell[0], r * cell[1] + 30
            dr.rectangle([ox + 4, oy + 4, ox + cell[0] - 4, oy + cell[1] - 4],
                         outline=(60, 60, 70))
            x = S.decode_f32(path).mean(axis=0)
            width = cell[0] - 24
            lo, hi = _envelope(x, width)
            mid = oy + (cell[1] - 8) // 2
            half = (cell[1] - 30) / 2
            for i in range(width):
                dr.line([(ox + 14 + i, mid - hi[i] * half),
                         (ox + 14 + i, mid - lo[i] * half)],
                        fill=(120, 200, 160))
            dr.line([(ox + 14, mid), (ox + 14 + width, mid)], fill=(60, 90, 80))
            dr.text((ox + 14, oy + cell[1] - 22), rel[:-4],
                    fill=(210, 200, 180))
        img.save(out_png)
        print(f"[verify] 波形图 {os.path.relpath(out_png, ROOT)}")

    music_loops = [rel for rel in MUSIC_DUR]
    amb_loops = [rel for rel in AMB_DUR]
    sheet(music_loops, os.path.join(REPORT_DIR, "waveforms_music.png"),
          cols=3, title="music loops (waveform envelope)")
    sheet(amb_loops, os.path.join(REPORT_DIR, "waveforms_ambience.png"),
          cols=3, title="ambience loops (waveform envelope)")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
