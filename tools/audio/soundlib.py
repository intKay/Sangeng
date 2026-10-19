"""soundlib.py — 材质 / 乐器 / 纹理发生器（供 music / ambience / sfx 使用）。

全部函数返回 float64 numpy 数组（mono，除非注明 stereo），
随机性全部来自传入的 numpy Generator，固定 seed 可复现。

命名约定
- 循环素材函数名带 _loop 或以 n 为长度参数，并要求频率/速率 lock 到 1/L；
- 一次性素材返回自然衰减的波形（不含房间混响，由调用方叠加房间）。
"""
from __future__ import annotations

import math

import numpy as np

import synth as S
from synth import SR, sec, tarr, TWOPI


def _norm(x, peak=1.0):
    """按峰值归一（内部小工具，避免各层电平失控）。"""
    m = float(np.max(np.abs(x)))
    return x * (peak / m) if m > 1e-12 else x


def _slow_noise(n, rnd, cutoff=4.0, circular=True):
    """慢速随机曲线，归一化到 [-1,1]，用于抖动/漂移。"""
    y = S.filt(S.white(n, rnd), ("lp", cutoff, 1), circular=circular)
    m = float(np.max(np.abs(y)))
    return y / m if m > 1e-12 else y


# ============================================================ 材质 ======
def wood(rnd, dur=0.30, f0=None, weight=1.0, hardness=1.0, bright=1.0):
    """木头：低模 + 体感低频 + 起音脆点。"""
    n = sec(dur)
    f0 = f0 if f0 is not None else 120.0 + rnd.random() * 90.0
    ratios = np.array([1.0, 2.27, 3.91, 5.62, 7.60, 9.80])
    amps = np.array([1.0, 0.62, 0.38, 0.2, 0.12, 0.07])
    amps[2:] *= hardness
    taus = np.array([0.20, 0.13, 0.075, 0.045, 0.03, 0.02]) * (0.7 + 0.6 * weight)
    body = S.modal(n, f0 * ratios, amps, taus, rnd=rnd, detune=0.012)
    thud = S.filt(S.white(n, rnd), ("lp", 320, 2)) * S.perc_env(n, 0.002, 0.035)
    click = S.filt(S.white(n, rnd), ("hp", 2400, 2)) * S.perc_env(n, 0.0004, 0.004)
    x = body * 0.8 + thud * (0.55 * weight) + click * (0.22 * bright)
    return S.dc_block(x)


def carpet(rnd, dur=0.20, weight=1.0):
    """地毯/软底：闷、无高频、短。"""
    n = sec(dur)
    x = S.filt(S.white(n, rnd), ("lp", 420, 2)) * S.perc_env(n, 0.004, 0.045)
    x += S.filt(S.white(n, rnd), ("lp", 160, 2)) * S.perc_env(n, 0.003, 0.09) * 0.8
    x += S.modal(n, [70, 105], [0.5, 0.25], [0.05, 0.035], detune=0.03) * 0.5
    return x * (0.8 + 0.4 * weight)


def tile(rnd, dur=0.28, f0=None, weight=1.0):
    """瓷砖：硬、亮、短促的反射。"""
    n = sec(dur)
    f0 = f0 if f0 is not None else 150.0 + rnd.random() * 70.0
    mod = S.modal(n, [f0, f0 * 2.4, 1700 + rnd.random() * 900,
                      3300 + rnd.random() * 1200, 5100],
                  [1.0, 0.3, 0.45, 0.25, 0.12],
                  [0.06, 0.04, 0.03, 0.02, 0.012], rnd=rnd, detune=0.02)
    click = S.filt(S.white(n, rnd), ("hp", 3500, 2)) * S.perc_env(n, 0.0004, 0.004)
    slap = S.filt(S.white(n, rnd), ("bp", 900, 5000, 2)) * S.perc_env(n, 0.001, 0.018)
    return (mod * 0.8 + click * 0.5 + slap * 0.28) * weight


def dirt(rnd, dur=0.24, weight=1.0):
    """土路/碎石：颗粒噪声 + 低频落步。"""
    n = sec(dur)
    x = np.zeros(n)
    ng = 16 + int(rnd.random() * 12)
    for _ in range(ng):
        p = sec(rnd.random() * 0.10)
        ln = sec(0.002 + rnd.random() * 0.008)
        g = S.filt(S.white(ln, rnd), ("hp", 1100 + rnd.random() * 2200, 2),
                   circular=False)
        S.add_at(x, p, g * (0.3 + rnd.random() * 0.7))
    x = x * 0.6
    x += S.modal(n, [85, 140, 230], [1.0, 0.45, 0.2],
                 [0.06, 0.04, 0.025], rnd=rnd, detune=0.04) * 0.7
    x += S.filt(S.white(n, rnd), ("lp", 900, 2)) * S.perc_env(n, 0.002, 0.03) * 0.4
    return x * weight


