# 《三更》美术设计说明

> 1.4.0 候选增补：六种既有材质加入受限 AI 微细节，调整颗粒、暗角与初始厨房光，补暖水瓶握把。见 [本轮说明](av_iteration_v1.4.md)。下文为 v1 程序化基础制作记录，“全部程序化”仅描述该历史阶段。

> 作者：art（团队美术 agent） · 版本：v1 · 固定种子 `20261018`
> 生成脚本：`tools/art/`（numpy 2.3.5 + Pillow 12.3，全部程序化，无任何外部图片素材；仅使用 Windows 自带中文字体 `simkai / simsun / simhei / msyh`）

---

## 1. 视觉方向

**1990 年代中国老公寓与乡镇的潮湿、褪色、低分辨率记忆。**

- 底色是「被用过很久」的东西：荧光灯惨白偏青、钠灯/白炽灯昏黄、月光冷蓝、霉斑、水渍、烟熏、掉漆。
- 所有贴图按 PS1 时代方式绘制：目标尺寸 ≤512px、放大后能看到笔触与颗粒；建筑面平铺，道具面完整铺满。
- 专门加入「画出来的痕迹」：手写感招牌、刷漆边缘、复印机脏点、胶片颗粒、扫描线。**不做**高清摄影感、玻璃拟态 UI、血腥与克苏鲁触手。

交付概览：

| 类别 | 路径 | 数量 |
|---|---|---|
| MAT_* 贴图 | `assets/textures/*.jpg / *.png` | 50 |
| 材质清单 | `assets/textures/manifest.json` | 50 条 |
| 海报 | `assets/art/poster-door.jpg` / `poster-mirror.jpg` / `poster-night.jpg` | 3（900×1200） |
| 入口底图 | `assets/art/hero.jpg` | 1（1600×900） |
| 印章 / 图标 | `assets/art/seal.png`（512，RGBA）、`assets/art/favicon.png`（128） | 2 |
| 自检 | `reports/art/contact_sheet.jpg`、`reports/art/verify.txt` | 2 |
| 设计说明 | 本文 | — |

**贴图目录总量 1.45 MB（50 张 + manifest，上限 8 MB）。**

---

## 2. 可复现性

```bat
set PY=python
%PY% tools\art\build_textures.py              :: 全部贴图 + manifest.json
%PY% tools\art\build_textures.py --only MAT_wallpaper,MAT_tile_green
%PY% tools\art\build_textures.py --list       :: 列出 50 个键名
%PY% tools\art\build_posters.py               :: 3 海报 + hero + seal + favicon
%PY% tools\art\build_reports.py               :: contact_sheet.jpg + verify.txt
```

- 每个材质用 `artlib.rng("<MAT_键名>")` 派生独立随机流（`md5(seed + name)`），因此单独重建某个材质与全量重建结果一致，跨进程稳定。
- 想改色调/参数：在 `textures_surfaces.py` / `textures_props.py` 的 `SPECS` 或对应 `build_*()` 里调整；`tint` / `emissive` 写在 `SPECS` 条目里，直接进 manifest。

---

## 3. 贴图技术做法（通用）

1. **无缝构造**：所有平铺材质都不靠「四边对齐补丁」，而是整个场在环面（torus）上解析构造：
   - 周期性值噪声 / fBm（`artlib.pnoise / fbm / ridged`，网格按 `cells` 环绕插值）；
   - 环形距离 `torus_delta` 生成斑点、霉点、椭圆、折线笔触、裂纹，天然跨边界连续；
   - 瓦片/灰缝/木板的坐标取自周期函数，而不是画线。
