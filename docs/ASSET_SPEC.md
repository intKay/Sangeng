# 《三更》3D 资产规格（给建模 agent）

目标：用 **headless Blender 脚本** 程序化建模，导出 3 个 GLB 场景，供 three.js 引擎加载。要求「低多边形 + 有细节 + 名字可编程」。全部几何原创，不下载模型/贴图。

## 0. 硬性工作方式（重要）

- 用户当前正在 Blender 里打开一个**重要项目**（`exhibits/jeanne-dielman/models/source.blend`）。**禁止**通过 Blender MCP 的 `execute_blender_code` 修改它，禁止 `read_factory_settings`，禁止保存任何 .blend。
- 只使用 **headless Blender**：
  `& "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b --factory-startup --python <你的脚本.py>`
  已测试可用（Blender 5.2.2 LTS，glTF 导出正常）。
- 所有建模脚本放 `tools/blender/`；导出物放 `assets/models/`；预览渲染与自检报告放 `reports/modeler/`。
- **不要写** `games/`、`engine/`、`assets/textures|audio|art/`、`docs/`（你的设计说明写在 `reports/modeler/modeling_notes.md`）。
- 完成后向 Lead 汇报：3 个 GLB、面数、导出大小、预览图路径、缺失/风险项。

## 1. 单位与坐标系

- 单位：米。Blender Z 向上；导出的 glTF 使用默认 `+Y up`（导出器自动转换，无需手工旋转）。
- 所有关卡平地：地面 `z = 0`；玩家眼高 1.62 m；门洞净高 ≥ 2.0 m、净宽 ≥ 0.9 m。
- 物体位置可用 Blender 直接摆放；导出后引擎按世界坐标读取，不需要你转换坐标。
- **不要**导出相机、灯光对象（灯用 Empty 表示，见 §2.5）。场景里也不要放环境光。

## 2. 命名与导出约定

### 2.1 导出参数（每个场景一个 GLB）
```python
bpy.ops.export_scene.gltf(
    filepath=out,
    export_format="GLB",
    use_selection=True,          # 只导出选中的对象
    export_apply=True,           # 应用修改器
    export_extras=True,          # 自定义属性 -> three.js userData
    export_yup=True,
    export_cameras=False,
    export_lights=False,
    export_texcoords=True,
    export_normals=True,
    export_materials="EXPORT",
    export_image_format="NONE",  # 场景里本就不该有贴图
)
```
- 三个文件：`door.glb`、`mirror.glb`、`nightroad.glb`（`assets/models/`）。
- 导出前把所有要导出的对象放进 collection `EXPORT` 并全选；预览用灯光/相机放另一个 collection 且不选中。
- 场景里**不赋任何真实贴图**；材质只用 Principled BSDF + 纯色（近似最终色调即可），材质名必须是 §3 的 `MAT_*`。引擎会按材质名替换成真实贴图。
- 静态几何建议按区域/材质 join 成较少的 mesh（降低 draw call）；**可交互物体、门、灯、实体、变体物件必须保持独立对象并保留名字**。

### 2.2 必须有稳定名字的对象类别

| 前缀 | 类型 | 说明 |
|---|---|---|
| `SPAWN_<id>` | Empty | 玩家出生点，放在地面上（z=0） |
| `LOOK_<id>` | Empty | 出生时看向的点，z≈1.5 |
| `LIGHT_<id>` | Empty | 引擎据此创建灯光，属性见 §2.5 |
| `INT_<id>` | Mesh 或 Empty 父级 | 可交互物体，属性见 §2.3 |
| `ENTITY_<id>` | Mesh/Empty 父级 | 怪物/实体，默认隐藏，原点在**脚底中心** |
| `MARK_<id>` | Empty | 给玩法代码用的位置标记（毛巾挂钩、凳子目标位等） |
| `V2_<id>`、`V3_<id>` | Mesh | 第二/第三轮才出现的变体道具，引擎默认隐藏 |
| `COL_<id>` | Mesh | 碰撞代理，简单盒状，引擎隐藏并按 AABB 碰撞 |
| `S_<id>` | Mesh | 其它静态物件（名字自由，但必须唯一） |

