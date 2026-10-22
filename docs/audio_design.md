# 《三更》音频设计说明书

> 1.4.0 候选增补：窗雨、远水、旷野风三条环境床混入本机 Stable Audio Open 生成层；音乐与其它声音沿用。暂停修复覆盖最终输出。见 [本轮说明](av_iteration_v1.4.md)。下文“所有声音程序化合成”为基础版历史记录。

三个心理恐怖短篇（《门后》《镜中》《夜路》）的原创音频资产设计、合成方法与自检说明。
所有声音均由 Python（numpy）程序化合成，ffmpeg/libvorbis 编码，**无任何外部下载素材**。

- 生成脚本：`tools/audio/`（`synth.py` / `soundlib.py` / `music.py` / `ambience.py` / `sfx.py` / `build.py` / `verify.py`）
- 资产目录：`assets/audio/{shared,door,mirror,nightroad}/`
- 自检报告：`reports/audio/verify.txt`、`analysis.txt`、波形图 `waveforms_music.png`、`waveforms_ambience.png`
- 复现：`python tools/audio/build.py all`（固定 seed，逐比特可复现）；`python tools/audio/verify.py all` 重跑自检

---

## 1. 声音设计原则

1. **恐怖来自低频身体感、错位与留白，不靠巨响。** 没有 jump-scare 式爆音；stinger 是缓慢的不协和音簇 + 低频气压，峰值与其它音效一致（约 -2 dBFS），响度靠音乐让位。
2. **可长期听的环境层。** 环境声都有近场/远场、左右声像差异与缓慢起伏；避免长时间单一白噪声。
3. **材质优先。** 木头、金属、纸、布、水、呼吸全部用模态合成 + 滤波噪声 + 颗粒噪声建模，几乎不用「电子游戏式」正弦哔声。
4. **音乐是氛围音乐。** 慢速、无强节拍、可循环；每首有可听的动机与和声进行。tension 不与 main 抢频段，可叠放。
5. **人声只做呼吸/气声/低语噪声。** 无 TTS、无可辨识词句，语义由游戏字幕承担。
6. **留 headroom。** 音乐/环境目标 RMS 约 -20.5 dBFS，峰值 ≤ -1.5 dBFS（文件实测峰值均 ≤ -1.57），引擎叠加心跳/紧张层不会削波。

## 2. 技术方案

### 2.1 合成核心（`synth.py`）

| 模块 | 方法 |
|---|---|
| 滤波 | 零相位 Butterworth 幅度响应（频域相乘）：一阶/二阶低通、高通、带通、二阶谐振（res）；循环素材用环形 FFT，一次性素材加零填充 |
| 噪声 | 白噪声、粉红（1/√f）、棕噪（1/f）、频谱整形噪声，统一 RMS 归一 |
| 材质 | 阻尼正弦模态叠加（`modal`）：木头/金属/玻璃/瓷砖的不同非谐分音组、不同衰减时间；配合噪声 thump / click 层 |
| 吱呀（stick-slip） | 移动共振中心 + 随机间隔脉冲激励（`creak`）：每次「粘滑」事件是一小段衰减模态，形成门轴/柜门的颗粒感 |
| 纸/布 | 颗粒噪声云：每颗粒 1–10 ms 带通噪声，随机中心频率/幅度/位置 + 低频揉搓层 |
| 水 | 上滑音高气泡（`water_drop`）、水滴群、分层带通噪声水流、气泡颗粒 |
| 呼吸/低语 | 带通噪声 + 共振峰滤波 + 音节包络（无基频词句） |
| 乐器 | 八音盒（非谐分音+亮起音）、加法钢琴（含非谐性，可倒放）、FM 钟、弓弦（加法锯齿+颤音+弓噪）、气声笛、sub drone、失谐弦乐 drone |
| 混响 | 程序化脉冲响应（指数衰减噪声 + 早期反射抽头 + 低通），FFT 卷积（线性/环形） |
| 电平 | 去直流 → RMS/峰值归一 → 无记忆 tanh 软限幅（不破坏循环）→ 峰值夹取 |

### 2.2 无缝循环的做法（关键）

不使用「首尾交叉淡化」这种近似手段，而是**让素材在数学上严格周期**：

