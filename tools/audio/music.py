"""music.py — 9 首氛围音乐（每游戏 main / tension / ending）。

结构原则
- main / tension 是严格周期循环：drone 频率锁相、音符尾音 add_wrapped、
  噪声环形滤波、混响环形卷积；因此首尾无缝。
- ending 是一次性收束曲，线性渲染 + 尾部淡出。
- 音乐性来自手写的动机/和声进行与配器变化，不是噪声堆叠。
"""
from __future__ import annotations

import math

import numpy as np

import soundlib as L
import synth as S
from synth import SR, sec, tarr, TWOPI


# ------------------------------------------------------------ 工具 --------
def _hz(m):
    return float(S.hz(m))


def add_loop(buf, start_s, mono, gain=1.0, pan=0.0):
    """把单声道事件环形叠放到立体声循环缓冲（尾音绕回开头）。"""
    S.add_wrapped(buf, sec(start_s), S.pan(np.asarray(mono, dtype=np.float64), pan), gain)


def add_lin(buf, start_s, mono, gain=1.0, pan=0.0):
    """一次性叠放（越界截断）。"""
    S.add_at(buf, sec(start_s), S.pan(np.asarray(mono, dtype=np.float64), pan), gain)


def finish(x, loop, rms_db=-20.0, fade_in=0.02, fade_out=0.6):
    """循环曲：周期信号直接响度归一；一次性曲：边缘淡入淡出。"""
    if loop:
        return S.finalize_loop(x, target_rms_db=rms_db, ceiling_db=-1.5)
    x = S.dc_block(x)
    x = S.normalize_rms(x, rms_db)
    # 一次性收束曲常有密集碎片/瞬态，Vorbis 解码会过冲约 2 dB，
    # 因此源峰值压到 -3.5 dBFS，确保解码后仍 ≤ -1 dBFS。
    x = S.soft_limit(x, -3.5)
    x = S.fade_edges(np.clip(x, -1.0, 1.0), fade_in, fade_out)
    return x


def _stereo_noise_bed(rnd, n, specs, gain, circular=True, am_rate=None, am_dep=0.0):
    """两声道独立噪声床（宽声场），可选慢速调制。"""
    out = np.zeros((2, n))
    for ch in range(2):
        b = S.noise_filtered(n, rnd, *specs, circular=circular)
        if am_rate:
            rate = S.lock_rate(am_rate, n) if circular else am_rate
            lfo = 0.5 + 0.5 * np.sin(TWOPI * rate * tarr(n) + rnd.random() * TWOPI)
            b = b * (1.0 - am_dep + am_dep * lfo)
        out[ch] = b * gain
    return out


