# 《三更》美术规格（给美术 agent）

目标：为三个 demo 生成 **1990 年代中国城市/乡野、潮湿褪色、低保真** 的贴图、海报与界面美术。全部程序化生成（numpy + Pillow），固定随机种子，脚本可复现。禁止下载/使用外部图片或版权素材。

## 0. 工具与路径

- Python（带 numpy/Pillow）：`python`
- 生成脚本：`tools/art/build_art.py`（+ 辅助模块），固定 seed；
- 输出：贴图 `assets/textures/`、海报 `assets/art/`；
- 自检报告：`reports/art/`；设计说明：`docs/art_design.md`。
- 可用中文字体：`C:\Windows\Fonts\simkai.ttf`（楷体）、`simsun.ttc`、`msyh.ttc`、`simhei.ttf`。

## 1. 视觉方向

- 关键词：潮湿、霉斑、褪色、荧光灯惨白、钠灯昏黄、月光冷蓝、纸的质感、被使用过的旧物。
- 参考气质：PS1/PS2 时代恐怖游戏的低分辨率贴图 + 中国 90/00 年代老公寓与乡镇实景记忆。
- **不要**：高清摄影感、现代 UI 玻璃拟态、血腥内脏、克苏鲁触手、赛博霓虹。
- 贴图允许「画出来的」痕迹：笔触、噪点、扫描线、复印机脏点、手写字歪斜。
- 全部 512px 以下（海报除外）；低分辨率是风格的一部分。

## 2. 贴图规格与 manifest

- 尺寸：建筑/大面积 256×256（必须无缝平铺）；道具 128×256 或 256×256；招牌/门牌/表盘 256×512 或 512×512；海报 900×1200。
- 格式：JPEG q88（不透明）；只有需要 alpha 的（蒸汽、印章）用 PNG。禁止大文件。
- 平铺类贴图必须可无缝循环（用 `np.roll` / 噪声周期性构造，并在四边做匹配）。地面/墙面 UV 约定为 **1 UV 单位 = 2 米**，所以 256px 贴图的细节尺度要符合 2m×2m。
- 输出 manifest：`assets/textures/manifest.json`
```json
{
  "materials": {
    "MAT_wallpaper": {
      "file": "wallpaper_old.jpg",
      "colorSpace": "srgb",
      "tint": "#d8d2b8",
      "emissive": null
    },
    "MAT_lamp_tube": {
      "file": "lamp_tube.jpg",
      "colorSpace": "srgb",
      "tint": "#ffffff",
      "emissive": "#cfe8d8",
      "emissiveIntensity": 1.6
    }
  }
}
```
  - `tint` 为引擎里 `material.color` 的乘色，默认 `#ffffff`。
  - 自发光材质（灯管/灯泡/灯笼/屏幕）`emissive` 给颜色，可选 `emissiveIntensity`。
  - 透明材质（蒸汽）给 `"transparent": true`，文件用 PNG。
  - 所有 `MAT_*` 键名必须与下面清单一致（建模端按这些名字赋材质）。

## 3. 必须交付的材质清单（40 项，键名固定）

