"""sfx.py — 三个 demo 的音效 + shared UI（全部单声道，按 AUDIO_SPEC §4 清单）。

每个函数返回**已经做过峰值归一/边缘淡出**的 mono 数组。
变体通过传入的 seed 不同自然产生差异（f0/时值/颗粒随机）。
"""
from __future__ import annotations

import math

import numpy as np

import soundlib as L
import synth as S
from music import _tile_ir
from synth import SR, sec, tarr, TWOPI


# ------------------------------------------------------------ 工具 --------
def _out(x, peak=-2.2, fout=0.03, fin=0.0008, rms_max=-11.0):
    # 源峰值不超过 -1.8 dBFS，给 Vorbis 编解码留出余量（解码后仍 ≤ -1 dBFS）；
    # 持续型声音再用 RMS 上限压一下，最后把峰值夹回规格区间 [-3, -1.8]。
    peak = min(float(peak), -1.8)
    y = S.finalize_oneshot(S.dc_block(np.asarray(x, dtype=np.float64)),
                           peak_target=peak, fin=fin, fout=fout,
                           ceiling_db=-1.8)
    if rms_max is not None:
        r_db = S.rms_db(y)
        if r_db > rms_max:
            y = y * float(S.db2lin(rms_max - r_db))
    p_db = S.peak_db(y)
    if p_db < -3.0:
        y = y * float(S.db2lin(-3.0 - p_db))
    elif p_db > -1.8:
        y = y * float(S.db2lin(-1.8 - p_db))
    return np.clip(y, -1.0, 1.0)


def _out_loop(x, peak=-2.3, rms_max=-11.0):
    # 循环音效统一到 -2.3 dBFS 源峰值（解码后约 -2.6 ~ -2.2，符合 -3~-1 规格）
    x = S.dc_block(np.asarray(x, dtype=np.float64))
    x = x * float(S.db2lin(peak - S.peak_db(x)))
    x = S.soft_limit(x, -1.5)
    if rms_max is not None:
        r_db = S.rms_db(x)
        if r_db > rms_max:
            x = x * float(S.db2lin(rms_max - r_db))
        p_db = S.peak_db(x)
        if p_db < -3.0:
            x = x * float(S.db2lin(-3.0 - p_db))
    return np.clip(x, -1.0, 1.0)


def _buf(dur):
    return np.zeros(sec(dur))


def _put(buf, start_s, mono, gain=1.0):
    S.add_at(buf, sec(start_s), mono, gain)


def _room_ir(seed, dur=0.7, decay=0.24, lp=5000, predelay=0.008):
    return S.make_ir(seed, dur=dur, decay=decay, predelay=predelay,
                     lp=lp, hp=90, taps=10, tap_spread=0.06)


def _room(x, ir, wet=0.22):
    return S.reverb(x, ir, wet=wet, dry=1.0, circular=False)


def _tile_room(seed):
    return _tile_ir(seed, dur=1.5, decay=0.45, tap_ms=44.0, lp=10000)


def _glitch_env(n, rate=60.0, depth=0.85, rnd=None):
    """快速通断（电流/闪烁）。"""
    t = tarr(n)
    pulse = 0.5 + 0.5 * np.sign(np.sin(TWOPI * rate * t + (rnd.random() * 0.5 if rnd is not None else 0.0)))
    return 1.0 - depth + depth * pulse


# =========================================================== shared UI ====
def ui_hover(seed=9001):
    """悬停：极轻的高频软点。"""
    rnd = np.random.default_rng(seed)
    n = sec(0.085)
    x = S.modal(n, [3100 + rnd.random() * 300, 4700], [1.0, 0.35],
                [0.012, 0.006], rnd=rnd, detune=0.01)
    x += S.filt(S.white(n, rnd), ("hp", 5000, 2), circular=False) * \
        S.perc_env(n, 0.0004, 0.003) * 0.25
    return _out(x, -5.0, fout=0.02)


def ui_click(seed=9002):
    """点击：短促、干的木质点击。"""
    rnd = np.random.default_rng(seed)
    n = sec(0.11)
    x = S.modal(n, [1250, 2100, 3400], [1.0, 0.5, 0.25],
                [0.022, 0.012, 0.007], rnd=rnd, detune=0.015)
    x += S.filt(S.white(n, rnd), ("hp", 2400, 2), circular=False) * \
        S.perc_env(n, 0.0003, 0.0035) * 0.5
    x += S.modal(n, [180], [0.5], [0.02], rnd=rnd) * 0.4
    return _out(x, -4.0, fout=0.025)


def ui_back(seed=9003):
    """返回：两声下行的轻点。"""
    rnd = np.random.default_rng(seed)
    n = sec(0.18)
    x = np.zeros(n)
    for i, (t0, f) in enumerate(((0.0, 1500.0), (0.055, 1080.0))):
        m = S.modal(sec(0.10), [f, f * 1.9], [1.0, 0.3],
                    [0.020, 0.010], rnd=rnd, detune=0.01)
        _put(x, t0, m, 0.8 - i * 0.2)
        _put(x, t0, S.filt(S.white(sec(0.10), rnd), ("hp", 3000, 2),
                           circular=False) * S.perc_env(sec(0.10), 0.0003, 0.002),
             0.15)
    return _out(x, -4.5, fout=0.03)


def ui_confirm(seed=9004):
    """确认：两音上行的小钟。"""
    rnd = np.random.default_rng(seed)
    n = sec(0.26)
    x = np.zeros(n)
    for t0, m, g in ((0.0, 74, 0.9), (0.075, 81, 0.75)):
        b = L.fm_bell(rnd, float(S.hz(m)), 0.22, ratio=2.0, index=1.1, vel=g,
                      index_tau=0.06)
        _put(x, t0, b, 0.5)
    x += S.filt(S.white(n, rnd), ("hp", 6000, 2), circular=False) * \
        S.perc_env(n, 0.0004, 0.003) * 0.12
    return _out(x, -4.0, fout=0.05)


# =========================================================== 门后 ========
def step_wood(seed):
    rnd = np.random.default_rng(seed)
    f0 = 120.0 + rnd.random() * 110.0
    x = L.wood(rnd, 0.34, f0, weight=1.15, hardness=0.95, bright=0.9)
    # 楼板/走廊的短反射
    ir = _room_ir(seed, dur=0.55, decay=0.2, lp=3600)
    return _out(_room(x, ir, 0.28), -2.0, fout=0.04)


def step_carpet(seed):
    rnd = np.random.default_rng(seed)
    x = L.carpet(rnd, 0.22, weight=1.0 + rnd.random() * 0.3)
    ir = _room_ir(seed, dur=0.35, decay=0.12, lp=2200)
    return _out(_room(x, ir, 0.18), -2.2, fout=0.035)