2. **像素中心**：所有网格、灰缝、木板缝使用 `x + 0.5` 的像素中心坐标，缩小 2 倍后接缝两侧严格对称；`artlib.downscale_tiled` 用环形 padding 再 Lanczos 缩小，避免边缘 clamp 拉出接缝。
3. **2× 工作分辨率**：每张贴图先按目标 2 倍绘制（如 256 → 512），最后缩小。既保留手绘笔触，又让文字/裂纹在低分辨率下不锯齿。
4. **做旧叠加**：水渍（黄褐 fBm）、霉斑（环形斑 + 颗粒）、竖向污痕（各向异性 fBm）、划痕（环面折线）、掉漆（阈值 + 亮边）、熏黑（模糊噪声）分层叠加，再统一降饱和 + 颗粒 + JPEG q88。
5. **文字类**：PIL 字体 → 蒙版 → 用 fBm 侵蚀（漏墨/掉漆）→ 阴影/亮边/漆滴 → 叠到木纹/珐琅/石面上；中文用楷体（手写招牌）、黑体（门牌/门牌字）、宋体（表盘/纸钱）。
6. **贴花与 alpha**：`MAT_stain_mold` / `MAT_stain_water` / `MAT_mirror_grime` / `MAT_steam` 输出 RGBA PNG，manifest 标 `transparent: true`；引擎按此开启透明混合（depthWrite=false）。其余全部 JPEG q88。
7. **自发光**：`MAT_lamp_tube`（#dff5e8 / 1.6）、`MAT_lamp_warm`（#ffcf92 / 1.5）、`MAT_lantern_paper`（#ff6a3a / 1.35）、`MAT_tv_static`（#a9bcc2 / 0.55）。贴图本身也画了灯管亮芯/灯泡光晕/纸灯笼透光，关灯时仍有形状。

---

## 4. 各材质做法

### 4.1 建筑与自然（23 张，全部平铺）

| 键名 | 尺寸 | 做法摘要 |
|---|---|---|
| MAT_wallpaper | 256 | 米绿纸底 + 细竖纹 + 5×5 错位花枝（椭圆叶+折线茎）+ 水渍 + 成簇霉点 + 竖向污痕 |
| MAT_wallpaper_dark | 256 | 同款压暗加脏，霉点密度×2、污迹更强，另加 7 处剥落露灰底 |
| MAT_plaster | 256 | 白灰底 + 阈值剥落片（露灰泥底 + 深色剥落边）+ 细裂纹 + 水渍 + 小霉点 |
| MAT_wood_floor | 256 | 16 排长条板（随机 1–3 道板缝/排），深红棕 6 色，拉长木纹 + 打蜡反光 + 污垢划痕 + 对称拼缝凹槽 |
| MAT_wood_door | 256 | 红棕漆木 + 竖板缝 + 稀疏小面积起皮露浅木 + 竖油污 + 浅划痕 |
| MAT_wood_dark | 256 | 深胡桃色细木纹 + 使用擦亮 + 浅划痕 + 局部污垢 |
| MAT_wood_pale | 256 | 廉价三合板：宽木纹带 + 3 处节疤 + 水渍/污垢 + 划痕 |
| MAT_paint_ceiling | 256 | 脏白顶 + 3 圈不规则黄褐水痕（鱼眼状边缘）+ 霉点 + 细裂纹 + 刮痕 |
| MAT_concrete | 256 | 水泥灰 + 骨料亮/暗颗粒 + 大块修补 + 裂缝 + 潮斑油污 |
| MAT_tile_green | 256 | 16×16 暗绿方砖、发黑灰缝、每砖色差/倒角、水垢白华、缝内霉、崩角 |
| MAT_tile_white | 256 | 16×16 白瓷砖、脏灰缝、黄褐水渍、白华、霉缝、崩边（比绿砖更旧） |
| MAT_tile_floor | 256 | 16×16 小方砖，灰/褐/土黄混色、脏缝、划痕、污垢 |
| MAT_metal_locker | 256 | 浅绿灰漆面 + 竖向拉丝 + 少量掉漆露铁 + 锈点 + 凹痕 + 明显划痕 + 灰 |
| MAT_metal_rust | 256 | 铁灰底 + 锈斑色阶 + 锈皮亮边/暗边 + 锈坑 + 孔洞 + 残铁 + 尘土 |
| MAT_glass_dirty | 256 | 深青灰玻璃 + 斜向反光条 + 雨痕 + 水垢点 + 手印暗斑 + 边缘暗角 |
| MAT_window_night | 256 | 深蓝黑夜空 + 云 + 14 点远处暖灯（带光晕）+ 冷反光 + 玻璃脏 |
| MAT_curtain | 256 | 泛黄的确良/蕾丝：6 道竖向褶皱明暗 + 织纹 + 蕾丝小花点 + 黄渍 + 灰 |
| MAT_soil | 256 | 土黄褐 + 两条摆动车辙 + 中间踩踏暗带 + 碎石亮边 + 干草茎 + 潮斑 |
| MAT_grass | 256 | 深色草底 + 5 组不同绿/枯色的草叶短笔触（逐组蒙版叠加）+ 露珠亮点 + 泥暗部 |
| MAT_bark | 256 | 纵脊纹理（脊状 fBm）+ 深裂 + 横裂纹 + 地衣斑点 |
| MAT_leaves | 256 | 5 层暗绿/枯色椭圆叶簇 + 叶脉高光短线 + 暗部空隙 |
| MAT_stone | 256 | 花岗岩灰 + 亮/暗矿物颗粒 + 裂缝 + 凹坑 + 苔 + 潮斑 |
| MAT_shrine_wood | 256 | 旧红木 + 纵向木纹 + 掉漆露木灰 + 香火熏黑 + 灰尘 + 细裂 |

