"""ambience.py — 12 条环境声循环（每游戏 4 条）。

全部为严格周期的立体声循环：持续音频率锁相、事件用 add_wrapped、
噪声环形滤波、混响环形卷积。每条都分「近场干声 / 远场湿声」两层，
保证有层次与左右声像，而不是一坨白噪声。
"""
from __future__ import annotations

import math

import numpy as np

import soundlib as L
import synth as S
from synth import SR, sec, tarr, TWOPI


# ------------------------------------------------------------ 工具 --------
def _finish(x, rms_db=-20.5):
    y = S.finalize_loop(x, target_rms_db=rms_db, ceiling_db=-1.0)
    return y


def _bed(rnd, n, specs, gain, decor=1.0, am_rate=None, am_dep=0.0):
    """两声道独立（decor=1）或相关（decor=0）的噪声床。"""
    out = np.zeros((2, n))
    base = S.noise_filtered(n, rnd, *specs, circular=True)
    rot = S.noise_filtered(n, rnd, *specs, circular=True)
    for ch in range(2):
        b = base if ch == 0 else ((1.0 - decor) * base + decor * rot)
        if am_rate:
            rate = S.lock_rate(am_rate, n)
            lfo = 0.5 + 0.5 * np.sin(TWOPI * rate * tarr(n) + ch * 1.3)
            b = b * (1.0 - am_dep + am_dep * lfo)
        out[ch] = b * gain
    return out


def _place(buf, start_s, mono, gain=1.0, pan=0.0):
    S.add_wrapped(buf, sec(start_s), S.pan(np.asarray(mono, dtype=np.float64), pan), gain)


def _wet(dry, wet, ir, wet_gain=1.0):
    """干声 + 远场混响（湿声单独控制）。"""
    return dry + S.reverb(wet, ir, wet=wet_gain, dry=0.0, circular=True)


def _clean(x, hp=24.0, lp=16000.0):
    return S.filt(x, ("hp", hp, 2), ("lp", lp, 2), circular=True)


# =========================================================== 门后 ========
def corridor_hum():
    """30s：日光灯嗡鸣 + 远处楼梯间回声 + 偶尔电流噼啪。"""
    rnd = np.random.default_rng(2101)
    n = sec(30.0)
    dry = np.zeros((2, n))
    wet = np.zeros((2, n))

    # 日光灯：100Hz 基波 + 谐波，两台轻微失谐形成慢拍
    h1 = L.hum(n, 100.0, harmonics=(1.0, .55, .34, .2, .12, .07, .04), wobble=0.010, rnd=rnd)
    h2 = L.hum(n, 100.6, harmonics=(.8, .4, .22, .12, .06), wobble=0.008, rnd=rnd)
    hum = h1 + h2 * 0.5
    dry += S.pan(hum * 0.085, -0.05)
    # 灯管的电流嘶声
    dry += _bed(rnd, n, (("bp", 2500, 7500, 2),), 0.006, decor=0.7, am_rate=0.11, am_dep=0.3)

    # 远处楼梯间：低频脚步 + 门框闷响（全部进湿声层）
    for t0, p in ((3.2, -0.55), (7.6, 0.35), (11.4, -0.2), (16.8, 0.6),
                  (21.3, -0.45), (26.5, 0.25)):
        st = L.thump(rnd, 0.9, 55 + rnd.random() * 15, 0.12, body=0.8, click=0.05)
        st = S.filt(st, ("lp", 420, 2), circular=False)
        _place(wet, t0, st, 0.15, p)
        st2 = L.thump(rnd, 0.8, 58 + rnd.random() * 12, 0.10, body=0.7, click=0.0)
        st2 = S.filt(st2, ("lp", 380, 2), circular=False)
        _place(wet, t0 + 0.42, st2, 0.09, p * 0.8)
    # 远处关门/拖动
    for t0, p in ((9.6, 0.5), (19.4, -0.5), (24.8, 0.15)):
        dr = L.wood(rnd, 0.7, 90, weight=1.4, hardness=0.5)
        dr = S.filt(dr, ("lp", 700, 2), circular=False)
        _place(wet, t0, dr, 0.11, p)
    # 楼梯间铁栏杆的轻响
    _place(wet, 14.6, L.metal(rnd, 1500, 0.9, strike=0.15, bright=0.5), 0.035, 0.55)

    # 电流噼啪（近场，稀疏）
    for t0, p in ((5.0, 0.7), (13.2, -0.6), (18.5, 0.4), (24.1, -0.7), (28.0, 0.55)):
        c = L.electric_crackle(rnd, 0.14, 1.0)
        _place(dry, t0, c, 0.030, p)

    # 低频建筑底噪
    dry += _bed(rnd, n, (("lp", 90, 2),), 0.030, decor=0.0)

    ir = S.make_ir(2101, dur=2.6, decay=0.85, predelay=0.02,
                   lp=3200, hp=80, taps=18, tap_spread=0.16)
    y = _wet(dry, wet, ir, 0.9)
    y = _clean(y, 28.0, 13000.0)
    return _finish(y, -20.5)