def door_open(seed):
    rnd = np.random.default_rng(seed)
    total = 2.6
    x = _buf(total)
    c1 = L.creak(rnd, 1.9, 220 + rnd.random() * 60, 500 + rnd.random() * 120,
                 spike=(0.010, 0.042), rough=0.85, shape="rise")
    c1 = S.filt(c1, ("lp", 3200, 2), circular=False)
    _put(x, 0.10, c1, 0.9)
    # 门轴第二层（稍有延迟，更高）
    c2 = L.creak(rnd, 0.9, 620, 1100, spike=(0.006, 0.02), metal=0.7, rough=1.1)
    _put(x, 0.55, S.filt(c2, ("lp", 5000, 2), circular=False), 0.22)
    # 门板受力
    _put(x, 0.05, L.wood(rnd, 0.9, 95, weight=1.8, hardness=0.6), 0.30)
    # 底部摩擦
    sc = L.scrape(rnd, 1.4, 500, 2200, metal=0.15, rate=13.0)
    env = S.ar_env(sec(1.4), 0.3, 0.5)
    _put(x, 0.35, S.filt(sc, ("lp", 3000, 2), circular=False) * env, 0.10)
    ir = _room_ir(seed, dur=1.1, decay=0.38, lp=4200)
    return _out(_room(x, ir, 0.26), -1.5, fout=0.08)


def door_close(seed):
    rnd = np.random.default_rng(seed)
    total = 1.6
    x = _buf(total)
    # 门板撞框
    _put(x, 0.02, L.thump(rnd, 1.3, 62 + rnd.random() * 8, 0.14,
                         body=1.3, click=0.45), 0.95)
    _put(x, 0.0, L.wood(rnd, 1.2, 88, weight=2.0, hardness=0.75), 0.7)
    # 门框金属件
    _put(x, 0.035, L.metal(rnd, 1900, 0.5,
                           taus=[0.12, 0.08, 0.05, 0.03, 0.02, 0.012, 0.008],
                           strike=0.6, bright=0.8), 0.28)
    # 把手回弹
    _put(x, 0.13, L.metal(rnd, 2600, 0.25, strike=0.3, bright=1.0), 0.12)
    ir = _room_ir(seed, dur=1.0, decay=0.34, lp=4000)
    return _out(_room(x, ir, 0.28), -1.5, fout=0.06)


def door_locked(seed):
    rnd = np.random.default_rng(seed)
    total = 1.5
    x = _buf(total)
    # 门把手来回拧：一组金属咔哒
    for i in range(4):
        t0 = 0.05 + i * (0.10 + rnd.random() * 0.06)
        m = L.metal(rnd, 1600 + rnd.random() * 1400, 0.30,
                    taus=[0.08, 0.05, 0.03, 0.02, 0.013, 0.008, 0.005],
                    strike=0.5, bright=1.0)
        _put(x, t0, m, 0.35 + rnd.random() * 0.25)
    # 锁芯顶死的闷响
    _put(x, 0.62, L.wood(rnd, 0.7, 120, weight=1.5, hardness=0.7), 0.45)
    _put(x, 0.62, L.thump(rnd, 0.8, 80, 0.09, body=0.8, click=0.15), 0.35)
    ir = _room_ir(seed, dur=0.8, decay=0.25, lp=3800)
    return _out(_room(x, ir, 0.24), -1.5, fout=0.06)


def door_unlock(seed):
    rnd = np.random.default_rng(seed)
    total = 1.8
    x = _buf(total)
    # 钥匙插入/刮擦
    sc = L.scrape(rnd, 0.5, 1800, 5200, metal=1.0, rate=35.0)
    _put(x, 0.02, S.filt(sc, ("hp", 900, 2), circular=False), 0.12)
    # 两下金属咔哒
    for t0, g in ((0.30, 0.5), (0.52, 0.7)):
        m = L.metal(rnd, 2100 + rnd.random() * 900, 0.45,
                    taus=[0.10, 0.07, 0.04, 0.025, 0.015, 0.01, 0.006],
                    strike=0.7, bright=1.0)
        _put(x, t0, m, g)
    # 门闩滑开（低频金属摩擦 + 落位）
    sc2 = L.scrape(rnd, 0.6, 500, 1800, metal=0.9, rate=20.0)
    _put(x, 0.62, S.filt(sc2, ("lp", 2600, 2), circular=False), 0.22)
    _put(x, 1.05, L.thump(rnd, 0.7, 70, 0.09, body=0.9, click=0.2), 0.45)
    ir = _room_ir(seed, dur=0.9, decay=0.3, lp=4200)
    return _out(_room(x, ir, 0.26), -1.6, fout=0.07)


def pickup_letter(seed):
    rnd = np.random.default_rng(seed)
    x = L.paper(rnd, 0.42, density=24 + int(rnd.random() * 12),
                bright=0.95, swells=2)
    _put(x, 0.0, L.cloth(rnd, 0.35, density=26, weight=0.55), 1.0)
    _put(x, 0.12, L.paper(rnd, 0.22, density=12, bright=1.0, swells=1), 0.4)
    ir = _room_ir(seed, dur=0.5, decay=0.15, lp=4200)
    return _out(_room(x, ir, 0.16), -2.2, fout=0.04)


def pickup_battery(seed):
    rnd = np.random.default_rng(seed)
    n = sec(0.4)
    x = S.modal(n, [780, 1420, 2260], [1.0, 0.5, 0.25],
                [0.05, 0.03, 0.02], rnd=rnd, detune=0.02)
    x += S.filt(S.white(n, rnd), ("hp", 3000, 2), circular=False) * \
        S.perc_env(n, 0.0003, 0.004) * 0.3
    _put(x, 0.11, S.modal(sec(0.3), [640, 1180], [1.0, 0.4],
                          [0.045, 0.025], rnd=rnd, detune=0.02), 0.5)
    ir = _room_ir(seed, dur=0.45, decay=0.14, lp=5000)
    return _out(_room(x, ir, 0.18), -2.2, fout=0.04)


def flashlight_click(seed):
    rnd = np.random.default_rng(seed)
    n = sec(0.22)
    x = np.zeros(n)
    for t0, f, g in ((0.0, 2400, 0.9), (0.045, 1700, 0.6)):
        m = L.metal(rnd, f, 0.14, taus=[0.02, 0.012, 0.007, 0.004, 0.003, 0.002, 0.001],
                    strike=0.4, bright=1.2)
        _put(x, t0, m, g)
        _put(x, t0, S.filt(S.white(sec(0.14), rnd), ("hp", 4000, 2), circular=False)
             * S.perc_env(sec(0.14), 0.0002, 0.002), 0.2)
    _put(x, 0.0, S.modal(n, [320], [0.8], [0.03], rnd=rnd), 0.35)
    ir = _room_ir(seed, dur=0.3, decay=0.1, lp=6000)
    return _out(_room(x, ir, 0.12), -2.0, fout=0.03)