### 4.2 道具、纸、灯、文字、实体（27 张）

| 键名 | 尺寸 | 做法摘要 |
|---|---|---|
| MAT_fabric_red | 128 | 红毛巾：毛圈颗粒 + 织纹 + 褪色块 + 旧渍 |
| MAT_fabric_white | 128 | 白布：斜向褶皱明暗 + 折痕线 + 泛黄 + 污点 |
| MAT_fabric_blue | 128 | 蓝灰工装：斜纹 + 洗旧泛白 + 褶皱 + 油渍 + 磨痕 |
| MAT_paper | 128 | 发黄纸纤维 + 交叉折痕 + 褐色霉点 + 边缘泛黄 |
| MAT_photo | 256 | 褪色全家福：相纸白边 + 米黄底 + 3 个重度模糊人形（无清晰人脸）+ 划痕 + 曝光角 |
| MAT_tv_static | 256 | CRT 雪花：近黑白噪点 + 扫描线 + 滚动亮带 + 行抖动 + 轻微彩噪 + 暗角 |
| MAT_lamp_tube | 128 | 日光灯管：横向亮芯 + 端部压暗 + 灰尘点（青白自发光） |
| MAT_lamp_warm | 128 | 白炽灯泡：暖黄径向光晕 + 灯丝暗斑/灰尘（暖黄自发光） |
| MAT_lantern_paper | 256 | 红纸灯笼：8 根竖向竹骨（x 向无缝）+ 上下收口 + 纸纤维 + 污渍（橙红自发光） |
| MAT_sign_night_1 | 512×256 | 旧木板（3 板拼 + 木纹 + 钉子）+ 楷体手写「土地庙 / 前方 500 米」+ 磨蚀 + 漆滴 + 泥点 |
| MAT_sign_night_2 | 512×256 | 同上 2 板，字更淡：「夜路难行 / 早些回家」 |
| MAT_sign_bath | 256×512 | 旧珐琅牌：深青底 + 白边 + 珐琅龟裂 + 锈流 + 竖排黑体「男湯」+ 四角螺丝 |
| MAT_shrine_tablet | 256×512 | 石牌位：花岗岩 + 内凹面板 + 阴刻宋体「土地之神位」+ 残留红漆 + 香灰 + 苔 + 崩边 |
| MAT_door_number_501–504 | 128 | 旧金属门牌：501 蓝、502 绿、504 褐（白字），503 奶白底黑字最清晰；圆角、倒角、螺丝、掉漆、锈、污垢 |
| MAT_clock_face | 256 | 旧挂钟：米黄漆面 + 罗马数字 + 60 刻度 + 时针 3 点/分针 12 点/红秒针 9 点 + 上海小字 + 霉斑 + 裂纹 + 玻璃反光 |
| MAT_mirror_grime | 512 | 透明底叠加：边缘雾污 + 竖向水痕 + 3 组指纹 + 灰尘膜 + 皂点 + 划痕 + 黄渍 |
| MAT_stain_mold | 256 | 透明底可平铺霉斑：多尺度 fBm 阈值成有机大斑 + 颗粒点 + 中心近黑边缘墨绿 |
| MAT_stain_water | 256 | 透明底可平铺水渍：3 圈不规则污边 + 淡色内圈 + 向下流痕 + 黄褐色 |
| MAT_entity_white | 256 | 惨白纸/皮肤：冷白底 + 纤维 + 褶皱明暗 + 冷蓝阴影 + 细裂纹 + 污点 |
| MAT_entity_hair | 128 | 黑发：近黑底 + 3 组发丝笔触（不同明度）+ 湿发高光 + 颗粒 |
| MAT_entity_face | 256 | 纸人脸：纸白底 + 纸纤维/褶皱 + 红颊 + 墨线眼（黑杏眼+眼线+眼窝）+ 细眉 + 鼻线 + 暗红细嘴 + 裂纹 + 污渍 |
| MAT_red_cloth | 128 | 庙里红布：深红 + 竖向褶皱明暗 + 织纹 + 褪色 + 灰 + 污渍 |
| MAT_paper_money | 128 | 黄纸 + 红印：粗外框 + 中央红圆/方孔 + 波浪纹 + 「冥府」小字 + 磨蚀 + 折痕 |
| MAT_steam | 256 | 透明水汽：多层 fBm 雾团 + 竖向拉丝 + 边缘淡出（alpha ≤0.7） |