# =========================================================== 门后 ========
def door_main():
    """60s，D 小调。旧屋：失谐八音盒动机 + 低频 drone + 磁带底噪。"""
    rnd = np.random.default_rng(2001)
    n = sec(60.0)
    buf = np.zeros((2, n))
    BEAT = 0.9375          # 64 BPM，4/4，小节 3.75s；16 小节 = 60s

    # --- 低频 drone（D1/D2）+ 极轻的拍频
    buf += S.pan(L.sub_drone(rnd, n, _hz(26), amp=0.40,
                             harmonics=(1.0, 0.30, 0.13, 0.05), beat=0.30), -0.05)
    buf += S.pan(L.sub_drone(rnd, n, _hz(38), amp=0.16,
                             harmonics=(1.0, 0.22, 0.08), beat=0.20), 0.08)

    # --- 低音弦：每两小节一个低音（D2 / Bb1 / G1 / A1）
    bass = [(0, 38), (2, 34), (4, 31), (6, 33),
            (8, 38), (10, 34), (12, 31), (14, 33)]
    for bar, m in bass:
        t0 = bar * 4 * BEAT
        sig = L.string_note(rnd, _hz(m), 2 * 4 * BEAT + 1.2, vel=1.0,
                            attack=0.8, release=1.6, bright=0.35)
        add_loop(buf, t0, sig, 0.13, pan=-0.12)
        fifth = L.string_note(rnd, _hz(m + 7), 2 * 4 * BEAT + 1.0, vel=1.0,
                              attack=1.1, release=1.8, bright=0.3)
        add_loop(buf, t0, fifth, 0.05, pan=0.10)

    # --- 八音盒动机（4 小节一句，16 小节 = 4 句）
    motif_a = [
        (0.0, 74, 1.5, .78), (2.0, 81, .75, .55), (3.0, 77, 1.0, .66),
        (4.5, 76, .5, .48), (5.0, 74, 1.25, .70), (6.5, 69, 1.0, .52),
        (7.5, 72, .5, .58), (8.0, 74, 1.5, .74), (10.0, 82, .75, .58),
        (11.0, 77, 1.0, .62), (12.5, 76, .5, .46), (13.0, 74, 2.0, .68),
        (15.0, 72, .75, .55),
    ]
    motif_b = [
        (0.0, 79, 1.5, .76), (2.0, 86, .75, .52), (3.0, 82, 1.0, .64),
        (4.5, 81, .5, .46), (5.0, 79, 1.25, .68), (6.5, 74, 1.0, .50),
        (7.5, 77, .5, .56), (8.0, 81, 1.5, .72), (10.0, 85, .75, .56),
        (11.0, 81, 1.0, .60), (12.5, 79, .5, .44), (13.0, 76, 2.0, .66),
        (15.0, 73, .75, .50),
    ]
    grace = [(0.0, 74, 1.5, .78), (2.0, 81, .75, .55), (3.0, 77, 1.0, .66),
             (5.0, 74, 1.25, .70), (6.5, 69, 1.0, .52), (7.5, 72, .5, .58),
             (8.0, 74, 1.5, .74), (10.0, 82, .75, .58), (11.0, 77, 1.0, .62),
             (13.0, 74, 2.0, .68), (15.0, 72, .75, .55)]

    def play_motif(events, start_bar, gain, bright=1.0, shadow=False):
        for (b, m, d, v) in events:
            tail = max(1.6, d * BEAT * 2.2)
            sig = L.musicbox(rnd, _hz(m), tail, vel=min(1.0, v * gain), bright=bright)
            pan = float(np.clip((m - 76) / 28.0, -0.30, 0.30))
            add_loop(buf, start_bar * 4 * BEAT + b * BEAT, sig, 0.34, pan)
            if shadow:  # 低八度的幽灵叠音
                sh = L.musicbox(rnd, _hz(m - 12), tail * 1.4, vel=v * 0.22, bright=0.7)
                add_loop(buf, start_bar * 4 * BEAT + b * BEAT + 0.02, sh, 0.34, pan * -1.2)

    play_motif(motif_a, 0, 0.95, bright=0.9)
    play_motif(motif_b, 4, 1.05, bright=1.0, shadow=True)
    # 第三句：前半句 + 留白 + 一个孤零零的低音
    play_motif(grace[:7], 8, 0.72, bright=0.85)
    add_loop(buf, 10 * 4 * BEAT + 2.0 * BEAT,
             L.musicbox(rnd, _hz(62), 3.2, vel=0.42, bright=0.7), 0.34, -0.15)
    play_motif(motif_b, 12, 1.0, bright=1.0, shadow=True)

    # --- 磁带底噪：抖晃 + 缓慢起伏
    hiss = S.pink(n, rnd, circular=True)
    hiss = S.filt(hiss, ("hp", 900, 2), ("lp", 9500, 2), circular=True)
    hiss = S.wobble(hiss, S.lock_rate(0.31, n), depth_s=0.0011, circular=True)
    hiss *= 0.6 + 0.4 * (0.5 + 0.5 * np.sin(TWOPI * S.lock_rate(0.043, n) * tarr(n)))
    buf += S.pan(hiss * 0.030, 0.18)
    rumble = S.filt(S.brown(n, rnd, circular=True), ("lp", 110, 2), circular=True)
    buf += S.pan(rumble * 0.030, -0.1)

    # --- 远处木头的吱呀（稀疏，极轻）
    for t0, p, f in ((12.4, -0.62, (170, 360)), (31.8, 0.58, (150, 300)),
                     (47.2, -0.5, (190, 420))):
        c = L.creak(rnd, 0.9, f[0], f[1], spike=(0.008, 0.03), rough=0.7)
        c = S.filt(c, ("lp", 2200, 2), circular=False)
        add_loop(buf, t0, c, 0.055, p)

    ir = S.make_ir(2001, dur=3.2, decay=0.85, predelay=0.022,
                   lp=4600, hp=90, taps=20, tap_spread=0.12)
    y = S.reverb(buf, ir, wet=0.30, dry=1.0, circular=True)
    y = S.filt(y, ("hp", 24, 2), ("lp", 16000, 2), circular=True)
    y = S.widen(y, 0.12)
    return finish(y, loop=True, rms_db=-20.5)