def room_tone():
    """30s：室内低频嗡鸣 + 钟表声 + 窗外雨。"""
    rnd = np.random.default_rng(2102)
    n = sec(30.0)
    dry = np.zeros((2, n))
    wet = np.zeros((2, n))

    # 低频嗡鸣（50Hz 及低次谐波）
    h = L.hum(n, 50.0, harmonics=(1.0, .45, .28, .15, .07), wobble=0.012, rnd=rnd)
    dry += S.pan(h * 0.075, 0.0)
    dry += _bed(rnd, n, (("lp", 110, 2),), 0.030, decor=0.3)

    # 钟表：每秒一次 tick / tock（交替音高、声像）
    for i in range(30):
        t0 = i * 1.0 + (rnd.random() * 0.008 - 0.004)
        base = 1750.0 if i % 2 == 0 else 1520.0
        tick = S.modal(sec(0.10),
                       [base, base * 1.62, base * 2.31],
                       [1.0, 0.35, 0.15],
                       [0.020, 0.012, 0.008], rnd=rnd, detune=0.01)
        tick += S.filt(S.white(sec(0.10), rnd), ("hp", 4000, 2), circular=False) * \
            S.perc_env(sec(0.10), 0.0003, 0.003)
        _place(dry, t0, tick, 0.085 + rnd.random() * 0.02,
               0.32 if i % 2 == 0 else 0.45)

    # 窗外雨：闷在玻璃外，宽声场
    dry += _bed(rnd, n, (("bp", 600, 3600, 2), ("lp", 2800, 2)), 0.030,
                decor=1.0, am_rate=0.043, am_dep=0.35)
    for t0 in S.sparse_positions(n, 2.1, rnd, 0.4):
        d = L.water_drop(rnd, 800 + rnd.random() * 700, 1800 + rnd.random() * 1200, 0.12, 0.05)
        _place(wet, t0 / SR, d, 0.020, float(rnd.random() * 2 - 1) * 0.7)

    # 房子偶尔的木头应力
    for t0, p in ((8.4, -0.5), (21.8, 0.55)):
        c = L.creak(rnd, 1.1, 150, 340, spike=(0.008, 0.03), rough=0.6)
        c = S.filt(c, ("lp", 1800, 2), circular=False)
        _place(wet, t0, c, 0.035, p)

    ir = S.make_ir(2102, dur=1.4, decay=0.4, predelay=0.01,
                   lp=2600, hp=90, taps=14, tap_spread=0.1)
    y = _wet(dry, wet, ir, 0.8)
    y = _clean(y, 26.0, 13000.0)
    return _finish(y, -20.5)


def rain_window():
    """30s：贴窗雨声（近场、细密、左右不同）。"""
    rnd = np.random.default_rng(2103)
    n = sec(30.0)
    buf = np.zeros((2, n))

    # 雨声主体：两层带宽不同的噪声，左右独立
    buf += _bed(rnd, n, (("bp", 1200, 9000, 2),), 0.065, decor=1.0,
                am_rate=0.17, am_dep=0.25)
    buf += _bed(rnd, n, (("bp", 300, 2400, 2),), 0.055, decor=0.85,
                am_rate=0.09, am_dep=0.3)
    # 玻璃共振（窗的低频响应）
    buf += _bed(rnd, n, (("bp", 380, 900, 2),), 0.012, decor=0.4)

    # 雨滴颗粒（几百个），左右随机
    for _ in range(320):
        t0 = rnd.random() * 30.0
        d = L.water_drop(rnd, 900 + rnd.random() * 900, 2200 + rnd.random() * 1600,
                         0.05 + rnd.random() * 0.05, 0.03)
        _place(buf, t0, d, 0.010 + rnd.random() * 0.020,
               float(rnd.random() * 2 - 1) * 0.85)

    # 偶尔的大雨滴 / 排水管
    for t0, p in ((4.6, 0.6), (11.2, -0.55), (19.8, 0.4), (26.4, -0.65)):
        d = L.water_drop(rnd, 380 + rnd.random() * 180, 800 + rnd.random() * 300, 0.14, 0.18)
        _place(buf, t0, d, 0.045, p)
    # 窗外低频路噪
    buf += _bed(rnd, n, (("lp", 100, 2),), 0.020, decor=0.2)

    y = _clean(buf, 60.0, 15000.0)
    return _finish(y, -20.5)


