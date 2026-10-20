# 三更 v1.3.0 验收记录

日期：2026-10-19；安装成品补验：2026-10-20（Asia/Taipei）
版本：`1.3.0`（网页包 / Windows 安装版 / 便携版）  
发布分支：`codex/v1.3.0-polish-release`（合并后由 tag `v1.3.0` 指向）  
验证机：Windows、单机；Chromium 由 Electron 44.9.0 内置（Chromium 152.0.7977.167）。

## 结论

v1.3.0 的网页包与 Windows 桌面包已完成本轮可执行的自动化验收：三篇核心交互、门后手电、暂停/设置、字幕队列、死亡重试、两种夜路结局、手机横屏触控布局、62 张贴图与音频资源、GLB 资产预算与打包完整性均通过。**尚未完成**手机真机、人耳音量平衡、真人完整通关、异机与 itch.io 线上验收；这些边界在本文件末尾列出。

## 发布产物

| 文件 | 字节 | SHA-256 |
|---|---:|---|
| `Sangeng-1.3.0-web.zip`（339 个运行文件） | 33,235,688 | `ad4f36c31588b3ffcbd3515da80381d82218fe53dde2cc3fe856624bec1b4628` |
| `Sangeng-1.3.0-Setup-x64.exe`（Electron 44.9.0） | 144,297,322 | `4a15d0b31d775c84a29c24edc53b88b89652d0dcf73755644d45c6bf3e4c39` |
| `Sangeng-1.3.0-Portable-x64.exe` | 144,067,433 | `18ee4d6d21ad35a50ac742499ce4958a3a615e14e77748d07f1696f3935e2f0b` |

网页包 manifest：`dist/web/web-manifest.json`（`runtime_files: 339`，`itch_limits_checked: true`）。桌面 manifest：`dist/desktop/desktop-manifest.json`。合并校验值见 Release 的 `SHA256SUMS.txt`。

## 验证矩阵

| 项目 | 方法 | 结果 | 证据 |
|---|---|---|---|
| 网页包结构 | `tools/build_web.py` 内置断言：ZIP CRC、`index.html` 在根、文件数 ≤ 1000、大小写唯一、路径长度、单文件与总量上限、Ogg/Mp3 成对 | 通过；339 个文件 | `dist/web/web-manifest.json` |
| 手机横屏触控 | `tools/verify_web.cjs` 的 `android-landscape`（Chromium 移动模拟 + sandbox iframe） | 三篇均可进入；`touch: true`；62 张贴图、0 缺失；音频 running，峰值约 0.20–0.21；旋转后仍可操作 | `reports/qa/release-1.3.0/web/android-landscape-*.png`、`android-landscape-result.json` |
| 小屏手机 | `verify_web.cjs` 的 `small-phone`（MP3 兜底路径） | 《门后》可交互；`mp3: true`；触控与旋转正常 | `reports/qa/release-1.3.0/web/small-phone-*.png`、`small-phone-result.json` |
| 桌面 Chromium | 同一脚本的桌面视口 | 入口页与三篇首屏、贴图 50→62 张全部就绪，0 请求失败 | `reports/qa/release-1.3.0/desktop/home.png` 等 |
| Windows 安装版运行 | `tools/verify_desktop.cjs` 对安装后的 `Sangeng.exe` | 三篇可启动；贴图 62/62、`audioMissing: []`；鼠标锁定、暂停/设置、核心 E 交互正常；窗口可正常关闭；0 page error、0 失败请求 | `reports/qa/release-1.3.0/desktop/result.json` |
| 内容回归（源码构建） | `tools/verify_content.cjs`（真实键鼠，调试放置接近交互物） | 门后：4 个新增查看、3 张字条、真实追逐死亡与重试、结局；镜中：错误使用死亡与重试、3 回合解谜、结局；夜路：5 盏灯、上香、选择提示、按 W 走向结局。三篇字幕队列与音频信号通过；`errors: []`、`failedRequests: []` | `reports/qa/release-1.3.0/content/source-result.json`、`content/*.png` |
| 内容回归（已安装成品，2026-10-20） | `verify_content.cjs` 指向实际安装后的 `Sangeng.exe`；真实键鼠，辅助放置玩家 | 门后：4 个新增查看、3 张字条、死亡重试与结局；镜中：错误使用死亡重试、3 回合 E 解谜与结局；夜路：5 盏灯 E 交互、上香与按键进入结局。三篇字幕及非零音频信号通过，0 页面错误、0 失败请求 | `reports/qa/release-1.3.0/content/packaged-result.json` |
| 已安装资源一致性（2026-10-20） | `verify_desktop_resources.cjs` 对安装目录 `resources/app.asar` 内文件逐项 SHA-256 比对网页发布 manifest | 339 个运行文件全部一致；仅另有 NOTICE、package.json、桌面入口 3 个文件 | `reports/qa/release-1.3.0/resources.json` |
| 贴图资产 | `reports/art/v1.0.2-verify.txt` + 运行时 `textures: 62` | 62 条 manifest 全部可加载；新增 12 张叙事贴图 386.4 KB（上限 500 KB） | `reports/art/v1.0.2-verify.txt` |
| GLB 资产 | `tools/blender/validate_assets.py` | door 8,652 tris / 43 材质 / 74 必需节点；mirror 4,716 / 31 / 58；nightroad 5,710 / 22 / 57；碰撞体与 SPAWN/LOOK 全部通过。door 超出目标 6,000 但低于上限 9,000，记为警告 | `reports/modeler/validate.txt` |
| 材质视觉对照 | `tools/verify_scene_views.cjs` 对 12 个疑难材质做近景取景 | 材质与位置符合预期（铭牌、日历、公告板、家庭照片、澡堂告示、土地庙牌位等） | `reports/qa/release-1.3.0/visuals/result.json` |