### 2.3 可交互物体的自定义属性（导出 extras，引擎读 userData）

在 Blender 对象上用 `obj["属性名"] = 值` 设置：
- `interact`：`door` / `pickup` / `examine` / `switch` / `valve` / `move` / `radio` / `lantern` / `incense` / `final`（按玩法分配，见各场景清单）
- `prompt`：交互提示中文，如 `"开门"`、`"捡起字条"`、`"点亮灯笼"`
- `id`：唯一短 id，如 `"door503"`、`"letter1"`
- 门额外：`open_angle`（默认 95，单位度）、`open_dir`（1 或 -1，开的方向）、`locked`（True/False）
- 初始隐藏的物件：`hidden = True`（如字条 2/3、电池 2、实体、结局物件）
- 需要旋转/移动的部件：**原点必须在转轴/底面上**（见 §2.4）

### 2.4 枢轴（Pivot）约定（非常重要，玩法代码依赖）

- 门扇：`INT_door_*` 的原点在**合页轴底部**，门扇沿局部 +X 延伸；引擎绕世界 Y 轴旋转 `open_angle`。
- 阀门/旋钮：原点在旋转轴中心。
- 灯笼：原点在灯笼主体中心（引擎在此放光源）。
- 凳子/模特/毛巾：原点在底面中心；引擎可把对象移动/旋转到 `MARK_*` 位置。
- 可拿取物：原点在物体中心。
- 其余部件用各自局部原点即可。
- 导出前对非交互静态物体 Apply Rotation & Scale（保留 Location）；交互物体保持原点不动。

### 2.5 灯光 Empty 属性

`LIGHT_<id>` 上设置：
- `light_kind`: `"point"` 或 `"spot"`
- `light_power`: 数字，Blender 瓦数（point 约 10–80；spot 约 50–300）
- `light_color`: 十六进制字符串，如 `"#ffcf9a"`
- `light_radius`: 影响范围（米，5–20）
- `light_cone_deg`: 仅 spot，如 55
- `light_flicker`: 0–1，闪烁强度（走廊灯 0.15，电视 0.3，普通灯 0）

引擎对 point 用 `PointLight`，spot 用朝下的 `SpotLight`（或按命名后缀 `_dir` 的特殊处理）。**不要**在 Blender 里加真实 light 对象。

### 2.6 材质与 UV

- 每个 mesh 的每个材质名必须来自 §3 清单，大小写精确。
- **每个面都要有材质**；未赋材质的面会被引擎显示成洋红。
- UV：建筑面（墙/地/顶）约定 **1 UV 单位 = 2 米**（即 2m 宽的墙 uv 从 0 到 1）；道具可用 smart project / cube project，尽量填满 0–1；门牌、招牌、表盘、纸片等等要**正面完整铺满 0–1**，不要镜像、不要旋转 90°。
- 门牌/招牌/画/照片是**薄盒或平面**，正面法线朝外。
- 不要做透明材质（蒸汽等由引擎处理）；灯管/灯泡/灯笼用 `MAT_lamp_*` / `MAT_lantern_paper`，引擎会让它们自发光。

### 2.7 碰撞代理 COL_*

- 用立方体/盒体，命名 `COL_<自由名>`，**不加材质**；引擎会隐藏它们并用世界 AABB 做水平碰撞（玩家不能穿过）。
- 必须覆盖：外墙、内墙、门框两侧、关闭时可挡路的家具（床、沙发、柜子、长凳、台面、更衣柜、供桌等）。
- **不要**给门洞开口本身放 COL（否则开了门也走不过去）；门扇由引擎按开关状态动态处理。
- 玩家半径 0.32 m，所以门洞两侧 COL 之间净宽 ≥ 0.9 m。
- 天花板不需要 COL；地面不需要 COL（引擎固定 y=0）。

### 2.8 面数预算

| 场景 | 目标 | 上限 |
|---|---|---|
| door | ≤ 6000 tris | 9000 |
| mirror | ≤ 5000 tris | 7000 |
| nightroad | ≤ 9000 tris | 12000 |