def grass(rnd, dur=0.26, weight=1.0):
    """草地：高频沙沙 + 细碎颗粒。"""
    n = sec(dur)
    bed = S.filt(S.white(n, rnd), ("bp", 1300, 7200, 2), circular=False)
    bed *= S.perc_env(n, 0.015, 0.075)
    x = bed
    for _ in range(9):
        p = sec(rnd.random() * 0.11)
        ln = sec(0.001 + rnd.random() * 0.004)
        g = S.filt(S.white(ln, rnd), ("hp", 3000, 2), circular=False)
        S.add_at(x, p, g * (0.2 + rnd.random() * 0.6))
    x += S.filt(S.white(n, rnd), ("lp", 500, 2)) * S.perc_env(n, 0.005, 0.035) * 0.3
    return x * weight


def cloth(rnd, dur=0.45, density=45, weight=1.0):
    """布料摩擦：中频、颗粒密集、无明显音高。"""
    n = sec(dur)
    x = np.zeros(n)
    count = int(density)
    pos = np.sort(rnd.random(count)) * n * 0.85
    for p in pos:
        ln = sec(0.003 + rnd.random() * 0.010)
        lo = 700 + rnd.random() * 1500
        hi = lo * (1.8 + rnd.random() * 2.0)
        g = S.filt(S.white(ln, rnd), ("bp", lo, min(hi, 9000), 2), circular=False)
        S.add_at(x, int(p), g * (0.2 + rnd.random() * 0.8) ** 1.4)
    x *= 0.5
    x += S.filt(S.white(n, rnd), ("bp", 500, 4000, 2), circular=False) * \
        S.perc_env(n, 0.01, dur * 0.3) * 0.18
    return x * weight


def paper(rnd, dur=0.55, density=26, bright=1.0, weight=1.0, swells=2):
    """纸：颗粒级褶皱 + 低频揉纸包络。"""
    n = sec(dur)
    x = np.zeros(n)
    # 颗粒层
    count = int(density)
    pos = np.sort(rnd.random(count)) * n * 0.9
    for p in pos:
        ln = sec(0.0015 + rnd.random() * 0.006)
        lo = 1100 + rnd.random() * 2600
        hi = min(11000, lo * (2.0 + rnd.random() * 3.0))
        g = S.filt(S.white(ln, rnd), ("bp", lo, hi, 2), circular=False)
        S.add_at(x, int(p), g * (0.15 + rnd.random() * 0.85) ** 1.5)
    x *= 0.55
    # 大面摩擦层（随揉纸起伏）
    bed = S.filt(S.white(n, rnd), ("bp", 1600, 8000, 2), circular=False)
    env = np.zeros(n)
    for k in range(swells):
        c = (k + 0.5) / max(1, swells) + (rnd.random() - 0.5) * 0.12
        w = 0.55 / max(1, swells) + 0.18
        env += np.exp(-0.5 * ((np.linspace(0, 1, n) - c) / w) ** 2)
    env = np.clip(env, 0, None)
    env = env / max(np.max(env), 1e-9)
    x += bed * env * 0.35 * bright
    # 低频揉搓
    low = S.filt(S.white(n, rnd), ("bp", 250, 900, 2), circular=False)
    x += low * env * 0.3
    x = S.dc_block(x)
    m = float(np.max(np.abs(x)))
    return x / m * weight if m > 1e-12 else x


def metal(rnd, f0=800.0, dur=0.8, ratios=None, taus=None, amps=None,
          bright=1.0, strike=0.55):
    """金属：非谐模态 + 短促激励。"""
    n = sec(dur)
    ratios = np.array(ratios if ratios is not None else
                      [1.0, 1.43, 1.86, 2.41, 2.93, 3.67, 4.51])
    if amps is None:
        amps = np.array([1.0, 0.7, 0.5, 0.34, 0.24, 0.15, 0.09])
    if taus is None:
        taus = np.array([0.35, 0.25, 0.18, 0.12, 0.08, 0.055, 0.04])
    x = S.modal(n, f0 * ratios, amps, taus, rnd=rnd, detune=0.02)
    hit = S.filt(S.white(n, rnd), ("bp", f0 * 1.5, min(14000, f0 * 12), 2),
                 circular=False) * S.perc_env(n, 0.0004, 0.006) * strike * bright
    return S.dc_block(x + hit)