def tv_static():
    """15s：电视雪花（低音量、可开关）。"""
    rnd = np.random.default_rng(2104)
    n = sec(15.0)
    buf = np.zeros((2, n))

    st = L.radio_static(rnd, n, circular=True, hum_amp=0.05)
    st = S.filt(st, ("bp", 300, 7500, 2), circular=True)
    st = st * (0.8 + 0.2 * np.sin(TWOPI * S.lock_rate(0.37, n) * tarr(n)))
    # 稍微偏向一侧，像角落里的电视
    buf += S.pan(st * 0.16, -0.30)
    # 极轻的 CRT 行频/电源啸叫
    t = tarr(n)
    whine = (np.sin(TWOPI * S.lock_freq(15675.0, n) * t) * 0.0030 +
             np.sin(TWOPI * S.lock_freq(7850.0, n) * t) * 0.0018)
    buf += S.pan(whine, -0.30)
    # 场同步的 50Hz 嗡嗡
    buf += S.pan(np.sin(TWOPI * S.lock_freq(50.0, n) * t) * 0.006, -0.25)
    # 音量不稳的抖动
    buf += _bed(rnd, n, (("bp", 2000, 8000, 2),), 0.004, decor=0.9,
                am_rate=0.8, am_dep=0.6)

    y = _clean(buf, 40.0, 17000.0)
    return _finish(y, -21.0)


# =========================================================== 镜中 ========
def fluorescent_buzz():
    """20s：日光灯电流 + 启辉器抖动 + 水管低频。"""
    rnd = np.random.default_rng(3101)
    n = sec(20.0)
    dry = np.zeros((2, n))
    wet = np.zeros((2, n))

    h1 = L.hum(n, 100.0, harmonics=(1.0, .7, .45, .3, .18, .1, .06), wobble=0.014, rnd=rnd)
    h2 = L.hum(n, 100.9, harmonics=(.7, .45, .28, .16, .08), wobble=0.012, rnd=rnd)
    dry += S.pan((h1 + 0.55 * h2) * 0.10, 0.12)
    dry += S.pan(h1 * 0.03, -0.35)

    # 灯管震动的细碎噪声
    dry += _bed(rnd, n, (("bp", 3200, 9500, 2),), 0.007, decor=0.7,
                am_rate=0.24, am_dep=0.45)

    # 启辉器/接触不良的噼啪
    for t0, p in ((2.4, 0.5), (6.1, -0.45), (9.5, 0.35), (13.8, -0.55),
                  (16.2, 0.5), (18.6, 0.2)):
        c = L.electric_crackle(rnd, 0.16, 1.0)
        _place(dry, t0, c, 0.032, p)
    # 一次灯管重启的短促低频
    _place(wet, 11.0, L.thump(rnd, 0.6, 80, 0.06, body=0.6, click=0.02), 0.05, 0.1)

    # 远处的澡堂水管低频
    dry += _bed(rnd, n, (("lp", 90, 2),), 0.030, decor=0.2)
    for t0 in S.sparse_positions(n, 6.5, rnd, 1.0):
        g = L.water_drop(rnd, 260, 620, 0.20, 0.30)
        _place(wet, t0 / SR, g, 0.020, 0.25)

    ir = S.make_ir(3101, dur=2.2, decay=0.7, predelay=0.015,
                   lp=6000, hp=100, taps=16, tap_spread=0.12)
    y = _wet(dry, wet, ir, 0.7)
    y = _clean(y, 30.0, 15500.0)
    return _finish(y, -20.5)