1. 持续音 / LFO 的频率锁定到循环长度 L 的整数倍频率：`lock_freq(f, n) = round(f·n/SR)·SR/n`，一个循环恰好是整数个周期；
2. 音符尾音用 `add_wrapped` **环形叠放**：超出末尾的衰减尾巴绕回开头，循环点就是同一条自然衰减曲线的延续；
3. 噪声床用**环形滤波**（对整段做 rfft → 乘传递函数 → irfft），结果天然是周期信号；
4. 混响用**环形卷积**，长尾同样绕回开头，跨循环点时混响是连续的；
5. 电平处理只用无记忆函数（常数增益 / tanh / 直流去除），不引入时变增益；
6. 一次性素材（音乐 ending 等）走线性路径 + 尾部淡出。

验证指标 `jump_rel = |x[0] - x[-1]| / rms(diff)`：把接缝跳变与「正常相邻样本差」比较。真实爆音会是几十以上；本套资产平均 0.9、最差 < 4，即与普通波形无异（见 `verify.txt`）。

### 2.3 编码与电平校准

- 音乐：立体声 44100 / OGG Vorbis **q5**；环境：立体声 q4；音效/UI：单声道 q4。
- 时长按规格精确截断（如 main 恰好 60.00s = 16 小节 × 3.75s）。
- Vorbis 对极短瞬态会有 0.5–1.6 dB 的峰值损失。因此单声道音效/UI 在 `build.py` 里做**闭环电平校准**：编码 → 解码测峰值 → 调增益再编码（最多 2 次），并把源峰值限制在 -1.2 dBFS 内，保证解码后峰值落在 -3 ~ -1 dBFS 规格区间。
- 固定随机种子：每个文件用固定 seed（见各生成函数），重跑输出一致。

---

## 3. 资产总览

| 分组 | 音乐 | 环境 | 音效 | UI | 合计 | 时长 |
|---|---|---|---|---|---|---|
| shared | — | — | — | 4 | 4 | 0.6s |
| door《门后》 | 3 | 4 | 34 | — | 41 | 316.9s |
| mirror《镜中》 | 3 | 4 | 32 | — | 39 | 316.8s |
| nightroad《夜路》 | 3 | 4 | 30 | — | 37 | 319.3s |
| **合计** | **9** | **12** | **96** | **4** | **121** | **953.7s（15.9 min）** |

manifest 引用文件全部存在（`verify.txt` 逐条核对，无缺失、无孤儿文件）。

### manifest 与引擎接口

每个游戏目录一份 `manifest.json`（格式见 `docs/AUDIO_SPEC.md` §2），`shared/manifest.json` 说明共用 UI。

| 分组 | music | ambience 键 | ui 路径 |
|---|---|---|---|
| door | main 60s / tension 45s / ending 40s | corridor / roomTone / rainWindow / tvStatic | `../shared/ui_*.ogg` |
| mirror | main 60s / tension 45s / ending 35s | fluorescent / waterDrip / distantWater / steamHiss | `../shared/ui_*.ogg` |
| nightroad | main 60s / tension 45s / ending 40s | windField / insects / nightRoomTone / distantDog | `../shared/ui_*.ogg` |

- `music.main` / `music.tension` 均 `loop: true`，`ending` 为 `loop: false`（一次性收束曲，带 fade）。
- sfx 多文件条目用 `files` 数组（引擎随机挑选）：脚步、耳语、灯闪、拾取、实体脚步/摩擦等。
- 需要循环的 sfx 条目带 `"loop": true`：`clockTick`、`heartbeat`、`breath`、`entityBreath`、`waterStream`、`radioStatic`、`doppelBreath`。
- `door` 的 sfx 键：stepWood / stepCarpet / doorOpen / doorClose / doorLocked / doorUnlock / pickupLetter / pickupBattery / flashlightClick / batteryLow / lightSwitch / lightFlicker / paperRustle / clockTick / heartbeat / breath / whisper / stinger / blackout / entityBreath / entityStep / entityCatch
- `mirror` 的 sfx 键：stepTile / towelPick / valveTurn / waterStream / waterSplash / switchClick / lightFlicker / lockerCreak / stoolDrag / radioOn / radioStatic / clockTick / mirrorTouch / glassCrack / doppelStep / doppelBreath / heartbeat / breath / whisper / stinger / blackout
- `nightroad` 的 sfx 键：stepDirt / stepGrass / matchStrike / lanternLight / paperFlutter / entityRustle / entityCatch / shrineBell / metalBell / windGust / crow / heartbeat / breath / whisper / stinger / blackout

