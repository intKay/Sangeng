# v1.3.0 网页包 · itch.io 手动上传

同一个 `Sangeng-1.3.0-web.zip` 用于桌面、Android 和 iPhone/iPad 网页浏览器，不需要为不同操作系统上传多份 HTML 包。需要支持 WebGL2、Pointer Events 和 Web Audio 的现代浏览器；没有生成 Android APK、iOS App 或原生 macOS/Linux 程序。

## 上传到现有项目

1. 打开 `https://kay-setsuna.itch.io/horror-demo` 的 Edit game。
2. Kind of project 选择 HTML。上传新的 `Sangeng-1.3.0-web.zip`，勾选 **This file will be played in the browser**。不要把 ZIP 再套一层文件夹，也不要只上传 index.html。
3. 原来的网页包取消“浏览器运行”选项，保留旧文件作为回退；已有 Windows EXE 可继续作为下载附件。
4. Embed options 开启 **Mobile Friendly**，推荐 **Click to launch in fullscreen**；如使用页面内嵌入，建议 1280×720 并开启 Fullscreen Button。不要强制锁定横屏；游戏会建议手机横屏，竖屏同样保留操作。
5. 保存，等待 itch.io 处理 ZIP，再打开项目页面测试。无需修改价格或项目可见性。

## 商店素材

- 封面：`630×500` JPEG；缩略图 `315×250`。暗色底 + 红色纸灯笼，标题“三更 / SANGENG / 三个心理恐怖短篇”，见交付包内的 `cover-630x500.jpg`。
- 截图：按文件名顺序上传 `screenshots/01-08`，含桌面场景与手机横屏触控 UI；建议第一张用入口页，第二张用手机触控界面。
- 文案：见交付包内 `PAGE.md`；标签、短描述与内容提示可直接复制。
- 仓库内 [`docs/screenshots/`](../docs/screenshots/) 也保留了 README 用的同一批画面。

手机在 itch.io 上按平台规则点击后全屏启动；浏览器实际全屏行为依设备而异，游戏不依赖 Fullscreen API 或 Pointer Lock API 才能触控游玩。依据：[itch.io 官方 HTML5 文档](https://itch.io/docs/creators/html5)。

## 操作

- 触屏：左下摇杆移动，右侧空白区域拖动环视；可同时移动与转头。点击交互、快走、手电和暂停按钮。手电仅在门后获得后显示。
- 键鼠：原 WASD、鼠标、E、Shift、F、Esc 保留。触屏电脑可在设置里切换“操作方式”。
- 第一次点击开始解锁声音；后台切回后可点击继续恢复。触屏默认低分辨率，设置中可以调整颗粒度和视角灵敏度。
- 摇杆在松手、取消、失焦、旋转或暂停时清零，避免持续移动。菜单和信纸在小屏可滚动。
- 不支持 Ogg/Vorbis 的浏览器会选择同名 MP3 备用音频。

## 建议你上传后实际检查

桌面鼠标锁定与 Esc；Android 双指移动/环视；iPhone Safari 点击开始后的声音、暂停/继续；横竖屏切换；打开信纸后能点“合上”；返回入口后另两篇也能开始。当前无存档，刷新会重新开始。

本轮自动化使用本地 ZIP、子目录和 sandbox iframe。浏览器模拟不能替代你手机的性能、手感与声音测试，也不等同于已经在 itch.io 线上验收。

## 重建与校验

```powershell
python tools/build_audio_fallbacks.py   # 原始音频改变时运行，需要 ffmpeg
python tools/build_web.py
python -c "import zipfile; zipfile.ZipFile('dist/web/Sangeng-1.3.0-web.zip').extractall('dist/web/qa-build')"
node tools/verify_web.cjs
```

输出位于 `dist/web/`，包含 ZIP、SHA256SUMS.txt、web-manifest.json。只收录游戏运行资源，没有私有项目资料或测试报告。