低多边形是风格，不是偷懒：用倒角（bevel）、多层线脚、门板凹槽、瓷砖分格、家具轮廓来做出"被真实使用过"的感觉。避免纯立方体堆砌；可以用圆柱、曲面、阵列、曲线转 mesh。

## 3. 材质键名（只能用这些）

```
MAT_wallpaper MAT_wallpaper_dark MAT_plaster MAT_wood_floor MAT_wood_door
MAT_wood_dark MAT_wood_pale MAT_paint_ceiling MAT_concrete MAT_tile_green
MAT_tile_white MAT_tile_floor MAT_metal_locker MAT_metal_rust MAT_glass_dirty
MAT_window_night MAT_curtain MAT_fabric_red MAT_fabric_white MAT_fabric_blue
MAT_paper MAT_photo MAT_tv_static MAT_lamp_tube MAT_lamp_warm MAT_lantern_paper
MAT_soil MAT_grass MAT_bark MAT_leaves MAT_stone MAT_shrine_wood MAT_sign_night_1
MAT_sign_night_2 MAT_sign_bath MAT_shrine_tablet MAT_door_number_501
MAT_door_number_502 MAT_door_number_503 MAT_door_number_504 MAT_clock_face
MAT_mirror_grime MAT_stain_mold MAT_stain_water MAT_entity_white MAT_entity_hair
MAT_entity_face MAT_red_cloth MAT_paper_money MAT_steam
MAT_photo_family_1 MAT_photo_family_2 MAT_photo_family_3 MAT_child_drawing
MAT_calendar MAT_notice_board MAT_couplet MAT_bath_poster MAT_bath_notice
MAT_mirror_crack MAT_handprint MAT_bath_ticket
```
> 贴图内容描述见 `docs/ART_SPEC.md`。若确需新材质，先向 Lead 报告，**不要**擅自新增。

## 4. 《门后》door.glb

### 4.1 布局（Blender 坐标，Z 上，地面 z=0）

**走廊**：x ∈ [-1.1, 1.1]，y ∈ [-18, 0]，层高 2.7。玩家从 y≈-1 出发向 -Y 走。
- 北端 y=0：墙 + 防火门 `INT_fire_door`（examine，锁着）。
- 南端 y=-18：电梯门 + 按钮 `INT_elevator_button`（examine）。
- 西墙 x=-1.1：501 门（y=-3.2）、502 门（y=-8.4）、公告栏、灭火器、管道、电表箱。
- 东墙 x=+1.1：503 门（y=-5.3，通往室内，**门洞真实开口**）、504 门（y=-10.2）、信箱（y=-1.5 附近）、配电箱。
- 走廊灯：5 组日光灯盒（y=-1.8/-5.4/-9/-12.6/-16.2，z≈2.6），材质 MAT_lamp_tube，下方放 LIGHT Empty。
- 细节：墙裙、踢脚线、地砖破损、水渍、小广告、垃圾、窗（y≈-14 东墙）带 MAT_window_night。

**503 室内**（在走廊东侧，通过 503 门洞相连）：
- 玄关：x ∈ [1.1, 2.6]，y ∈ [-6.3, -4.3]，层高 2.6；鞋柜 `S_shoe_cabinet`（柜顶放 `INT_flashlight`，默认可见）、衣帽钩、拖鞋、雨伞、穿衣镜。
- 客厅：x ∈ [2.6, 6.6]，y ∈ [-7.8, -2.9]；餐桌 + 2 椅、沙发、茶几、电视柜 + CRT 电视（MAT_tv_static 雪花屏）、书架、落地灯、地毯、挂钟 `INT_clock`、墙上全家福 `S_photo_1/2`、南墙窗 + 窗帘。
- 厨房小凹间：x ∈ [2.6, 4.2]，y ∈ [-9.6, -7.8]；灶台、水槽、吊柜（放 `INT_letter_02`）。
- 卧室：x ∈ [6.6, 9.4]，y ∈ [-7.8, -3.4]；门在 x=6.6 墙上 y≈-5.6（`INT_door_bedroom`，locked=True），门洞真实开口；床、衣柜、床头柜、椅子 `S_chair_final`（面向南窗）、南墙窗 + 窗帘、床灯、照片。
- 地面：客厅木地板 MAT_wood_floor；厨房/玄关可用 MAT_concrete 或旧地砖；卧室木地板。
- 墙面：MAT_wallpaper / MAT_wallpaper_dark / MAT_plaster；顶 MAT_paint_ceiling。

