# v1.0.2 交接说明（内容 / 场景 / 美术 / Blender）

分支：`feat/v1.0.2-door-mirror`（基于 `main` v1.0.1 `d60a745`）
负责人：Lead（内容、场景、blender、美术）；引擎 / 测试 / 集成 / 打包 / Release 由 Codex 负责。
本分支**没有修改** `engine/`、`vendor/`、`tools/build_release.py`、`package.json` 或既有测试。本地验证服务：`python serve.py 8140`。

## 1. 这一轮改了什么

优先级按用户要求：《门后》>《镜中》>《夜路》。目标是保留原有气质，补齐“空间的叙事”和镜中可读性，不平均用力。

### 《门后》

- **空间叙事**：新增旧照片（3 张）、孩子蜡笔画、1999 挂历、公告栏、门框对联、门口女式布鞋、旧电话、缝纫机、暖水瓶、客厅窗边椅子等可查看物；新增对应文字（照片里的家庭、被圈住的日期、寻人启事、空相框等）。全部守“不解释、只呈现”。
- **变体**：走廊新增儿童小鞋、门缝暖光、走廊儿童画（V2）；503 门板手印、湿脚印（V3）；第二轮/第三轮椅子逐步挪到 503 门口。
- **实体**：`ENTITY_she` 重做（分层白裙/手臂/湿发/暗面部），新增坐在卧室椅子上的 `ENTITY_she_sitting`；第三轮走廊加入短暂“一瞥”，被看见就消失，不参与追逐。
- **追逐/结局**：调整追逐速度、闪现节奏与首次看见时的停顿提示；结局改为换成坐姿实体、点亮卧室灯、读信后多停留 2.8s，让玩家看清她。
- **灯光**：进入 503 后打开玄关/客厅/落地灯/厨房；第二、三轮逐步熄灯；第三轮保留一盏走廊灯与远端灯让“一瞥”可读。

### 《镜中》

- **空间叙事**：新增澡堂海报、票价/营业时间牌、通知栏、旧澡票、开柜里的工装、长凳上的鞋/报纸/毛巾堆/盆/瓶/梳/烟、地漏头发、天花板漏水、加长凳等；新增可查看文字（1999 年海报、最后一张澡票、被抠掉的营业时间、寻人启事）。
- **镜面可读性**：每完成/错误一步推进镜面水汽手印（GLB 的 `S_handprint_1/2/3` 保持隐藏，游戏层用同一套 `MAT_handprint` 纹理自建 3 个加色 quad，随步数 1/2/3 枚显示）；目标栏显示“还差 N 处”；正确对齐有更明确的字幕/音效反馈；R2/R3 增加低照度补光并限制 sanity/threat 上限（0.58/0.64），保留冷绿潮湿感。
- **结局**：第三次对齐后显示手印与 `S_mirror_crack`（游戏层 quad；GLB 同名节点保持隐藏）、镜面故障白闪，镜中人从镜中“走出”（现实场景实体显隐/位置 + 轮廓光），结局文字接到海报与澡票。
- 保留三回合与 `window.__MIRROR__.debug` 接口（新增 `handprints/crack/revealNew/examineInfo`）。

### 《夜路》

- 只做了 Blender 侧的纸人轮廓/纸感小修与全局 UV 修正，玩法和节奏未动。

## 2. 资产变化

| 文件 | 变化 | 大小 / 面数 |
|---|---|---|
| `assets/models/door.glb` | 新增叙事道具、实体重做、变体；全局 UV V 修正 | 702,232 B；8,652 tris（< 9,000 cap） |
| `assets/models/mirror.glb` | 新增道具、手印/裂纹平面、实体微调 | 412,760 B；4,716 tris（< 7,000） |
| `assets/models/nightroad.glb` | 仅全局 UV V 修正/纸人微调（字节数未变） | 477,148 B；5,710 tris |
| `assets/textures/` | 新增 12 张 v1.0.2 叙事贴图；manifest 50 → 62 条 | +386 KB |

> **重要**：模型脚本修正了一个存量 bug：glTF 导出器已翻转 V，而引擎 `TextureLoader` 的 `flipY=true` 又翻一次，导致所有 unit-UV 正面在引擎里上下颠倒。`lib_build._uv_unit_front` 已统一修正 V（U 方向核过无镜像）。这会同时影响 v1.0.1 存量的门牌 501/502/503/504、`S_sign_bath`、夜路路牌、土地庙石牌位——请 Codex/QA 在引擎里顺手抽查它们现在是否正立（我这边的截图里 503 门牌、男湯、夜路路牌、石牌位已正立）。

新增材质（ASSET_SPEC §3 已追加；ART_SPEC §6 有说明）：
`MAT_photo_family_1/2/3`、`MAT_child_drawing`、`MAT_calendar`、`MAT_notice_board`、`MAT_couplet`、`MAT_bath_poster`、`MAT_bath_notice`、`MAT_bath_ticket`、`MAT_mirror_crack`、`MAT_handprint`。

## 3. 新增对象契约（gameplay 代码使用；引擎无需改动）

### door.glb
- 可查看：`INT_photo_1/2/3`、`INT_child_drawing`、`INT_calendar`、`INT_notice_board`、`INT_couplet`、`INT_shoes_waiting`、`INT_phone`、`INT_sewing_machine`、`INT_thermos`、`INT_chair_final`
- 变体（hidden）：`V2_shoes_waiting`、`V2_light_under_door`、`V2_drawing_corr`、`V3_handprints_door`、`V3_wet_footprints`
- 实体：`ENTITY_she`（站立/追逐）、`ENTITY_she_sitting`（结局，hidden）