def battery_low(seed):
    rnd = np.random.default_rng(seed)
    n = sec(1.1)
    t = tarr(n)
    # 电压不足的嗡嗡 + 断续
    buzz = np.sin(TWOPI * 118.0 * t) + 0.5 * np.sin(TWOPI * 236.0 * t) + \
        0.25 * np.sin(TWOPI * 354.0 * t)
    buzz *= _glitch_env(n, 13.0, 0.8, rnd)
    buzz *= S.ar_env(n, 0.02, 0.25)
    x = buzz * 0.5
    x += S.filt(S.white(n, rnd), ("bp", 1500, 6000, 2), circular=False) * \
        S.ar_env(n, 0.01, 0.3) * 0.06
    ir = _room_ir(seed, dur=0.4, decay=0.12, lp=4000)
    return _out(_room(x, ir, 0.12), -2.5, fout=0.04)


def light_switch(seed):
    rnd = np.random.default_rng(seed)
    n = sec(0.30)
    x = np.zeros(n)
    # 塑料开关
    _put(x, 0.0, S.modal(sec(0.16), [1150, 1980, 2800], [1.0, 0.6, 0.25],
                         [0.020, 0.012, 0.008], rnd=rnd, detune=0.02), 0.6)
    _put(x, 0.0, S.filt(S.white(sec(0.16), rnd), ("hp", 2600, 2),
                        circular=False) * S.perc_env(sec(0.16), 0.0003, 0.003), 0.5)
    # 起辉的电火花
    _put(x, 0.055, L.electric_crackle(rnd, 0.10, 0.7), 0.20)
    ir = _room_ir(seed, dur=0.35, decay=0.12, lp=6000)
    return _out(_room(x, ir, 0.14), -2.0, fout=0.03)


def light_flicker(seed):
    rnd = np.random.default_rng(seed)
    n = sec(0.9)
    t = tarr(n)
    buzz = (np.sin(TWOPI * 100.0 * t) + 0.55 * np.sin(TWOPI * 200.0 * t) +
            0.3 * np.sin(TWOPI * 300.0 * t))
    buzz *= _glitch_env(n, 21.0, 0.95, rnd) * S.ar_env(n, 0.01, 0.2)
    x = buzz * 0.55
    for t0 in (0.05, 0.28, 0.55):
        _put(x, t0, L.electric_crackle(rnd, 0.09, 0.9), 0.22)
    _put(x, 0.0, L.thump(rnd, 0.4, 70, 0.04, body=0.5, click=0.1), 0.15)
    ir = _room_ir(seed, dur=0.5, decay=0.18, lp=5000)
    return _out(_room(x, ir, 0.18), -2.0, fout=0.04)


def paper_rustle(seed):
    rnd = np.random.default_rng(seed)
    x = L.paper(rnd, 0.9, density=36 + int(rnd.random() * 14),
                bright=1.0, swells=3)
    _put(x, 0.0, L.cloth(rnd, 0.8, density=34, weight=0.5), 1.0)
    ir = _room_ir(seed, dur=0.6, decay=0.2, lp=4500)
    return _out(_room(x, ir, 0.18), -2.2, fout=0.05)


def clock_tick():
    """2s 循环：tick-tock（60 BPM）。"""
    rnd = np.random.default_rng(9301)
    n = sec(2.0)
    x = np.zeros(n)
    for i, base in enumerate((1780.0, 1520.0)):
        tick = S.modal(sec(0.14), [base, base * 1.62, base * 2.31],
                       [1.0, 0.35, 0.15], [0.022, 0.013, 0.008],
                       rnd=rnd, detune=0.008)
        tick += S.filt(S.white(sec(0.14), rnd), ("hp", 4200, 2),
                       circular=False) * S.perc_env(sec(0.14), 0.0003, 0.003) * 0.5
        S.add_wrapped(x, sec(i * 1.0), tick, 1.0 - i * 0.12)
    # 机芯的极轻底噪
    x += S.filt(S.white(n, rnd), ("bp", 800, 3000, 2), circular=True) * 0.006
    return _out_loop(x, -3.0)


def heartbeat(seed=9302):
    """10s 循环，60 BPM。"""
    rnd = np.random.default_rng(seed)
    x = L.heartbeat_loop(rnd, sec(10.0), bpm=60.0, strength=1.0)
    x = S.filt(x, ("hp", 24, 2), ("lp", 9000, 2), circular=True)
    return _out_loop(x, -2.5)


def breath(seed=9303):
    """8s 循环呼吸。"""
    rnd = np.random.default_rng(seed)
    x = L.breath_loop(rnd, sec(8.0), cycle=4.0, deep=1.0)
    x = S.filt(x, ("hp", 110, 2), ("lp", 9000, 2), circular=True)
    ir = _room_ir(seed, dur=1.2, decay=0.35, lp=5000)
    x = S.reverb(x, ir, wet=0.15, dry=1.0, circular=True)
    return _out_loop(x, -3.0)


def whisper(seed):
    rnd = np.random.default_rng(seed)
    total = 1.9 + rnd.random() * 0.6
    x = L.whisper(rnd, total, syllables=3 + int(rnd.random() * 4),
                  sib=0.5 + rnd.random() * 0.3,
                  pitch=0.85 + rnd.random() * 0.35)
    ir = _room_ir(seed, dur=1.0, decay=0.3, lp=5200)
    x = _room(x, ir, 0.3)
    return _out(x, -2.2, fout=0.08)


def stinger(seed):
    """无巨响的刺点：不协和音簇渐强 + 低频压迫。"""
    rnd = np.random.default_rng(seed)
    total = 3.2
    x = _buf(total)
    variant = seed % 2
    # 不协和音簇（小二度/三全音）
    notes = ([60, 61, 66, 67] if variant == 0 else [55, 58, 61, 66])
    for m in notes:
        nsec = sec(2.2)
        s = L.string_note(rnd, float(S.hz(m)), 2.2, vel=0.55,
                          attack=0.9, release=1.1, bright=0.7, vib_cents=14.0)
        _put(x, 0.15, s, 0.34)
    # 反向噪声渐强（吸气）
    sw = S.noise_filtered(sec(1.6), rnd, ("bp", 400, 4500, 2), circular=False)
    ramp = np.exp(tarr(sec(1.6)) / 0.45)
    ramp /= ramp[-1]
    _put(x, 0.0, sw * ramp, 0.18)
    # 低频撞（闷，不刺耳）
    _put(x, 1.55, L.thump(rnd, 1.4, 48, 0.16, body=1.1, click=0.1), 0.5)
    # 高频擦弦
    c = L.creak(rnd, 1.4, 900, 2200, spike=(0.005, 0.02), metal=0.6, rough=0.9)
    _put(x, 0.9, S.filt(c, ("hp", 700, 2), ("lp", 7000, 2), circular=False), 0.10)
    ir = _room_ir(seed, dur=2.0, decay=0.8, lp=4000)
    x = _room(x, ir, 0.4)
    return _out(x, -1.5, fout=0.15)