def glass(rnd, f0=1200.0, dur=1.2, bright=1.0, strike=0.6, decay=1.0):
    n = sec(dur)
    ratios = np.array([1.0, 1.52, 2.17, 2.83, 3.61, 4.72, 6.03])
    amps = np.array([1.0, 0.6, 0.42, 0.28, 0.18, 0.1, 0.05]) * bright
    taus = np.array([0.55, 0.4, 0.3, 0.22, 0.16, 0.11, 0.08]) * decay
    x = S.modal(n, f0 * ratios, amps, taus, rnd=rnd, detune=0.015)
    hit = S.filt(S.white(n, rnd), ("hp", 4000, 2), circular=False) * \
        S.perc_env(n, 0.0003, 0.004) * strike
    return x + hit


def thump(rnd, dur=0.5, f0=55.0, tau=0.08, body=1.0, click=0.25):
    """低频撞击（心跳/脚步/门撞的公共底层）。"""
    n = sec(dur)
    x = S.modal(n, [f0, f0 * 1.85, f0 * 2.9], [1.0, 0.42, 0.18],
                [tau, tau * 0.7, tau * 0.5], rnd=rnd, detune=0.02)
    x += S.filt(S.white(n, rnd), ("lp", 160, 2)) * S.perc_env(n, 0.001, tau * 0.9) * body
    x += S.filt(S.white(n, rnd), ("hp", 1800, 2)) * \
        S.perc_env(n, 0.0003, 0.003) * click
    return S.dc_block(x)


def creak(rnd, dur=1.0, f_lo=250.0, f_hi=650.0, spike=(0.006, 0.028),
          metal=0.0, rough=1.0, shape="rise"):
    """木头/金属的吱呀声：stick-slip 脉冲激励 + 移动共振 + 摩擦底噪。"""
    n = sec(dur)
    t = tarr(n)
    # 中心频率轨迹
    if shape == "rise":
        base = f_lo * (f_hi / f_lo) ** np.clip(t / max(dur, 1e-6), 0, 1)
    elif shape == "fall":
        base = f_hi * (f_lo / f_hi) ** np.clip(t / max(dur, 1e-6), 0, 1)
    else:
        base = f_lo + (f_hi - f_lo) * (0.5 - 0.5 * np.cos(np.pi * np.clip(t / dur, 0, 1)))
    jit = _slow_noise(n, rnd, 5.0, circular=True)
    f_traj = base * (1.0 + 0.035 * jit * rough)
    # stick-slip 事件
    x = np.zeros(n)
    tt = 0.0
    while tt < dur - 0.006:
        p = sec(tt)
        f = float(f_traj[min(n - 1, p)])
        tau = spike[0] + rnd.random() * (spike[1] - spike[0])
        amp = (0.35 + rnd.random() * 0.65) ** 1.5
        m = min(n - p, sec(tau * 8))
        if m > 8:
            ratios = [f, f * 2.02, f * (3.1 if metal else 1.99), f * 1.51]
            burst = S.modal(m, ratios,
                            [1.0, 0.32, 0.18 + 0.2 * metal, 0.12],
                            [tau, tau * 0.6, tau * 0.4, tau * 0.3],
                            detune=0.015)
            S.add_at(x, p, burst, amp)
        tt += 0.004 + rnd.exponential(max(0.006, 0.018 / max(rough, 0.1)))
    # 摩擦底噪（空气感）
    air = S.filt(S.white(n, rnd), ("bp", f_lo * 0.7, min(9000, f_hi * 2.6), 2),
                 circular=False)
    air *= S.ar_env(n, dur * 0.12, dur * 0.22) * 0.10 * (0.5 + 0.5 * rough)
    x = x + air
    # 低频木应力
    x += S.modal(n, [f_lo * 0.3, f_lo * 0.45], [0.4, 0.2],
                 [0.25, 0.18], detune=0.03) * 0.5
    x *= S.ar_env(n, 0.01, dur * 0.12)
    return S.dc_block(x)