def door_tension():
    """45s。无旋律：低频脉动 + 金属摩擦 + 心跳暗示。"""
    rnd = np.random.default_rng(2002)
    n = sec(45.0)
    t = tarr(n)
    buf = np.zeros((2, n))

    # --- 低频脉动（40 BPM，lub-dub 心跳暗示）
    period = 1.5
    for i in range(30):
        pos = i * period + 0.02 * math.sin(i * 1.7)
        g = 0.55 + 0.12 * math.sin(i * 0.9)
        lub = L.thump(rnd, 1.2, 44 + rnd.random() * 3, 0.14, body=0.9, click=0.0)
        add_loop(buf, pos, lub, g * 0.75, pan=-0.05)
        dub = L.thump(rnd, 1.0, 40 + rnd.random() * 3, 0.11, body=0.7, click=0.0)
        add_loop(buf, pos + 0.28, dub, g * 0.42, pan=0.08)

    # --- 持续低频 drone（D1 + A1 的纯五度，加入失谐拍频）
    buf += S.pan(L.sub_drone(rnd, n, _hz(26), amp=0.34,
                             harmonics=(1.0, 0.28, 0.10), beat=0.5), -0.04)
    buf += S.pan(L.sub_drone(rnd, n, _hz(33), amp=0.12,
                             harmonics=(1.0, 0.2), beat=0.4), 0.06)

    # --- 不协和：A1 与 Bb1 的极小音差（慢拍）
    tt = tarr(n)
    a = np.sin(TWOPI * S.lock_freq(_hz(33), n) * tt)
    bb = np.sin(TWOPI * S.lock_freq(_hz(34), n) * tt + 0.7)
    buf += S.pan((a + bb) * 0.045, 0.0)

    # --- 金属摩擦：长段、缓慢起伏、不同声像
    for t0, dur, pan, lo, hi in ((1.5, 11.0, -0.45, 600, 2200),
                                 (14.0, 13.0, 0.50, 750, 2900),
                                 (28.5, 12.0, -0.25, 520, 1900)):
        sc = L.scrape(rnd, dur, lo, hi, metal=0.8, rate=9.0)
        sc = S.filt(sc, ("bp", 380, 4200, 2), circular=False)
        env = S.ar_env(sec(dur), dur * 0.35, dur * 0.35)
        add_loop(buf, t0, sc * env, 0.075, pan)
        # 伴随的金属共振（远处管道）
        ring = L.metal(rnd, 1200 + rnd.random() * 600, 4.5,
                       taus=[0.9, 0.7, 0.5, 0.35, 0.25, 0.18, 0.12],
                       strike=0.2, bright=0.5)
        add_loop(buf, t0 + dur * 0.4, ring, 0.050, -pan)

    # --- 稀疏木/金属应力声
    for t0, p in ((7.0, 0.55), (19.5, -0.6), (33.0, 0.4), (41.0, -0.35)):
        c = L.creak(rnd, 1.2, 180 + rnd.random() * 120, 480 + rnd.random() * 300,
                    spike=(0.01, 0.04), metal=0.3, rough=0.8)
        c = S.filt(c, ("lp", 3000, 2), circular=False)
        add_loop(buf, t0, c, 0.085, p)

    # --- 反向渐强（吸气感），两次
    for t0, dur, g in ((9.0, 2.6, 0.10), (30.0, 3.0, 0.13)):
        nn = sec(dur)
        sw = S.noise_filtered(nn, rnd, ("bp", 300, 2600, 2), circular=False)
        ramp = np.exp(tarr(nn) / (dur * 0.35))
        ramp /= max(ramp[-1], 1e-9)
        sw = sw * ramp * S.fade_edges(np.ones(nn), 0.01, 0.04)
        add_loop(buf, t0, sw, g, pan=0.3 if t0 > 20 else -0.3)

    ir = S.make_ir(2002, dur=4.0, decay=1.0, predelay=0.03,
                   lp=3200, hp=70, taps=24, tap_spread=0.16)
    y = S.reverb(buf, ir, wet=0.34, dry=1.0, circular=True)
    y = S.filt(y, ("hp", 22, 2), ("lp", 14000, 2), circular=True)
    return finish(y, loop=True, rms_db=-20.5)


def door_ending():
    """40s。同一八音盒动机放慢、加大混响、逐渐失真。"""
    rnd = np.random.default_rng(2003)
    n = sec(40.0)
    buf = np.zeros((2, n))
    BEAT = 1.25             # 48 BPM，比 main 慢 25%

    # --- 低频 drone（D1），逐渐变暗
    drone = L.sub_drone(rnd, n, _hz(26), amp=0.42,
                        harmonics=(1.0, 0.30, 0.12), beat=0.4)
    buf += S.pan(drone, -0.05)

    motif_a = [
        (0.0, 74, 1.5, .75), (2.0, 81, .75, .5), (3.0, 77, 1.0, .6),
        (4.5, 76, .5, .42), (5.0, 74, 1.25, .66), (6.5, 69, 1.0, .46),
        (7.5, 72, .5, .52), (8.0, 74, 1.5, .7), (10.0, 82, .75, .52),
        (11.0, 77, 1.0, .56), (12.5, 76, .5, .4), (13.0, 74, 2.0, .62),
        (15.0, 72, .75, .48),
    ]
    motif_b = [
        (0.0, 79, 1.5, .7), (2.0, 86, .75, .46), (3.0, 82, 1.0, .58),
        (5.0, 79, 1.25, .6), (6.5, 74, 1.0, .44), (7.5, 77, .5, .5),
        (8.0, 81, 1.5, .64), (10.0, 85, .75, .48), (11.0, 81, 1.0, .54),
        (13.0, 76, 2.0, .6),
    ]

    def place(events, t_start, gain, detune_start, detune_end, drive_start,
              drive_end, lp_end):
        span = max(1.0, (max(e[0] for e in events) + 1.0) * BEAT)
        for (b, m, d, v) in events:
            rel = b * BEAT / span
            det = detune_start + (detune_end - detune_start) * rel
            drv = drive_start + (drive_end - drive_start) * rel
            hz = _hz(m) * 2.0 ** ((det + (rnd.random() * 2 - 1) * 2.0) / 1200.0)
            tail = max(1.8, d * BEAT * 2.6)
            sig = L.musicbox(rnd, hz, tail, vel=v * gain, bright=0.85)
            sig = np.tanh(drv * sig) / np.tanh(drv)
            # 越靠后越暗
            cut = 9000 + (lp_end - 9000) * rel
            sig = S.filt(sig, ("lp", max(900.0, cut), 2), circular=False)
            add_lin(buf, t_start + b * BEAT, sig, 0.36,
                    float(np.clip((m - 76) / 26.0, -0.3, 0.3)))

    place(motif_a, 2.0, 0.95, 0.0, -12.0, 1.0, 1.8, 7500)
    place(motif_b[:7], 22.0, 0.85, -14.0, -38.0, 2.2, 4.0, 3800)
    # 最后的长音（D5），重失真 + 大混响尾
    last = L.musicbox(rnd, _hz(74) * 2 ** (-45 / 1200.0), 9.0, vel=0.75, bright=0.6)
    last = np.tanh(5.0 * last) / np.tanh(5.0)
    last = S.filt(last, ("lp", 2600, 2), circular=False)
    add_lin(buf, 30.5, last, 0.34, 0.0)

    # --- 低频涌动 + 两次闷响
    rumble = S.filt(S.brown(sec(40), rnd, circular=False), ("lp", 95, 2), circular=False)
    rumble *= S.ar_env(n, 4.0, 6.0)
    buf += S.pan(rumble * 0.10, 0.0)
    for t0, g in ((16.5, 0.22), (27.8, 0.30)):
        add_lin(buf, t0, L.thump(rnd, 1.8, 42, 0.22, body=1.0, click=0.0), g, -0.1)

    ir = S.make_ir(2003, dur=5.8, decay=1.9, predelay=0.04,
                   lp=3800, hp=60, taps=26, tap_spread=0.2)
    y = S.reverb(buf, ir, wet=0.45, dry=1.0, circular=False)
    y = S.filt(y, ("hp", 22, 2), ("lp", 13000, 2), circular=False)
    # 整体收束：最后 3 秒淡出（finish 会再叠 0.6s）
    env = S.ar_env(n, 0.05, 3.2)
    y = y * env
    return finish(y, loop=False, rms_db=-20.0, fade_in=0.05, fade_out=1.0)