def blackout(seed):
    rnd = np.random.default_rng(seed)
    total = 2.4
    x = _buf(total)
    # 开关断电的咔
    _put(x, 0.0, S.modal(sec(0.2), [1300, 2200], [1.0, 0.5],
                         [0.02, 0.012], rnd=rnd), 0.5)
    # 电流下降：100Hz 下滑到 30Hz
    nsec = sec(1.8)
    t = tarr(nsec)
    f = 100.0 * (30.0 / 100.0) ** np.clip(t / 1.6, 0, 1)
    hum = (np.sin(S.phase_of(f, nsec)) + 0.5 * np.sin(2.0 * S.phase_of(f, nsec)))
    hum *= np.exp(-t / 0.75) * (1.0 - np.exp(-t / 0.02))
    _put(x, 0.05, hum, 0.30)
    # 低频余韵
    _put(x, 0.1, L.thump(rnd, 1.6, 44, 0.2, body=1.0, click=0.0), 0.42)
    # 灯管的最后一下噼啪
    _put(x, 0.32, L.electric_crackle(rnd, 0.14, 0.8), 0.12)
    ir = _room_ir(seed, dur=1.4, decay=0.5, lp=3400)
    x = _room(x, ir, 0.32)
    return _out(x, -1.5, fout=0.12)


def entity_breath(seed=9304):
    """10s 循环：更低、更慢、更湿的呼吸。"""
    rnd = np.random.default_rng(seed)
    n = sec(10.0)
    x = L.breath_loop(rnd, n, cycle=5.0, deep=1.15)
    x = S.filt(x, ("hp", 60, 2), ("lp", 2600, 2), circular=True)
    # 低频体感
    x += L.sub_drone(rnd, n, 46.0, amp=0.10, harmonics=(1.0, 0.2), beat=0.3)
    ir = _room_ir(seed, dur=1.6, decay=0.55, lp=2400)
    x = S.reverb(x, ir, wet=0.35, dry=1.0, circular=True)
    return _out_loop(x, -2.5)


def entity_step(seed):
    rnd = np.random.default_rng(seed)
    total = 1.4
    x = _buf(total)
    # 湿重的落步
    _put(x, 0.0, L.thump(rnd, 1.1, 38 + rnd.random() * 6, 0.18,
                        body=1.3, click=0.15), 0.9)
    _put(x, 0.0, L.wood(rnd, 0.8, 68, weight=2.2, hardness=0.4), 0.4)
    # 拖拽的摩擦
    sc = L.scrape(rnd, 1.0, 250, 1400, metal=0.1, rate=9.0)
    _put(x, 0.12, S.filt(sc, ("lp", 1600, 2), circular=False) *
         S.ar_env(sec(1.0), 0.1, 0.4), 0.16)
    ir = _room_ir(seed, dur=1.2, decay=0.45, lp=2200)
    return _out(_room(x, ir, 0.4), -1.5, fout=0.1)


def entity_catch(seed):
    rnd = np.random.default_rng(seed)
    total = 2.2
    x = _buf(total)
    # 猛吸气
    gas = S.filt(S.white(sec(0.8), rnd), ("bp", 500, 3800, 2), circular=False)
    gas = S.filt(gas, ("res", 800, 3), circular=False) * \
        S.swell_env(sec(0.8), 0.25, 0.3, 1.3)
    _put(x, 0.05, gas, 0.55)
    # 抓住布料
    cl = L.cloth(rnd, 0.6, density=70, weight=1.4)
    _put(x, 0.45, S.filt(cl, ("bp", 300, 5000, 2), circular=False), 0.45)
    # 低频压迫
    cl2 = L.thump(rnd, 1.4, 40, 0.25, body=1.2, click=0.0)
    _put(x, 0.5, cl2, 0.7)
    ir = _room_ir(seed, dur=1.4, decay=0.5, lp=3000)
    return _out(_room(x, ir, 0.35), -1.5, fout=0.12)


# =========================================================== 镜中 ========
def step_tile(seed):
    rnd = np.random.default_rng(seed)
    x = L.tile(rnd, 0.34, weight=1.0)
    # 湿脚步 + 瓷砖混响
    wet = S.filt(S.white(sec(0.2), rnd), ("bp", 500, 6000, 2), circular=False) * \
        S.perc_env(sec(0.2), 0.0005, 0.012)
    _put(x, 0.0, wet, 0.20)
    ir = _tile_room(seed)
    return _out(_room(x, ir, 0.30), -2.0, fout=0.05)


def towel_pick(seed):
    rnd = np.random.default_rng(seed)
    x = L.cloth(rnd, 0.6, density=52, weight=1.2)
    _put(x, 0.35, S.filt(S.white(sec(0.12), rnd), ("bp", 800, 5000, 2),
                         circular=False) * S.perc_env(sec(0.12), 0.001, 0.015), 0.2)
    ir = _tile_room(seed)
    return _out(_room(x, ir, 0.22), -2.0, fout=0.05)


def valve_turn(seed):
    rnd = np.random.default_rng(seed)
    total = 1.8
    x = _buf(total)
    # 金属阀门吱嘎
    c = L.creak(rnd, 1.0, 700 + rnd.random() * 200, 1400 + rnd.random() * 300,
                spike=(0.006, 0.022), metal=1.0, rough=1.0)
    _put(x, 0.05, S.filt(c, ("hp", 400, 2), circular=False), 0.35)
    # 水管里的水锤
    _put(x, 0.95, L.thump(rnd, 0.9, 62, 0.12, body=1.0, click=0.15), 0.55)
    _put(x, 0.95, L.metal(rnd, 900, 0.7, strike=0.3, bright=0.7), 0.18)
    # 滴水
    _put(x, 1.35, L.water_drop(rnd, 600, 1500, 0.12, 0.1), 0.15)
    ir = _tile_room(seed)
    return _out(_room(x, ir, 0.3), -1.7, fout=0.08)


def water_stream(seed=9401):
    rnd = np.random.default_rng(seed)
    n = sec(10.0)
    x = L.water_stream_loop(rnd, n)
    x = S.filt(x, ("hp", 40, 2), ("lp", 12000, 2), circular=True)
    ir = _tile_room(seed)
    x = S.reverb(x, ir, wet=0.25, dry=1.0, circular=True)
    return _out_loop(x, -2.5)


def water_splash(seed):
    rnd = np.random.default_rng(seed)
    x = L.water_splash(rnd, 0.9, strength=1.0)
    ir = _tile_room(seed)
    return _out(_room(x, ir, 0.3), -2.0, fout=0.1)


def switch_click(seed):
    rnd = np.random.default_rng(seed)
    n = sec(0.26)
    x = np.zeros(n)
    _put(x, 0.0, S.modal(sec(0.14), [980, 1720, 2450], [1.0, 0.55, 0.22],
                         [0.018, 0.011, 0.007], rnd=rnd, detune=0.02), 0.6)
    _put(x, 0.0, S.filt(S.white(sec(0.14), rnd), ("hp", 2200, 2),
                        circular=False) * S.perc_env(sec(0.14), 0.0003, 0.003), 0.55)
    ir = _tile_room(seed)
    return _out(_room(x, ir, 0.18), -2.0, fout=0.03)