### 4.2 必须命名的交互/实体/灯/出生点

- 门：`INT_door_503`（主门，interact=door，prompt="开门"，open_angle=95，open_dir=1）、`INT_door_bedroom`（locked=True，interact=door）、`INT_door_501`、`INT_door_502`、`INT_door_504`（interact=door，locked=True，examine 用；可以只做门扇，引擎按 locked 提示）、`INT_fire_door`（examine）、`INT_elevator_button`（examine）。
- 开关：`INT_switch_corridor`（switch/examine）、`INT_switch_living`（switch，控制客厅顶灯）。
- 拾取：`INT_flashlight`（pickup）、`INT_battery_01`（pickup，走廊信箱上）、`INT_battery_02`（pickup，客厅电视柜上）、`INT_letter_01`（pickup，餐桌上）、`INT_letter_02`（pickup，厨房台面）、`INT_letter_03`（pickup，客厅书架上）、`INT_letter_final`（pickup/final，卧室床上，hidden=True）。
- 环境：`INT_clock`（examine，客厅墙面）、`S_photo_1`、`S_photo_2`。
- 实体：`ENTITY_she`（白裙长发女人，站立，脚底原点，hidden=True，~350–700 tris，面部不要太清晰）。
- 出生点：`SPAWN_corridor`(0,-1.0,0)/`LOOK_corridor`(0,-10,1.55)；`SPAWN_apartment`(1.9,-5.3,0)/`LOOK_apartment`(4.5,-5.2,1.55)；`SPAWN_bedroom`(7.0,-5.4,0)/`LOOK_bedroom`(8.6,-6.4,1.4)。
- 灯光 Empty：`LIGHT_corr_01..05`（point，冷白 `#cfe0d8`，power 20，radius 7，flicker 0.12）、`LIGHT_entry`（暖白，10W，radius 4）、`LIGHT_living`（暖白 25W，radius 7）、`LIGHT_tv`（冷蓝 `#8fb4ff`，8W，radius 3，flicker 0.35）、`LIGHT_floor_lamp`（暖黄 `#ffcf9a`，18W，radius 5）、`LIGHT_kitchen`（冷白 12W，radius 4）、`LIGHT_bedroom`（暗红暖 `#d99a6a`，12W，radius 4，默认可在引擎关掉）、`LIGHT_moon_bed`（冷蓝 `#7e9cc8`，6W，radius 5）。
- 第二轮变体（hidden=True，`V2_` 前缀）：`V2_corr_chair`（走廊中央的折叠椅）、`V2_door_501_ajar`（501 半开门扇）、`V2_stain_01/02/03`（墙面污渍平面，贴 MAT_stain_mold / MAT_stain_water）、`V2_mail_scatter`（散落信件）、`V2_bulb_dead`（走廊一只灭掉的灯管，材质 MAT_metal_rust 或暗玻璃）。
- 第三轮变体（hidden=True，`V3_` 前缀）：`V3_handprints_01/02/03`（墙上的深色手印/抓痕平面，MAT_stain_mold）、`V3_stain_04/05/06`、`V3_door_502_ajar`、`V3_door_504_ajar`、`V3_corr_water`（走廊积水平面，MAT_stain_water）。
- COL：走廊两侧墙、503 门洞两侧墙、室内各墙、厨房、卧室墙；家具（鞋柜、餐桌、沙发、茶几、电视柜、书架、床、衣柜、床头柜、厨房台面、吊柜）；电梯口/防火门；边界封死。

### 4.3 玩法需要的空间关系（给玩法代码的提示，建模需保证）

