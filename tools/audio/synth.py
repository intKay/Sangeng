"""synth.py — 《三更》原创程序化音频 DSP 核心（只依赖 numpy）。

设计原则
--------
1. 所有循环素材采用「周期化构造」：音高频率锁到 1/L 的整数倍；
   噪声在频域做环形（circular）滤波；音符尾音用 add_wrapped 绕回开头；
   混响用环形卷积。因此首尾严格连续，数学上就是周期信号，无需交叉淡化。
2. 一次性音效使用线性滤波 / 线性卷积，末尾做短淡出。
3. 全部随机数由显式传入的 numpy Generator 驱动，固定 seed 可完全复现。
"""
from __future__ import annotations

import math
import os
import subprocess

import numpy as np

SR = 44100
TWOPI = 2.0 * math.pi


# ---------------------------------------------------------------- basics ---
def sec(d):
    """秒 -> 采样点数。"""
    return int(round(float(d) * SR))


def tarr(n):
    return np.arange(int(n), dtype=np.float64) / SR


def midi_hz(m):
    return 440.0 * 2.0 ** ((np.asarray(m, dtype=np.float64) - 69.0) / 12.0)


def hz(m):
    return midi_hz(m)


def db2lin(v):
    return 10.0 ** (np.asarray(v, dtype=np.float64) / 20.0)


def lin2db(v):
    return 20.0 * np.log10(np.maximum(np.asarray(v, dtype=np.float64), 1e-12))


def rms(x):
    return float(np.sqrt(np.mean(np.square(np.asarray(x, dtype=np.float64)))))


def rms_db(x):
    return float(lin2db(rms(x)))


def peak_db(x):
    return float(lin2db(np.max(np.abs(np.asarray(x, dtype=np.float64)))))


# ------------------------------------------------------------ filtering ---
def _g_lp(f, fc, order=2):
    return 1.0 / np.sqrt(1.0 + (f / max(float(fc), 1e-9)) ** (2 * order))


def _g_hp(f, fc, order=2):
    return 1.0 / np.sqrt(1.0 + (max(float(fc), 1e-9) / np.maximum(f, 1e-9)) ** (2 * order))


def _g_bp(f, lo, hi, order=2):
    return _g_lp(f, hi, order) * _g_hp(f, lo, order)


def _g_res(f, fc, q):
    r = f / max(float(fc), 1e-9)
    return 1.0 / np.sqrt(1.0 + (q * (r - 1.0 / np.maximum(r, 1e-12))) ** 2)


def _filter_gain(f, specs):
    g = np.ones_like(f)
    for spec in specs:
        kind = spec[0]
        if kind == "lp":
            g *= _g_lp(f, spec[1], spec[2] if len(spec) > 2 else 2)
        elif kind == "hp":
            g *= _g_hp(f, spec[1], spec[2] if len(spec) > 2 else 2)
        elif kind == "bp":
            g *= _g_bp(f, spec[1], spec[2], spec[3] if len(spec) > 3 else 2)
        elif kind == "res":
            g *= _g_res(f, spec[1], spec[2])
        else:  # pragma: no cover
            raise ValueError(f"unknown filter spec {spec!r}")
    return g


def filt(x, *specs, circular=True, pad=8192):
    """零相位幅度滤波。specs: ('lp',fc[,order]) ('hp',..) ('bp',lo,hi[,order]) ('res',fc,q)。

    循环素材必须 circular=True（结果严格周期）；一次性素材 circular=False。
    """
    x = np.asarray(x, dtype=np.float64)
    if x.ndim == 2:
        return np.stack([filt(ch, *specs, circular=circular, pad=pad) for ch in x])
    n = x.size
    if circular or n < 2 * pad:
        f = np.fft.rfftfreq(n, 1.0 / SR)
        return np.fft.irfft(np.fft.rfft(x) * _filter_gain(f, specs), n)
    xp = np.concatenate([np.zeros(pad), x, np.zeros(pad)])
    f = np.fft.rfftfreq(xp.size, 1.0 / SR)
    y = np.fft.irfft(np.fft.rfft(xp) * _filter_gain(f, specs), xp.size)
    return y[pad:pad + n]