def scrape(rnd, dur=1.0, lo=900.0, hi=3500.0, metal=0.5, rate=18.0):
    """金属/木头的持续摩擦（不规则的摩擦颗粒）。"""
    n = sec(dur)
    bed = S.filt(S.white(n, rnd), ("bp", lo, hi, 2), circular=False)
    am = _slow_noise(n, rnd, rate, circular=False)
    am = 0.25 + 0.75 * (0.5 + 0.5 * am) ** 1.6
    x = bed * am
    # 刮擦的尖锐颗粒
    for _ in range(int(6 + 10 * metal)):
        p = sec(rnd.random() * dur * 0.95)
        ln = sec(0.004 + rnd.random() * 0.012)
        g = S.filt(S.white(ln, rnd), ("bp", lo * 1.5, min(16000, hi * 2.5), 2),
                   circular=False)
        S.add_at(x, p, g * (0.15 + rnd.random() * 0.5))
    x *= S.ar_env(n, dur * 0.06, dur * 0.1)
    return S.dc_block(x)


# ============================================================ 水 ========
def water_drop(rnd, f_lo=520.0, f_hi=1500.0, dur=0.22, tail=0.10):
    """水滴：气泡共振频率上滑 + 极短 click。"""
    n = sec(dur + tail)
    t = tarr(n)
    rise = np.clip(t / max(dur, 1e-6), 0, 1)
    f = f_lo * (f_hi / f_lo) ** rise
    ph = S.phase_of(f, n)
    tone = np.sin(ph) * S.perc_env(n, 0.0015, dur * 0.55)
    tone += 0.25 * np.sin(2.0 * ph) * S.perc_env(n, 0.001, dur * 0.25)
    click = S.filt(S.white(n, rnd), ("hp", 3200, 2), circular=False) * \
        S.perc_env(n, 0.0003, 0.0025)
    return S.dc_block(tone * 0.7 + click * 0.35)


def water_splash(rnd, dur=0.7, strength=1.0):
    n = sec(dur)
    x = S.filt(S.white(n, rnd), ("bp", 400, 7000, 2), circular=False) * \
        S.perc_env(n, 0.003, 0.075)
    x *= 0.6
    for _ in range(9):
        p = sec(0.01 + rnd.random() * 0.28)
        d = water_drop(rnd, 620 + rnd.random() * 500, 1500 + rnd.random() * 900,
                       0.10, 0.06)
        S.add_at(x, p, d * (0.2 + rnd.random() * 0.6))
    return x * strength


def water_stream_loop(rnd, n):
    """水流循环：三层带通噪声 + 气泡。"""
    n = int(n)
    t = tarr(n)
    x = np.zeros(n)
    for lo, hi, amp, rate, dep in (
            (260, 1300, 1.00, 0.37, 0.33),
            (1200, 4600, 0.42, 0.73, 0.40),
            (70, 420, 0.55, 0.19, 0.28)):
        b = S.noise_filtered(n, rnd, ("bp", lo, hi, 2), circular=True)
        lfo = np.sin(TWOPI * S.lock_rate(rate, n) * t + rnd.random() * TWOPI)
        x += b * amp * (1.0 - dep + dep * (0.5 + 0.5 * lfo))
    for p in S.sparse_positions(n, 0.42, rnd, 0.08):
        d = water_drop(rnd, 380 + rnd.random() * 450, 900 + rnd.random() * 700,
                       0.09, 0.05)
        S.add_wrapped(x, p, d, 0.22)
    return x


def breath_loop(rnd, n, cycle=4.0, deep=1.0):
    """呼吸循环（无音高，用噪声+共振峰）。cycle 秒一次呼吸。"""
    n = int(n)
    cycles = max(1, int(round((n / SR) / cycle)))
    cyc = n / float(cycles)
    x = np.zeros(n)
    for c in range(cycles):
        start = int(round(c * cyc))
        inl = int(cyc * 0.40)
        outl = int(cyc * 0.48)
        # 吸气：高频气声上行
        inh = S.filt(S.white(inl, rnd), ("bp", 600, 4200, 2), circular=False)
        inh = S.filt(inh, ("res", 900, 3), ("res", 2400, 4), circular=False)
        inh *= S.swell_env(inl, inl / SR * 0.75, inl / SR * 0.25, 1.5)
        # 呼气：低频、更长
        exh = S.filt(S.white(outl, rnd), ("bp", 220, 1900, 2), circular=False)
        exh = S.filt(exh, ("res", 480, 3), ("res", 1400, 4), circular=False)
        exh *= S.swell_env(outl, outl / SR * 0.12, outl / SR * 0.8, 1.1)
        S.add_wrapped(x, start, inh * 0.85 * deep)
        S.add_wrapped(x, start + inl + int(cyc * 0.06), exh * deep)
    # 极低的身体共鸣
    x += S.filt(S.white(n, rnd), ("lp", 120, 2), circular=True) * 0.12 * deep
    return x


