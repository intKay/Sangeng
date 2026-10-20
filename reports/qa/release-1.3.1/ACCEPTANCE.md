# 三更 v1.3.1 验收记录（输入方式补丁）

日期：2026-10-20（Asia/Taipei）  
版本：`1.3.1`（网页包 / Windows 安装版 / 便携版）  
范围：修复“测试、录屏或调试时鼠标频繁被指针锁定”的体验问题；内容、场景与 v1.3.0 相同。  
基线：v1.3.0 的完整验收见 [`reports/qa/release-1.3.0/ACCEPTANCE.md`](../release-1.3.0/ACCEPTANCE.md)。

## 变更内容

- 设置 → 操作方式新增 **鼠标拖动（不锁定指针）**：不申请 Pointer Lock；按住左键拖动环视；`WASD` / `E` / `Shift` / `Esc` 继续可用；点击画布不会重新锁定。
- 默认 **键盘 / 鼠标（锁定指针）** 手感不变；`Esc` 释放并暂停。
- 选择写入本地设置（`sangeng-settings-v1`），切回键鼠模式时恢复锁定。
- 触屏模式与自动识别逻辑保持：自动识别只在触屏设备或无 Pointer Lock API 时进入触控；`drag` 模式不会误开虚拟摇杆。
- 拖动模式使用画布 `grab / grabbing` 光标，避免隐藏光标。

涉及文件：`engine/player.js`、`engine/engine.js`、`engine/touch.js`、`engine/ui.js`、`engine/engine.css`。

## 发布产物

| 文件 | 字节 | SHA-256 |
|---|---:|---|
| `Sangeng-1.3.1-web.zip`（339 个运行文件） | 33,233,885 | `eb848f8fc245c03bb175555b7ee3a82f17494cb235ec4519bc4f94f0410860dc` |
| `Sangeng-1.3.1-Setup-x64.exe` | 144,297,932 | `f2c3f0fafdcdb35f9c26ac28a3ebfb8c1f886df52f7b5bf7270407ab34d72d43` |
| `Sangeng-1.3.1-Portable-x64.exe` | 144,068,038 | `57948b2437aa1396da77ba0a73536e6b0026e2c7355c0320390338105f583301` |

## 验证矩阵

| 项目 | 方法 | 结果 | 证据 |
|---|---|---|---|
| 输入模式专项 | `tools/verify_pointer_mode.cjs`（Electron 源码运行 + 打包后的 `win-unpacked\Sangeng.exe`，真实鼠标/键盘） | 两种运行结果一致：默认 `auto` 模式锁定指针；`Esc` 释放；切到 `drag` 后恢复游戏不再锁定；左键拖动使 yaw 变化 -0.476；拖动中与点击画布后均无指针锁定；切回 `mouse` 模式恢复锁定；0 运行时错误 | `reports/qa/pointer-mode/result.json`、`reports/qa/release-1.3.1/pointer-mode/result.json`、`settings-modes.png`、`drag-mode-playing.png` |
| 网页包结构 | `tools/build_web.py` 内置断言（CRC、根目录 index、文件数、大小写唯一、路径长度、单文件/总量、Ogg+MP3 成对） | 339 个文件；33,233,885 字节 | `dist/web/web-manifest.json` |
| 手机 / 桌面浏览器 | `tools/verify_web.cjs` 对从 ZIP 解压的 `qa-build` | Android 横屏 3 篇、竖屏、小屏手机（MP3 兜底）、平板、桌面 3 篇、WebKit 手机：入口与章节可进入，贴图 62/62，`touch` 标志正确，sandbox iframe 与旋转正常 | `reports/qa/release-1.3.1/web/result.json` 与 `*.png` |
| 内容回归 | `tools/verify_content.cjs`（真实键鼠，调试放置接近交互物） | 门后 3 拾取 + 4 查看 + 死亡重试 + 结局；镜中错误死亡重试 + 3 回合 + 结局；夜路 5 灯 + 上香 + 按 W 结局；字幕队列（含 120ms 间隔）通过；三篇 `errors: []`、`failedRequests: []` | `reports/qa/release-1.3.1/content/source-result.json`、`*.png` |
| Windows 便携版 | 启动冒烟：把 `Sangeng-1.3.1-Portable-x64.exe` 的字节级副本（SHA-256 一致）放到干净的 ASCII 目录后双击启动，等待窗口、截图、正常关闭 | 自解压与窗口启动通过，进程从 `%TEMP%` 解包运行；运行时资源与交互由上面的打包 `win-unpacked` 专项覆盖 | `reports/qa/release-1.3.1/desktop/portable-smoke.json`、`portable-smoke.png` |

## 自动化环境说明

- Electron 自动化在 Windows 上使用 `--no-sandbox --disable-gpu --disable-features=CalculateNativeWinOcclusion` 等测试用参数；**不改变游戏可执行文件或安装包的运行参数**。
- 内容回归的 `tools/verify_content.cjs` 增加了字幕轮询断言与失焦暂停恢复，只影响测试宿主；不改变游戏逻辑。
- 输入模式判断以真实 Electron 窗口验证（源码运行 + 打包 `win-unpacked`）；网页包构建由 `build_web.py` 从同一份源码生成。
- 便携版自解压启动器不会把 `--remote-debugging-port` 转发给内部应用，因此旧的 CDP 便携验收脚本不适用于该目标；本版改为窗口级启动冒烟 + 打包应用专项回归。安装版此前已由 v1.3.0 的安装后验收覆盖，本补丁未改安装器逻辑。
- 在 `C:\AIProjects\文艺漫游` 下的部分路径（含 `.scratch` 与普通子目录）直接运行便携自解压 EXE 会出现 `NSIS Error`；同一字节的副本放到 `C:\Temp`、`C:\AIProjects\test-portable` 或 `C:\Temp\中文目录` 均可正常解包启动。根因未确认，判断为本机/工作区路径相关的自解压启动异常，不影响发布包字节；`portable-smoke.json` 记录了复制校验和运行位置。

## 未覆盖与限制

- 未做真实手机 / 平板与 itch.io 线上验收；手机结论来自 Chromium 设备模拟。
- 未做人耳音量平衡、真人完整通关、异机验收。
- 桌面包仅 Windows x64，EXE 未数字签名。
- 未在更多 Windows 用户路径/受限目录下验证便携自解压；上面记录了一处本机路径相关异常。
- 指针锁定行为依赖浏览器权限与用户手势；在禁止 Pointer Lock 的 iframe 中，键鼠模式会自动退化为不锁定（游戏仍可用拖动模式游玩），本轮未针对该场景做真机验收。