---

## 5. manifest 语义

`assets/textures/manifest.json` 结构：

```json
{ "materials": {
  "MAT_lamp_tube": {
    "file": "lamp_tube.jpg", "colorSpace": "srgb",
    "tint": "#ffffff", "emissive": "#dff5e8", "emissiveIntensity": 1.6
  },
  "MAT_stain_mold": {
    "file": "stain_mold.png", "colorSpace": "srgb",
    "tint": "#ffffff", "emissive": null, "transparent": true
  }
} }
```

- `tint`：引擎 `material.color` 乘色。墙纸/木地板/木门等用近白暖色微调（`#efe8d4`、`#f0dcc8`、`#f2e2d2`），其余 `#ffffff`。
- `emissive` / `emissiveIntensity`：灯管、灯泡、纸灯笼、CRT 雪花四个材质。
- `transparent: true`：`MAT_stain_mold`、`MAT_stain_water`、`MAT_mirror_grime`、`MAT_steam`（RGBA PNG）。**这是对 ART_SPEC「只有蒸汽用 PNG」的一处有意偏离**：前三个是贴花/叠加材质，必须有 alpha 才不出现矩形硬边；已在交付时同步 Lead，引擎已按 `transparent` 实现透明混合 + depthWrite=false。
- 所有键名严格对应 `ASSET_SPEC §3` 的 50 个 `MAT_*`，未改名、未新增。

---

## 6. 三个游戏的调色板

### 《门后》DOOR —— 冷绿日光灯 × 暖黄门缝 × 红棕旧木

| 色值 | 用途 |
|---|---|
| `#2F3B31` | 走廊暗绿墙纸/墙裙主色（低照度底色） |
| `#7E8F7A` | 荧光灯冷青白环境光（= LIGHT_corr `#cfe0d8` 的低饱和反射） |
| `#B9AC8B` | 老墙纸米色、顶棚脏白、纸张 |
| `#3B241B` | 红棕木门/木地板/家具暗部 |
| `#D99A6A` | 卧室暖红、门缝透光、白炽灯 |
| `#0D1210` | 暗部与雾色（近黑，带绿） |

### 《镜中》MIRROR —— 暗绿瓷砖 × 镜面冷蓝 × 一条红毛巾

| 色值 | 用途 |
|---|---|
| `#3F5A4A` | 澡堂暗绿方砖主色 |
| `#CFD4C4` | 灯管冷白 / 瓷砖高光 / 水汽白 |
| `#8A3B34` | 红毛巾（画面唯一高饱和色，视觉锚点） |
| `#7E9CC8` | 镜面冷蓝反光、月光、水汽阴影 |
| `#2A3230` | 潮湿暗部、瓷砖缝、更衣柜暗面 |
| `#B3A273` | 泛黄窗帘/白布/旧纸张 |

### 《夜路》NIGHTROAD —— 月蓝 × 土褐 × 灯笼橙红

| 色值 | 用途 |
|---|---|
| `#0A1018` | 夜空深蓝黑（最暗部） |
| `#1B2A34` | 雾蓝灰、远山/树线、空气透视 |
| `#7E9CC8` | 月光冷蓝（LIGHT_moon / 灯杆高光） |
| `#8E2F26` | 灯笼红 / 纸灯笼自发光基底 |
| `#6B5A44` | 土路褐、田埂、树皮 |
| `#D8D3C8` | 纸人惨白（唯一的「白」，在雾里发灰） |

