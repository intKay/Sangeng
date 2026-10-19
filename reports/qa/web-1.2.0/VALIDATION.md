# 三更 v1.2.0 网页手机适配验收

日期：2026-10-19。交付为 v1.2.0 网页 ZIP；用户手动上传 itch.io，本轮未操作线上 itch.io 项目。Windows 桌面包保留 v1.1.0。

## 已实现

左侧模拟摇杆移动、右侧拖动环视、双指并行、交互/手电/快走/暂停按钮；触屏无需 Pointer Lock。保留键盘鼠标并提供自动/触屏/键鼠设置。安全区、横竖屏和小屏滚动面板；手机首次默认 0.45 渲染比例，尊重已保存设置。暂停、取消触点、失焦和旋转时清空触控输入。添加 121 个 MP3 备用音频，供不支持 Ogg/Vorbis 的浏览器选择。

## 实际验证

- 对最终 ZIP 解包内容执行浏览器测试，使用大小写敏感文件映射、/itch/game/ 子目录和 sandbox iframe（allow-scripts、allow-same-origin、allow-pointer-lock），运行真实 Three.js/WebGL 渲染及真实浏览器输入事件。
- Chromium：844×390 三篇、390×844、320×568、768×1024，以及 1280×720 桌面三篇，共 9 项。真实 CDP 双触点移动与转头、touchCancel 清零、屏幕交互、门后手电、暂停/继续、快走切换、信纸合上、旋转和返回入口通过；桌面鼠标锁定与键盘 E 保留。每篇 50 张纹理、音频缺失 0、声音信号非零。320px 用例强制 MP3 选择并实际解码/测量输出。
- Windows Playwright WebKit：390×844，画面、拖动、屏幕按钮、菜单和旋转通过。该运行时没有 AudioContext，音频明确记为 supported=false，未冒称 iPhone 声音验证通过。
- ZIP CRC、327 个文件逐项 SHA-256、itch.io 默认文件数/路径长度/解包体积限制通过；原始 assets/vendor 文件与 v1.0.1 清单逐项一致，未重新制作场景、美术或原始 Ogg 音频。
- 只收录 index.html、engine、games、assets、vendor 的允许资源；不包含私人数据、原始会话、凭据、node_modules、报告或桌面运行时。

测试首次 Python 回环服务连接失败，随后改用同进程 Node 服务完成浏览器验收。没有把连接失败或单纯 DOM 检查记作通过。原始成功结果为 result.json；失败截图与中间记录在本地保留并从 Git 排除。

## 仍需用户上传后测试

未在真实 Android/iPhone/iPad 上验收，未验证手机性能、手感、刘海实际尺寸、浏览器工具栏动态高度、人耳声音、后台切回及远端 itch.io iframe。没有重新逐篇完整通关。WebKit for Windows 不代表 iOS Safari 的音频与 GPU 实现。网页依赖现代 WebGL2 浏览器，没有生成 APK/iOS/macOS/Linux 原生程序。

上传同一个 ZIP 并勾选浏览器运行与 Mobile Friendly，推荐 Click to launch in fullscreen。详见 docs/ITCHIO_MOBILE.md。

ZIP SHA-256：`40496504bd29003f71bc8ab996510fe2f1ca3a8d0973df80be4cfdb335ce3516`。