- 玩家的门 503 在走廊东墙，开门后能直接走进玄关。
- 卧室门打开后，能从客厅直接走进去。
- 走廊足够宽（2.2m）让实体从远端追来；实体藏身/出现点由引擎放在走廊南端附近（建议建模时把南端电梯区域做得略暗一些）。
- 灯管损坏时房间要仍能靠手电视物：室内不用非自然光源也能看清轮廓（别做全黑贴图）。

## 5. 《镜中》mirror.glb

### 5.1 布局

**更衣室**：x ∈ [-3.6, 3.6]，y ∈ [-2.8, 2.8]，层高 3.0。
- 北墙 y=+2.8：镜墙。`MIRROR_surface` 是一块**独立平板 mesh**，位于 y=2.74，面向 -Y，尺寸 4.2m × 1.5m（x -2.1..2.1，z 1.0..2.5），UV 完整 0–1。周围镜框 `S_mirror_frame`；镜前洗手台 `S_basin_counter`（z 0.8–0.95），3 个台盆 + 水龙头 `S_faucet_01..03`，台面上肥皂盒、杯子、拖把池。
- 南墙 y=-2.8：两排更衣柜 `S_locker_bank_1`（x -3.2..-0.7）、`S_locker_bank_2`（x 0.7..3.2），柜门缝隙清晰；`INT_locker_02` 是 bank_1 的第二扇柜门（原点在左侧铰链，可开 100°），其它柜门静态关闭。柜顶灰尘、旧毛巾。
- 房间中央：长凳 `S_bench`（1.8×0.45×0.45，沿 x 向，y≈-0.4）和一张木凳 `INT_stool_01`；另一张凳子 `INT_stool_02` 初始靠西墙（引擎会移动它，配 `MARK_stool_home`/`MARK_stool_away`，away 目标在镜前洗手台下方）。
- 东墙 x=+3.6：通往浴池的门 `S_door_bath`（关着，上方 MAT_sign_bath「男湯」，门缝透出蒸汽 `S_steam_01/02`，透明材质 MAT_steam，引擎可微动），暖气片、拖把桶。
- 西墙 x=-3.6：高窗 `S_window_high`（MAT_glass_dirty + MAT_window_night），墙钟 `INT_clock`，电灯开关 `INT_switch`（在门附近），挂钩和旧工作服。
- 天花板：2 组日光灯 `S_tube_01/02`（MAT_lamp_tube）+ LIGHT；墙面瓷砖 MAT_tile_green（下半墙），上半墙 MAT_plaster；地面 MAT_tile_floor；天花 MAT_paint_ceiling。地漏、积水、破损瓷砖、长凳下水渍。
- 道具：红色毛巾 `INT_towel`（初始在地面上，配 `MARK_towel_floor` 与挂钩位置 `MARK_towel_hook`）、收音机 `INT_radio`（在长凳上）、旧模特 `INT_mannequin`（角落，白色/木色，可整体旋转）、拖把、水桶、肥皂、香烟、报纸。

### 5.2 必须命名

- `MIRROR_surface`（镜面平板；引擎会替换成实时反射材质，必须保持独立、UV 完整）。
- 交互：`INT_towel`（move，prompt="拿起毛巾"）、`INT_valve`（valve，prompt="拧阀门"，原点在阀门轴心，材质 MAT_metal_rust）、`INT_switch`（switch，prompt="开关灯"）、`INT_stool_01`（move）、`INT_stool_02`（move，配 MARK）、`INT_locker_02`（move/door，原点左铰链）、`INT_radio`（radio）、`INT_mannequin`（move）、`INT_clock`（examine）。
- MARK：`MARK_towel_floor`、`MARK_towel_hook`（挂钩处，z≈1.55）、`MARK_stool_home`（西墙边）、`MARK_stool_away`（洗手台下）。
- 反射实体：`ENTITY_reflection`（人形，白色/灰白，背面或正面朝镜，脚底原点，hidden=True，~400–800 tris）。
- 出生点：`SPAWN_mirror`(0,-1.6,0)/`LOOK_mirror`(0,2.5,1.5)。
- 灯：`LIGHT_tube_01`、`LIGHT_tube_02`（冷白 `#d7f0e4`，power 25，radius 8，其中一支 flicker 0.08）、`LIGHT_bench`（暖黄 `#ffcf9a`，15W，radius 4）、`LIGHT_bath`（门缝暖光/蒸汽光，`#ffb87a`，10W，radius 3）、`LIGHT_window`（冷蓝 `#7e9cc8`，8W，radius 6）。
- COL：四面墙、洗手台整体、两排更衣柜、长凳、门、暖气片、模特。

