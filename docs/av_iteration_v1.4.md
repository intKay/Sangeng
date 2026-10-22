# 1.4.0 音画候选 · 2026-10-22

目标是让既有低多边形场景和生活物件更易辨识，让环境声服务空间氛围。保留暖灰、霉绿、旧红纸的色板与原有分辨率；音乐、叙事提示声、玩法路线不在本轮改动范围。

本版位于 `codex/v1.4.0-audiovisual`，基线 `18df312`，远端回退标签 `codex/av-baseline-20261021`。这是候选分支，未替换 itch.io 或稳定 Release。需要回看原版时，可在另一个工作目录检出该标签；无需重置正在使用的工作区。

## ComfyUI 与 Blender

`tools/av/blender_comfy_bridge.py` 在全新后台 Blender 场景渲染材质平面，通过本机 ComfyUI 的 `/upload/image`、`/prompt` 和 `/history` 生成，再加载回 Blender 节点、打包贴图并导出 `.blend` / `.glb`。实际执行记录在 `reports/av-v1.4/bridge-proof.json`，样例工程和渲染同目录。这是资产往返流水线，不是实时 GUI 插件。

启动本机 ComfyUI（默认 `127.0.0.1:8188`，需 DreamShaper 8 checkpoint），从仓库目录运行：

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' -b --factory-startup --python tools/av/blender_comfy_bridge.py
```

客户端仅允许 localhost，脚本不打开用户已有场景或修改 Blender 启动配置。原理参考 [ComfyUI HTTP routes](https://docs.comfy.org/development/comfyui-server/comms_routes)。

## 最终表现

- 六种墙纸、灰泥、瓷砖、木板、灯笼纸材质以原纹理为源，低 denoise 生成后仅提取亮度高频残差。每通道变化不超过 11/255，边缘逐像素保留，原尺寸与材质 tint 保留。平均差很小，主观可读性变化主要来自后期与局部灯光。
- 屏幕基础颗粒 .06 → .035、暗角 .50 → .44、dither .012 → .008，仍随 sanity/threat 变化。《门后》初始厨房灯 .55 → .75，后续剧情熄灯逻辑保留。
- 暖水瓶补四段 D 型握把、底圈和颈圈，保留交互父节点。door 模型 8652 → 8764 三角形；依旧高于原建议目标 6000，但在原硬上限内。
- 三条环境床分别为窗雨、远水、旷野风。Stable Audio Open 生成源经带通、交叠加窗循环与响度约束，原床系数 .92、新层系数 .24（幅度系数，不等于能量百分比）。最终各 30 秒，含 OGG 与 MP3。
- 暂停新增最终输出 gate，并串行同步 AudioContext 的 suspend/resume，覆盖混响、心跳与已排程源；暂停中的 UI 瞬态不积压。

精确生成源保存在 `tools/av/sources/`，不含模型权重。`build_materials.py --from-sources`、`build_ambience.py --from-sources` 可复现后处理，需 Python / numpy / Pillow，音频还需 ffmpeg；重新推理存在 GPU/版本非确定性。默认不带该参数会调用本机模型重新生成。

## 审看与验证

```powershell
python serve.py 8138
```

打开 `http://127.0.0.1:8138/reports/av-v1.4/` 比较画面和单轨声音；游戏入口为服务根目录。审看页原版与候选入口同机位，时间性噪声并非完全锁帧。物件近景使用辅助定位；原版 door-detail 机位错误，不能用于同机位比较，审看页已排除。

`before/result.json` 与 `after/result.json` 记录真实生产代码浏览器采样。三篇各加载 62 种材质，无音频缺失或 placeholder；最终暂停输出测得零，即使验收中强制恢复 Context。渲染器是 SwiftShader，不能用这些帧时推断 RTX 3050 表现。

`audio-lifecycle.json` 记录暂停调音量、解锁、恢复、静音与快切。隔离浏览器中将最终 gate 变异为 1 后，静音断言确实拒绝漏音；测试未改生产源码。`reports/audio/verify.txt` 全 121 音频通过格式/响度/循环数值检查。接缝阈值仅为工程筛查，不构成真人听感结论。

最终网页包 manifest / SHA256 在 `dist/web/`；浏览器配置覆盖见 `reports/qa/release-1.4.0/web-final/result.json`。WebKit 测试运行时没有 AudioContext，因此仅验证 MP3 资源回退与触屏交互，不声称 Safari 实机声音通过。浏览器交互含辅助定位，不等于完整自然通关；无物理手机、正常 GPU、真人试听与全程游玩验收。桌面安装包本轮未重建。

最终包 SHA256：`8b9c091dbb3156fc067f909ae8213379c0d00ced6447602cdaaf4b542eacb67c`，33,824,317 字节。六种浏览器配置通过；三篇桌面与 Android 横屏交互均有实际状态变化记录。额外音频生命周期验收通过，变异漏音输出 RMS 约 .0184 被拒绝；正常暂停与静音输出均为零。

`tools/av/verify_artifacts.py` 使用 numpy / Pillow 再查最终材质边界、九份生成源 SHA256 和全部运行文件与打包 manifest 一致性。当前项目默认 `python` 未装 numpy，应使用已有科学计算 Python 环境；本机实际通过的解释器为 Python 3.11。根项目 `src/validate_project.py` 亦通过。GLB 检查通过并保留上述超建议目标警告；这不代表真机性能验收。