# ---------------------------------------------------------------- noise ---
def white(n, rnd):
    return rnd.standard_normal(int(n))


def shaped_noise(n, rnd, gain_fn, circular=True, pad=8192):
    """频谱整形噪声；返回 RMS=1 的信号。circular=True 时严格周期。"""
    n = int(n)
    if circular or n < 2 * pad:
        f = np.fft.rfftfreq(n, 1.0 / SR)
        y = np.fft.irfft(np.fft.rfft(white(n, rnd)) * gain_fn(f), n)
    else:
        m = n + 2 * pad
        f = np.fft.rfftfreq(m, 1.0 / SR)
        y = np.fft.irfft(np.fft.rfft(white(m, rnd)) * gain_fn(f), m)[pad:pad + n]
    return y / max(rms(y), 1e-12)


def pink(n, rnd, circular=True):
    return shaped_noise(n, rnd, lambda f: 1.0 / np.sqrt(np.maximum(f, 20.0)), circular)


def brown(n, rnd, circular=True):
    return shaped_noise(n, rnd, lambda f: 1.0 / np.maximum(f, 20.0), circular)


def noise_filtered(n, rnd, *specs, circular=True):
    """滤波白噪声，RMS=1。"""
    y = filt(white(n, rnd), *specs, circular=circular)
    return y / max(rms(y), 1e-12)


