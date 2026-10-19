# 《三更》音频规格（给音频 agent）

目标：为三个 demo 各做一套 **原创、可循环、低信噪** 的恐怖音频资产。全部用 Python 合成（numpy）+ ffmpeg 编码，脚本可复现。禁止下载外部素材。

## 0. 工具与路径

- Python 解释器（带 numpy/Pillow）：`python`
- ffmpeg 在 PATH（可 `ffmpeg -encoders | findstr vorbis` 验证 libvorbis）。
- 生成脚本写在 `tools/audio/`（建议 `build_audio.py` + `synth.py`，固定随机种子）。
- 输出根目录：`assets/audio/`，按游戏分文件夹；不要写其它目录（报告写 `reports/audio/`）。

## 1. 格式与响度标准

| 类型 | 声道 | 采样率 | 编码 | 说明 |
|---|---|---|---|---|
| 音乐 | 立体声 | 44100 | OGG Vorbis q5 | 必须无缝循环（首尾样本连续、无爆音） |
| 环境 ambience | 立体声 | 44100 | OGG Vorbis q4 | 必须无缝循环 |
| 音效 sfx | 单声道 | 44100 | OGG Vorbis q4 | 短促，起音快，尾音可控 |
| UI | 单声道 | 44100 | OGG Vorbis q4 | 极短，轻 |

- 峰值 ≤ -1 dBFS；音乐/环境 RMS 约 -22 ~ -18 dBFS；SFX 峰值 -3 ~ -1 dBFS。
- 循环素材：生成时多写 1–2 秒，头尾做 200–500ms 交叉淡化后精确截断到目标长度；确保 `[0]` 与 `[-1]` 平滑。
- 所有文件 OGG；写完后用 `ffprobe` 批量验证时长、采样率、声道，把结果写进 `reports/audio/verify.txt`。

## 2. manifest 格式（每个游戏一份）

`assets/audio/door/manifest.json`、`mirror/manifest.json`、`nightroad/manifest.json`：

```json
{
  "id": "door",
  "music": {
    "main":    { "file": "music/main.ogg",    "volume": 0.50, "loop": true, "fade": 4.0 },
    "tension": { "file": "music/tension.ogg", "volume": 0.45, "loop": true, "fade": 2.0 },
    "ending":  { "file": "music/ending.ogg",  "volume": 0.55, "loop": false, "fade": 2.0 }
  },
  "ambience": {
    "corridor": { "file": "ambience/corridor_hum.ogg", "volume": 0.55, "loop": true }
  },
  "sfx": {
    "stepWood": { "files": ["sfx/step_wood_1.ogg", "sfx/step_wood_2.ogg"], "volume": 0.55 },
    "doorOpen": { "files": ["sfx/door_open.ogg"], "volume": 0.9 }
  },
  "ui": {
    "hover":  { "files": ["../shared/ui_hover.ogg"], "volume": 0.35 },
    "click":  { "files": ["../shared/ui_click.ogg"], "volume": 0.45 },
    "back":   { "files": ["../shared/ui_back.ogg"], "volume": 0.4 },
    "confirm":{ "files": ["../shared/ui_confirm.ogg"], "volume": 0.5 }
  }
}
```
- 引擎按 manifest 加载；`file` 相对 manifest 所在目录。
- 多文件条目（`files` 数组）由引擎随机挑选，用于脚步/耳语等。
- 需要循环的 sfx（如 heartbeat / clockTick / waterStream / radioStatic）在**条目里加 `"loop": true`**，引擎会按循环播放。

## 3. 声音设计原则

- 心理恐怖：**低频身体感 + 听觉幻觉 + 日常声音的微小错位**，避免廉价巨响。
- 「音乐」是氛围音乐：慢速、无强节拍、可循环；每个游戏 3 首（main / tension / ending）。tension 在实体接近时交叉淡入，应能与 main 叠放。
- 环境声要能长期听：走廊灯管嗡鸣、雨、远处电视、水滴、日光灯电流、虫鸣、风。
- 所有「人声」用呼吸/气声/低语噪声合成，不用 TTS，不出现可辨识词句（字幕由游戏文字承担）。
- 保留 headroom：引擎会叠加心跳与音乐。

## 4. 文件清单（必须全部交付）

### 4.1 shared（三游戏共用 UI）
`assets/audio/shared/`：`ui_hover.ogg`、`ui_click.ogg`、`ui_back.ogg`、`ui_confirm.ogg`（各 0.05–0.25s），另加 `assets/audio/shared/manifest.json` 说明。

### 4.2 《门后》 door/
music：
- `music/main.ogg` 约 60s：旧屋氛围，失谐八音盒动机（D 小调）+ 低频 drone + 磁带底噪；
- `music/tension.ogg` 约 45s：无旋律，低频脉动 + 金属摩擦 + 心跳暗示；
- `music/ending.ogg` 约 40s：同一八音盒动机放慢、混响加大、逐渐失真。