### mirror.glb
- `S_bath_poster`、`S_bath_notice`、`S_ticket_board`、`S_bath_ticket`、`S_open_locker_clothes`、`S_shoes_bench`、`S_towel_pile`、`S_basin`、`S_bucket`、`S_mop`、`S_bottles`、`S_comb`、`S_cigarette`、`S_newspaper_bench`、`S_hair_drain`、`S_ceiling_leak`、`S_bench_extra`
- 镜面贴花（父级 hidden，但 `S_` 前缀引擎不会自动隐藏）：`S_handprint_1/2/3`、`S_mirror_crack` —— **mirror game.js 在 setup 里手动 `setVisible(..., false)`**，实际可见的是游戏层用同纹理自建的加色 quad；请 Codex 不要移动/改名，也不要删这两张纹理，结局/手印视觉依赖它们。
- `ENTITY_reflection`（镜中人；hidden）

### 玩法代码改动
- `games/door/game.js`：新增查看物、光照、循环变体、glimpse、追逐参数、坐姿实体结局。
- `games/mirror/game.js`：新增 examine、手印阶段、目标/反馈、结局裂纹与镜中人出场。
- `games/nightroad/game.js`：未改。
- 无 engine API 变更；全部使用现有 `game.interact.add` / `setVisible` / `setLight` / `openPaper` / `finish` / `fail` / `setThreat` / `setSanity` / `isLookingAt` / `makeDoor`。

## 4. 需要 Codex 做的集成 / 测试

1. **engine/ui.js 字幕计时器 bug（须由 Codex 修）**：`subtitleTimer` 在队列清空后会停在负值，之后 `subtitle()` 的 `if (!this.subtitleTimer)` 判为假，字幕只入队不显示（mirror 已复现）。建议：过期分支里置 `this.subtitleTimer = 0`，并把入口判断改成 `<= 0`。本分支在 `games/door/game.js`、`games/nightroad/game.js`、`games/mirror/game.js` 里各有一个游戏层兜底（door/nightroad 是 setup 里的 subtitle 包装，mirror 是 `say()`），引擎修好后这些兜底可删；**请不要只在引擎修而不回归 door/nightroad 的字幕**。
2. `npm` 构建/`python tools/build_release.py` 会按目录自动收 `assets/`（脚本 `rglob`），不需要改打包清单；请确认 12 张新贴图与 3 个新 GLB 进入产物，`build-manifest.json` 的资产数量相应增长。
2. 本分支是内容分支，未改版本号；请按 Release 流程决定 v1.0.2 版本号与发布说明。
3. 视觉抽查（因全局 V 翻转会动到旧资产）：
   - 门后：503 门牌 + 501/502/504 门牌；`S_sign_bath`；夜路 `S_sign_1/2`、`S_shrine_tablet`；门后新照片/挂历/公告栏/儿童画是否正立且不被墙体遮挡。
   - 镜中：海报/票价牌/通知栏正立；`S_handprint_1/2/3`、`S_mirror_crack` 初始不可见，只在对应阶段出现；镜面反射仍正常。
4. 交互回归：门后新查看物（E）、三循环、追逐/死亡重试、坐姿结局；镜中三回合、错误惩罚、结局；夜路无需重测（仅 UV 变化）。
5. 性能：door 8,652 tris / mirror 4,716（引擎低分辨率渲染），新增 draw call 约 30–40；请在发布包上确认帧率与加载时间无明显退化。
6. 若引擎/测试发现必须由引擎侧修的问题（例如新增 S_ 贴花的自动隐藏约定），请在引擎分支处理或在 handoff 里回写；本分支不会改 engine。

## 5. 本地验证记录（Lead）

- `node --check games/door/game.js`、`games/mirror/game.js`、`games/nightroad/game.js` 均通过。
- 三作本地加载（8140）：音频 ready、贴图 62/62、无 console error；门后/镜中/夜路的标题→开始均可进入。
- 门后：真实 E 拾取字条 1、2 触发 V2/V3，`glimpse=true`；坐姿实体结局可达；新查看物（照片/挂历/公告栏/儿童画/小鞋等）注册且可显示；503 门牌/对联/公告栏文字正立；字幕 wrapper 验证连续字幕正常。
- 镜中：新道具/海报/票价牌正立；手印阶段（1/2/3 枚）与结局（crack=true、ending 音乐、ENDING 页）通过；R3 补光后长凳/镜框/柜门可辨；console 0 error。
- 夜路：路牌/牌位正立；只加了字幕 wrapper，核心流程未改。

## 6. 需要用户试玩判断的点

- 门后：新增照片/挂历/公告栏/小鞋是否让 503“像一个有人等过的家”；第三轮一瞥出现的时机与亮度是否吓人但不过分；坐姿结局的情绪是否成立。
- 镜中：手印逐步出现是否读得懂；海报/澡票的叙事是否过多或刚好；R3 补光后的明暗是否仍够压抑；结局“镜中人走出”是否有效。
- 全局：新增物件在 PS1 低分辨率 + 颗粒下是否仍可辨；是否有性能/加载问题。