# ------------------------------------------------------------ envelopes ---
def smoothstep(x):
    x = np.clip(np.asarray(x, dtype=np.float64), 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


def ar_env(n, attack=0.01, release=0.05):
    """前后平滑包络（smoothstep），中间为 1。"""
    n = int(n)
    e = np.ones(n)
    na = min(n, max(1, sec(attack)))
    nr = min(n, max(1, sec(release)))
    e[:na] = smoothstep(np.linspace(0.0, 1.0, na, endpoint=False))
    e[n - nr:] *= smoothstep(np.linspace(1.0, 0.0, nr, endpoint=False))
    return e


def perc_env(n, attack=0.004, tau=0.2):
    """打击包络：快起指数落。t=0 时为 0，避免起始爆音。"""
    t = tarr(n)
    a = 1.0 - np.exp(-t / max(float(attack), 1e-5))
    return a * np.exp(-t / max(float(tau), 1e-5))


def swell_env(n, attack=0.5, release=0.8, shape=1.6):
    """慢起慢落（反向/吸气感）。"""
    n = int(n)
    e = np.ones(n)
    na = min(n, max(2, sec(attack)))
    nr = min(n, max(2, sec(release)))
    e[:na] = smoothstep(np.linspace(0.0, 1.0, na, endpoint=False)) ** shape
    e[n - nr:] *= smoothstep(np.linspace(1.0, 0.0, nr, endpoint=False))
    return e


# ------------------------------------------------------- phase / tones ----
def phase_of(freq, n, phase0=0.0):
    """频率可随时间变化的相位积分（freq 标量或长度 n 的数组）。"""
    n = int(n)
    f = np.broadcast_to(np.asarray(freq, dtype=np.float64), (n,))
    return TWOPI * np.cumsum(f) / SR + phase0


def lock_freq(f, n, sr=SR):
    """把频率锁到循环长度 n 的整数倍频率上，保证严格周期（无缝循环）。"""
    n = int(n)
    k = max(1, int(round(float(f) * n / sr)))
    return k * sr / float(n)


def lock_rate(rate, n, sr=SR):
    """LFO 速率锁相（至少 1 个周期）。"""
    return lock_freq(rate, n, sr)


def modal(n, freqs, amps=None, taus=None, rnd=None, detune=0.0, phase0=0.0,
          random_phase=False):
    """模态叠加：sum a_i * exp(-t/tau_i) * sin(2pi f_i t + p_i)，起音在 0。"""
    n = int(n)
    t = tarr(n)
    out = np.zeros(n)
    freqs = np.asarray(freqs, dtype=np.float64)
    if amps is None:
        amps = np.linspace(1.0, 0.3, len(freqs))
    amps = np.asarray(amps, dtype=np.float64)
    if taus is None:
        taus = np.full(len(freqs), 0.2)
    taus = np.asarray(taus, dtype=np.float64)
    for i, f0 in enumerate(freqs):
        f = float(f0)
        if rnd is not None and detune:
            f *= 1.0 + detune * (rnd.random() * 2.0 - 1.0)
        ph = phase0
        if random_phase and rnd is not None:
            ph += rnd.random() * TWOPI
        out += amps[i] * np.exp(-t / max(taus[i], 1e-5)) * np.sin(TWOPI * f * t + ph)
    return out


# ---------------------------------------------------- placement helpers ---
def _promote(buf, sig):
    sig = np.asarray(sig, dtype=np.float64)
    if sig.ndim == 1 and buf.ndim == 2:
        sig = np.broadcast_to(sig, (buf.shape[0], sig.size))
    return sig


def add_at(buf, start, sig, gain=1.0):
    """线性叠放（越界截断）。"""
    n = buf.shape[-1]
    s = int(round(start))
    sig = _promote(buf, sig)
    L = sig.shape[-1]
    a, b = max(0, s), min(n, s + L)
    if b > a:
        buf[..., a:b] += gain * sig[..., a - s:b - s]


def add_wrapped(buf, start, sig, gain=1.0):
    """环形叠放：尾音绕回开头，保证 loop 首尾无缝。"""
    n = buf.shape[-1]
    s = int(round(start)) % n
    sig = _promote(buf, sig)
    L = sig.shape[-1]
    k, pos = 0, s
    while k < L:
        m = min(n - pos, L - k)
        if m <= 0:
            break
        buf[..., pos:pos + m] += gain * sig[..., k:k + m]
        k += m
        pos = 0


def sparse_positions(n, mean_gap, rnd, min_gap=0.05, start_jitter=True):
    """稀疏事件位置（采样点），指数间隔。"""
    n = int(n)
    out = []
    t = rnd.random() * mean_gap if start_jitter else 0.0
    total = n / SR
    while t < total:
        out.append(sec(t))
        t += max(min_gap, rnd.exponential(mean_gap))
    return out


# ------------------------------------------------------------- stereo -----
def pan(mono, p=0.0):
    """等功率声像：p=-1 左，+1 右。"""
    a = (float(np.clip(p, -1.0, 1.0)) + 1.0) * math.pi / 4.0
    mono = np.asarray(mono, dtype=np.float64)
    return np.stack([mono * math.cos(a), mono * math.sin(a)])


def widen(x, amount=0.35):
    """M/S 展宽（只作用于立体声）。"""
    x = np.asarray(x, dtype=np.float64)
    if x.ndim != 2:
        return x
    m = 0.5 * (x[0] + x[1])
    s = 0.5 * (x[0] - x[1]) * (1.0 + amount)
    return np.stack([m + s, m - s])


def wobble(x, rate, depth_s=0.0008, circular=True):
    """磁带抖晃：周期性变速读取（depth_s 为最大时移，秒）。"""
    x = np.asarray(x, dtype=np.float64)
    n = x.shape[-1]
    t = tarr(n)
    pos = np.arange(n, dtype=np.float64) + depth_s * SR * np.sin(TWOPI * rate * t)
    if circular:
        pos = np.mod(pos, n)
        return np.interp(pos, np.arange(n), x, period=n)
    return np.interp(pos, np.arange(n), x)


def resample(x, ratio):
    """变采样率（ratio>1 变短变高）。"""
    x = np.asarray(x, dtype=np.float64)
    n = x.shape[-1]
    m = max(1, int(round(n / ratio)))
    idx = np.linspace(0.0, n - 1.0, m)
    y = np.interp(idx, np.arange(n), x)
    return y


def pitch_variant(x, semitones, length=None):
    """变速变调，再裁/补到指定长度（保持时长）。"""
    y = resample(x, 2.0 ** (float(semitones) / 12.0))
    n = len(y) if length is None else int(length)
    if len(y) >= n:
        return y[:n]
    return np.pad(y, (0, n - len(y)))


# ------------------------------------------------------ convolution ------
def fftconv(a, b):
    """线性卷积（截断到 len(a)+len(b)-1）。"""
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    n = a.size + b.size - 1
    N = 1 << int(max(1, n - 1).bit_length())
    return np.fft.irfft(np.fft.rfft(a, N) * np.fft.rfft(b, N), N)[:n]


def circ_conv(a, b):
    """环形卷积（循环素材用；len(b) <= len(a)）。"""
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    n = a.size
    bb = np.zeros(n)
    m = min(n, b.size)
    bb[:m] = b[:m]
    return np.fft.irfft(np.fft.rfft(a) * np.fft.rfft(bb), n)


def make_ir(seed, dur=2.0, decay=0.5, predelay=0.012, lp=6500, hp=60,
            taps=14, tap_spread=0.10, stereo=True, bright=1.0):
    """程序化房间脉冲响应（噪声 + 早期反射）。每个声道单位能量。"""
    rnd = np.random.default_rng(seed)
    n = sec(dur)
    t = tarr(n)
    pre = min(n - 1, sec(predelay))
    chans = []
    for ch in range(2 if stereo else 1):
        ir = rnd.standard_normal(n) * np.exp(-t / max(decay, 1e-3))
        if pre > 0:
            ir = np.concatenate([np.zeros(pre), ir])[:n]
        for _ in range(taps):
            pos = pre + sec(rnd.random() * tap_spread)
            if pos < n:
                sgn = 1.0 if rnd.random() < 0.5 else -1.0
                amp = 0.55 * math.exp(-rnd.random() * 2.5)
                if ch == 1:
                    amp *= 0.65 + 0.35 * rnd.random()
                ir[pos] += sgn * amp
        ir = filt(ir, ("lp", lp, 2), ("hp", hp, 2), circular=False, pad=4096)
        ir /= max(math.sqrt(float(np.sum(ir * ir))), 1e-9)
        chans.append(ir)
    return np.stack(chans) if stereo else chans[0]


def reverb(x, ir, wet=0.3, dry=1.0, circular=False):
    """卷积混响。x 为 (n,) 或 (2,n)；ir 为 (m,) 或 (2,m)。
    mono 输入返回 mono（用 IR 的第一声道），stereo 输入返回 stereo。"""
    x = np.asarray(x, dtype=np.float64)
    ir = np.asarray(ir, dtype=np.float64)
    if ir.ndim == 1:
        ir2 = np.stack([ir, ir])
    elif ir.shape[0] == 1:
        ir2 = np.stack([ir[0], ir[0]])
    else:
        ir2 = ir
    if x.ndim == 1:
        h = ir2[0]
        w = circ_conv(x, h) if circular else fftconv(x, h)[:x.size]
        return dry * x + wet * w
    n = x.shape[1]
    out = dry * x
    for ch in range(2):
        h = ir2[ch]
        w = circ_conv(x[ch], h) if circular else fftconv(x[ch], h)[:n]
        out[ch] += wet * w
    return out


# ------------------------------------------------------ level/utility -----
def dc_block(x):
    x = np.asarray(x, dtype=np.float64)
    return x - np.mean(x, axis=-1, keepdims=True)


def normalize_rms(x, target_db):
    x = np.asarray(x, dtype=np.float64)
    g = float(db2lin(target_db)) / max(rms(x), 1e-12)
    return x * g


def soft_limit(x, ceiling_db=-1.0, knee_db=3.0):
    """无记忆软限幅（因此不会破坏循环连续性）。"""
    x = np.asarray(x, dtype=np.float64)
    ceil = float(db2lin(ceiling_db))
    knee = ceil * float(db2lin(-abs(knee_db)))
    a = np.abs(x)
    over = a > knee
    if np.any(over):
        y = x.copy()
        span = max(ceil - knee, 1e-9)
        y[over] = np.sign(x[over]) * (knee + span * np.tanh((a[over] - knee) / span))
        x = y
    return x


def fade_edges(x, fin=0.002, fout=0.02):
    return np.asarray(x, dtype=np.float64) * ar_env(np.asarray(x).shape[-1], fin, fout)


def finalize_loop(x, target_rms_db=-20.0, ceiling_db=-1.5):
    """循环素材最终处理：去直流 -> RMS 归一 -> 软限幅 -> 截断。"""
    x = dc_block(x)
    x = normalize_rms(x, target_rms_db)
    x = soft_limit(x, ceiling_db)
    return np.clip(x, -1.0, 1.0)


def finalize_oneshot(x, peak_target=-2.2, fin=0.0015, fout=0.02, ceiling_db=-1.8):
    """一次性音效：去直流 -> 峰值归一 -> 软限幅 -> 边缘淡入淡出。"""
    x = dc_block(np.asarray(x, dtype=np.float64))
    p = peak_db(x)
    if p > -90.0:
        x = x * float(db2lin(peak_target - p))
    x = soft_limit(x, ceiling_db)
    if fout > 0:
        x = fade_edges(x, fin, fout)
    return np.clip(x, -1.0, 1.0)


def seam_metrics(x):
    """循环接缝指标（相对普通相邻样本差）：
    jump_rel = |x0-x[-1]| / rms(diff)；< ~4 表示与正常波形无区别（听不出接缝）。
    """
    x = np.asarray(x, dtype=np.float64)
    if x.ndim == 2:
        x = x.T.reshape(-1)
    if x.size < 8:
        return 0.0, 0.0
    diff = np.diff(x)
    rd = max(float(np.sqrt(np.mean(diff ** 2))), 1e-9)
    jump = abs(float(x[0]) - float(x[-1])) / rd
    slope = abs(float(x[1] - x[0]) - float(x[-1] - x[-2])) / rd
    return round(jump, 3), round(slope, 3)


# ------------------------------------------------------------- encode -----
def encode_ogg(path, data, quality=5):
    """把 float 波形（(n,) 或 (2,n)）用 ffmpeg/libvorbis 编码为 OGG。"""
    data = np.asarray(data, dtype=np.float32)
    if data.ndim == 1:
        ch = 1
        raw = np.ascontiguousarray(data).tobytes()
    elif data.shape[0] == 2:
        ch = 2
        raw = np.ascontiguousarray(data.T).tobytes()
    else:
        raise ValueError(f"unsupported channel layout {data.shape}")
    d = os.path.dirname(os.path.abspath(path))
    if d:
        os.makedirs(d, exist_ok=True)
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "f32le", "-ar", str(SR), "-ac", str(ch), "-i", "-",
        "-c:a", "libvorbis", "-q:a", str(int(quality)), str(path),
    ]
    proc = subprocess.run(cmd, input=raw, capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed for {path}: {proc.stderr.decode('utf-8', 'replace')}")


def decode_f32(path):
    """用 ffmpeg 把音频解码为 float32 的 numpy 数组（用于自检）。返回 (ch,n)。"""
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(path),
           "-f", "f32le", "-acodec", "pcm_f32le", "-"]
    proc = subprocess.run(cmd, capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(f"decode failed {path}")
    a = np.frombuffer(proc.stdout, dtype=np.float32).astype(np.float64)
    probe = ffprobe(path)
    ch = int(probe.get("channels", 1) or 1)
    return a.reshape(-1, ch).T if ch > 1 else a.reshape(1, -1)


def ffprobe(path):
    """返回 dict: duration/sample_rate/channels/codec。"""
    import json
    cmd = ["ffprobe", "-v", "error", "-show_entries",
           "stream=codec_name,sample_rate,channels,duration:format=duration",
           "-of", "json", str(path)]
    proc = subprocess.run(cmd, capture_output=True)
    if proc.returncode != 0:
        return {}
    info = json.loads(proc.stdout.decode("utf-8", "replace"))
    streams = info.get("streams") or [{}]
    s = streams[0]
    dur = s.get("duration") or (info.get("format") or {}).get("duration")
    return {
        "codec": s.get("codec_name", ""),
        "sample_rate": int(s.get("sample_rate", 0) or 0),
        "channels": int(s.get("channels", 0) or 0),
        "duration": float(dur) if dur else 0.0,
    }