# =========================================================== 镜中 ========
def _tile_ir(seed, dur=2.8, decay=0.6, tap_ms=48.0, lp=9000):
    """瓷砖/玻璃房间：噪声尾 + 梳状早期反射（flutter echo）。"""
    ir = S.make_ir(seed, dur=dur, decay=decay, predelay=0.006,
                   lp=lp, hp=110, taps=8, tap_spread=0.05)
    rnd = np.random.default_rng(seed + 1)
    n = ir.shape[1]
    for i in range(1, 30):
        pos = sec(i * tap_ms / 1000.0)
        if pos >= n:
            break
        amp = 0.55 * math.exp(-i * 0.10)
        sign = -1.0 if i % 2 else 1.0
        for ch in range(2):
            ir[ch, pos] += sign * amp * (1.0 if ch == 0 else 0.82)
    for ch in range(2):
        ir[ch] = S.filt(ir[ch], ("lp", lp, 2), ("hp", 100, 2), circular=False, pad=4096)
        ir[ch] /= max(math.sqrt(float(np.sum(ir[ch] ** 2))), 1e-9)
    return ir


def mirror_main():
    """60s，A 小调。玻璃/瓷砖混响 + 反向钢琴 + FM 钟声。"""
    rnd = np.random.default_rng(3001)
    n = sec(60.0)
    buf = np.zeros((2, n))
    BEAT = 0.9375
    BAR = 4 * BEAT

    # --- 和声（A 小调：Am - F - Dm - E，每两小节一个和弦）
    chords = [
        (0, [57, 60, 64]), (2, [53, 57, 60]), (4, [50, 53, 57]), (6, [52, 56, 59]),
        (8, [57, 60, 64]), (10, [53, 57, 60]), (12, [50, 53, 57]), (14, [52, 56, 59]),
    ]
    for bar, notes in chords:
        t_land = bar * BAR
        for j, m in enumerate(notes):
            # 反向钢琴：音符在 bar 头「落」下，所以从前面开始渲染并倒置。
            # 倒放后末尾（原起音）只做 12ms 淡出——保留「突然切入」的锐利感。
            tail = 3.0
            p = L.piano(rnd, _hz(m), tail, vel=0.8, bright=0.6)
            rev = p[::-1].copy()
            rev = S.fade_edges(rev, 0.004, 0.012)
            add_loop(buf, t_land - tail + 0.05 * j, rev, 0.16,
                     pan=(j - 1) * 0.28 + 0.05)

    # --- 低频 A 铺底（A1 + E2 五度）
    buf += S.pan(L.sub_drone(rnd, n, _hz(33), amp=0.16,
                             harmonics=(1.0, 0.3, 0.12), beat=0.25), -0.05)
    buf += S.pan(L.sub_drone(rnd, n, _hz(40), amp=0.07,
                             harmonics=(1.0, 0.2), beat=0.2), 0.12)

    # --- FM 钟声：稀疏两三音一组，A 小调五声 + G#
    bells = [
        (15.0, 81, .50, -0.40), (17.2, 76, .38, 0.35), (19.0, 72, .44, -0.10),
        (22.5, 79, .48, 0.45), (24.7, 84, .36, -0.25), (26.2, 76, .40, 0.15),
        (30.0, 81, .52, -0.35), (31.6, 88, .34, 0.40), (33.0, 84, .42, -0.15),
        (37.5, 79, .46, 0.30), (39.0, 76, .38, -0.30),
        (45.0, 81, .44, 0.35), (46.5, 79, .40, -0.35), (48.0, 72, .48, 0.05),
        (52.5, 76, .38, -0.30), (54.0, 84, .40, 0.40), (55.5, 81, .34, -0.2),
    ]
    for t0, m, v, p in bells:
        sig = L.fm_bell(rnd, _hz(m), 3.6, ratio=3.5, index=2.6, vel=v,
                        index_tau=0.5)
        add_loop(buf, t0, sig, 0.20, p)
        body = L.fm_bell(rnd, _hz(m - 12), 4.2, ratio=2.0, index=1.5,
                         vel=v * 0.4, index_tau=0.7)
        add_loop(buf, t0, body, 0.14, -p * 0.5)

    # --- 高频玻璃空气 + 极轻的玻璃应力
    air = _stereo_noise_bed(rnd, n, (("bp", 5200, 11500, 2),), 0.016,
                            am_rate=0.061, am_dep=0.7)
    buf += air
    for t0, p, f in ((8.5, 0.5, (1100, 2400)), (28.0, -0.55, (1400, 3100)),
                     (44.5, 0.4, (900, 2000))):
        c = L.creak(rnd, 1.4, f[0], f[1], spike=(0.006, 0.02), metal=1.0, rough=0.9)
        c = S.filt(c, ("hp", 700, 2), ("lp", 7000, 2), circular=False)
        add_loop(buf, t0, c, 0.045, p)

    # --- 稀疏的低频头音（远处关门）
    for t0, p in ((12.0, -0.3), (36.0, 0.35)):
        add_loop(buf, t0, L.thump(rnd, 2.2, 44, 0.3, body=1.0, click=0.0), 0.10, p)

    ir = _tile_ir(3001, dur=3.0, decay=0.7, tap_ms=48.0, lp=9500)
    y = S.reverb(buf, ir, wet=0.42, dry=1.0, circular=True)
    y = S.filt(y, ("hp", 28, 2), ("lp", 17000, 2), circular=True)
    y = S.widen(y, 0.15)
    return finish(y, loop=True, rms_db=-20.5)


