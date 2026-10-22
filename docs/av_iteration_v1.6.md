# 1.6 旧屋美术返工

用户否定了 1.5 的质感。本轮把《门后》的一个完整居住空间作为主要返工对象，使用[六项审看门槛](art_direction_v1.6.md)。不以贴图数量、分辨率或模型更换代替审美判断。

## 最终取舍

- 恢复灰褐小砖与不同木材的分工，撤掉抢眼的棋盘地面、共享地毯/窗帘与木纹瓶身。15 个既有槽重新加工，加上独立地毯、搪瓷、胶木；共 18 张低幅度高度图。材质定义总数 65。
- 墙纸褪色与接缝保持低对比，漏水处、墙根与角落使用世界坐标局部沉积和剥落；保留留白。门的接触磨损绑定导出 UV，开门时不会留在空间中。
- 漆木保留连贯细纹和较宽的褪色，减少高频斑点。窗帘压低印花，折面与挂耳承担体积。沙发保留灰蓝与米灰配色，避免织物变成像素迷彩。
- 主光集中于灯具，走廊保留向顶面散射的点光；客厅增加受控制的间接填光与窗边冷光，减少无来源的水面和浮尘。
- 修复 503 门口墙裙跨门洞的遮挡；书柜由实心盒子改成开放柜体，书本成组靠边且落在层板上。第三张字条从背板后移到可见前沿，ID/事件不变。沙发与桌椅近景轮廓增加有限倒角。
- 声音沿用 1.5；没有额外生成、加音量或增加事件。本轮使用已保存的本机 Z-Image 源继续加工，没有新的 ComfyUI 采样。原始生成源与模型信息保留在 `tools/av/sources-v15/`，不分发权重。

## 审美审看记录

`reports/av-v1.6/index.html` 提供七个相同机位、三个版本切换。1.4 来源 `f669c15`，1.5 来源 `a655483`；均由独立静态服务器加载对应 Git 归档，使用同一采集脚本。截图固定机位、时间与闪烁种子，实际运行生产 renderer，禁止用离线 Blender 效果替代玩家画面。

| 门槛 | 最终内部判断与证据 | 仍有的限制 |
|---|---|---|
| 材料身份 | 厨房搪瓷/胶木、窗帘、地毯、木地板、沙发分别成立；见 02/03/04/07 | 仍为低模与旧纹理体系，未改成照片级 PBR |
| 尺度与重复 | 撤掉大棋盘、重复水环和高反差木纹噪点；七机位未发现抢眼的镜像接缝 | 大墙纸仍会平铺，不是独一份手绘墙面 |
| 做旧来源 | 墙顶局部渗水、墙根积灰、门把手与下沿失漆、瓶口腐蚀 | 日常物件保持部分完好，未统一做成废墟 |
| 受光层次 | 走廊顶面可读、客厅有主光与有限冷暖差，物件接触处保留遮蔽 | 小地图灯光仍为实时近似，阴影受低预算限制 |
| 画面主次 | 路/门/家具先于表面斑点，减少浮尘与水面；比较 01/02/04 | 压抑暗部保留，屏幕显示与旧画质设置会影响观感 |
| 多视角 | 走廊、客厅、厨房、窗、门、书柜、沙发逐张审看 | 固定辅助机位不等于完整真人游玩 |

A—H 的研究图记录了返工过程：A 的黑面是顶点颜色回退缺失；B—C 的顶面死黑与重复污痕、D—G 的门口/书柜结构、窗帘与木材噪点均被退回。最终候选通过上述内部审看，不代表用户已经接受。保留 1.4 与 1.5，便于用户逐项比较与退回。

## 验证范围

最终报告分别位于：

- `reports/av-v1.6/structural-verification.json`：GLB 命名、原交互属性、世界矩阵和全部碰撞边界、18 张高度图边缘、Web ZIP 和运行文件哈希。允许且明确记录第三张字条的位置修正。
- `reports/modeler/validate.txt`：门后 9776 tris，原 6000 目标警告保留；近景倒角、开放书柜和书组使硬上限由 9000 调为 10000。镜中 4716 / 夜路 5710，面数不变。
- `reports/av-v1.6/route/after/result.json`：正常 WASD、拖动视角和 E，从出生点进入公寓，不使用 teleport；仅第一段路线。
- `reports/qa/release-1.6.0/content/browser-result.json`：辅助摆位后实际 E/F/W 操作，三篇关键拾取/循环/死亡重试/结局与字幕/声音信号。它证明事件可触发，不证明普通玩家可解谜。
- `reports/av-v1.6/after/result.json`：本机 RTX 3050 的三篇入口与近景、资源加载、主场景/镜面阴影刷新、最终声音输出与暂停。帧时间仅为短样本，不能当完整性能基准。
- `reports/qa/release-1.6.0/web/result.json`：从构建 ZIP 解出的嵌套 iframe，在六种浏览器/屏幕配置检查加载、移动、交互、暂停、设置与触屏转向；未使用真实手机或线上 itch.io。
- `reports/av-v1.6/audio-lifecycle.json`：隔离环境下的最终静音门、恢复竞态与故意绕过门的变异对照。

Electron 独立测试窗口本轮启动失败；改用隔离 Edge 真 GPU 跑内容回归，不把结果写成桌面安装包验收。没有重新打包 EXE、发布 GitHub Release 或覆盖线上 itch.io。Web 包在 `dist/web/Sangeng-1.6.0-web.zip`，版本为候选。

WebKit 自动化环境缺少 AudioContext：该配置通过界面/输入检查，但声音不在本轮验证范围。声音信号、最终静音门与恢复竞态来自支持 WebAudio 的 Chromium/Edge；没有真人试听验收。

## 复现与回退

素材加工使用 Python 3.11 + numpy/Pillow，固定派生种子；`python tools/av/build_v16_surfaces.py`。模型用独立 headless Blender 5.2.2，不接触用户交互窗口：

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' -b --factory-startup --python-exit-code 1 --python tools/blender/build_door.py
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' -b --factory-startup --python-exit-code 1 --python tools/av/bake_v16_ao.py -- --refresh-door
python serve.py 8139
```

`--refresh-door` 只在刚重新构建原始门后 GLB 后使用，避免重复把 AO 烘进 AO。没有该参数时重用固定原始输入。首次复现时运行该命令顺序会建立输入缓存。

当前工作分支 `codex/v1.6.0-art-direction`；回退只需在独立 checkout 查看标签 `codex/av-v1.5-before-art-review`，或 `codex/av-v1.4-before-upgrade`。不要用强制 reset 覆盖当前未保存工作。