def whisper(rnd, dur=1.8, syllables=4, sib=0.5, pitch=1.0, wet=0.0):
    """低语：共振峰噪声 + 音节包络 + 擦音，无可辨识词句。"""
    n = sec(dur)
    x = np.zeros(n)
    cursor = 0.03
    for _ in range(int(syllables)):
        sdur = min(0.16 + rnd.random() * 0.15, dur - cursor - 0.04)
        if sdur <= 0.05:
            break
        ln = sec(sdur)
        base = S.filt(S.white(ln, rnd), ("bp", 200, 3000, 2), circular=False)
        f1 = (380 + rnd.random() * 420) * pitch
        f2 = (1050 + rnd.random() * 800) * pitch
        form = S.filt(base, ("res", f1, 5), ("res", f2, 7),
                      ("lp", 5200), circular=False)
        form = _norm(form)
        env = S.swell_env(ln, sdur * 0.22, sdur * 0.32, 1.2)
        S.add_at(x, sec(cursor), form * env * 0.55)
        if rnd.random() < 0.75:
            sn = sec(0.035 + rnd.random() * 0.05)
            sibn = S.filt(S.white(sn, rnd), ("hp", 4200 + rnd.random() * 2600, 2),
                          circular=False)
            S.add_at(x, sec(cursor), sibn * S.perc_env(sn, 0.002, 0.018) * 0.5 * sib)
        cursor += sdur + 0.025 + rnd.random() * 0.16
    # 气口
    x += S.filt(S.white(n, rnd), ("hp", 3000, 2), circular=False) * 0.03
    return S.dc_block(x)


def heartbeat_loop(rnd, n, bpm=60.0, strength=1.0, jitter=0.004):
    """心跳循环（lub-dub，低频体感）。"""
    n = int(n)
    beats = max(1, int(round((n / SR) * bpm / 60.0)))
    step = n / float(beats)
    x = np.zeros(n)
    for i in range(beats):
        pos = int(round(i * step + rnd.uniform(-jitter, jitter) * SR))
        lub = thump(rnd, 0.55, 48 + rnd.random() * 5, 0.075, body=0.9, click=0.1)
        S.add_wrapped(x, pos, lub, strength)
        dub = thump(rnd, 0.5, 42 + rnd.random() * 4, 0.06, body=0.7, click=0.05)
        S.add_wrapped(x, pos + sec(0.27 + rnd.random() * 0.02), dub, 0.6 * strength)
    # 极低频底
    t = tarr(n)
    x += np.sin(TWOPI * S.lock_freq(37.0, n) * t) * 0.10 * strength
    return x


# ============================================================ 电/风/其他 ==
def hum(n, f0=100.0, harmonics=(1.0, 0.5, 0.34, 0.2, 0.11, 0.06), wobble=0.006,
        rnd=None, locked=True):
    """日光灯/变压器嗡鸣（循环素材，频率锁相）。"""
    n = int(n)
    rnd = rnd or np.random.default_rng(0)
    t = tarr(n)
    x = np.zeros(n)
    for i, a in enumerate(harmonics):
        f = f0 * (i + 1)
        if locked:
            f = S.lock_freq(f, n)
        x += a * np.sin(TWOPI * f * t + rnd.random() * TWOPI)
    if wobble:
        rate = S.lock_rate(0.7, n) if locked else 0.7
        x *= 1.0 - wobble + wobble * 0.5 * (1.0 + np.sin(TWOPI * rate * t + 0.4))
    return x


def electric_crackle(rnd, dur=0.12, amp=1.0):
    """电流噼啪（极短）。"""
    n = sec(dur)
    x = np.zeros(n)
    for _ in range(3 + int(rnd.random() * 4)):
        p = sec(rnd.random() * dur * 0.7)
        ln = sec(0.0015 + rnd.random() * 0.005)
        g = S.filt(S.white(ln, rnd), ("hp", 2200 + rnd.random() * 2000, 2),
                   circular=False)
        S.add_at(x, p, g * (0.3 + rnd.random() * 0.7))
    x = S.filt(x, ("res", 3100, 2), ("hp", 1500), circular=False)
    return x * amp


def radio_static(rnd, n, circular=True, hum_amp=0.07):
    """收音机雪花噪声（循环素材）。"""
    n = int(n)
    x = S.noise_filtered(n, rnd, ("bp", 240, 6800, 2), circular=circular)
    am = _slow_noise(n, rnd, 18.0, circular=circular)
    x = x * (0.86 + 0.14 * am)
    x += S.noise_filtered(n, rnd, ("bp", 3800, 9500, 2), circular=circular) * 0.18
    t = tarr(n)
    x += np.sin(TWOPI * S.lock_freq(50.0, n) * t) * hum_amp
    return x