> 引擎 `AudioManager.setThreat()` 会查找 `sfx.heartbeat` 与 `sfx.breath` 作为危险层，三个 manifest 里这两个键都齐备（mirror 的 `breath` 是澡堂呼吸循环 8s，为引擎危险层补的；规格清单未强制但引擎需要）。
> `playMusic()` 目前对 music 一律 `loop: true`；`ending` 在 manifest 里是 `loop: false`，建议游戏进入结局静态页后调用 `stopMusic()`，或引擎按 `entry.loop` 决定是否循环。

---

## 4. 共用 UI（shared）

| 文件 | 时长 | 设计 |
|---|---|---|
| `ui_hover.ogg` | 0.085s | 3.1–4.7 kHz 短促模态点 + 极轻高频噪声，近乎「耳语式」的确认，不抢注意力 |
| `ui_click.ogg` | 0.11s | 1.25/2.1/3.4 kHz 木质短击 + 180 Hz 体感，明确的「按下去」 |
| `ui_back.ogg` | 0.18s | 两声下行轻点（1.5 kHz → 1.08 kHz），有「退回」的方向感 |
| `ui_confirm.ogg` | 0.26s | 两个 FM 小钟上行（D5→A5），微弱、克制，不形成欢快感 |

UI 峰值约 -3.7 ~ -4.7 dBFS（轻），manifest 再乘 0.35–0.5。

---

## 5. 《门后》DOOR

主题：回家、等待、没说出口的话；2000 年前后老公寓五楼走廊与 503 室。

### 5.1 音乐

**`music/main.ogg` — 60.0s，D 小调，64 BPM（4/4，16 小节）**

- 动机 A（4 小节，D 音起，D5–A5–F5–E5–D5…）落在 Dm→Bb 和声上；动机 B 是它的回答（G5–D6–Bb5–A5…），落在 Gm→A（含 C# 导音）上。
- 结构：A（第 1–4 小节）→ B + 低八度幽灵叠音（5–8）→ A 前半句 + **两小节留白** + 一个孤零零的低音 D4（9–12）→ B（13–16）。留白是这首的「呼吸」。
- 配器：八音盒（非谐分音、亮起音、轻微失谐）、每两小节一个低音弦（D2/Bb1/G1/A1）与五度泛音、D1/D2 sub drone、粉红噪声磁带底噪（0.31 Hz 抖晃 + 0.043 Hz 起伏）、棕噪房间底噪、3 声极轻的远处木头吱呀。
- 混响 3.2s（走廊/旧屋），wet 0.30。

**`music/tension.ogg` — 45.0s，无旋律**

- 40 BPM 的低频脉动（lub-dub）＝心跳暗示；D1+A1 drone；A1/Bb1 极小二度的慢拍。
- 三段 11–13s 的金属摩擦（左右交替声像）+ 远处管道共振；4 声木/金属应力；2 次反向渐强（吸气感）。
- 混响更暗更长（4.0s，lowpass 3.2 kHz），与 main 叠放时不抢八音盒频段。

**`music/ending.ogg` — 40.0s，不循环**

- 动机 A / B 放慢到 48 BPM；音高逐音下漂（0 → -12 音分，后段 -14 → -38 音分）；tanh 失真从 1 增到 4；低通从 7.5 kHz 收到 2.6 kHz。
- 混响 5.8s、wet 0.45；低频涌动 + 两次闷响；最后是一个被压暗的长 D5 落进混响，尾部淡出。

### 5.2 环境

