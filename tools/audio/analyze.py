"""analyze.py — 客观听感分析（补充报告 reports/audio/analysis.txt）。

对每首音乐/每条环境输出：
- 全曲 RMS / 峰值 / 波峰因数；
- 各频段能量（sub <60, low 60-250, mid 250-2000, high 2000-8000, air >8000）；
- 频谱质心/平坦度（判断是「有音高的音乐」还是「噪声」）；
- 逐秒 RMS 起伏（动态范围），确认有结构而不是平铺；
- 立体声相关系数（环境声的空间宽度）。
"""
from __future__ import annotations

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import synth as S  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
ASSETS = os.path.join(ROOT, "assets", "audio")
REPORT = os.path.join(ROOT, "reports", "audio", "analysis.txt")

BANDS = (("sub", 0, 60), ("low", 60, 250), ("mid", 250, 2000),
         ("high", 2000, 8000), ("air", 8000, 20000))


def band_energies(x, sr=S.SR):
    """x: (ch,n) -> 每个频段的 RMS dB（两声道平均）。"""
    out = {}
    for name, lo, hi in BANDS:
        y = S.filt(x, ("hp", max(lo, 20), 2), ("lp", hi, 2), circular=True)
        out[name] = S.rms_db(y)
    return out


def spec_stats(x, sr=S.SR):
    m = x.mean(axis=0)
    m = m - m.mean()
    w = np.hanning(m.size)
    X = np.abs(np.fft.rfft(m * w))
    f = np.fft.rfftfreq(m.size, 1.0 / sr)
    p = X ** 2
    p_sum = max(p.sum(), 1e-20)
    centroid = float((f * p).sum() / p_sum)
    flatness = float(np.exp(np.mean(np.log(p + 1e-20))) / (np.mean(p) + 1e-20))
    return centroid, flatness


def window_rms(x, win=1.0):
    n = int(win * S.SR)
    ch = x.shape[0]
    m = x.reshape(ch, -1, n).mean(axis=1) if x.shape[1] >= n else x
    k = x.shape[1] // n
    if k < 2:
        return np.array([S.rms_db(x)])
    seg = x[:, :k * n].reshape(ch, k, n)
    vals = [S.rms_db(seg[:, i, :]) for i in range(k)]
    return np.array(vals)


def main():
    files = []
    for g in ("door", "mirror", "nightroad"):
        for sub in ("music", "ambience"):
            d = os.path.join(ASSETS, g, sub)
            if not os.path.isdir(d):
                continue
            for fn in sorted(os.listdir(d)):
                if fn.endswith(".ogg"):
                    files.append(f"{g}/{sub}/{fn}")
    lines = ["《三更》音频客观听感分析（补充 verify.txt）", "=" * 100, ""]
    hdr = (f"{'文件':40s} {'RMS':>7s} {'峰':>7s} {'sub':>7s} {'low':>7s} "
           f"{'mid':>7s} {'high':>7s} {'air':>7s} {'质心Hz':>8s} {'平坦':>6s} "
           f"{'起伏dB':>7s} {'L/R相关':>8s}")
    lines.append(hdr)
    lines.append("-" * 100)
    for rel in files:
        p = os.path.join(ASSETS, rel)
        if not os.path.exists(p):
            continue
        x = S.decode_f32(p)
        be = band_energies(x)
        c, flat = spec_stats(x)
        wr = window_rms(x)
        dyn = float(np.max(wr) - np.min(wr)) if wr.size > 1 else 0.0
        if x.shape[0] == 2:
            corr = float(np.corrcoef(x[0], x[1])[0, 1])
        else:
            corr = 1.0
        lines.append(
            f"{rel:40s} {S.rms_db(x):7.2f} {S.peak_db(x):7.2f} "
            f"{be['sub']:7.2f} {be['low']:7.2f} {be['mid']:7.2f} "
            f"{be['high']:7.2f} {be['air']:7.2f} {c:8.0f} {flat:6.3f} "
            f"{dyn:7.2f} {corr:8.3f}")
    text = "\n".join(lines) + "\n"
    with open(REPORT, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print(text)
    print(f"[analyze] {os.path.relpath(REPORT, ROOT)}")


if __name__ == "__main__":
    main()