### 5.3 玩法需要

- 镜面必须是一块**平面**，玩家站在镜子前（约 y≈2.0）能看到完整镜面，镜面反射用引擎的 planar reflection helper。
- 房间中央要留出足够空间（玩家能绕过长凳走动，半径 0.32m）。
- 镜子两侧、洗手台上方要留出挂毛巾的挂钩位置（`MARK_towel_hook`）。
- 房里要能同时看到：镜面、毛巾、阀门、灯开关、凳子、柜门、收音机、模特——方便玩家对比镜子。
- 反射场景是同一 GLB 的克隆，玩法代码会移动克隆里的物品；所以所有可交互部件都要能独立移动/旋转，别把毛巾/凳子/柜门/阀门焊进静态 join。

## 6. 《夜路》nightroad.glb

### 6.1 布局

- 土路：宽 3.2m，从 y=0 延伸到 y=-98，带轻微 S 弯（中心线建议：(0,0)→(1.5,-16)→(-0.5,-32)→(2.0,-48)→(0,-64)→(-1.5,-80)→(0,-98)）。路面用 MAT_soil，边缘 MAT_grass，远处稻田/草地平面。
- 玩家出生：`SPAWN_night_start`(0, 1.2, 0)，`LOOK_night_start`(0,-25,1.4)。
- 五盏纸灯笼 `INT_lantern_01..05`：位于土路两侧，y ≈ -12 / -28 / -44 / -60 / -78，x 在路缘 ±1.8~2.3；每盏 = 木杆 + 横挑 + 红纸灯笼（MAT_lantern_paper），原点在灯笼主体中心，z≈1.35；未点亮由引擎控制自发光与灯光，模型要能看出是灯笼（竹骨、竖纹）。
- 土地庙（终点，y≈-98）：`S_shrine` 小庙 1.4m 宽 × 1.2m 深 × 1.8m 高，旧红木 MAT_shrine_wood，屋顶、门洞、红布 `S_shrine_cloth`、石牌位 `S_shrine_tablet`（MAT_shrine_tablet，正面 0–1 UV）、香炉 `S_incense_burner`（内插香，`INT_incense` 为可交互香束，prompt="上香"）、两根蜡烛（MAT_lamp_warm）、台阶、小香炉、供品。庙在路尽头略高处（仍可用平地，做 2–3 级台阶但玩法不需要走上：玩家在庙前交互）。
- 树：8–12 棵低多边形树（`S_tree_01..10`，树干圆柱 + 2–3 个多面体树冠，MAT_bark / MAT_leaves），分布在路两侧 5–12m；主树 1 棵在庙旁。
- 电线杆：`S_pole_01..04` 沿路，木杆 + 横担 + 下垂电线（曲线转 mesh 或细圆柱链，低面数），偶尔挂一盏不亮的路灯。
- 路牌：`S_sign_1`（y≈-8，MAT_sign_night_1），`S_sign_2`（y≈-50，MAT_sign_night_2），木柱 + 板面，板面正面 UV 完整。
- 路边：`S_grave_01..03`（土坟/石碑，MAT_stone，远处田边）、`S_paper_money_01..04`（MAT_paper_money 小平面，路边散落）、`S_scarecrow`（y≈-36 田里，稻草人剪影，MAT_fabric_white/木）、`S_bicycle`（y≈-70 路边，倒地的旧自行车，低面数，可选）、`S_village_lights`（远处 y≈-120 的几盏暖色小灯，MAT_lamp_warm，暗示村子）。
- 实体：`ENTITY_paper`（纸人，身高 ~1.75，纸白身体、墨线眼、红颊、红绳，脚底原点，hidden=True，~500–900 tris；轮廓要像人但比例略不对）。
- 灯光：`LIGHT_shrine`（暖红 `#ff9a5a`，point，12W，radius 4）、`LIGHT_moon`（冷蓝，可作为方向光由引擎处理，不必建 Empty）、`LIGHT_village`（远处微弱暖光，point 8W，radius 10）。
- COL：沿路两侧的隐形边墙 `COL_path_edge_L_01..08`、`COL_path_edge_R_01..08`（每段 8–14m，高 2m，玩家不能走出路和路肩）；`COL_shrine`、`COL_tree_shrine`、`COL_pole_*`（可选）。道具、纸钱不要 COL。
- 环境：地上碎石、泥坑、草垛、落叶、田埂；用低面数几何和材质变化做层次，不要靠贴图细节。