---

## 7. 海报与包装

三张海报全部由 numpy 程序化绘制，透视面**采样真实 MAT_\* 贴图**（走廊采样 tile_floor / wallpaper_dark / wood_door / paint_ceiling，镜中采样 tile_green / fabric_red / mirror_grime，夜路采样 soil / grass / paper_money），因此海报与游戏内材质同源、色调一致。海报上**没有任何标题文字**（标题由 HTML 叠加），只保留一次性相机式的橙色日期戳（`98 03 12 / 98 07 04 / 98 11 21`）。

| 文件 | 画面 |
|---|---|
| `poster-door.jpg` 900×1200 | 暗绿走廊一点透视：地砖、墙裙、四扇侧门（带小门牌）、顶棚水渍、日光灯冷光池；尽头一扇门，门缝/门底透出暖光，周围暗角与颗粒。低对比、偏绿、重度颗粒与划痕。 |
| `poster-mirror.jpg` 900×1200 | 绿瓷砖澡堂：上半墙剥落白灰，中部一条长镜（深绿金属框），镜中反射出更暗的瓷砖/灯管/更衣柜与一个模糊的惨白人形；镜面叠加 real grime 贴图 + 冷凝水珠；前景左下一条红毛巾垂落，是画面唯一暖色；右侧浴池门缝暖光；水汽覆盖下半部。 |
| `poster-night.jpg` 900×1200 | 雾中乡道一点透视：月蓝夜空、月亮与薄云、远处树线与村子暖灯、电线杆与下垂电线、两条车辙的土路、路边散落纸钱；路右侧远处一盏红灯笼亮着，近处路边一个比例略不对的白纸人轮廓（墨线眼）；整体月蓝/青灰，灯笼一点暖橙。 |
| `hero.jpg` 1600×900 | 三张海报中间条带的重度模糊拼贴，横向渐变融合、压暗、去饱和、暗角；整体明度低，作为入口页背景，可读作「左走廊 / 中镜面 / 右夜路」三层意象。 |
| `seal.png` 512×512 | 透明底红色方印：做旧缺边、缺墨斑驳、印泥不匀；白文（镂空）楷体「三更」竖排；可用于标题页角落，背景色透出即为「白文」。 |
| `favicon.png` 128×128 | 黑底 + 红印方块 + 镂空「三」；小尺寸下仍是可辨认的红色印章块。 |

---

## 8. 自检与已知弱项

- `reports/art/verify.txt`：50/50 键名与文件一一对应、manifest 覆盖检查、尺寸/格式/模式检查、**全部平铺贴图的接缝指标**（首末行列与相邻列差的比值，阈值 1.9；当前最大 1.44）、总大小检查、海报/hero/seal/favicon 尺寸检查 → `VERIFY OK`。
- `reports/art/contact_sheet.jpg`：50 张贴图联系表，带键名/尺寸/大小标注；平铺材质以 **2×2 平铺**显示，便于检查接缝。
- 已知弱项与剩余风险：
  1. `MAT_wallpaper` / `MAT_wallpaper_dark` 的花枝图案在游戏距离上非常隐约（故意做褪色），近看才明显；若 Lead 觉得墙面太素，可提高 `_wallpaper` 的 `leaf_col` 对比或图案 alpha，脚本里改 1 行即可。
  2. `MAT_plaster` 的剥落斑块偏「迷彩」，近看略图案化；已比首版收敛，但不是写实级。
  3. `MAT_metal_rust`、`MAT_stain_water` 属于风格化锈/水渍，可辨认但不算精细。
  4. `poster-night.jpg` 两侧树是剪影式多边形，近看略假；`poster-mirror.jpg` 构图偏对称；hero 刻意重模糊，细节不可辨（作为背景符合要求）。
  5. `MAT_clock_face` 的指针是画死在 3:00 的，不会随时间转动；若玩法需要走时，需引擎叠加动态指针（贴图只做表盘底）。
  6. 贴花类 PNG 依赖引擎透明混合，已与 Lead 确认实现；若以后改渲染管线，注意 `transparent` 与 `depthWrite=false`。