def water_drip():
    """30s：湿瓷砖房间的水滴（大混响、稀疏）。"""
    rnd = np.random.default_rng(3102)
    n = sec(30.0)
    dry = np.zeros((2, n))
    wet = np.zeros((2, n))

    # 低层：远处排水/空气
    dry += _bed(rnd, n, (("bp", 200, 1400, 2),), 0.022, decor=0.9,
                am_rate=0.07, am_dep=0.4)

    # 水滴事件
    for t0 in S.sparse_positions(n, 1.9, rnd, 0.35):
        f_lo = 420 + rnd.random() * 700
        d = L.water_drop(rnd, f_lo, f_lo * (2.0 + rnd.random() * 1.2), 0.13, 0.12)
        _place(wet, t0 / SR, d, 0.10 + rnd.random() * 0.12,
               float(rnd.random() * 2 - 1) * 0.75)
    # 大水滴/管壁声
    for t0, p in ((5.5, 0.55), (14.2, -0.6), (23.5, 0.3)):
        d = L.water_drop(rnd, 260, 700, 0.2, 0.4)
        _place(wet, t0, d, 0.16, p)
    dry += _bed(rnd, n, (("hp", 5000, 2),), 0.004, decor=1.0)

    ir = S.make_ir(3102, dur=3.4, decay=0.9, predelay=0.012,
                   lp=9000, hp=120, taps=22, tap_spread=0.1)
    y = _wet(dry, wet, ir, 1.0)
    y = _clean(y, 34.0, 16500.0)
    return _finish(y, -20.5)


def distant_water():
    """30s：远处澡堂水声/蒸汽（闷、宽、缓慢起伏）。"""
    rnd = np.random.default_rng(3103)
    n = sec(30.0)
    dry = np.zeros((2, n))
    wet = np.zeros((2, n))

    # 水流主体（远处，被空气吸收）
    dry += _bed(rnd, n, (("bp", 350, 2600, 2), ("lp", 2400, 2)), 0.048, decor=1.0,
                am_rate=0.083, am_dep=0.45)
    dry += _bed(rnd, n, (("bp", 90, 500, 2),), 0.030, decor=0.6,
                am_rate=0.041, am_dep=0.4)
    # 气泡/翻涌
    for t0 in S.sparse_positions(n, 2.6, rnd, 0.5):
        d = L.water_drop(rnd, 300 + rnd.random() * 260, 700 + rnd.random() * 500, 0.10, 0.12)
        _place(wet, t0 / SR, d, 0.030, float(rnd.random() * 2 - 1) * 0.8)
    # 蒸汽嘶声
    dry += _bed(rnd, n, (("hp", 3500, 2),), 0.010, decor=0.8, am_rate=0.13, am_dep=0.55)

    ir = S.make_ir(3103, dur=3.0, decay=1.1, predelay=0.03,
                   lp=2800, hp=90, taps=18, tap_spread=0.2)
    y = _wet(dry, wet, ir, 1.1)
    y = _clean(y, 26.0, 11000.0)
    return _finish(y, -20.5)


def steam_hiss():
    """15s：蒸汽嘶声（可开关）。"""
    rnd = np.random.default_rng(3104)
    n = sec(15.0)
    buf = np.zeros((2, n))

    hiss = _bed(rnd, n, (("hp", 2800, 2),), 0.075, decor=0.9,
                am_rate=0.19, am_dep=0.28)
    # 收一点极高频，给嘶声一点「管道里的身体」
    hiss = S.filt(hiss, ("lp", 13500, 2), circular=True) + \
        _bed(rnd, n, (("bp", 900, 2600, 2),), 0.012, decor=0.7,
             am_rate=0.15, am_dep=0.4)
    buf += hiss
    # 管道共振
    t = tarr(n)
    for f, g in ((1830, 0.006), (2740, 0.004), (3960, 0.003)):
        buf += S.pan(np.sin(TWOPI * S.lock_freq(f, n) * t) * g *
                     (0.6 + 0.4 * np.sin(TWOPI * S.lock_rate(0.21, n) * t)), 0.0)
    # 水滴被蒸汽吹动
    for t0 in S.sparse_positions(n, 1.4, rnd, 0.2):
        d = L.water_drop(rnd, 500 + rnd.random() * 400, 1200 + rnd.random() * 800, 0.08, 0.05)
        _place(buf, t0 / SR, d, 0.024, float(rnd.random() * 2 - 1) * 0.6)
    buf += _bed(rnd, n, (("lp", 120, 2),), 0.012, decor=0.2)

    y = _clean(buf, 70.0, 16000.0)
    return _finish(y, -20.5)