def crow(rnd, dur=0.5):
    """乌鸦单声「嘎」：锯齿 + 共振峰 + 快速下滑。"""
    n = sec(dur)
    t = tarr(n)
    f = 540.0 * (1.0 - 0.30 * np.clip(t / dur, 0, 1))
    f *= 1.0 + 0.02 * _slow_noise(n, rnd, 40.0, circular=False)
    ph = S.phase_of(f, n, rnd.random() * TWOPI)
    raw = 2.0 * ((ph / TWOPI) % 1.0) - 1.0
    raw = S.filt(raw, ("res", 1250, 2.5), ("res", 2600, 3.0),
                 ("bp", 350, 5200), circular=False)
    env = S.ar_env(n, 0.008, dur * 0.3) * (0.72 + 0.28 * np.sin(TWOPI * 38 * t))
    return S.dc_block(raw * env)


def wind_gust(rnd, dur=2.5, strength=1.0, tone=1.0, circular=False):
    """风阵：低频带移动 + 哨音。"""
    n = sec(dur)
    t = tarr(n)
    w = 0.5 - 0.5 * np.cos(TWOPI * np.clip(t / dur, 0, 1))
    lo = S.filt(S.white(n, rnd), ("bp", 70, 380, 2), circular=circular)
    hi = S.filt(S.white(n, rnd), ("bp", 480, 2400, 2), circular=circular)
    x = lo * (1.0 - 0.55 * w) + hi * w * 0.75
    env = S.swell_env(n, dur * 0.45, dur * 0.38, 1.25) if not circular else np.ones(n)
    fw = 520.0 + 260.0 * np.sin(TWOPI * 0.43 * t + 1.1) + 90.0 * _slow_noise(n, rnd, 2.0, circular=False)
    whistle = np.sin(S.phase_of(np.maximum(fw, 60.0), n)) * 0.10 * tone
    return (x * 0.9 + whistle) * env * strength


def match_strike(rnd, dur=0.9):
    """划火柴：摩擦 -> 点燃 -> 火苗。"""
    n = sec(dur)
    x = np.zeros(n)
    ln = sec(0.10)
    scratch = S.filt(S.white(ln, rnd), ("hp", 1500, 2), circular=False)
    scratch *= S.perc_env(ln, 0.004, 0.025)
    S.add_at(x, 0, scratch * 0.9)
    for _ in range(12):
        p = sec(rnd.random() * 0.09)
        gl = sec(0.0015 + rnd.random() * 0.004)
        g = S.filt(S.white(gl, rnd), ("hp", 3500, 2), circular=False)
        S.add_at(x, p, g * (0.2 + rnd.random() * 0.6))
    fl = sec(dur * 0.82)
    fizz = S.filt(S.white(fl, rnd), ("bp", 1400, 9000, 2), circular=False)
    am = 0.45 + 0.55 * (0.5 + 0.5 * _slow_noise(fl, rnd, 70.0, circular=False))
    fizz *= am * S.perc_env(fl, 0.02, dur * 0.30) * 0.42
    S.add_at(x, sec(0.10), fizz)
    # 火苗的低频呼呼
    low = S.filt(S.white(fl, rnd), ("lp", 300, 2), circular=False)
    S.add_at(x, sec(0.12), low * S.swell_env(fl, 0.08, dur * 0.4) * 0.18)
    return S.dc_block(x)


def fire_crackle(rnd, n, density=3.0):
    """火堆/蜡烛的细碎爆裂（循环）。"""
    n = int(n)
    x = np.zeros(n)
    for p in S.sparse_positions(n, 1.0 / max(density, 0.1), rnd, 0.03):
        ln = sec(0.002 + rnd.random() * 0.006)
        g = S.filt(S.white(ln, rnd), ("bp", 900, 7000, 2), circular=False)
        S.add_wrapped(x, p, g * (0.2 + rnd.random() * 0.8))
    return x + S.noise_filtered(n, rnd, ("lp", 220, 2), circular=True) * 0.05


# ============================================================ 乐器 ======
def musicbox(rnd, hz, dur=2.4, vel=1.0, bright=1.0):
    """八音盒/音叉：非谐泛音 + 亮起音。"""
    n = sec(dur)
    ratios = np.array([1.0, 2.003, 3.02, 4.11, 5.43, 6.79, 8.16])
    amps = np.array([1.0, 0.5, 0.28, 0.15, 0.08, 0.045, 0.025])
    amps[3:] *= bright
    taus = np.array([0.85, 0.5, 0.27, 0.15, 0.10, 0.065, 0.045]) * \
        (0.75 + 0.5 * rnd.random())
    det = (rnd.random() * 2.0 - 1.0) * 0.0018
    x = S.modal(n, hz * (1.0 + det) * ratios, amps * vel, taus, rnd=rnd, detune=0.006)
    click = S.filt(S.white(n, rnd), ("hp", 3200, 2), circular=False) * \
        S.perc_env(n, 0.0003, 0.0045)
    x += click * 0.13 * vel * bright
    return S.dc_block(x)