def mirror_tension():
    """45s。高频耳鸣 + 呼吸 + 玻璃应力。"""
    rnd = np.random.default_rng(3002)
    n = sec(45.0)
    t = tarr(n)
    buf = np.zeros((2, n))

    # --- 耳鸣：三条高频正弦，轻微拍频与起伏
    tin = (np.sin(TWOPI * S.lock_freq(4180, n) * t)
           + np.sin(TWOPI * S.lock_freq(4183.1, n) * t + 0.6)
           + 0.45 * np.sin(TWOPI * S.lock_freq(6270, n) * t + 1.7)
           + 0.20 * np.sin(TWOPI * S.lock_freq(8370, n) * t + 0.3))
    tin *= 0.5 + 0.5 * np.sin(TWOPI * S.lock_rate(0.031, n) * t + 0.9)
    buf += S.pan(tin * 0.010, 0.28)
    buf += S.pan(tin * 0.006, -0.3)   # 双耳不对称，制造「颅内」感

    # --- 呼吸层（循环，周期锁相）
    br = L.breath_loop(rnd, n, cycle=4.5, deep=1.0)
    br = S.filt(br, ("hp", 90, 2), circular=True)
    buf += S.pan(br * 0.30, 0.22)
    # 第二层呼吸，稍不同步（也是周期内偏移，仍然可循环）
    br2 = L.breath_loop(rnd, n, cycle=4.5, deep=0.8)
    br2 = S.wobble(br2, S.lock_rate(0.1, n), 0.0006, circular=True)
    buf += S.pan(br2 * 0.16, -0.45)

    # --- 玻璃应力：高频吱嘎 + 偶尔的细小裂纹
    for t0, p, f in ((4.0, -0.45, (1600, 3400)), (13.5, 0.5, (1900, 4200)),
                     (22.0, -0.3, (1400, 3000)), (31.5, 0.42, (2100, 4800)),
                     (39.0, -0.5, (1500, 3600))):
        c = L.creak(rnd, 2.0, f[0], f[1], spike=(0.005, 0.02), metal=1.0, rough=1.0)
        c = S.filt(c, ("hp", 900, 2), ("lp", 8500, 2), circular=False)
        add_loop(buf, t0, c, 0.09, p)
    for t0, p in ((18.0, 0.6), (35.5, -0.55)):
        g = L.glass(rnd, 3800 + rnd.random() * 800, 0.7, bright=1.2, strike=0.4)
        add_loop(buf, t0, S.filt(g, ("hp", 1500, 2), circular=False), 0.05, p)

    # --- 低频：A1 drone + 不协和的 Bb1，缓慢起伏
    swell = 0.55 + 0.45 * np.sin(TWOPI * S.lock_rate(0.022, n) * t - 1.2)
    d1 = L.sub_drone(rnd, n, _hz(33), amp=1.0, harmonics=(1.0, 0.3, 0.12), beat=0.4)
    d2 = L.sub_drone(rnd, n, _hz(34), amp=1.0, harmonics=(1.0, 0.25), beat=0.3)
    buf += S.pan((d1 * 0.11 + d2 * 0.05) * swell, -0.06)

    # --- 玻璃房间空气
    buf += _stereo_noise_bed(rnd, n, (("bp", 3000, 9000, 2),), 0.012,
                             am_rate=0.05, am_dep=0.6)

    ir = _tile_ir(3002, dur=3.6, decay=0.9, tap_ms=44.0, lp=10000)
    y = S.reverb(buf, ir, wet=0.38, dry=1.0, circular=True)
    y = S.filt(y, ("hp", 26, 2), ("lp", 17000, 2), circular=True)
    y = S.widen(y, 0.18)
    return finish(y, loop=True, rms_db=-20.5)