| 文件 | 长度 | 内容与层次 |
|---|---|---|
| `corridor_hum.ogg` | 30s | 日光灯 100/100.6 Hz 双嗡鸣（谐波列、慢拍）为中心；远处楼梯间低频脚步与关门（进湿声层，走廊混响 2.6s）；5 声近场电流噼啪（随机声像）；建筑低频底噪 |
| `room_tone.ogg` | 30s | 50 Hz 室内嗡鸣 + 低噪；每秒一次钟表 tick/tock（交替 1750/1520 Hz，偏右）；窗外雨（带通 600–3600 Hz、低通 2.8 kHz，左右去相关，慢速起伏）；少量水滴进湿声层；2 声房子木头应力 |
| `rain_window.ogg` | 30s | 贴窗雨：1.2–9 kHz 与 300–2400 Hz 两层雨声 + 玻璃共振 380–900 Hz；320 个雨滴颗粒随机左右；4 个大水滴/排水管声；几乎不加混响（近场） |
| `tv_static.ogg` | 15s | 电视雪花（带通 300–7500 Hz、亮度抖动）、偏左 -0.3 声像；CRT 行频 15.675 kHz 与 7.85 kHz 极轻啸叫；50 Hz 电源嗡；可开关的低音量层 |

### 5.3 音效（34 个）

- **脚步**：`step_wood_1..4` 木头模态（6 组非谐分音 + 低频体感 + 起音脆点 + 0.55s 走廊反射），f0 与衰减随机；`step_carpet_1..3` 低通噪声闷响 + 70/105 Hz 体感。
- **门**：`door_open` 双层吱呀（移动共振中心 + stick-slip 脉冲群 + 门板低频应力 + 底部摩擦，2.6s）；`door_close` 低频撞 + 木头模态 + 门框金属件 + 把手回弹；`door_locked` 四次金属把手咔哒 + 锁芯顶死闷响；`door_unlock` 钥匙刮擦 + 两次金属咔哒 + 门闩滑开 + 落位。
- **拾取/手电**：`pickup_letter_1..2` 纸的颗粒云 + 布料；`pickup_battery` 塑料/金属小件；`flashlight_click` 两段金属+塑料 click；`battery_low` 118 Hz 断续嗡鸣（电压不足）。
- **灯**：`light_switch` 塑料 click + 起辉电火花；`light_flicker_1..2` 100 Hz 嗡鸣被 21 Hz 快速通断 + 三处电流噼啪。
- **纸/钟**：`paper_rustle_1..2` 揉纸颗粒云 + 布料；`clock_tick` 2s 循环 tick-tock（60 BPM）。
- **心跳/呼吸**：`heartbeat` 10s 循环（60 BPM，lub-dub + 37 Hz 极低频）；`breath` 8s 循环（4s 一次吸/呼）。
- **人声**：`whisper_1..3` 共振峰噪声音节 + 擦音，3–7 个音节，无可辨识词句。
- **刺点**：`stinger_1..2` 不协和音簇（小二度/三全音）缓慢渐强 + 反向吸气 + 低频气压 + 高频擦弦；**刻意不炸**。
- **断电**：`blackout` 开关咔 + 100→30 Hz 下滑嗡鸣 + 低频余韵 + 最后一下噼啪。
- **实体**：`entity_breath` 10s 循环（5s 一次、更低更湿、46 Hz 体感）；`entity_step_1..2` 38 Hz 湿重落步 + 木头 + 拖拽摩擦；`entity_catch` 猛吸气 + 抓住布料 + 低频压迫。

---

## 6. 《镜中》MIRROR

主题：自我、替身、留下的人；90 年代公共澡堂更衣室（瓷砖、长镜、储物柜、水汽、日光灯）。

### 6.1 音乐

**`music/main.ogg` — 60.0s，A 小调**

- 和声：Am – F – Dm – E，每两小节一个和弦（16 小节循环）。
- 反向钢琴：每个和弦的钢琴音先渲染 3.0s 长尾再**倒置**，让「渐强」结束在强拍上（这是全曲的骨架，也是「镜子里的时间方向反了」的隐喻）；和弦音之间错开 50ms 形成琶音。
- FM 钟声：稀疏的两三音组，A 小调五声 + 导音 G#，左右交替声像；高八度与低八度各一层。
- 瓷砖混响：自制 IR = 噪声尾 + 48ms 间隔梳状早期反射（flutter echo），wet 0.42，空间明亮。
- 另有 A1/E2 铺底、5.2–11.5 kHz 高频空气、3 声玻璃应力、2 声远处低频闷响。

