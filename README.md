# 三更 · SANGENG

三个浏览器第一人称心理恐怖短篇，共用一套低多边形 3D 引擎。当前版本 **v1.0.1**。

| 一更《门后》 | 二更《镜中》 | 三更《夜路》 |
|---|---|---|
| 老公寓里的夜间探访 | 公共澡堂更衣室 | 乡野夜路上的灯火 |
| 约 6–8 分钟 | 约 5–7 分钟 | 约 7–10 分钟 |

![三更](assets/art/hero.jpg)

## 下载游玩

在本仓库 **Releases** 下载 `Sangeng-1.0.1-Windows.zip`，解压并双击 EXE。免安装 Python 或 Node；需要 Windows 10/11、.NET Framework 4.8，以及支持 WebGL2 的 Edge/Chrome。游戏资源内嵌在 EXE 中，离线可玩。游玩时保留启动器窗口，结束后点击“退出”。

便携版使用已安装浏览器的应用窗口，没有内置 Chromium；EXE 未数字签名。首次点击“开始”后启用声音。

WASD 移动，鼠标环视，Shift 快走，**E 交互**，Esc 暂停。F 为《门后》拾取后的手电开关。暂无存档和移动端操作。

内容提示：心理恐怖、闪烁画面、幽闭空间、死亡意象；无血腥画面。

## 从源码启动

```powershell
python serve.py
```

用 Edge/Chrome 打开 `http://127.0.0.1:8137/`，也可双击 `start_sangeng.cmd`。服务器仅用 Python 标准库。需要 HTTP 服务加载 ES Modules、GLB 与音频，请通过启动脚本进入。

## v1.0.1

- 修复音源漏接混音节点导致的音乐、环境与音效无声。
- 隐藏物件不再拦截交互射线，当前物件的提示变化可及时刷新。
- 长按 E 不再连续触发拾取、开合等操作。
- 提供 Windows 便携包、单文件 EXE、网页托管 ZIP 和校验文件。

本轮定向验证覆盖三篇核心 E 交互、门后 F、暂停/继续、音量设置、长按 E 与音频信号；205 个打包运行文件经 HTTP 逐字节核对。未重新逐关完整通关、未做人耳音量平衡或异机验收。细节见 [验证范围](docs/VALIDATION.md)。

## 结构与构建

- `engine/`：Three.js 渲染、后处理、玩家、交互、Web Audio 与界面。
- `games/`：三个短篇。
- `assets/`：低模、程序化贴图、合成音频与海报。
- `tools/`：Blender、音频、美术生成及 Windows 发布工具。
- `docs/`：设计、接口、资产规范与分享说明。

```powershell
python tools/build_release.py
```

Windows 构建需要系统 .NET Framework C# 编译器。产物位于 `dist/`。重建资产还需要 Blender，以及 numpy、Pillow、ffmpeg 等各资产脚本列出的依赖；游玩与打包不需要安装这些资产生成依赖。

分享网址可使用网页 ZIP，步骤见 [分享说明](docs/SHARING.md)。原创内容与第三方许可见 [NOTICE](NOTICE.md)。