def light_flicker_mirror(seed):
    rnd = np.random.default_rng(seed)
    n = sec(1.0)
    t = tarr(n)
    buzz = (np.sin(TWOPI * 100.0 * t) + 0.6 * np.sin(TWOPI * 200.0 * t) +
            0.35 * np.sin(TWOPI * 400.0 * t))
    buzz *= _glitch_env(n, 17.0, 0.9, rnd) * S.ar_env(n, 0.01, 0.25)
    x = buzz * 0.5
    for t0 in (0.04, 0.36, 0.62):
        _put(x, t0, L.electric_crackle(rnd, 0.08, 0.8), 0.18)
    ir = _tile_room(seed)
    return _out(_room(x, ir, 0.2), -2.0, fout=0.04)


def locker_creak(seed):
    rnd = np.random.default_rng(seed)
    total = 1.5
    x = _buf(total)
    c = L.creak(rnd, 1.1, 900 + rnd.random() * 300, 1600 + rnd.random() * 500,
                spike=(0.005, 0.018), metal=1.0, rough=1.2)
    _put(x, 0.05, S.filt(c, ("hp", 500, 2), ("lp", 9000, 2), circular=False), 0.5)
    # 柜门到位的小金属声
    _put(x, 1.05, L.metal(rnd, 1800, 0.4, strike=0.4, bright=1.0), 0.25)
    ir = _tile_room(seed)
    return _out(_room(x, ir, 0.32), -1.8, fout=0.08)


def stool_drag(seed):
    rnd = np.random.default_rng(seed)
    total = 1.3
    x = _buf(total)
    sc = L.scrape(rnd, 1.0, 260, 1300, metal=0.0, rate=14.0)
    _put(x, 0.0, S.filt(sc, ("lp", 2600, 2), circular=False) *
         S.ar_env(sec(1.0), 0.06, 0.3), 0.55)
    _put(x, 0.86, L.wood(rnd, 0.4, 110, weight=1.3, hardness=0.6), 0.45)
    ir = _tile_room(seed)
    return _out(_room(x, ir, 0.3), -1.8, fout=0.06)


def radio_on(seed):
    rnd = np.random.default_rng(seed)
    total = 2.0
    x = _buf(total)
    # 开关
    _put(x, 0.0, S.modal(sec(0.15), [900, 1600], [1.0, 0.5],
                         [0.02, 0.012], rnd=rnd), 0.5)
    # 雪花爆音
    st = S.filt(S.white(sec(1.2), rnd), ("bp", 300, 7000, 2), circular=False)
    st *= S.ar_env(sec(1.2), 0.01, 0.4)
    _put(x, 0.06, st, 0.65)
    # 调谐扫频（高频啸叫滑过）
    nsec = sec(0.9)
    t = tarr(nsec)
    f = 3000.0 * (700.0 / 3000.0) ** np.clip(t / 0.8, 0, 1)
    wh = np.sin(S.phase_of(f, nsec)) * S.swell_env(nsec, 0.2, 0.35) * 0.18
    _put(x, 0.06, wh, 1.0)
    # 50Hz 电源声
    _put(x, 0.08, np.sin(TWOPI * 50.0 * tarr(sec(1.0))) * 0.05, 1.0)
    ir = _tile_room(seed)
    return _out(_room(x, ir, 0.22), -2.0, fout=0.08)


def radio_static_loop(seed=9402):
    rnd = np.random.default_rng(seed)
    n = sec(8.0)
    x = L.radio_static(rnd, n, circular=True, hum_amp=0.06)
    x = S.filt(x, ("bp", 240, 8000, 2), circular=True)
    ir = _tile_room(seed)
    x = S.reverb(x, ir, wet=0.2, dry=1.0, circular=True)
    return _out_loop(x, -3.0)


def mirror_breath(seed=9405):
    """8s 循环：澡堂里的呼吸（带瓷砖混响，供引擎危险层使用）。"""
    rnd = np.random.default_rng(seed)
    x = L.breath_loop(rnd, sec(8.0), cycle=4.0, deep=1.0)
    x = S.filt(x, ("hp", 90, 2), ("lp", 7000, 2), circular=True)
    ir = _tile_room(seed)
    x = S.reverb(x, ir, wet=0.22, dry=1.0, circular=True)
    return _out_loop(x)


def mirror_touch(seed):
    rnd = np.random.default_rng(seed)
    total = 1.6
    x = _buf(total)
    # 手指在玻璃上的摩擦（高频、粘滞）
    nsec = sec(0.7)
    t = tarr(nsec)
    fric = S.filt(S.white(nsec, rnd), ("hp", 3500, 2), circular=False)
    fric *= (0.6 + 0.4 * np.sin(TWOPI * 17.0 * t)) * S.swell_env(nsec, 0.15, 0.3)
    _put(x, 0.0, fric, 0.30)
    # 玻璃的共振
    g = L.glass(rnd, 2900 + rnd.random() * 800, 1.2, bright=0.7, strike=0.15)
    _put(x, 0.1, g, 0.25)
    # 极轻的吱
    c = L.creak(rnd, 0.5, 2200, 3800, spike=(0.004, 0.012), metal=1.0, rough=1.3)
    _put(x, 0.2, S.filt(c, ("hp", 1200, 2), circular=False), 0.08)
    ir = _tile_room(seed)
    return _out(_room(x, ir, 0.32), -1.8, fout=0.1)


def glass_crack(seed):
    rnd = np.random.default_rng(seed)
    total = 2.2
    x = _buf(total)
    # 主裂纹：极短的爆裂
    burst = S.filt(S.white(sec(0.25), rnd), ("hp", 1800, 2), circular=False)
    burst *= S.perc_env(sec(0.25), 0.0003, 0.012)
    _put(x, 0.0, burst, 0.9)
    _put(x, 0.0, L.thump(rnd, 0.8, 60, 0.08, body=1.0, click=0.4), 0.5)
    # 碎片飞散
    for _ in range(14):
        t0 = rnd.exponential(0.4)
        g = L.glass(rnd, 2200 + rnd.random() * 4800, 0.5 + rnd.random(),
                    bright=1.2, strike=0.2, decay=0.6)
        _put(x, t0, g, 0.06 + rnd.random() * 0.16)
    ir = _tile_room(seed)
    return _out(_room(x, ir, 0.42), -1.5, fout=0.15)


def doppel_step(seed):
    """替身的脚步：把瓷砖脚步倒放，混响拉长（错位感）。"""
    rnd = np.random.default_rng(seed)
    dur = 0.30 + rnd.random() * 0.1
    base = L.tile(rnd, dur, weight=1.0)
    nsec = base.size
    base = base + S.filt(S.white(nsec, rnd), ("bp", 700, 6000, 2), circular=False) * \
        S.perc_env(nsec, 0.0005, 0.01) * 0.2
    rev = base[::-1].copy()
    rev = S.fade_edges(rev, 0.004, 0.02)
    x = np.concatenate([rev, np.zeros(sec(0.3))])
    _put(x, 0.32, L.thump(rnd, 1.0, 48, 0.16, body=1.0, click=0.05), 0.4)
    ir = _tile_room(seed)
    return _out(_room(x, ir, 0.45), -1.8, fout=0.12)