**`music/tension.ogg` — 45.0s**

- 耳鸣：4180 / 4183.1 / 6270 / 8370 Hz 四条极轻正弦（拍频约 3 Hz），双耳不对称声像制造「颅内」感，慢速起伏。
- 两层不同步的呼吸循环（4.5s 周期，其中一层加抖晃）；5 声玻璃应力吱嘎（1.4–4.8 kHz）、2 声玻璃细鸣；A1 + Bb1 drone 缓慢起伏；瓷砖混响 3.6s。

**`music/ending.ogg` — 35.0s，不循环**

- 前 1.6s 反向吸气 → 1.0s 镜面碎裂（低频冲击 + 高频爆 + 26 片高频碎片）→ 双层大混响（8s + 7s）。
- 之后 9 次越来越稀的碎片掉落、玻璃在地面滚动的细响、低频 90→32 Hz 下落；尾音在 33s 后淡出。

### 6.2 环境

| 文件 | 长度 | 内容与层次 |
|---|---|---|
| `fluorescent_buzz.ogg` | 20s | 100/100.9 Hz 双嗡鸣（偏右）+ 灯管震动细噪（3.2–9.5 kHz，0.24 Hz 调制）；6 声启辉器噼啪；一次灯管重启低频；远处澡堂水管低频与气泡 |
| `water_drip.ogg` | 30s | 湿瓷砖房间：平均 1.9s 一次水滴（随机音高/声像/幅度），进 3.4s 大混响；3 个大水滴；低层水流空气 |
| `distant_water.ogg` | 30s | 远处澡堂水流：带通 350–2600 Hz + 低通 2.4 kHz（空气吸收）、慢速起伏；气泡/翻涌颗粒；蒸汽嘶声；宽声场 |
| `steam_hiss.ogg` | 15s | 蒸汽嘶声（>2.8 kHz）、管道共振 1.83/2.74/3.96 kHz、水滴被吹动；可开关 |

### 6.3 音效（32 个）

- **脚步**：`step_tile_1..4` 瓷砖硬击 + 湿脚步噪声 + 瓷砖混响。
- **水**：`water_stream` 10s 循环（三层带通噪声 + 气泡）；`water_splash`；`valve_turn_1..2` 金属阀门吱嘎 + 水锤；`distant_water` 见环境。
- **更衣室**：`towel_pick` 布料 + 轻抽；`locker_creak_1..2` 金属吱呀 + 柜门到位；`stool_drag` 木头拖地 + 落位；`switch_click`；`light_flicker_1..2`（100 Hz 蜂鸣 + 快速通断）；`clock_tick` 2s 循环。
- **收音机**：`radio_on` 开关 + 雪花 + 调谐扫频；`radio_static` 8s 循环。
- **镜子/玻璃**：`mirror_touch` 手指摩擦 + 玻璃共振 + 极轻吱声；`glass_crack` 主裂纹 + 14 片碎片 + 瓷砖混响。
- **替身**：`doppel_step_1..3` 瓷砖脚步**倒放** + 加长混响（错位感）；`doppel_breath` 8s 循环（倒放的呼吸）。
- **危险层**：`heartbeat` 10s 循环 66 BPM；`breath` 8s 循环（澡堂混响，供引擎危险层）。
- **其它**：`whisper_1..3`；`stinger_1..2`（玻璃高频音簇 + 反向吸气 + 低频落）；`blackout`（灯管断电下滑音）。

---

## 7. 《夜路》NIGHTROAD

主题：送葬、乡野志怪、回头；深夜乡道：土路、稻田、电线杆、纸钱、田埂、土地庙。

### 7.1 音乐

**`music/main.ogg` — 60.0s，E 小调，64 BPM（16 小节）**

- 低音弦乐 drone：E1 四个失谐声部（±9 音分）+ 慢颤音，低通 430 Hz；叠加 E1 sub。
- 和声：Em – C – Am – Bm，每四小节换一次低音弦（E2/C2/A1/B1 + 五度）。
- 气声笛旋律（E 小调五声：E G A B D）：四句，长音为主、有换气留白；第 9 小节起低音大提琴加入对位（E3/C3/B2 长音，偏左）。
- 空气声两层（250–2600 Hz 与 4–9 kHz，慢速起伏）；混响 3.6s。

