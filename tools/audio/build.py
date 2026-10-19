"""build.py — 合成全部音频资产并写出 manifest（可重复运行，固定 seed）。

用法（在 horror-demos/tools/audio 下）:
  python build.py door        # shared UI + 《门后》全部 + 写 4 个 manifest
  python build.py mirror      # 《镜中》
  python build.py nightroad   # 《夜路》
  python build.py all         # 全部
  python build.py manifests   # 只重写 manifest

输出目录: horror-demos/assets/audio/{shared,door,mirror,nightroad}/
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import ambience  # noqa: E402
import music  # noqa: E402
import sfx  # noqa: E402
import synth as S  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
ASSETS = os.path.join(ROOT, "assets", "audio")

FILES = {}
FILES.update(music.ALL)
FILES.update(ambience.ALL)
FILES.update(sfx.ALL)

GROUPS = {
    "shared": [k for k in FILES if k.startswith("shared/")],
    "door": [k for k in FILES if k.startswith("door/")],
    "mirror": [k for k in FILES if k.startswith("mirror/")],
    "nightroad": [k for k in FILES if k.startswith("nightroad/")],
}


# ---------------------------------------------------------- manifest ------
def mfile(path, volume, loop=None, fade=None):
    d = {"file": path, "volume": volume}
    if loop is not None:
        d["loop"] = loop
    if fade is not None:
        d["fade"] = fade
    return d


def mfiles(paths, volume, loop=None):
    d = {"files": paths, "volume": volume}
    if loop is not None:
        d["loop"] = loop
    return d


def _ui_entries():
    return {
        "hover": mfiles(["../shared/ui_hover.ogg"], 0.35),
        "click": mfiles(["../shared/ui_click.ogg"], 0.45),
        "back": mfiles(["../shared/ui_back.ogg"], 0.40),
        "confirm": mfiles(["../shared/ui_confirm.ogg"], 0.50),
    }


def _music(main, tension, ending):
    return {
        "main": mfile("music/main.ogg", main[0], loop=True, fade=main[1]),
        "tension": mfile("music/tension.ogg", tension[0], loop=True, fade=tension[1]),
        "ending": mfile("music/ending.ogg", ending[0], loop=False, fade=ending[1]),
    }


DOOR_MANIFEST = {
    "id": "door",
    "music": _music((0.50, 4.0), (0.45, 2.0), (0.55, 2.0)),
    "ambience": {
        "corridor": mfile("ambience/corridor_hum.ogg", 0.55, loop=True),
        "roomTone": mfile("ambience/room_tone.ogg", 0.50, loop=True),
        "rainWindow": mfile("ambience/rain_window.ogg", 0.45, loop=True),
        "tvStatic": mfile("ambience/tv_static.ogg", 0.35, loop=True),
    },
    "sfx": {
        "stepWood": mfiles([f"sfx/step_wood_{i}.ogg" for i in range(1, 5)], 0.55),
        "stepCarpet": mfiles([f"sfx/step_carpet_{i}.ogg" for i in range(1, 4)], 0.50),
        "doorOpen": mfiles(["sfx/door_open.ogg"], 0.90),
        "doorClose": mfiles(["sfx/door_close.ogg"], 0.90),
        "doorLocked": mfiles(["sfx/door_locked.ogg"], 0.85),
        "doorUnlock": mfiles(["sfx/door_unlock.ogg"], 0.85),
        "pickupLetter": mfiles([f"sfx/pickup_letter_{i}.ogg" for i in range(1, 3)], 0.70),
        "pickupBattery": mfiles(["sfx/pickup_battery.ogg"], 0.70),
        "flashlightClick": mfiles(["sfx/flashlight_click.ogg"], 0.60),
        "batteryLow": mfiles(["sfx/battery_low.ogg"], 0.50),
        "lightSwitch": mfiles(["sfx/light_switch.ogg"], 0.70),
        "lightFlicker": mfiles([f"sfx/light_flicker_{i}.ogg" for i in range(1, 3)], 0.60),
        "paperRustle": mfiles([f"sfx/paper_rustle_{i}.ogg" for i in range(1, 3)], 0.55),
        "clockTick": mfiles(["sfx/clock_tick.ogg"], 0.40, loop=True),
        "heartbeat": mfiles(["sfx/heartbeat.ogg"], 0.65, loop=True),
        "breath": mfiles(["sfx/breath.ogg"], 0.50, loop=True),
        "whisper": mfiles([f"sfx/whisper_{i}.ogg" for i in range(1, 4)], 0.55),
        "stinger": mfiles([f"sfx/stinger_{i}.ogg" for i in range(1, 3)], 0.80),
        "blackout": mfiles(["sfx/blackout.ogg"], 0.80),
        "entityBreath": mfiles(["sfx/entity_breath.ogg"], 0.65, loop=True),
        "entityStep": mfiles([f"sfx/entity_step_{i}.ogg" for i in range(1, 3)], 0.80),
        "entityCatch": mfiles(["sfx/entity_catch.ogg"], 0.90),
    },
    "ui": _ui_entries(),
}

MIRROR_MANIFEST = {
    "id": "mirror",
    "music": _music((0.50, 4.0), (0.45, 2.0), (0.55, 2.0)),
    "ambience": {
        "fluorescent": mfile("ambience/fluorescent_buzz.ogg", 0.55, loop=True),
        "waterDrip": mfile("ambience/water_drip.ogg", 0.55, loop=True),
        "distantWater": mfile("ambience/distant_water.ogg", 0.45, loop=True),
        "steamHiss": mfile("ambience/steam_hiss.ogg", 0.40, loop=True),
    },
    "sfx": {
        "stepTile": mfiles([f"sfx/step_tile_{i}.ogg" for i in range(1, 5)], 0.55),
        "towelPick": mfiles(["sfx/towel_pick.ogg"], 0.60),
        "valveTurn": mfiles([f"sfx/valve_turn_{i}.ogg" for i in range(1, 3)], 0.80),
        "waterStream": mfiles(["sfx/water_stream.ogg"], 0.55, loop=True),
        "waterSplash": mfiles(["sfx/water_splash.ogg"], 0.80),
        "switchClick": mfiles(["sfx/switch_click.ogg"], 0.70),
        "lightFlicker": mfiles([f"sfx/light_flicker_{i}.ogg" for i in range(1, 3)], 0.60),
        "lockerCreak": mfiles([f"sfx/locker_creak_{i}.ogg" for i in range(1, 3)], 0.70),
        "stoolDrag": mfiles(["sfx/stool_drag.ogg"], 0.70),
        "radioOn": mfiles(["sfx/radio_on.ogg"], 0.70),
        "radioStatic": mfiles(["sfx/radio_static.ogg"], 0.45, loop=True),
        "clockTick": mfiles(["sfx/clock_tick.ogg"], 0.40, loop=True),
        "mirrorTouch": mfiles(["sfx/mirror_touch.ogg"], 0.70),
        "glassCrack": mfiles(["sfx/glass_crack.ogg"], 0.95),
        "doppelStep": mfiles([f"sfx/doppel_step_{i}.ogg" for i in range(1, 4)], 0.70),
        "doppelBreath": mfiles(["sfx/doppel_breath.ogg"], 0.65, loop=True),
        "heartbeat": mfiles(["sfx/heartbeat.ogg"], 0.65, loop=True),
        "breath": mfiles(["sfx/breath.ogg"], 0.50, loop=True),
        "whisper": mfiles([f"sfx/whisper_{i}.ogg" for i in range(1, 4)], 0.55),
        "stinger": mfiles([f"sfx/stinger_{i}.ogg" for i in range(1, 3)], 0.80),
        "blackout": mfiles(["sfx/blackout.ogg"], 0.80),
    },
    "ui": _ui_entries(),
}

NIGHTROAD_MANIFEST = {
    "id": "nightroad",
    "music": _music((0.50, 4.0), (0.45, 2.0), (0.55, 2.0)),
    "ambience": {
        "windField": mfile("ambience/wind_field.ogg", 0.55, loop=True),
        "insects": mfile("ambience/insects.ogg", 0.45, loop=True),
        "nightRoomTone": mfile("ambience/night_room_tone.ogg", 0.55, loop=True),
        "distantDog": mfile("ambience/distant_dog.ogg", 0.40, loop=True),
    },
    "sfx": {
        "stepDirt": mfiles([f"sfx/step_dirt_{i}.ogg" for i in range(1, 5)], 0.55),
        "stepGrass": mfiles([f"sfx/step_grass_{i}.ogg" for i in range(1, 4)], 0.50),
        "matchStrike": mfiles([f"sfx/match_strike_{i}.ogg" for i in range(1, 3)], 0.80),
        "lanternLight": mfiles([f"sfx/lantern_light_{i}.ogg" for i in range(1, 3)], 0.85),
        "paperFlutter": mfiles([f"sfx/paper_flutter_{i}.ogg" for i in range(1, 3)], 0.55),
        "entityRustle": mfiles([f"sfx/entity_rustle_{i}.ogg" for i in range(1, 4)], 0.70),
        "entityCatch": mfiles(["sfx/entity_catch.ogg"], 0.90),
        "shrineBell": mfiles(["sfx/shrine_bell.ogg"], 0.90),
        "metalBell": mfiles(["sfx/metal_bell.ogg"], 0.55),
        "windGust": mfiles([f"sfx/wind_gust_{i}.ogg" for i in range(1, 3)], 0.65),
        "crow": mfiles(["sfx/crow.ogg"], 0.65),
        "heartbeat": mfiles(["sfx/heartbeat.ogg"], 0.65, loop=True),
        "breath": mfiles(["sfx/breath.ogg"], 0.50, loop=True),
        "whisper": mfiles([f"sfx/whisper_{i}.ogg" for i in range(1, 4)], 0.55),
        "stinger": mfiles([f"sfx/stinger_{i}.ogg" for i in range(1, 3)], 0.80),
        "blackout": mfiles(["sfx/blackout.ogg"], 0.80),
    },
    "ui": _ui_entries(),
}

SHARED_MANIFEST = {
    "id": "shared",
    "ui": {
        "hover": mfiles(["ui_hover.ogg"], 0.35),
        "click": mfiles(["ui_click.ogg"], 0.45),
        "back": mfiles(["ui_back.ogg"], 0.40),
        "confirm": mfiles(["ui_confirm.ogg"], 0.50),
    },
}

MANIFESTS = {
    "door/manifest.json": DOOR_MANIFEST,
    "mirror/manifest.json": MIRROR_MANIFEST,
    "nightroad/manifest.json": NIGHTROAD_MANIFEST,
    "shared/manifest.json": SHARED_MANIFEST,
}


def write_manifests():
    for rel, obj in MANIFESTS.items():
        path = os.path.join(ASSETS, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"manifest  {rel}")


# ------------------------------------------------------------- build ------
def quality_for(rel):
    if rel.startswith("shared/"):
        return 4
    if "/music/" in rel:
        return 5
    return 4


def _is_single(rel):
    """单声道音效/UI（音乐与环境是立体声）。"""
    return not ("/music/" in rel or "/ambience/" in rel)


def encode_adaptive(dst, data, q, target_peak_db):
    """编码后按实测解码峰值做一次增益校正。

    Vorbis 对极短瞬态会有 0.5~1.6 dB 的峰值损失，直接编码会让解码峰值
    落到 -3 dBFS 以下（不满足 SFX 峰值 -3~-1 规格）。这里先编码再解码测量，
    调整约两次让解码峰值落在目标附近；同时把源峰值限制在 -1.2 dBFS 以内，
    避免削波/过冲。
    """
    data = np.asarray(data, dtype=np.float64)
    src_cap = float(S.db2lin(-1.2))
    p_src = S.peak_db(data)
    if p_src > -1.2:
        data = data * float(S.db2lin(-1.2 - p_src))
    S.encode_ogg(dst, data, q)
    for _ in range(2):
        p = S.peak_db(S.decode_f32(dst))
        if abs(p - target_peak_db) < 0.25:
            break
        g = float(S.db2lin(target_peak_db - p))
        cand = data * g
        cp = S.peak_db(cand)
        if cp > -1.2:
            cand = cand * float(S.db2lin(-1.2 - cp))
        data = cand
        S.encode_ogg(dst, data, q)
    return S.ffprobe(dst)


def build_files(rels, force=False):
    done = 0
    total = 0.0
    t_start = time.time()
    for rel in rels:
        fn = FILES.get(rel)
        if fn is None:
            raise KeyError(f"no generator for {rel}")
        q = quality_for(rel)
        dst = os.path.join(ASSETS, rel)
        t0 = time.time()
        data = fn()
        dur = np_dur(data)
        total += dur
        if _is_single(rel):
            target = -4.5 if rel.startswith("shared/") else -2.0
            info = encode_adaptive(dst, data, q, target)
        else:
            S.encode_ogg(dst, data, q)
            info = S.ffprobe(dst)
        dt = time.time() - t0
        print(f"  {rel:44s} {dur:6.2f}s q{q} enc={dt:5.2f}s "
              f"ch={info.get('channels')} sr={info.get('sample_rate')}")
        done += 1
    print(f"[build] {done} files, audio {total:.1f}s, wall {time.time()-t_start:.1f}s")
    return done, total


def np_dur(data):
    n = data.shape[-1]
    return n / float(S.SR)


def main(argv):
    args = list(argv[1:])
    match = None
    keep = []
    for a in args:
        if a.startswith("--match="):
            match = [s for s in a.split("=", 1)[1].split(",") if s]
        else:
            keep.append(a)
    mode = keep[0] if keep else "all"
    if mode == "manifests":
        write_manifests()
        return 0
    if mode == "all":
        groups = ["shared", "door", "mirror", "nightroad"]
    elif mode in GROUPS:
        groups = ["shared", "door", "mirror", "nightroad"] if mode == "shared" else ["shared", mode]
    else:
        print(__doc__)
        return 2
    os.makedirs(ASSETS, exist_ok=True)
    total_files = 0
    total_dur = 0.0
    for g in groups:
        rels = GROUPS[g]
        if match:
            rels = [r for r in rels if any(m in r for m in match)]
        if not rels:
            continue
        print(f"[build] {g}: {len(rels)} files")
        n, d = build_files(rels)
        total_files += n
        total_dur += d
    write_manifests()
    print(f"[build] TOTAL {total_files} files, {total_dur:.1f}s audio")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