# =========================================================== 夜路 ========
def wind_field():
    """30s：田野夜风（宽声场、慢阵风、草叶摩擦）。"""
    rnd = np.random.default_rng(4101)
    n = sec(30.0)
    t = tarr(n)
    buf = np.zeros((2, n))

    # 风的主体：两个频段 + 左右独立，慢速起伏
    gust = 0.55 + 0.45 * np.sin(TWOPI * S.lock_rate(0.043, n) * t + 0.3)
    gust2 = 0.5 + 0.5 * np.sin(TWOPI * S.lock_rate(0.071, n) * t + 2.1)
    low = _bed(rnd, n, (("bp", 80, 520, 2),), 0.075, decor=1.0)
    mid = _bed(rnd, n, (("bp", 420, 2100, 2),), 0.045, decor=1.0)
    buf += low * (0.5 + 0.5 * gust)
    buf += mid * (0.35 + 0.65 * gust2)
    # 草的沙沙（高频，随阵风）
    grass = _bed(rnd, n, (("bp", 2200, 8000, 2),), 0.018, decor=1.0)
    buf += grass * (0.25 + 0.75 * gust2 ** 2)
    # 极低频
    buf += _bed(rnd, n, (("lp", 70, 2),), 0.045, decor=0.2)

    # 两次更明显的风阵（进湿声层，像远处林子的风声）
    wet = np.zeros((2, n))
    for t0, dur, p in ((4.0, 8.0, -0.5), (18.0, 10.0, 0.55)):
        wg = L.wind_gust(rnd, dur, strength=0.9, tone=0.6)
        _place(wet, t0, wg, 0.10, p)
    ir = S.make_ir(4101, dur=2.4, decay=0.9, predelay=0.02,
                   lp=2400, hp=80, taps=16, tap_spread=0.2)
    y = buf + S.reverb(wet, ir, wet=0.8, dry=0.0, circular=True)
    y = _clean(y, 26.0, 14000.0)
    return _finish(y, -20.5)


def insects():
    """30s：秋夜虫鸣（稀疏、有起伏、不同声像）。"""
    rnd = np.random.default_rng(4102)
    n = sec(30.0)
    buf = np.zeros((2, n))

    # 夜风底
    buf += _bed(rnd, n, (("bp", 120, 1400, 2),), 0.017, decor=1.0,
                am_rate=0.05, am_dep=0.5)
    buf += _bed(rnd, n, (("lp", 90, 2),), 0.020, decor=0.2)

    def chirp(freq, dur, pulse_rate, gain, pulse_depth=0.85):
        nn = sec(dur)
        tt = tarr(nn)
        pulse = 0.5 + 0.5 * np.sin(TWOPI * pulse_rate * tt)
        tone = np.sin(TWOPI * freq * tt)
        tone += 0.4 * np.sin(TWOPI * freq * 2.0 * tt)
        env = np.sin(np.pi * np.clip(tt / dur, 0, 1)) ** 0.6
        return tone * (1.0 - pulse_depth + pulse_depth * pulse) * env * gain

    # 三种虫：不同音高/节奏/位置，成簇出现
    singers = [
        (4650.0, 34.0, 22.0, -0.55, 0.020, 3.0, 7.5),   # (f, pulse, chirp_dur_ms, pan, gain, cluster_gap_s, cluster_len)
        (4050.0, 27.0, 30.0, 0.62, 0.016, 4.5, 6.0),
        (5300.0, 46.0, 16.0, -0.15, 0.012, 5.5, 5.0),
    ]
    for freq, prate, cdur_ms, pan, gain, gap, clen in singers:
        t0 = rnd.random() * 4.0
        while t0 < 30.0 - 1.0:
            t1 = min(30.0 - 0.5, t0 + clen * (0.6 + rnd.random() * 0.8))
            tt = t0
            while tt < t1:
                _place(buf, tt,
                       chirp(freq * (1 + (rnd.random() - 0.5) * 0.006),
                             cdur_ms / 1000.0, prate,
                             0.6 + rnd.random() * 0.6),
                       gain, pan)
                tt += cdur_ms / 1000.0 + 0.04 + rnd.random() * 0.09
            t0 = t1 + gap * (0.5 + rnd.random())

    y = _clean(buf, 40.0, 15000.0)
    return _finish(y, -20.5)