def mirror_ending():
    """35s。镜面碎裂后的长混响尾音。"""
    rnd = np.random.default_rng(3003)
    n = sec(35.0)
    buf = np.zeros((2, n))

    # --- 碎裂前的吸气
    sw = S.noise_filtered(sec(1.6), rnd, ("bp", 500, 5000, 2), circular=False)
    ramp = np.exp(tarr(sec(1.6)) / 0.42)
    ramp /= max(ramp[-1], 1e-9)
    add_lin(buf, 0.0, sw * ramp, 0.22, 0.0)

    # --- 主碎裂：低频冲击 + 高频噪声爆 + 大量高频碎片
    boom = L.thump(rnd, 2.5, 40, 0.35, body=1.2, click=0.1)
    add_lin(buf, 1.0, boom, 0.5, 0.0)
    burst = S.filt(S.white(sec(0.6), rnd), ("hp", 1500, 2), circular=False)
    burst *= S.perc_env(sec(0.6), 0.001, 0.09)
    add_lin(buf, 1.0, burst, 0.30, 0.0)
    for _ in range(26):
        tt = 1.0 + rnd.exponential(0.55)
        f = 2600 + rnd.random() * 4200
        g = L.glass(rnd, f, 0.8 + rnd.random() * 1.8, bright=1.2,
                    strike=0.2 + rnd.random() * 0.4, decay=1.0)
        add_lin(buf, tt, g, 0.10 + rnd.random() * 0.10,
                float(rnd.random() * 2 - 1) * 0.8)

    # --- 碎片陆续掉落（越来越稀）
    shard_times = [2.2, 3.1, 4.4, 6.0, 8.3, 11.0, 14.5, 19.0, 24.5]
    for i, tt in enumerate(shard_times):
        f = 2200 + rnd.random() * 3800
        g = L.glass(rnd, f, 1.2 + rnd.random(), bright=1.0, strike=0.1,
                    decay=1.2)
        add_lin(buf, tt, g, 0.10 * math.exp(-i * 0.16),
                float(rnd.random() * 2 - 1) * 0.7)
    # 玻璃在地面滚动/摩擦的极细声
    for tt in (5.0, 12.5, 21.0):
        c = L.creak(rnd, 1.0, 2600, 4200, spike=(0.004, 0.012),
                    metal=1.0, rough=1.0)
        add_lin(buf, tt, S.filt(c, ("hp", 1500, 2), circular=False), 0.035,
                float(rnd.random() * 2 - 1) * 0.6)

    # --- 低频下落 + 长 drone
    t = tarr(sec(3.2))
    fdrop = 90.0 * (32.0 / 90.0) ** np.clip(t / 3.0, 0, 1)
    drop = np.sin(S.phase_of(fdrop, sec(3.2))) * S.perc_env(sec(3.2), 0.01, 1.1)
    add_lin(buf, 1.0, drop, 0.20, 0.0)
    buf += S.pan(L.sub_drone(rnd, n, _hz(33), amp=0.10,
                             harmonics=(1.0, 0.25), beat=0.3), 0.0) * \
        S.ar_env(n, 3.0, 8.0)

    ir = S.make_ir(3003, dur=8.0, decay=2.8, predelay=0.05,
                   lp=7600, hp=90, taps=30, tap_spread=0.25)
    y = S.reverb(buf, ir, wet=0.48, dry=1.0, circular=False)
    # 再叠一层更长的「房间」，制造巨大空间
    ir2 = S.make_ir(3004, dur=7.0, decay=3.2, predelay=0.12,
                    lp=4200, hp=70, taps=18, tap_spread=0.3)
    y = S.reverb(y, ir2, wet=0.18, dry=1.0, circular=False)
    y = S.filt(y, ("hp", 26, 2), ("lp", 15000, 2), circular=False)
    env = S.ar_env(n, 0.02, 4.0)
    y = y * env
    return finish(y, loop=False, rms_db=-20.0, fade_in=0.05, fade_out=1.2)