def piano(rnd, hz, dur=3.0, vel=1.0, bright=0.55):
    """钢琴（加法合成，带非谐性）；反向使用可做 reverse piano。"""
    n = sec(dur)
    t = tarr(n)
    x = np.zeros(n)
    B = 0.0004
    K = int(min(20, 5200.0 / max(hz, 40.0)))
    for k in range(1, K + 1):
        f = hz * k * math.sqrt(1.0 + B * k * k)
        if f > 16000:
            break
        a = (1.0 / k ** 1.35) * math.exp(-k * (1.0 - bright) * 0.30)
        tau = (1.9 / (1.0 + 0.55 * k)) * (0.8 + 0.4 * rnd.random())
        x += a * np.exp(-t / tau) * np.sin(TWOPI * f * t + rnd.random() * TWOPI)
    hammer = S.filt(S.white(n, rnd), ("lp", max(800.0, hz * 6), 2), circular=False) * \
        S.perc_env(n, 0.0008, 0.010)
    x = x * (1.0 - np.exp(-t / 0.002)) + hammer * 0.16
    return S.dc_block(x * vel)


def fm_bell(rnd, hz, dur=2.5, ratio=3.5, index=3.0, vel=1.0, index_tau=0.35):
    """FM 钟声：玻璃/金属质感，长衰减。"""
    n = sec(dur)
    t = tarr(n)
    I = index * np.exp(-t / max(index_tau, 1e-3))
    mod = np.sin(TWOPI * hz * ratio * t + rnd.random() * TWOPI)
    sig = np.sin(TWOPI * hz * t + I * mod)
    sig += 0.22 * np.sin(TWOPI * hz * 1.004 * t + 0.7)
    env = (1.0 - np.exp(-t / 0.0025)) * np.exp(-t / (dur * 0.42))
    strike = S.filt(S.white(n, rnd), ("hp", 3500, 2), circular=False) * \
        S.perc_env(n, 0.0003, 0.004)
    return S.dc_block((sig * env + strike * 0.10) * vel)


def string_note(rnd, hz, dur, vel=1.0, attack=0.5, release=0.6,
                vib_rate=None, vib_cents=8.0, bright=1.0):
    """弓弦：加法锯齿 + 颤音 + 弓噪。"""
    n = sec(dur)
    t = tarr(n)
    if vib_rate is None:
        vib_rate = 0.16 + rnd.random() * 0.22
    f = hz * (1.0 + vib_cents / 1200.0 * np.sin(TWOPI * vib_rate * t)) * \
        (1.0 + 0.0008 * np.sin(TWOPI * 0.05 * t + 0.3))
    ph = S.phase_of(f, n, rnd.random() * TWOPI)
    K = int(min(16, 4400.0 / max(hz, 30.0)))
    x = np.zeros(n)
    for k in range(1, K + 1):
        x += (1.0 / k ** 1.15) * np.sin(k * ph + rnd.random() * 0.6)
    env = S.ar_env(n, attack, release)
    bow = S.filt(S.white(n, rnd), ("bp", max(150.0, hz * 0.7),
                                    min(7000.0, hz * 7.0), 2), circular=False) * \
        S.perc_env(n, max(0.02, attack * 0.5), max(0.08, dur * 0.35)) * 0.05
    x = x * env + bow
    x = S.filt(x, ("lp", 2300.0 * bright, 2), circular=False)
    return S.dc_block(x * vel)


def flute_note(rnd, hz, dur, vel=1.0, attack=0.22, release=0.45,
               vib_rate=4.2, vib_cents=7.0, breath=0.4):
    """气声笛：正弦 + 气声 + 颤音。"""
    n = sec(dur)
    t = tarr(n)
    vib = np.sin(TWOPI * vib_rate * t) * np.clip(t / 0.7, 0, 1)
    f = hz * (1.0 + vib_cents / 1200.0 * vib) * \
        (1.0 + 0.004 * np.clip(1.0 - t / 0.15, 0, 1))
    ph = S.phase_of(f, n, rnd.random() * TWOPI)
    tone = np.sin(ph) + 0.16 * np.sin(2.0 * ph) + 0.04 * np.sin(3.0 * ph)
    env = S.ar_env(n, attack, release)
    br = S.filt(S.white(n, rnd), ("bp", hz * 0.6, min(9000.0, hz * 3.4), 2),
                circular=False) * env * breath
    return S.dc_block((tone * env + br * 0.55) * vel)


