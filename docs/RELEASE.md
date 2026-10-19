# 三更 v1.0.1

2026-10-19 发布。三个心理恐怖短篇的声音/交互修复与便携分发版。

## 修复

- 补齐 Web Audio 的音源与混音节点连接，解决“资源就绪但无声”。
- 射线忽略隐藏物件；交互提示在同一目标变化时刷新。
- E 键过滤自动重复，保留松开后再次交互。

## 分发

- `Sangeng-1.0.1-Windows.zip`：推荐给 Windows 玩家，包含 EXE、说明和第三方许可。
- `Sangeng-1.0.1-Windows.exe`：内嵌资源的单文件启动器。
- `Sangeng-1.0.1-web.zip`：静态网页游戏，供 HTTP(S) 托管。
- `SHA256SUMS.txt` 与 `build-manifest.json`：下载校验、运行文件与包的哈希。

Windows 需要 .NET Framework 4.8 与支持 WebGL2 的 Edge/Chrome。便携版使用本机浏览器，无需 Python 或 Node，不需要联网；游玩时保留启动器窗口。

三篇核心交互、暂停与设置、音频信号和打包服务通过定向回归。测试边界和限制见 [VALIDATION.md](VALIDATION.md)。
