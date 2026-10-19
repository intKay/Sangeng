# v1.0.2 本地视觉验证截图

分支：`feat/v1.0.2-door-mirror`（内容提交 `4827cfb`，另含本目录与交接说明的追加提交）
本地服务器：`python serve.py 8140`，Chromium/Playwright，1280×720，Windows。

| 文件 | 内容 |
|---|---|
| `door_gate.jpg` | 门后 · 503 门口：新公告栏、门框对联、门牌、门口布鞋 |
| `door_ending.jpg` | 门后 · 结局：坐在椅子上的 `ENTITY_she_sitting` 与卧室暖光 |
| `mirror_handprints.jpg` | 镜中 · 第三回合：镜面水汽手印（2 枚，游戏层加色 quad） |
| `mirror_walkout.jpg` | 镜中 · 结局演出：镜中人从镜面“走出”，现实侧轮廓光 |
| `mirror_ending.jpg` | 镜中 · 结局页「留下的人」 |
| `nightroad_sign.jpg` | 夜路 · 路牌（全局 unit-UV V 修正后文字正立；玩法未改） |

## 本轮本地检查

- `node --check games/{door,mirror,nightroad}/game.js` 通过。
- 三个 demo 依次加载并点击开始：音频 ready、贴图 62/62、console 0 error、无未处理 JS 异常。
- 门后：真实 E 拾取三张字条中的前两张触发 V2/V3 与 `glimpse`；503 门牌/对联/公告栏正立；坐姿结局可达；新增查看物（照片/挂历/公告栏/儿童画/小鞋等）全部可触发。
- 镜中：三回合、手印阶段 1/2/3 枚、`crack=true`、结局页与 ending 音乐均通过；R3 补光后长凳/镜框/柜门可辨。
- 夜路：路牌/石牌位正立；仅加字幕 wrapper，玩法未改。
- 资产校验：`reports/modeler/v1.0.2-validate.txt`（door 8652 tris / mirror 4716 / nightroad 5710，VALIDATE OK）、`reports/art/v1.0.2-verify.txt`（62 材质，V102 VERIFY OK）。

> 这是本地内容分支的验证证据，不代表 Codex 的最终发布测试；引擎、打包、Release 由 Codex 负责。详见 `docs/HANDOFF-v1.0.2.md`。
