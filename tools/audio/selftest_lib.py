"""selftest_lib.py — 逐个调用 soundlib 发生器，检查 NaN/长度/峰值/耗时。"""
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import soundlib as L
import synth as S


def check(name, fn):
    rnd = np.random.default_rng(abs(hash(name)) % (2 ** 31))
    t0 = time.time()
    x = fn(rnd)
    dt = time.time() - t0
    if isinstance(x, tuple):
        arrs = x
    else:
        arrs = (x,)
    msgs = []
    for a in arrs:
        a = np.asarray(a, dtype=np.float64)
        bad = int(np.sum(~np.isfinite(a)))
        pk = 20 * np.log10(max(np.max(np.abs(a)), 1e-12))
        msgs.append(f"{a.shape} peak={pk:6.2f}dB nan={bad}")
    print(f"{name:22s} {dt*1000:7.1f}ms  " + " | ".join(msgs))


def main():
    rnd0 = np.random.default_rng(0)
    cases = {
        "wood": lambda r: L.wood(r, 0.3),
        "carpet": lambda r: L.carpet(r, 0.2),
        "tile": lambda r: L.tile(r, 0.28),
        "dirt": lambda r: L.dirt(r, 0.24),
        "grass": lambda r: L.grass(r, 0.26),
        "cloth": lambda r: L.cloth(r, 0.45),
        "paper": lambda r: L.paper(r, 0.55),
        "metal": lambda r: L.metal(r, 800, 0.8),
        "glass": lambda r: L.glass(r, 1400, 1.2),
        "thump": lambda r: L.thump(r, 0.5),
        "creak": lambda r: L.creak(r, 1.0, 260, 620),
        "scrape": lambda r: L.scrape(r, 1.0),
        "water_drop": lambda r: L.water_drop(r),
        "water_splash": lambda r: L.water_splash(r),
        "water_stream": lambda r: L.water_stream_loop(r, S.sec(10)),
        "breath_loop": lambda r: L.breath_loop(r, S.sec(8)),
        "whisper": lambda r: L.whisper(r, 1.8),
        "heartbeat": lambda r: L.heartbeat_loop(r, S.sec(10)),
        "hum": lambda r: L.hum(S.sec(5)),
        "crackle": lambda r: L.electric_crackle(r),
        "radio_static": lambda r: L.radio_static(r, S.sec(8)),
        "crow": lambda r: L.crow(r, 0.5),
        "wind": lambda r: L.wind_gust(r, 2.5),
        "match": lambda r: L.match_strike(r),
        "fire_crackle": lambda r: L.fire_crackle(r, S.sec(5)),
        "musicbox": lambda r: L.musicbox(r, S.hz(74), 2.4),
        "piano": lambda r: L.piano(r, S.hz(50), 3.0),
        "fm_bell": lambda r: L.fm_bell(r, S.hz(74), 2.5),
        "string_note": lambda r: L.string_note(r, S.hz(40), 4.0),
        "flute_note": lambda r: L.flute_note(r, S.hz(64), 3.0),
        "sub_drone": lambda r: L.sub_drone(r, S.sec(10), 40),
        "saw_drone": lambda r: L.saw_drone(r, S.sec(10), 60),
        "sweep_noise": lambda r: L.filter_sweep_noise(r, S.sec(5), 300, 3000),
    }
    for name, fn in cases.items():
        check(name, fn)


if __name__ == "__main__":
    main()