| 键名 | 内容描述 | 尺寸 | 平铺 |
|---|---|---|---|
| MAT_wallpaper | 暗绿米色老墙纸，细花枝，霉点水渍 | 256 | 是 |
| MAT_wallpaper_dark | 同款更深更脏（走廊/第三轮） | 256 | 是 |
| MAT_plaster | 剥落白灰墙，露底 | 256 | 是 |
| MAT_wood_floor | 深红棕拼花木地板，磨损 | 256 | 是 |
| MAT_wood_door | 红棕漆木门，旧漆起皮 | 256 | 是 |
| MAT_wood_dark | 深棕旧家具木纹 | 256 | 是 |
| MAT_wood_pale | 浅黄三合板/廉价木 | 256 | 是 |
| MAT_paint_ceiling | 脏白顶棚，水渍 | 256 | 是 |
| MAT_concrete | 水泥地/楼梯间 | 256 | 是 |
| MAT_tile_green | 澡堂暗绿方砖，勾缝发黑 | 256 | 是 |
| MAT_tile_white | 白瓷砖，水垢 | 256 | 是 |
| MAT_tile_floor | 小方砖地面，脏缝 | 256 | 是 |
| MAT_metal_locker | 更衣柜漆面金属，划痕 | 256 | 是 |
| MAT_metal_rust | 锈蚀铁皮 | 256 | 是 |
| MAT_glass_dirty | 脏玻璃/窗（深色，带反光条纹） | 256 | 否 |
| MAT_window_night | 窗外夜色：深蓝黑 + 零星暖灯点 | 256 | 否 |
| MAT_curtain | 泛黄蕾丝/的确良窗帘 | 256 | 是 |
| MAT_fabric_red | 红毛巾/红布，起球 | 128 | 否 |
| MAT_fabric_white | 白布/纸衣/旧衬衫 | 128 | 否 |
| MAT_fabric_blue | 蓝灰旧工装 | 128 | 否 |
| MAT_paper | 发黄纸张/字条/纸钱底 | 128 | 否 |
| MAT_photo | 模糊褪色全家福（无清晰人脸） | 256 | 否 |
| MAT_tv_static | CRT 雪花屏（黑白噪点+扫描线） | 256 | 否 |
| MAT_lamp_tube | 日光灯管（自发光青白） | 128 | 否 |
| MAT_lamp_warm | 白炽灯泡（自发光暖黄） | 128 | 否 |
| MAT_lantern_paper | 红纸灯笼（自发光橙红，竹骨） | 256 | 否 |
| MAT_soil | 乡间土路，车辙与碎石 | 256 | 是 |
| MAT_grass | 深色野草/稻田 | 256 | 是 |
| MAT_bark | 树皮 | 256 | 是 |
| MAT_leaves | 暗色树叶/树冠 | 256 | 是 |
| MAT_stone | 石头/墓碑/界碑 | 256 | 是 |
| MAT_shrine_wood | 土地庙旧红木/木构件 | 256 | 是 |
| MAT_sign_night_1 | 木牌：「土地庙 前方 500 米」（竖排或横排） | 512×256 | 否 |
| MAT_sign_night_2 | 木牌：「夜路难行 早些回家」 | 512×256 | 否 |
| MAT_sign_bath | 澡堂门牌：「男湯」竖排 | 256×512 | 否 |
| MAT_shrine_tablet | 石牌位：「土地之神位」 | 256×512 | 否 |
| MAT_door_number_501 | 门牌「501」，旧金属底 | 128 | 否 |
| MAT_door_number_502 | 门牌「502」 | 128 | 否 |
| MAT_door_number_503 | 门牌「503」（最重要，要能看清） | 128 | 否 |
| MAT_door_number_504 | 门牌「504」 | 128 | 否 |
| MAT_clock_face | 挂钟表盘（罗马数字或刻度，旧） | 256 | 否 |
| MAT_mirror_grime | 镜面污渍/水痕/指纹（叠加用，可半透明 PNG） | 512 | 否 |
| MAT_stain_mold | 霉斑贴花（可平铺，深绿黑） | 256 | 是 |
| MAT_stain_water | 水渍贴花（黄褐边缘） | 256 | 是 |
| MAT_entity_white | 实体惨白皮肤/纸（冷白，细纹） | 256 | 否 |
| MAT_entity_hair | 黑色发丝/纸黑 | 128 | 否 |
| MAT_entity_face | 纸人脸（白底、红颊、墨线眼，恐怖谷但不血腥） | 256 | 否 |
| MAT_red_cloth | 庙里的红布/红绳 | 128 | 否 |
| MAT_paper_money | 黄纸红印的纸钱 | 128 | 否 |
| MAT_steam | 水汽/蒸汽（半透明 PNG，边缘柔） | 256 | 否 |

> 若建模端需要额外键名，以 `docs/ASSET_SPEC.md` 为准；两边不一致时向 Lead 报告，不要私自改名。

## 4. 其他美术交付

### 4.1 海报（3 张，900×1200，JPEG q90）
- `assets/art/poster-door.jpg`：暗绿走廊透视，尽头一扇门缝透出暖光；低对比、颗粒、四周更暗。
- `assets/art/poster-mirror.jpg`：绿瓷砖与长镜，镜中一个模糊人形，前景一条红毛巾；冷调。
- `assets/art/poster-night.jpg`：雾中土路，远处一点红灯笼，路边白色纸人轮廓；月蓝与暖橙对比。
- 海报上不要写标题（标题由 HTML 排版叠加）；可以有模糊污渍、划痕、日期戳。
- 允许用 numpy 做透视/噪声/模糊，Pillow 做几何与调色；不要求写实。

### 4.2 入口与包装
- `assets/art/hero.jpg` 1600×900：三张海报的拼贴/模糊底层，作为入口页背景（要暗，整体明度低）。
- `assets/art/seal.png` 512×512：透明底红色方印，白文「三更」（篆意或楷体），带做旧缺边。
- `assets/art/favicon.png` 128×128：黑底红印「三」。
- `assets/art/loading_*.jpg`（可选）：每个游戏 1 张标题页背景（可用海报裁切）。

### 4.3 清单与自检
- `reports/art/contact_sheet.jpg`：所有贴图的联系表（带键名标注，便于 Lead 检查）。
- `reports/art/verify.txt`：文件尺寸/大小/manifest 键名覆盖检查（清单里每个 MAT_ 都有文件）。
- `docs/art_design.md`：视觉阐述、每张贴图的制作方法、调色板（每个游戏 4–6 色）。
- 完成后向 Lead 汇报：文件数、manifest 路径、自检结果、哪些贴图是弱项。

## 5. 验收硬指标

- 清单里 40+ 个 `MAT_*` 全部有对应文件和 manifest 条目；
- 建筑贴图无缝（放大看四边没有接缝）；
- 贴图文件总量 ≤ 8 MB；
- 三张海报 + hero + seal + favicon 存在且尺寸正确；
- 脚本固定 seed，可重跑生成同样结果；无外部素材。