## 内容回归细节

- **门后**：503 门开合与提示刷新；手电拾取与 F 切换；照片、日历、公告板、儿童画 4 个新增查看；3 张字条分别触发 3 轮循环；实体真实追上后死亡、重试保留已拾取字条；坐姿与椅子对齐；最终信件进入结局。
- **镜中**：故意错误使用阀门触发惩罚/死亡与重试；3 个回合全部用真实 E 解谜；镜面裂纹与结局；字幕队列在转场后仍按顺序显示。
- **夜路**：5 盏灯全部用真实 E 点亮；上香触发 8 秒过场；选择提示出现；按 W 前进约 2.2 秒进入“没有回头”结局。
- 三篇均报告 `textures: 62`、`missing: []`、`signal.peak > 0`、`errors: []`、`failedRequests: []`。

## 自动化环境说明

- `tools/verify_content.cjs` 本轮新增了以下测试侧改进：可选 `SANGENG_QA_FLAGS`（本机使用 `--no-sandbox --disable-gpu --disable-features=CalculateNativeWinOcclusion --disable-background-timer-throttling --disable-renderer-backgrounding`）、交互前自动从失焦暂停中继续、延长的等待改用轮询辅助函数。**这些只影响测试宿主，不改变游戏运行参数或可执行文件。**
- 内容回归使用 `player.teleportToPos()` 把玩家放到交互物附近，交互仍由真实键盘 `E / F / W` 与按钮触发；这不等于正常路线可达性验收。
- 失败样本 `content/failure.json` 与 `failure.png` 保留为本地历史记录：此前曾在夜路新增结局断言后超时，测试脚本已修正按键时序与失焦暂停处理。2026-10-20 使用同一已安装成品完整复验通过，成功结果以 `content/packaged-result.json` 为准；源码结果另见 `content/source-result.json`。
- 2026-10-20 从 GitHub API 核对 v1.3.0 为正式公开 Release，标签与当时 main 均指向 `f5fd38bdea5747d3f62c7336039bd7c295e66400`。本地网页 ZIP、Setup EXE、Portable EXE 的 SHA-256 与远端附件 digest 一致；这项核对不等于重新下载两个 EXE。本次只补验收证据，不更换发布包或移动标签。

## 复验命令

```powershell
# 网页包与 manifest
python tools/build_web.py
python -c "import zipfile; zipfile.ZipFile('dist/web/Sangeng-1.3.0-web.zip').extractall('dist/web/qa-build')"

# 手机/桌面浏览器验收（需要 Playwright Chromium）
node tools/verify_web.cjs

# 内容回归（源码构建）
$env:SANGENG_QA_FLAGS='--no-sandbox --disable-gpu --disable-features=CalculateNativeWinOcclusion'
node tools/verify_content.cjs

# Windows 安装版运行验收
node tools/verify_desktop.cjs "<安装后的 Sangeng.exe 路径>"

# 已安装成品完整内容回归与资源比对
node tools/verify_content.cjs "<安装后的 Sangeng.exe 路径>"
node tools/verify_desktop_resources.cjs "<安装目录>/resources/app.asar" dist/web/web-manifest.json
```

## 未覆盖与限制

- 没有真实手机（Android / iPhone）与平板真机测试；触屏结论来自 Chromium 设备模拟与 sandbox iframe。
- 没有真人完整通关、人耳音量平衡、真实鼠标手感与晕动评价。
- 没有异机验收；桌面包仅 Windows x64，EXE 未数字签名。
- 未在 itch.io 线上页面验收；同一网页包由用户手动上传。
- 没有重新做人耳混音与各篇节奏的主观评估；镜面偏暗、关灯回合灯管仍自发光等观感限制沿用 v1.2.0。
