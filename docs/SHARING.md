# 三更 v1.0.1 · 游玩与分享

## 给朋友一个可执行文件

本地生成目录：`dist/`。

发送 **`Sangeng-1.0.1-Windows.zip`**（约 17.5 MB，内含 EXE、中文说明与许可）。朋友解压后双击 `Sangeng-1.0.1-Windows.exe`；也可以直接发送这个 EXE，游戏资源已内嵌，无需额外素材目录。保留启动器窗口，游玩结束点击“退出”。

- Windows 10/11、.NET Framework 4.8、支持 WebGL2 的 Edge 或 Chrome；免 Python，免 Node，离线运行。
- 这是编译后的 Windows 便携启动器：内嵌资源 + 本地静态服务 + 已安装浏览器的应用窗口，**没有内置浏览器内核**。
- 不需要管理员权限；只监听 `127.0.0.1` 的随机端口，不向局域网开放。
- 启动时不解压素材、不创建浏览器 profile、不读取私人文件；浏览器自身仍按正常设置工作。
- 点击“开始”解锁声音；WASD 移动，鼠标环视，Shift 快走，E 交互，Esc 暂停。F 只在《门后》拾取手电后可用。E 松开再按即可再次使用。
- 当前 EXE 未数字签名，Windows 可能提示未知发布者。保留来源说明，不建议让收件人关闭系统安全防护。
- 关闭启动器会停止服务；已打开的游戏画面可能暂时继续，但重新加载、返回入口等请求将失败，请先结束游玩。

## 分享一个网址

使用 **`Sangeng-1.0.1-web.zip`**。ZIP 根目录已有 `index.html`，同时包含全部相对路径资源和 three.js 许可，不包含私人档案、DSH 会话、生成脚本与测试报告。

可在 itch.io 创建项目，选择 HTML 游戏、上传 ZIP、勾选浏览器运行。建议桌面、1280×720 或更大，并启用全屏。正式分享前在托管预览中检查声音、指针锁定与 Esc；本轮没有上传或验收远端 iframe。操作依据：[itch.io 官方 HTML5 上传文档](https://itch.io/docs/creators/html5)。

也可将 ZIP 内容部署到普通 HTTPS 静态托管。模块、GLB、音频需要 HTTP(S) 服务；直接双击解压出的 HTML 不能替代托管。

## 如果希望完全不依赖本机浏览器

下一种方案是用 Electron 内置 Chromium，再打包安装版/便携版。它会增大下载体积，并增加依赖更新和签名维护；本轮交付选择了可本机编译、免下载运行时的轻量启动器。[Electron 官方分发说明](https://www.electronjs.org/docs/latest/tutorial/distribution-overview)。

## 重新构建与验证

```powershell
python tools\build_release.py
```

构建使用 Python 标准库和 Windows 自带 .NET Framework C# 编译器，不安装依赖。`dist/build-manifest.json` 记录每个运行文件与三个分发产物的 SHA-256；构建脚本仅收录游戏目录白名单。

便携服务器验收模式（从项目根目录）：

```powershell
& .\dist\Sangeng-1.0.1-Windows.exe --serve-only .\output\playwright\desktop-url.txt
python tools\verify_release.py (Get-Content output\playwright\desktop-url.txt -Raw).Trim()
```

该模式不打开 UI，需先创建 URL 文件的父目录；结束时停止自己启动的测试进程。浏览器回归脚本为 `tools/review-runtime.js`，用 Playwright CLI `run-code --filename` 在目标服务页执行；交互引擎回归探针为 `tools/review-probe.js`。

three.js 依 MIT 分发。原创资产的授权边界沿用 v1.0 发布说明；本轮仅提供分享技术包，未重新授予商业使用许可。