ambience：
- `ambience/corridor_hum.ogg` 约 30s：日光灯嗡鸣 + 远处楼梯间回声 + 偶尔电流噼啪；
- `ambience/room_tone.ogg` 约 30s：室内低频嗡鸣 + 钟表声 + 窗外雨；
- `ambience/rain_window.ogg` 约 30s：贴窗雨声；
- `ambience/tv_static.ogg` 约 15s：电视雪花（低音量，可开关）。

sfx（最低数量）：
- 脚步 `step_wood_1..4`、`step_carpet_1..3`；
- `door_open`、`door_close`、`door_locked`、`door_unlock`；
- `pickup_letter_1..2`、`pickup_battery`、`flashlight_click`、`battery_low`；
- `light_switch`、`light_flicker_1..2`；
- `paper_rustle_1..2`、`clock_tick`（loop）；
- `heartbeat`（loop，60bpm，约 10s）、`breath`（loop，约 8s）、
- `whisper_1..3`、`stinger_1..2`、`blackout`；
- 实体：`entity_breath`（loop）、`entity_step_1..2`、`entity_catch`。

### 4.3 《镜中》 mirror/
music：
- `music/main.ogg` 约 60s：玻璃/瓷砖混响，反向钢琴与 FM 钟声，A 小调；
- `music/tension.ogg` 约 45s：高频耳鸣 + 呼吸 + 玻璃应力声；
- `music/ending.ogg` 约 35s：镜面碎裂后的长混响尾音。

ambience：
- `ambience/fluorescent_buzz.ogg` 约 20s；
- `ambience/water_drip.ogg` 约 30s；
- `ambience/distant_water.ogg` 约 30s（远处澡堂水声/蒸汽）；
- `ambience/steam_hiss.ogg` 约 15s（可开关）。

sfx：
- 脚步 `step_tile_1..4`；
- `towel_pick`、`valve_turn_1..2`、`water_stream`（loop）、`water_splash`；
- `switch_click`、`light_flicker_1..2`、`locker_creak_1..2`、`stool_drag`；
- `radio_on`、`radio_static`（loop）、`clock_tick`（loop）；
- `mirror_touch`、`glass_crack`、`doppel_step_1..3`、`doppel_breath`（loop）；
- `heartbeat`（loop）、`whisper_1..3`、`stinger_1..2`、`blackout`。

### 4.4 《夜路》 nightroad/
music：
- `music/main.ogg` 约 60s：低音弦乐 drone + 气声笛，E 小调，缓慢；
- `music/tension.ogg` 约 45s：纸的摩擦 + 低频逼近 + 不协和音簇；
- `music/ending.ogg` 约 40s：庙里的钟声与风声，安静收束。

ambience：
- `ambience/wind_field.ogg` 约 30s；
- `ambience/insects.ogg` 约 30s：秋夜虫鸣（有稀疏起伏）；
- `ambience/night_room_tone.ogg` 约 30s：极低的环境底噪；
- `ambience/distant_dog.ogg` 约 12s：远处狗吠（稀疏）。

sfx：
- 脚步 `step_dirt_1..4`、`step_grass_1..3`；
- `match_strike_1..2`、`lantern_light_1..2`、`paper_flutter_1..2`；
- `entity_rustle_1..3`、`entity_catch`；
- `shrine_bell`、`metal_bell`（灯笼/风铃）、`wind_gust_1..2`、`crow`；
- `heartbeat`（loop）、`breath`（loop）、`whisper_1..3`、`stinger_1..2`、`blackout`。

## 5. 合成建议（可自由发挥，但需满足听感）

- numpy 生成：正弦/FM 合成、滤波噪声（一阶/二阶低通、带通）、脉冲激励 + 阻尼振荡（金属/木材/纸）、颗粒噪声、简单卷积混响（自造脉冲响应）。
- 音乐可用慢速琶音 + 长音铺底 + 少量随机音符；**每首必须有可听的音乐性结构**（动机/和声/起伏），不是纯噪声。
- 环境声必须有层次（近场/远场、左右声像差异）；避免长时间单一白噪声。
- 恐怖音效优先「有机材质」：木头、金属、纸、水、呼吸；避免电子游戏式合成音。
- 若某个音效太短或太糊，宁可多做 2 个变体。

## 6. 交付与自检

1. 全部文件 + 3 个 manifest + shared manifest；
2. `reports/audio/verify.txt`：每个文件时长/采样率/声道/峰值，以及 manifest 中引用的文件全部存在；
3. `reports/audio/waveforms_*.png`（可选）：关键 loop 的波形图，确认无爆音/静音断裂；
4. `docs/audio_design.md`：逐曲/逐类说明设计意图、循环长度、使用场景；
5. 完成后向 Lead 汇报：文件总数、总时长、manifest 路径、自检结果、已知不足。

## 7. 验收硬指标

- manifest 引用的每个文件都存在，能被 ffprobe 读取；
- 三个游戏每套至少：3 首音乐 + 3 条环境 loop + 20 个以上 sfx 条目；
- 所有 loop 素材无爆音（峰值达标、首尾交叉淡化）；
- 无外部下载素材，脚本可复现。