# =========================================================== 夜路 ========
def nightroad_main():
    """60s，E 小调。低音弦乐 drone + 气声笛，缓慢。"""
    rnd = np.random.default_rng(4001)
    n = sec(60.0)
    buf = np.zeros((2, n))
    BEAT = 0.9375
    BAR = 4 * BEAT

    # --- 低音弦乐 drone（E1，四个失谐声部）
    dr = L.saw_drone(rnd, n, _hz(28), amp=0.34, voices=4,
                     detune_cents=9.0, lp=430.0, vib_rate=0.11, vib_cents=6.0)
    buf += S.pan(dr, -0.08)
    buf += S.pan(L.sub_drone(rnd, n, _hz(28), amp=0.24,
                             harmonics=(1.0, 0.22, 0.08), beat=0.4), 0.04)

    # --- 每四小节换一次和声低音：Em - C - Am - Bm
    for i, (bar, m) in enumerate(((0, 40), (4, 36), (8, 33), (12, 35))):
        t0 = bar * BAR
        sig = L.string_note(rnd, _hz(m), 4 * BAR + 1.5, vel=1.0,
                            attack=1.6, release=2.2, bright=0.4)
        add_loop(buf, t0, sig, 0.13, pan=0.10)
        fifth = L.string_note(rnd, _hz(m + 7), 4 * BAR + 1.2, vel=1.0,
                              attack=1.9, release=2.4, bright=0.35)
        add_loop(buf, t0, fifth, 0.06, pan=-0.14)

    # --- 气声笛旋律（E 小调五声：E G A B D）
    phrase1 = [(0.0, 71, 2.0, .55), (2.0, 74, 1.75, .5), (3.75, 71, 0.5, .42),
               (4.0, 69, 2.0, .5), (6.25, 67, 0.75, .44), (7.0, 64, 1.5, .5)]
    phrase2 = [(0.0, 76, 2.0, .52), (2.0, 74, 1.0, .46), (3.0, 71, 2.25, .5),
               (5.5, 69, 0.75, .4), (6.5, 67, 1.5, .46)]
    phrase3 = [(0.0, 64, 1.5, .42), (1.75, 67, 1.0, .4), (3.0, 69, 2.5, .44)]
    phrase4 = [(0.0, 71, 1.5, .46), (1.75, 74, 1.0, .42), (3.0, 76, 2.0, .48),
               (5.25, 74, 1.0, .4), (6.5, 71, 2.25, .44)]

    def play_phrase(events, t_start, gain, pan=0.16, breath=0.35):
        for (b, m, d, v) in events:
            dur = max(1.0, d * BEAT * 1.5)
            sig = L.flute_note(rnd, _hz(m), dur, vel=v * gain,
                               attack=0.28, release=0.55,
                               vib_rate=4.0 + rnd.random(), vib_cents=7.0,
                               breath=breath)
            add_loop(buf, t_start + b * BEAT, sig, 0.42, pan)

    play_phrase(phrase1, 1 * BAR, 0.85)
    play_phrase(phrase2, 5 * BAR, 0.95, pan=0.10)
    play_phrase(phrase3, 9 * BAR, 0.65, pan=0.22, breath=0.45)
    play_phrase(phrase4, 12 * BAR, 0.9, pan=0.05)

    # --- 中段低音大提琴对位（E3 / C3 / B2 长音）
    for i, (t0, m) in enumerate(((24.0, 52), (36.0, 48), (48.0, 47))):
        sig = L.string_note(rnd, _hz(m), 7.0, vel=0.7, attack=1.4,
                            release=2.0, bright=0.45, vib_cents=10.0)
        add_loop(buf, t0, sig, 0.075, pan=-0.3)

    # --- 空气声（夜晚的稀薄空气）
    air = _stereo_noise_bed(rnd, n, (("bp", 250, 2600, 2),), 0.028,
                            am_rate=0.037, am_dep=0.55)
    buf += air
    hi_air = _stereo_noise_bed(rnd, n, (("bp", 4000, 9000, 2),), 0.008,
                               am_rate=0.021, am_dep=0.7)
    buf += hi_air

    ir = S.make_ir(4001, dur=3.6, decay=1.1, predelay=0.03,
                   lp=4200, hp=70, taps=18, tap_spread=0.18)
    y = S.reverb(buf, ir, wet=0.36, dry=1.0, circular=True)
    y = S.filt(y, ("hp", 24, 2), ("lp", 15000, 2), circular=True)
    y = S.widen(y, 0.12)
    return finish(y, loop=True, rms_db=-20.5)


