# 三更 v1.3.1 · 桌面游玩与分享

下载 [v1.3.1 Release](https://github.com/intKay/Sangeng/releases/tag/v1.3.1) 的安装版 `Sangeng-1.3.1-Setup-x64.exe`，双击安装并使用桌面快捷方式启动。

免安装使用 `Sangeng-1.3.1-Portable-x64.exe`：下载后直接双击；它自动解包内置运行时，首次启动需要几秒。无需 ZIP 解压工具，也无需打开浏览器。

- Windows 10/11 x64，支持 WebGL2 的显卡。内置 Electron 44.9.0 / Chromium 152；不调用 Edge/Chrome，不启动本地 HTTP 服务，不需要 Python、Node 或 .NET。
- 桌面版与网页包来自同一份源码：三篇场景、62 张贴图、121 个音频事件与界面一致；桌面版额外内置 Electron 运行时，因此包体约 144 MB。
- 首次点击“开始”解锁声音。WASD 移动，鼠标环视，Shift 快走，E 交互，Esc 暂停；F 仅用于门后拾取后的手电。
- 不想被锁定鼠标：暂停 → 设置 → 操作方式 → **鼠标拖动（不锁定指针）**。按住左键拖动环视，WASD 与 E 照常使用，浏览器不再捕获指针；切回“键盘 / 鼠标（锁定指针）”即恢复原手感。
- 关闭窗口即退出。设置保存在当前 Windows 用户的应用数据目录；便携 EXE 指免安装，设置仍按用户保存。
- 未数字签名，可能出现未知发布者提示；请核对下载来源和 `SHA256SUMS.txt`，无需关闭安全防护。
- 默认安装范围是当前用户。

## 手机 / 浏览器

同一个网页包适配桌面与触屏：摇杆移动、拖动环视、交互 / 快走 / 手电 / 暂停按钮，横竖屏与安全区均已适配。下载 `Sangeng-1.3.1-web.zip` 用于完整静态托管或上传 itch.io，请勿在 ZIP 内直接双击 HTML；手动步骤见 [itch.io 手机适配说明](ITCHIO_MOBILE.md)。

## 旧 ZIP 无图片的诊断边界

用户反馈是浏览器打开后无图片，并非已确认解压失败。旧包本地 CRC 通过且 SHA-256 与远端附件元数据一致；没有证据表明原 Release ZIP 损坏。直接从 ZIP 预览 HTML、只取出 HTML、没有 HTTP 服务等情况可能导致资源或模块加载失败，但本次未取得用户原始打开步骤，不能断定具体原因。

v1.0.1 / v1.1.0 / v1.2.0 历史 Release 及附件保留；其 web.zip 用于完整静态托管，不应从 ZIP 内直接双击 HTML 游玩。旧 Windows EXE 是调用本机浏览器的 C# 启动器，新版桌面包不再走该链路。

## 从源码构建

```powershell
npm ci
npm run dist
```

使用 Node.js 22.12+；首次安装与构建需联网。输出 `dist/desktop/` 的两种 EXE、SHA-256 和 manifest；工具使用独立临时目录构建。网页包使用 `python tools/build_web.py`。

验收与限制见 [v1.3.1 验收记录](../reports/qa/release-1.3.1/ACCEPTANCE.md)。