**`music/tension.ogg` — 45.0s**

- 纸的摩擦：6 段 4–7s 的长纸声（颗粒密度不同、左右交替）——「纸人在靠近」。
- 低频逼近：E1 以 0.044 Hz 缓慢起伏加大；不协和音簇 E2+F2、B2+C3（小二度）以 0.067 Hz 渐强。
- 4 声木头/纸的移动、2 次吸气；混响 4.0s。

**`music/ending.ogg` — 40.0s，不循环**

- 庙钟 f0 = 110 Hz（含 hum 0.5、prime、tierce 等非谐分音），敲三次、一次比一次轻（1s / 9.5s / 20s），远处回声。
- 风力两层 + 两次风阵；极低 E1 drone；混响 5.0s；35s 后安静收束。

### 7.2 环境

| 文件 | 长度 | 内容与层次 |
|---|---|---|
| `wind_field.ogg` | 30s | 三层风（80–520 / 420–2100 / 2.2–8 kHz 草叶）+ 两次远景风阵；左右独立噪声、两条不同速率的阵风包络；极低频底 |
| `insects.ogg` | 30s | 三种秋虫（4650 / 4050 / 5300 Hz，不同脉冲率、不同声像），成簇出现、簇间留白；夜风底 |
| `night_room_tone.ogg` | 30s | 「极低」环境底噪：<55 Hz 地鸣、微弱空气、极疏的木头收缩声；几乎只有低频，RMS 刻意维持在规格下限 |
| `distant_dog.ogg` | 12s | 远处狗吠 2–3 声（带音高下滑的「汪」），远距低通 1.6 kHz + 混响；稀疏 |

### 7.3 音效（30 个）

- **脚步**：`step_dirt_1..4` 碎石颗粒 + 低频落步；`step_grass_1..3` 高频草叶沙沙 + 细颗粒。
- **火/灯**：`match_strike_1..2` 摩擦 → 点燃 → 火苗；`lantern_light_1..2` 火柴 + 纸灯笼着火的低频火苗 + 纸 + 提灯金属环 + 火苗爆裂；`metal_bell` 小风铃/灯笼金属声；`shrine_bell` 土地庙大钟（6.5s）。
- **纸**：`paper_flutter_1..2` 被风带动的纸（AM 忽明忽暗）；`entity_rustle_1..3` 纸人衣料（纸 + 布 + 拖拽 + 极低呼吸）。
- **实体**：`entity_catch` 纸扑过来 + 抓住 + 吸气。
- **环境音效**：`wind_gust_1..2`；`crow`（两声「嘎」，远处混响）。
- **心跳/呼吸/人声/刺点**：`heartbeat` 10s 循环 64 BPM；`breath` 8s 循环；`whisper_1..3`；`stinger_1..2`（纸的突然摩擦 + 不协和高音 + 低频逼近 + 木头猛紧）；`blackout`（灯笼熄灭：噗 + 低频 + 风）。

---

## 8. 响度与格式（实测见 `verify.txt`）

| 类型 | 声道 | 采样率 | 编码 | 实测峰值 | 实测 RMS |
|---|---|---|---|---|---|
| 音乐 | 2 | 44100 | Vorbis q5 | -10.4 ~ -1.24 dBFS | -20.50 ~ -19.96 dBFS |
| 环境 | 2 | 44100 | Vorbis q4 | -10.5 ~ -2.8 dBFS | -22.01 ~ -20.51 dBFS |
| 音效 | 1 | 44100 | Vorbis q4 | -2.95 ~ -1.10 dBFS | 依材质而定 |
| UI | 1 | 44100 | Vorbis q4 | -4.7 ~ -3.7 dBFS | 轻 |

循环素材接缝 `jump_rel` 平均 0.91、最差 3.71（阈值 6），听感上无爆音。
`verify.txt` 同时核对：codec=vorbis、采样率、声道、时长、manifest 引用文件是否存在、孤儿文件。
`analysis.txt` 补充客观听感指标：各频段能量、频谱质心/平坦度、逐秒动态范围、立体声相关。