def sub_drone(rnd, n, hz, amp=1.0, harmonics=(1.0, 0.34, 0.14, 0.06),
              beat=0.35, drift=0.4):
    """循环低频 drone（频率锁相，严格周期）。"""
    n = int(n)
    t = tarr(n)
    x = np.zeros(n)
    for i, a in enumerate(harmonics):
        f = S.lock_freq(hz * (i + 1), n)
        x += a * np.sin(TWOPI * f * t + rnd.random() * TWOPI)
    # 两台轻微失谐的振荡器形成拍频
    if beat > 0:
        f2 = S.lock_freq(hz * (1.0 + 0.0025), n)
        x += beat * np.sin(TWOPI * f2 * t + rnd.random() * TWOPI)
    if drift > 0:
        rate = S.lock_rate(0.055, n)
        x *= 1.0 - drift * 0.5 + drift * 0.5 * np.sin(TWOPI * rate * t + 1.2)
    return x * amp


def saw_drone(rnd, n, hz, amp=1.0, voices=3, detune_cents=7.0, lp=1200.0,
              vib_rate=0.13, vib_cents=5.0):
    """循环弦乐 drone（多声部失谐 + 慢颤音，频率锁相，严格周期）。"""
    n = int(n)
    t = tarr(n)
    x = np.zeros(n)
    for v in range(int(voices)):
        cents = detune_cents * (v - (voices - 1) / 2.0)
        ratio = 2.0 ** (cents / 1200.0)
        rate = S.lock_rate(vib_rate * (0.7 + 0.3 * v), n)
        vib = vib_cents / 1200.0 * np.sin(TWOPI * rate * t + v * 1.7)
        base = S.lock_freq(hz * ratio, n)
        ph = S.phase_of(base * (1.0 + vib), n, rnd.random() * TWOPI)
        K = int(min(14, max(3, lp * 1.6 / max(hz, 20.0))))
        for k in range(1, K + 1):
            x += (1.0 / k ** 1.1) * np.sin(k * ph + rnd.random() * 0.4) / voices
    x = S.filt(x, ("lp", lp, 2), circular=True)
    x /= max(float(np.max(np.abs(x))), 1e-9)
    return x * amp


def bell(rnd, f0=200.0, dur=8.0, ratios=None, amps=None, taus=None,
         strike=0.7, bright=1.0):
    """钟：非谐分音 + 长衰减 + 敲击噪声（庙钟/风铃共用）。"""
    n = sec(dur)
    ratios = np.array(ratios if ratios is not None else
                      [0.5, 1.0, 1.19, 1.51, 2.0, 2.51, 3.0, 4.1, 5.2])
    if amps is None:
        amps = np.array([0.75, 1.0, 0.5, 0.45, 0.55, 0.18, 0.13, 0.06, 0.03])
    if taus is None:
        taus = np.array([0.9, 0.65, 0.5, 0.45, 0.35, 0.22, 0.16, 0.1, 0.06]) * dur * 0.6
    amps = np.array(amps) * np.array([1.0] + [bright] * (len(amps) - 1))
    x = S.modal(n, f0 * ratios, amps, taus, rnd=rnd, detune=0.004)
    hit = S.filt(S.white(n, rnd), ("bp", f0 * 2, min(14000, f0 * 22), 2),
                 circular=False) * S.perc_env(n, 0.0005, 0.008) * strike
    return S.dc_block(x + hit)


def filter_sweep_noise(rnd, n, f_start, f_end, q=2.0, circular=True):
    """带通中心缓慢移动的噪声（吸气/水汽/风）。用 3 段交叉淡化近似。"""
    n = int(n)
    t = np.linspace(0.0, 1.0, n)
    bands = 4
    x = np.zeros(n)
    for b in range(bands):
        c = f_start * (f_end / f_start) ** ((b + 0.5) / bands)
        width = c * 0.55 + 120.0
        seg = S.noise_filtered(n, rnd, ("bp", max(40.0, c - width),
                                        c + width, 2), circular=circular)
        centre = (b + 0.5) / bands
        w = np.exp(-0.5 * ((t - centre) / (0.34 / bands + 0.18)) ** 2)
        x += seg * w * q
    return x
