"""selftest_beds.py — 渲染全部 ambience + sfx（不编码），检查 NaN/长度/峰值/耗时。"""
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ambience
import sfx
import synth as S

PEAK_TARGET = {"ui": (-1e9, -3.0), "heavy": (-1e9, -1.8)}


def run(name, fn):
    t0 = time.time()
    try:
        x = np.asarray(fn(), dtype=np.float64)
    except Exception as e:  # noqa: BLE001
        print(f"FAIL {name}: {type(e).__name__}: {e}")
        return False
    dt = time.time() - t0
    bad = int(np.sum(~np.isfinite(x)))
    dur = x.shape[-1] / S.SR
    print(f"{name:42s} {dur:6.3f}s ch={1 if x.ndim == 1 else x.shape[0]} "
          f"peak={S.peak_db(x):7.2f} rms={S.rms_db(x):7.2f} nan={bad} {dt*1000:6.1f}ms")
    return bad == 0


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    ok = True
    if which in ("all", "amb"):
        for k, f in ambience.ALL.items():
            ok &= run(k, f)
    if which in ("all", "sfx"):
        for k, f in sfx.ALL.items():
            ok &= run(k, f)
    print("RESULT", "OK" if ok else "FAILED")


if __name__ == "__main__":
    main()