### 8.1 客观分析摘要（`reports/audio/analysis.txt`）

- **音乐是调性的**（频谱平坦度 ≈ 0.000–0.003，远低于噪声），三首 main 的逐秒动态范围 7.3–9.0 dB，说明有乐句起伏而非平铺；ending 的动态范围 26–64 dB，符合「长衰减 / 收束」设计。
- 频段平衡：door main 的八音盒动机在 mid 段 ≈ -29.7 dB，sub/low drone ≈ -23/-26 dB——低频绝对能量更大，但按等响曲线（40 Hz 约需 +34 dB 才等响于 600 Hz），人耳听到的旋律与低频体感是平衡的。
- **环境声有空间宽度**：雨/水/风/虫的 L/R 相关系数 0.09–0.52（宽声场），而日光灯嗡鸣 / 电视雪花 / 房间底噪为 0.94–0.99（点声源，集中），层次符合场景。
- 玻璃/瓷砖房间用梳状早期反射 IR，镜中 main 的「反向钢琴落点和弦」在波形图上呈清晰的周期切入结构。

## 9. 已知不足 / 后续可改进

1. **无法主观试听**：本套资产由生成脚本 + 客观指标（峰值/RMS/接缝/频谱/动态）验收，未经过真人盲听。个别音色（如纸的低频揉搓、金属摩擦）可能仍需要按实际场景音量再平衡；引擎可用 manifest 的 volume 快速微调。
2. **tension 与 main 的叠放比例**由引擎交叉淡化控制，manifest 给了建议 volume（0.50 / 0.45），实际以游戏内混音为准。
3. **whisper 不追求可辨识**：按规格只做气声/低语噪声，若剧情需要「听不清但像人声」的更强暗示，可再提高共振峰锐度。
4. **sfx 单声道**：按 AUDIO_SPEC 单声道交付，左右声像由引擎（WebAudio Panner）负责，故素材本身无立体声定位。
5. **Vorbis 瞬态损失**：已用闭环电平校准补偿（单声道音效/UI 编码后回读峰值再调增益，最多 2 次）；收束曲（密集碎片）源峰值压到 -3.5 dBFS，避免解码过冲越过 -1 dBFS。
6. **ambience 循环里的随机事件**（脚步、水滴、虫鸣）在极长播放时会听出「同一段重复」，建议引擎按 2–4 条 ambience 交叉淡化或轻微改变播放速率来稀释；本套素材已把循环长度拉到 30s。
7. **极短音效的时长**（0.09–0.3s）在 WebAudio 中若以非零音量立即停止，可能产生尾部咔声，建议引擎在 stop 时做 5–10 ms 增益斜坡（素材本身已做淡出）。

## 10. 复现与自检命令

```powershell
$py = "python"
cd <repository-root>

# 全部生成（固定 seed，覆盖写入）
& $py tools\audio\build.py all

# 单个游戏 / 单个文件
& $py tools\audio\build.py door
& $py tools\audio\build.py door --match=door/sfx/heartbeat

# 自检（写 reports/audio/verify.txt + 波形图）
& $py tools\audio\verify.py all --png

# 客观听感分析（写 reports/audio/analysis.txt）
& $py tools\audio\analyze.py
```

脚本清单：

| 文件 | 作用 |
|---|---|
| `tools/audio/synth.py` | DSP 核心：滤波/噪声/包络/模态/混响/环形叠放/电平/编码/ffprobe |
| `tools/audio/soundlib.py` | 材质、乐器、纹理发生器（木头/金属/纸/水/呼吸/风/虫/钟…） |
| `tools/audio/music.py` | 9 首音乐（每游戏 main / tension / ending） |
| `tools/audio/ambience.py` | 12 条环境循环 |
| `tools/audio/sfx.py` | 95 个音效 + 4 个 UI |
| `tools/audio/build.py` | 编码、自适应电平校准、manifest 写出、分组构建 |
| `tools/audio/verify.py` | ffprobe + 解码实测自检、报告与波形图 |
| `tools/audio/analyze.py` | 客观听感分析（频段/质心/动态/立体声宽度） |
| `tools/audio/selftest_*.py` | 开发期单测（发生器 / 音乐 / 床） |