### 6.2 命名必须项

`SPAWN_night_start`、`LOOK_night_start`、`INT_lantern_01..05`、`INT_incense`、`ENTITY_paper`、`S_shrine`、`S_shrine_tablet`、`S_incense_burner`、`S_sign_1`、`S_sign_2`、`S_grave_01..03`、`S_scarecrow`、`LIGHT_shrine`、`LIGHT_village`、`COL_path_edge_L_01..08`、`COL_path_edge_R_01..08`、`COL_shrine`。

### 6.3 玩法需要

- 玩家沿路前进，五盏灯笼在路侧可见但要在雾中若隐若现（引擎雾距离约 25–40m，所以灯笼间距 16–20m 合理）。
- 每盏灯笼的位置是重生点；游戏代码会从灯笼对象位置取坐标。
- 终点庙前要有 3–4m 见方的空地供玩家站定交互。
- 回头时能看到来路与纸人——路面不要有遮挡视线的急弯。

## 7. 自检（必须做）

### 7.1 脚本自检
写 `tools/blender/validate_assets.py`（headless 运行），对每个 GLB：
- 打印：文件大小、mesh 数、tri 数、材质名列表、Empty 名列表、自定义属性覆盖情况；
- 检查：必需名字是否齐全（§4.2/§5.2/§6.2）；材质名是否都在 §3 清单；tri 数是否超预算；COL_ 是否存在；spawn/look 是否成对；
- 结果写 `reports/modeler/validate.txt`，并打印 `VALIDATE OK` / `VALIDATE FAIL: ...`。

### 7.2 预览渲染
`tools/blender/render_previews.py`：
- 每个场景 3 张 960×540 EEVEE 渲染：
  - `door_preview_corridor.png`（走廊出生点视角）、`door_preview_living.png`（客厅）、`door_preview_bedroom.png`（卧室）；
  - `mirror_preview_room.png`（从门口看镜墙）、`mirror_preview_mirror.png`（近镜面）、`mirror_preview_lockers.png`；
  - `nightroad_preview_start.png`（路起点）、`nightroad_preview_mid.png`（灯笼段）、`nightroad_preview_shrine.png`（庙）。
- 用临时相机 + 灯光，放在 `PREVIEW` collection，**不要导出**；渲染完检查：物体是否落地、门洞是否通、尺度是否合理、有没有缺失面/穿模。
- 用 read_image 工具亲自看渲染图，至少迭代 2 轮修问题（灯光/构图/空洞）。
- 渲染图放 `reports/modeler/`。

### 7.3 完成汇报
向 Lead 汇报：
- 3 个 GLB 的路径/大小/面数；
- validate.txt 结论；
- 每张预览的路径和你自己看到的问题（已修/未修）；
- 玩法依赖的名字是否全部存在；
- 剩余风险。

## 8. 验收清单

- [ ] `door.glb` / `mirror.glb` / `nightroad.glb` 存在，可被 Blender / three.js 正常加载；
- [ ] 所有必需名字存在，自定义属性正确；门/毛巾/凳子等枢轴正确；
- [ ] 材质名全部在清单内，无贴图、无相机、无灯光对象；
- [ ] COL 覆盖碰撞，门洞净宽 ≥ 0.9m；
- [ ] 面数在预算内，视觉上不是一堆纯方块；
- [ ] 9 张预览图目视通过，物体不悬空/不陷地/不穿墙；
- [ ] 脚本在 `tools/blender/` 可重跑复现。