def nightroad_tension():
    """45s。纸的摩擦 + 低频逼近 + 不协和音簇。"""
    rnd = np.random.default_rng(4002)
    n = sec(45.0)
    t = tarr(n)
    buf = np.zeros((2, n))

    # --- 纸的摩擦（纸人靠近）
    for t0, dur, p, dens in ((1.0, 5.5, -0.45, 34), (8.0, 6.5, 0.50, 42),
                             (16.0, 5.0, -0.30, 30), (24.5, 7.0, 0.40, 46),
                             (34.0, 6.0, -0.15, 38), (41.0, 4.0, 0.55, 28)):
        pp = L.paper(rnd, dur, density=dens, bright=0.9, swells=3)
        env = S.ar_env(sec(dur), dur * 0.25, dur * 0.3)
        add_loop(buf, t0, pp * env, 0.11, p)

    # --- 低频逼近：两层 sub，幅度缓慢起伏
    env_low = 0.5 - 0.5 * np.cos(TWOPI * S.lock_rate(0.044, n) * t)
    d1 = L.sub_drone(rnd, n, _hz(28), amp=1.0, harmonics=(1.0, 0.3, 0.12), beat=0.4)
    buf += S.pan(d1 * 0.26 * (0.35 + 0.65 * env_low), -0.04)

    # --- 不协和音簇：E2+F2、B2+C3（小二度）缓慢渐强
    cl_env = 0.35 + 0.65 * (0.5 - 0.5 * np.cos(TWOPI * S.lock_rate(0.067, n) * t))
    for m, g in ((40, 1.0), (41, 0.8), (47, 0.55), (48, 0.45)):
        v = L.saw_drone(rnd, n, _hz(m), amp=1.0, voices=2,
                        detune_cents=6.0, lp=900.0, vib_rate=0.17)
        buf += S.pan(v * 0.050 * g * cl_env, 0.30 if m % 2 else -0.30)

    # --- 稀疏的木头/纸的移动
    for t0, p in ((5.0, 0.55), (19.0, -0.6), (30.0, 0.45), (38.5, -0.4)):
        c = L.creak(rnd, 1.1, 160 + rnd.random() * 100, 420 + rnd.random() * 220,
                    spike=(0.01, 0.035), rough=0.7)
        c = S.filt(c, ("lp", 2400, 2), circular=False)
        add_loop(buf, t0, c, 0.07, p)
        pp = L.paper(rnd, 1.6, density=22, bright=0.8, swells=2)
        add_loop(buf, t0 + 0.3, pp, 0.05, -p)

    # --- 两次吸气（身后）
    for t0 in (12.0, 33.0):
        br = L.breath_loop(rnd, sec(9.0), cycle=9.0, deep=1.0)
        br = S.filt(br, ("hp", 100, 2), circular=False)
        add_loop(buf, t0, br, 0.30, 0.35 if t0 < 20 else -0.35)

    ir = S.make_ir(4002, dur=4.0, decay=1.3, predelay=0.03,
                   lp=3400, hp=65, taps=22, tap_spread=0.2)
    y = S.reverb(buf, ir, wet=0.36, dry=1.0, circular=True)
    y = S.filt(y, ("hp", 22, 2), ("lp", 14000, 2), circular=True)
    return finish(y, loop=True, rms_db=-20.5)


def nightroad_ending():
    """40s。庙里的钟声与风声，安静收束。"""
    rnd = np.random.default_rng(4003)
    n = sec(40.0)
    buf = np.zeros((2, n))

    # --- 庙钟：三次敲击，一次比一次轻
    bell_ratios = [0.5, 1.0, 1.19, 1.51, 2.0, 2.52, 2.98, 4.05, 5.1]
    bell_amps = [0.60, 1.0, 0.42, 0.38, 0.55, 0.16, 0.11, 0.05, 0.025]
    for t0, f0, g, dur in ((1.0, 110.0, 0.62, 26.0),
                           (9.5, 110.0, 0.30, 20.0),
                           (20.0, 110.0, 0.15, 14.0)):
        b = L.bell(rnd, f0, dur, ratios=bell_ratios, amps=bell_amps,
                   strike=0.8, bright=0.75)
        add_lin(buf, t0, b, g, 0.0)
    # 钟声的远处回声
    echo = L.bell(rnd, 110.0, 8.0, ratios=bell_ratios, amps=bell_amps,
                  strike=0.2, bright=0.5)
    add_lin(buf, 1.35, S.filt(echo, ("lp", 900, 2), circular=False), 0.10, -0.45)

    # --- 风：低频层 + 两次风阵
    t = tarr(n)
    wind = S.filt(S.white(n, rnd), ("bp", 90, 700, 2), circular=False)
    wind *= 0.55 + 0.45 * np.sin(TWOPI * 0.023 * t + 0.5)
    buf += S.pan(wind * 0.055, -0.2)
    wind2 = S.filt(S.white(n, rnd), ("bp", 1400, 5200, 2), circular=False)
    wind2 *= 0.4 + 0.6 * (0.5 + 0.5 * np.sin(TWOPI * 0.017 * t + 2.0))
    buf += S.pan(wind2 * 0.018, 0.5)
    for t0, dur, g, p in ((4.0, 9.0, 0.20, 0.35), (24.0, 11.0, 0.16, -0.4)):
        wg = L.wind_gust(rnd, dur, strength=1.0, tone=0.8)
        add_lin(buf, t0, wg, g, p)

    # --- 极低的 drone（E1），作为庙的「地」
    buf += S.pan(L.sub_drone(rnd, n, _hz(28), amp=0.13,
                             harmonics=(1.0, 0.2), beat=0.3) * S.ar_env(n, 2.0, 6.0),
                 0.0)

    ir = S.make_ir(4003, dur=5.0, decay=2.0, predelay=0.04,
                   lp=3600, hp=60, taps=24, tap_spread=0.22)
    y = S.reverb(buf, ir, wet=0.40, dry=1.0, circular=False)
    y = S.filt(y, ("hp", 22, 2), ("lp", 14000, 2), circular=False)
    env = S.ar_env(n, 0.1, 4.0)
    y = y * env
    return finish(y, loop=False, rms_db=-20.0, fade_in=0.1, fade_out=1.5)


ALL = {
    "door/music/main.ogg": door_main,
    "door/music/tension.ogg": door_tension,
    "door/music/ending.ogg": door_ending,
    "mirror/music/main.ogg": mirror_main,
    "mirror/music/tension.ogg": mirror_tension,
    "mirror/music/ending.ogg": mirror_ending,
    "nightroad/music/main.ogg": nightroad_main,
    "nightroad/music/tension.ogg": nightroad_tension,
    "nightroad/music/ending.ogg": nightroad_ending,
}