def night_room_tone():
    """30s：极低的环境底噪（几乎只有空气与地鸣）。"""
    rnd = np.random.default_rng(4103)
    n = sec(30.0)
    buf = np.zeros((2, n))

    buf += _bed(rnd, n, (("lp", 55, 2),), 0.10, decor=0.15)
    buf += _bed(rnd, n, (("hp", 2000, 2),), 0.0025, decor=1.0)
    buf += _bed(rnd, n, (("bp", 120, 700, 2),), 0.010, decor=0.8,
                am_rate=0.03, am_dep=0.4)
    # 极疏的木头收缩声
    wet = np.zeros((2, n))
    for t0, p in ((7.2, -0.4), (21.6, 0.5)):
        c = L.creak(rnd, 0.8, 120, 280, spike=(0.01, 0.04), rough=0.5)
        c = S.filt(c, ("lp", 1200, 2), circular=False)
        _place(wet, t0, c, 0.020, p)
    ir = S.make_ir(4103, dur=1.6, decay=0.5, predelay=0.01,
                   lp=1800, hp=60, taps=12, tap_spread=0.1)
    y = buf + S.reverb(wet, ir, wet=0.7, dry=0.0, circular=True)
    y = _clean(y, 20.0, 9000.0)
    return _finish(y, -22.0)


def _bark(rnd):
    """远处犬吠的单声「汪」。"""
    dur = 0.16 + rnd.random() * 0.08
    n = sec(dur)
    t = tarr(n)
    f = (400.0 + rnd.random() * 130) * (1.0 - 0.42 * np.clip(t / dur, 0, 1))
    ph = S.phase_of(f, n, rnd.random() * TWOPI)
    raw = 2.0 * ((ph / TWOPI) % 1.0) - 1.0
    raw = S.filt(raw, ("res", 650, 3), ("res", 1450, 3),
                 ("bp", 220, 2400), circular=False)
    env = S.ar_env(n, 0.006, dur * 0.55) * (0.75 + 0.25 * np.sin(TWOPI * 42 * t))
    return S.dc_block(raw * env)


def distant_dog():
    """12s：远处狗吠（稀疏、2-3 声）。"""
    rnd = np.random.default_rng(4104)
    n = sec(12.0)
    dry = np.zeros((2, n))
    dry += _bed(rnd, n, (("bp", 150, 1200, 2),), 0.014, decor=1.0,
                am_rate=0.08, am_dep=0.5)
    dry += _bed(rnd, n, (("lp", 80, 2),), 0.016, decor=0.2)

    wet = np.zeros((2, n))
    # 第一次：两声连吠
    for t0, g in ((1.4, 0.16), (2.05, 0.11)):
        b = _bark(rnd)
        _place(wet, t0, b, g, -0.45)
    # 第二次：更远的一声
    _place(wet, 8.4, _bark(rnd), 0.09, 0.3)

    ir = S.make_ir(4104, dur=2.6, decay=1.0, predelay=0.02,
                   lp=1600, hp=90, taps=16, tap_spread=0.2)
    y = _wet(dry, wet, ir, 1.3)
    y = _clean(y, 40.0, 7000.0)
    return _finish(y, -21.5)


ALL = {
    "door/ambience/corridor_hum.ogg": corridor_hum,
    "door/ambience/room_tone.ogg": room_tone,
    "door/ambience/rain_window.ogg": rain_window,
    "door/ambience/tv_static.ogg": tv_static,
    "mirror/ambience/fluorescent_buzz.ogg": fluorescent_buzz,
    "mirror/ambience/water_drip.ogg": water_drip,
    "mirror/ambience/distant_water.ogg": distant_water,
    "mirror/ambience/steam_hiss.ogg": steam_hiss,
    "nightroad/ambience/wind_field.ogg": wind_field,
    "nightroad/ambience/insects.ogg": insects,
    "nightroad/ambience/night_room_tone.ogg": night_room_tone,
    "nightroad/ambience/distant_dog.ogg": distant_dog,
}
