# 三更 v1.1.0 · 桌面游玩与分享

下载 [最新 Release](https://github.com/intKay/Sangeng/releases/latest) 的安装版 `Sangeng-1.1.0-Setup-x64.exe`，双击安装并使用桌面快捷方式启动。

免安装使用 `Sangeng-1.1.0-Portable-x64.exe`：下载后直接双击；它自动解包内置运行时，首次启动需要几秒。无需 ZIP 解压工具，也无需打开浏览器。

- Windows 10/11 x64，支持 WebGL2 的显卡。内置 Electron 44.9.0 / Chromium 152；不调用 Edge/Chrome，不启动本地 HTTP 服务，不需要 Python、Node 或 .NET。
- 三篇与 v1.0.1 的 205 个运行文件逐字节一致，保留原有玩法、美术与声音。
- 首次点击“开始”解锁声音。WASD 移动，鼠标环视，Shift 快走，E 交互，Esc 暂停；F 仅用于门后拾取后的手电。
- 关闭窗口即退出。设置保存在当前 Windows 用户的应用数据目录；便携 EXE 指免安装，设置仍按用户保存。
- 未数字签名，可能出现未知发布者提示；请核对下载来源和 `SHA256SUMS.txt`，无需关闭安全防护。
- 内置完整运行时后下载约 128 MB；默认安装范围是当前用户。

## 旧 ZIP 无图片的诊断边界

用户反馈是浏览器打开后无图片，并非已确认解压失败。旧包本地 CRC 通过且 SHA-256 与远端附件元数据一致；没有证据表明原 Release ZIP 损坏。直接从 ZIP 预览 HTML、只取出 HTML、没有 HTTP 服务等情况可能导致资源或模块加载失败，但本次未取得用户原始打开步骤，不能断定具体原因。

v1.0.1 历史 Release 及附件保留；其 web.zip 用于完整静态托管，不应从 ZIP 内直接双击 HTML 游玩。旧 Windows EXE 是调用本机浏览器的 C# 启动器，新版桌面包不再走该链路。

## 从源码构建

```powershell
npm ci
npm run dist
```

使用 Node.js 22.12+；首次安装与构建需联网。输出 `dist/desktop/` 的两种 EXE、SHA-256 和 manifest；工具使用独立临时目录构建，避免源工作区内生成 EXE 的本机启动异常。独立中文临时目录启动对照通过，没有把该异常归因为通用中文路径问题。

验收与限制见 [v1.1.0 验证记录](../reports/qa/desktop-1.1.0/VALIDATION.md)。