def doppel_breath(seed=9403):
    """8s 循环：倒放的呼吸（错位的吸气）。"""
    rnd = np.random.default_rng(seed)
    n = sec(8.0)
    x = L.breath_loop(rnd, n, cycle=4.0, deep=1.05)
    x = x[::-1].copy()          # 反转仍是周期信号
    x = S.filt(x, ("hp", 70, 2), ("lp", 5000, 2), circular=True)
    ir = _room_ir(seed, dur=1.4, decay=0.5, lp=3200)
    x = S.reverb(x, ir, wet=0.3, dry=1.0, circular=True)
    return _out_loop(x, -3.0)


def heartbeat_mirror(seed=9404):
    rnd = np.random.default_rng(seed)
    x = L.heartbeat_loop(rnd, sec(10.0), bpm=66.0, strength=1.0)
    x = S.filt(x, ("hp", 26, 2), ("lp", 9000, 2), circular=True)
    return _out_loop(x, -2.5)


def stinger_mirror(seed):
    """玻璃高频音簇 + 反向吸气 + 低频落。"""
    rnd = np.random.default_rng(seed)
    total = 3.0
    x = _buf(total)
    for i, f in enumerate((2200, 2350, 3720, 3950)):
        g = L.glass(rnd, f, 2.0 + i * 0.2, bright=1.0, strike=0.25, decay=1.4)
        _put(x, 0.1 + i * 0.05, g, 0.16)
    sw = S.noise_filtered(sec(1.4), rnd, ("bp", 2000, 9000, 2), circular=False)
    ramp = np.exp(tarr(sec(1.4)) / 0.4)
    ramp /= ramp[-1]
    _put(x, 0.0, sw * ramp, 0.14)
    _put(x, 1.3, L.thump(rnd, 1.4, 46, 0.18, body=1.2, click=0.1), 0.45)
    ir = _tile_room(seed)
    x = S.reverb(x, ir, wet=0.45, dry=1.0, circular=False)
    return _out(x, -1.5, fout=0.2)


def blackout_mirror(seed):
    rnd = np.random.default_rng(seed)
    total = 2.6
    x = _buf(total)
    _put(x, 0.0, S.modal(sec(0.2), [1000, 1750, 2600], [1.0, 0.5, 0.2],
                         [0.018, 0.01, 0.007], rnd=rnd), 0.5)
    nsec = sec(2.0)
    t = tarr(nsec)
    f = 100.0 * (32.0 / 100.0) ** np.clip(t / 1.8, 0, 1)
    hum = (np.sin(S.phase_of(f, nsec)) + 0.5 * np.sin(2 * S.phase_of(f, nsec)))
    hum *= np.exp(-t / 0.85) * (1.0 - np.exp(-t / 0.02))
    _put(x, 0.05, hum, 0.32)
    _put(x, 0.08, L.thump(rnd, 1.8, 42, 0.22, body=1.0, click=0.0), 0.4)
    _put(x, 0.3, L.electric_crackle(rnd, 0.12, 0.7), 0.1)
    ir = _tile_room(seed)
    x = S.reverb(x, ir, wet=0.4, dry=1.0, circular=False)
    return _out(x, -1.5, fout=0.15)


# =========================================================== 夜路 ========
def step_dirt(seed):
    rnd = np.random.default_rng(seed)
    x = L.dirt(rnd, 0.30, weight=1.0 + rnd.random() * 0.3)
    ir = _room_ir(seed, dur=0.45, decay=0.16, lp=2800)
    return _out(_room(x, ir, 0.18), -2.0, fout=0.04)


def step_grass(seed):
    rnd = np.random.default_rng(seed)
    x = L.grass(rnd, 0.32, weight=1.0)
    ir = _room_ir(seed, dur=0.4, decay=0.14, lp=5000)
    return _out(_room(x, ir, 0.14), -2.2, fout=0.04)


def match_strike(seed):
    rnd = np.random.default_rng(seed)
    x = L.match_strike(rnd, 1.0)
    ir = _room_ir(seed, dur=0.5, decay=0.18, lp=4500)
    return _out(_room(x, ir, 0.16), -2.0, fout=0.06)


def lantern_light(seed):
    rnd = np.random.default_rng(seed)
    total = 2.4
    x = _buf(total)
    _put(x, 0.0, L.match_strike(rnd, 0.9), 0.8)
    # 纸灯笼被点着：火苗起来
    nsec = sec(1.8)
    flame = S.filt(S.white(nsec, rnd), ("bp", 300, 3500, 2), circular=False)
    flame *= S.swell_env(nsec, 0.5, 0.4) * 0.5
    _put(x, 0.35, flame, 0.4)
    # 灯笼罩的纸
    _put(x, 0.45, L.paper(rnd, 0.7, density=20, bright=0.7, swells=1), 0.25)
    # 提灯的金属环
    _put(x, 0.6, L.metal(rnd, 2400, 0.5, strike=0.2, bright=1.0), 0.10)
    # 火苗的细碎爆裂
    _put(x, 0.6, L.fire_crackle(rnd, sec(1.4), density=2.0), 0.10)
    ir = _room_ir(seed, dur=1.0, decay=0.35, lp=3000)
    return _out(_room(x, ir, 0.28), -1.8, fout=0.1)


def paper_flutter(seed):
    rnd = np.random.default_rng(seed)
    nsec = 1.3
    x = L.paper(rnd, nsec, density=34, bright=0.9, swells=3)
    # 风带动纸的忽明忽暗
    t = tarr(sec(nsec))
    x = x * (0.55 + 0.45 * np.sin(TWOPI * 2.3 * t + rnd.random() * 3))
    ir = _room_ir(seed, dur=0.8, decay=0.3, lp=3800)
    return _out(_room(x, ir, 0.22), -2.0, fout=0.07)


def entity_rustle(seed):
    rnd = np.random.default_rng(seed)
    total = 2.2
    x = _buf(total)
    # 纸人衣料的移动：纸 + 布 + 极低的呼吸
    p1 = L.paper(rnd, 1.4, density=44, bright=0.85, swells=3)
    _put(x, 0.05, p1, 0.5)
    c1 = L.cloth(rnd, 1.2, density=55, weight=1.0)
    _put(x, 0.15, c1, 0.3)
    # 低频摩擦（纸人身体的拖拽）
    sc = L.scrape(rnd, 1.0, 180, 900, metal=0.0, rate=8.0)
    _put(x, 0.35, S.filt(sc, ("lp", 1400, 2), circular=False), 0.18)
    br = L.breath_loop(rnd, sec(1.4), cycle=1.4, deep=0.7)
    _put(x, 0.4, S.filt(br, ("lp", 1600, 2), circular=False), 0.18)
    ir = _room_ir(seed, dur=1.0, decay=0.35, lp=2600)
    return _out(_room(x, ir, 0.3), -1.8, fout=0.1)


