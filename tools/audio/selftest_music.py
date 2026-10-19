"""selftest_music.py — 渲染全部 9 首音乐，打印耗时/长度/电平/循环接缝，保存预览 OGG。"""
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import music
import synth as S

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "..", "..", "reports", "audio", "preview")
LOOPS = {"main", "tension"}


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    os.makedirs(OUT, exist_ok=True)
    total_s = 0.0
    for path, fn in music.ALL.items():
        if only and only not in path:
            continue
        t0 = time.time()
        x = fn()
        dt = time.time() - t0
        n = x.shape[1]
        dur = n / S.SR
        total_s += dur
        j, sl = S.seam_metrics(x)
        name = path.replace("/", "_")
        out = os.path.join(OUT, name)
        S.encode_ogg(out, x, 5)
        info = S.ffprobe(out)
        print(f"{path:28s} {dur:6.1f}s render={dt:6.2f}s peak={S.peak_db(x):6.2f} "
              f"rms={S.rms_db(x):6.2f} seam={j:7.4f}/{sl:7.4f} "
              f"ogg={info.get('duration',0):6.2f}s {os.path.getsize(out)//1024}KB")
    print(f"total music dur={total_s:.1f}s")


if __name__ == "__main__":
    main()