def entity_catch_night(seed):
    rnd = np.random.default_rng(seed)
    total = 2.2
    x = _buf(total)
    # 纸扑过来
    p1 = L.paper(rnd, 0.8, density=70, bright=1.0, swells=2)
    _put(x, 0.0, p1, 0.7)
    # 抓住
    _put(x, 0.18, L.thump(rnd, 1.4, 38, 0.22, body=1.2, click=0.0), 0.65)
    cl = L.cloth(rnd, 0.7, density=80, weight=1.5)
    _put(x, 0.1, S.filt(cl, ("bp", 250, 4500, 2), circular=False), 0.4)
    # 吸气
    gas = S.filt(S.white(sec(0.7), rnd), ("bp", 400, 3000, 2), circular=False)
    _put(x, 0.25, gas * S.swell_env(sec(0.7), 0.2, 0.3, 1.2), 0.35)
    ir = _room_ir(seed, dur=1.4, decay=0.5, lp=2400)
    return _out(_room(x, ir, 0.35), -1.5, fout=0.12)


def shrine_bell(seed):
    rnd = np.random.default_rng(seed)
    total = 6.5
    x = _buf(total)
    b = L.bell(rnd, 105.0, 5.5,
               ratios=[0.5, 1.0, 1.19, 1.51, 2.0, 2.52, 2.98, 4.05],
               amps=[0.6, 1.0, 0.4, 0.36, 0.5, 0.15, 0.1, 0.04],
               strike=0.7, bright=0.7)
    _put(x, 0.0, b, 0.85)
    ir = S.make_ir(seed, dur=3.2, decay=1.3, predelay=0.03,
                   lp=3200, hp=60, taps=20, tap_spread=0.2)
    x = _room(x, ir, 0.4)
    return _out(x, -1.5, fout=0.4)


def metal_bell(seed):
    rnd = np.random.default_rng(seed)
    total = 3.4
    x = _buf(total)
    b = L.bell(rnd, 2450.0, 2.6,
               ratios=[1.0, 1.51, 2.03, 2.62, 3.41, 4.2],
               amps=[1.0, 0.5, 0.38, 0.22, 0.12, 0.06],
               strike=0.35, bright=1.0)
    _put(x, 0.0, b, 0.7)
    _put(x, 0.42, L.bell(rnd, 3300.0, 2.0, strike=0.2, bright=1.0), 0.25)
    ir = _room_ir(seed, dur=1.6, decay=0.7, lp=8000)
    x = _room(x, ir, 0.3)
    return _out(x, -1.8, fout=0.3)


def wind_gust(seed):
    rnd = np.random.default_rng(seed)
    dur = 2.0 + rnd.random() * 1.0
    x = L.wind_gust(rnd, dur, strength=1.0, tone=0.7 + rnd.random() * 0.4)
    ir = _room_ir(seed, dur=1.2, decay=0.4, lp=2600)
    return _out(_room(x, ir, 0.25), -2.2, fout=0.3)


def crow(seed):
    rnd = np.random.default_rng(seed)
    total = 1.8
    x = _buf(total)
    for t0, g in ((0.05, 1.0), (0.62, 0.55)):
        c = L.crow(rnd, 0.45 + rnd.random() * 0.1)
        _put(x, t0, c, g)
    # 远处的空间
    ir = S.make_ir(seed, dur=1.8, decay=0.7, predelay=0.02,
                   lp=1800, hp=120, taps=14, tap_spread=0.2)
    x = _room(x, ir, 0.45)
    return _out(x, -2.0, fout=0.15)


def night_heartbeat(seed=9501):
    rnd = np.random.default_rng(seed)
    x = L.heartbeat_loop(rnd, sec(10.0), bpm=64.0, strength=1.0)
    x = S.filt(x, ("hp", 24, 2), ("lp", 8500, 2), circular=True)
    return _out_loop(x, -2.5)


def night_breath(seed=9502):
    rnd = np.random.default_rng(seed)
    x = L.breath_loop(rnd, sec(8.0), cycle=4.0, deep=1.0)
    x = S.filt(x, ("hp", 100, 2), ("lp", 8000, 2), circular=True)
    ir = _room_ir(seed, dur=1.0, decay=0.3, lp=3600)
    x = S.reverb(x, ir, wet=0.18, dry=1.0, circular=True)
    return _out_loop(x, -3.0)


def night_whisper(seed):
    rnd = np.random.default_rng(seed)
    total = 2.0 + rnd.random() * 0.8
    x = L.whisper(rnd, total, syllables=3 + int(rnd.random() * 4),
                  sib=0.6, pitch=0.9 + rnd.random() * 0.3)
    ir = S.make_ir(seed, dur=1.4, decay=0.5, predelay=0.02, lp=4000,
                   hp=100, taps=12, tap_spread=0.2)
    x = _room(x, ir, 0.4)
    return _out(x, -2.2, fout=0.1)


def night_stinger(seed):
    """纸的尖响 + 低频逼近，不靠巨响。"""
    rnd = np.random.default_rng(seed)
    total = 3.0
    x = _buf(total)
    # 纸的突然摩擦
    pp = L.paper(rnd, 1.2, density=64, bright=1.0, swells=2)
    _put(x, 0.35, pp, 0.5)
    # 不协和高音（小三度 + 三全音）
    for i, m in enumerate((72, 75, 78)):
        g = L.flute_note(rnd, float(S.hz(m)), 2.0, vel=0.5, attack=0.5,
                         release=0.9, breath=0.8)
        _put(x, 0.2 + i * 0.06, g, 0.12)
    # 低频
    _put(x, 0.5, L.thump(rnd, 1.8, 44, 0.22, body=1.2, click=0.05), 0.55)
    # 木头猛紧
    c = L.creak(rnd, 1.2, 200, 520, spike=(0.01, 0.04), rough=0.8)
    _put(x, 0.3, S.filt(c, ("lp", 2600, 2), circular=False), 0.10)
    ir = _room_ir(seed, dur=1.8, decay=0.7, lp=3000)
    x = _room(x, ir, 0.4)
    return _out(x, -1.5, fout=0.2)


def night_blackout(seed):
    rnd = np.random.default_rng(seed)
    total = 2.4
    x = _buf(total)
    # 灯笼熄灭：噗的一声 + 风
    _put(x, 0.0, S.filt(S.white(sec(0.5), rnd), ("lp", 600, 2), circular=False)
         * S.perc_env(sec(0.5), 0.005, 0.09), 0.6)
    _put(x, 0.0, L.thump(rnd, 1.4, 46, 0.2, body=1.0, click=0.0), 0.4)
    wg = L.wind_gust(rnd, 1.6, strength=0.6, tone=0.4)
    _put(x, 0.15, wg, 0.3)
    ir = _room_ir(seed, dur=1.4, decay=0.5, lp=2400)
    x = _room(x, ir, 0.35)
    return _out(x, -1.5, fout=0.15)


# =========================================================== 注册表 ======
ALL = {}

# ---- 门后 ----
for i in range(1, 5):
    ALL[f"door/sfx/step_wood_{i}.ogg"] = (lambda s: lambda: step_wood(s))(1300 + i)
for i in range(1, 4):
    ALL[f"door/sfx/step_carpet_{i}.ogg"] = (lambda s: lambda: step_carpet(s))(1400 + i)
ALL["door/sfx/door_open.ogg"] = lambda: door_open(1501)
ALL["door/sfx/door_close.ogg"] = lambda: door_close(1502)
ALL["door/sfx/door_locked.ogg"] = lambda: door_locked(1503)
ALL["door/sfx/door_unlock.ogg"] = lambda: door_unlock(1504)
ALL["door/sfx/pickup_letter_1.ogg"] = lambda: pickup_letter(1511)
ALL["door/sfx/pickup_letter_2.ogg"] = lambda: pickup_letter(1512)
ALL["door/sfx/pickup_battery.ogg"] = lambda: pickup_battery(1513)
ALL["door/sfx/flashlight_click.ogg"] = lambda: flashlight_click(1514)
ALL["door/sfx/battery_low.ogg"] = lambda: battery_low(1515)
ALL["door/sfx/light_switch.ogg"] = lambda: light_switch(1521)
ALL["door/sfx/light_flicker_1.ogg"] = lambda: light_flicker(1522)
ALL["door/sfx/light_flicker_2.ogg"] = lambda: light_flicker(1523)
ALL["door/sfx/paper_rustle_1.ogg"] = lambda: paper_rustle(1531)
ALL["door/sfx/paper_rustle_2.ogg"] = lambda: paper_rustle(1532)
ALL["door/sfx/clock_tick.ogg"] = clock_tick
ALL["door/sfx/heartbeat.ogg"] = heartbeat
ALL["door/sfx/breath.ogg"] = breath
for i in range(1, 4):
    ALL[f"door/sfx/whisper_{i}.ogg"] = (lambda s: lambda: whisper(s))(1540 + i)
for i in range(1, 3):
    ALL[f"door/sfx/stinger_{i}.ogg"] = (lambda s: lambda: stinger(s))(1560 + i)
ALL["door/sfx/blackout.ogg"] = lambda: blackout(1570)
ALL["door/sfx/entity_breath.ogg"] = entity_breath
for i in range(1, 3):
    ALL[f"door/sfx/entity_step_{i}.ogg"] = (lambda s: lambda: entity_step(s))(1580 + i)
ALL["door/sfx/entity_catch.ogg"] = lambda: entity_catch(1590)

# ---- 镜中 ----
for i in range(1, 5):
    ALL[f"mirror/sfx/step_tile_{i}.ogg"] = (lambda s: lambda: step_tile(s))(2300 + i)
ALL["mirror/sfx/towel_pick.ogg"] = lambda: towel_pick(2401)
for i in range(1, 3):
    ALL[f"mirror/sfx/valve_turn_{i}.ogg"] = (lambda s: lambda: valve_turn(s))(2402 + i)
ALL["mirror/sfx/water_stream.ogg"] = water_stream
ALL["mirror/sfx/water_splash.ogg"] = lambda: water_splash(2410)
ALL["mirror/sfx/switch_click.ogg"] = lambda: switch_click(2421)
for i in range(1, 3):
    ALL[f"mirror/sfx/light_flicker_{i}.ogg"] = \
        (lambda s: lambda: light_flicker_mirror(s))(2422 + i)
for i in range(1, 3):
    ALL[f"mirror/sfx/locker_creak_{i}.ogg"] = \
        (lambda s: lambda: locker_creak(s))(2430 + i)
ALL["mirror/sfx/stool_drag.ogg"] = lambda: stool_drag(2440)
ALL["mirror/sfx/radio_on.ogg"] = lambda: radio_on(2451)
ALL["mirror/sfx/radio_static.ogg"] = radio_static_loop
ALL["mirror/sfx/clock_tick.ogg"] = clock_tick
ALL["mirror/sfx/mirror_touch.ogg"] = lambda: mirror_touch(2461)
ALL["mirror/sfx/glass_crack.ogg"] = lambda: glass_crack(2462)
for i in range(1, 4):
    ALL[f"mirror/sfx/doppel_step_{i}.ogg"] = (lambda s: lambda: doppel_step(s))(2470 + i)
ALL["mirror/sfx/doppel_breath.ogg"] = doppel_breath
ALL["mirror/sfx/breath.ogg"] = mirror_breath
ALL["mirror/sfx/heartbeat.ogg"] = heartbeat_mirror
for i in range(1, 4):
    ALL[f"mirror/sfx/whisper_{i}.ogg"] = (lambda s: lambda: whisper(s))(2490 + i)
for i in range(1, 3):
    ALL[f"mirror/sfx/stinger_{i}.ogg"] = (lambda s: lambda: stinger_mirror(s))(2510 + i)
ALL["mirror/sfx/blackout.ogg"] = lambda: blackout_mirror(2520)

# ---- 夜路 ----
for i in range(1, 5):
    ALL[f"nightroad/sfx/step_dirt_{i}.ogg"] = (lambda s: lambda: step_dirt(s))(3300 + i)
for i in range(1, 4):
    ALL[f"nightroad/sfx/step_grass_{i}.ogg"] = (lambda s: lambda: step_grass(s))(3310 + i)
for i in range(1, 3):
    ALL[f"nightroad/sfx/match_strike_{i}.ogg"] = \
        (lambda s: lambda: match_strike(s))(3320 + i)
for i in range(1, 3):
    ALL[f"nightroad/sfx/lantern_light_{i}.ogg"] = \
        (lambda s: lambda: lantern_light(s))(3330 + i)
for i in range(1, 3):
    ALL[f"nightroad/sfx/paper_flutter_{i}.ogg"] = \
        (lambda s: lambda: paper_flutter(s))(3340 + i)
for i in range(1, 4):
    ALL[f"nightroad/sfx/entity_rustle_{i}.ogg"] = \
        (lambda s: lambda: entity_rustle(s))(3350 + i)
ALL["nightroad/sfx/entity_catch.ogg"] = lambda: entity_catch_night(3360)
ALL["nightroad/sfx/shrine_bell.ogg"] = lambda: shrine_bell(3370)
ALL["nightroad/sfx/metal_bell.ogg"] = lambda: metal_bell(3371)
for i in range(1, 3):
    ALL[f"nightroad/sfx/wind_gust_{i}.ogg"] = (lambda s: lambda: wind_gust(s))(3380 + i)
ALL["nightroad/sfx/crow.ogg"] = lambda: crow(3390)
ALL["nightroad/sfx/heartbeat.ogg"] = night_heartbeat
ALL["nightroad/sfx/breath.ogg"] = night_breath
for i in range(1, 4):
    ALL[f"nightroad/sfx/whisper_{i}.ogg"] = (lambda s: lambda: night_whisper(s))(3400 + i)
for i in range(1, 3):
    ALL[f"nightroad/sfx/stinger_{i}.ogg"] = (lambda s: lambda: night_stinger(s))(3420 + i)
ALL["nightroad/sfx/blackout.ogg"] = lambda: night_blackout(3430)

# ---- shared UI ----
ALL["shared/ui_hover.ogg"] = ui_hover
ALL["shared/ui_click.ogg"] = ui_click
ALL["shared/ui_back.ogg"] = ui_back
ALL["shared/ui_confirm.ogg"] = ui_confirm
