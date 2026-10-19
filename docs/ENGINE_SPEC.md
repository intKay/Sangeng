# 《三更》共享引擎接口（给玩法 agent）

引擎代码在 `engine/`，r160 three.js 已本地 vendor。先读 `games/door/game.js`（Lead 完成的完整示例），再用本文件查 API。**不要改 engine/ 与 vendor/；engine 有问题直接报告 Lead。**

## 1. 页面模板

每个游戏的 `games/<id>/index.html`：

```html
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>镜中 · 三更</title>
  <link rel="icon" href="../../assets/art/favicon.png">
  <link rel="stylesheet" href="../../engine/engine.css">
</head>
<body>
  <canvas id="gl"></canvas>
  <script type="importmap">
  { "imports": {
      "three": "../../vendor/three/three.module.js",
      "three/addons/": "../../vendor/three/addons/"
  } }
  </script>
  <script type="module" src="./game.js"></script>
</body>
</html>
```

## 2. 启动

```js
import * as THREE from 'three';
import { HorrorGame } from '../../engine/engine.js';
import { clamp } from '../../engine/utils.js';

const config = {
  id: 'mirror',
  title: '镜中',
  chapter: '二更 · MIRROR',
  titleEn: 'IN THE MIRROR',
  poster: '../../assets/art/poster-mirror.jpg',
  warning: '……心理恐怖、闪烁画面……',
  homeUrl: '../../index.html',
  model: '../../assets/models/mirror.glb',
  textures: '../../assets/textures/manifest.json',
  audio: '../../assets/audio/mirror/manifest.json',
  footstepSfx: 'stepTile',
  flashlight: null,                       // 本作没有手电；有则 { batterySeconds, intensity }
  ambient: { color: 0x2a3330, intensity: 0.3 },
  fog: { color: 0x070a09, density: 0.05 },
  theme: { accent: '#9fb0a8', ink: '#d8d2c0', bg: '#060807' },
  playerStart: { spawn: 'SPAWN_mirror', look: 'LOOK_mirror' },
  renderScale: 0.6,

  async setup(game) { /* 加载完成、标题页之前调用一次，建交互/隐藏物件/取引用 */ },
  start(game) { /* 点击“开始”后调用，初始化一局 */ },
  update(game, dt) { /* 每帧（仅 playing 状态） */ },
  respawn(game) { /* 死亡后点“再来一次” */ },
  onFail(game) {},
  onFinish(game) {},
};

const game = new HorrorGame(config);
game.load().then(() => { window.__MIRROR__ = { game, /* 调试入口 */ }; });
```

## 3. 生命周期与状态

- `new HorrorGame(config)` → `game.load()`：加载贴图/音频/GLB，显示加载页，然后进入标题页。
- `config.setup(game)`：`async` 可用。此时 `game.level / ui / audio / player / interact / find()` 都已就绪，但玩家尚未开始。
- `game.start()`：引擎处理（隐藏标题、锁定鼠标、播放 UI 音、开始 `update`），随后调 `config.start`。
- `config.update(game, dt)`：只在 `game.state === 'playing'` 时每帧调用。
- `game.fail(text)`：显示死亡页，之后玩家点重试 → `config.respawn(game)`。
- `game.finish({ chapter, title, lines, footer })`：显示结局页。
- 暂停/设置/pointerlock/标题/死亡/结局 UI 由引擎处理，不要自己写覆盖层。

## 4. 引擎对象

| 属性 | 说明 |
|---|---|
| `game.scene / camera / renderer` | three.js 场景、相机、渲染器 |
| `game.level` | GLB 根节点（THREE.Group，名字 level） |
| `game.player` | 第一人称控制器，见 §5 |
| `game.audio` | 音频管理器，见 §7 |
| `game.ui` | DOM 界面，见 §8 |
| `game.interact` | 交互管理器，见 §9 |
| `game.colliders` | `{ boxes: [{box: Box3, enabled}] }`，COL_ 已自动加入 |
| `game.markers` | `SPAWN_* / LOOK_* / MARK_*` Object3D |
| `game.variants` | `V2_/V3_` Object3D，初始隐藏 |
| `game.entities` | `ENTITY_*` 根节点（自动隐藏） |
| `game.hidden` | 带 `userData.hidden` 的交互物（自动隐藏） |
| `game.state` | `'boot' | 'title' | 'playing' | 'paused' | 'dead' | 'ending' | 'paper'` |
| `game.time` | 累计秒 |
| `game.threat / game.sanity` | 0–1，驱动后处理与音频心跳（用 setter） |
| `game.settings` | `{ sensitivity, volume, subtitles, renderScale }` |

### 常用方法

```js
game.find('INT_door_503')                  // level.getObjectByName
game.getMarker('SPAWN_mirror')             // 返回 THREE.Vector3（不存在则 null）
game.setVisible('INT_letter_02', false)    // 按名字显示/隐藏
game.setVariants('V2_', true)              // 同前缀变体全部显示
game.showEntity('ENTITY_reflection', true) // 显示实体根节点
game.setLight('LIGHT_tube_02', false)      // 按 LIGHT_* 名字开关
game.setThreat(0.6); game.setSanity(0.4);  // 0..1
game.isLookingAt(object, { maxDistance: 20, fovDot: 0.5 }) // 玩家是否看着且无遮挡
game.createReflectionScene()               // 为镜子克隆整个场景（含灯光/雾）
game.createMirror('MIRROR_surface', { tint, grimeStrength, resolutionScale }) // 见 §10
game.makeDoor('INT_door_...', opts)        // 见 §9
game.openPaper({ head, lines, onClose })   // 信纸/纸面全屏，自动暂停输入；E 或按钮关闭
game.finish(...) / game.fail(text) / game.retry? (引擎负责按钮)
window.__SANGENG__ = game                  // 引擎自动暴露，QA 可用
```

## 5. Player（第一人称）

```js
game.player.position          // THREE.Vector3（脚底，y=0）
game.player.eyePosition       // 相机位置
game.player.enabled           // 引擎管理，不要手动改（除非明确需要）
game.player.teleportTo(spawnName, lookName)          // 名字可带/不带 SPAWN_ 前缀
game.player.teleportToPos(vec3, lookAtVec3)
game.player.lookAt(vec3)
game.player.onFootstep = (speed, sprinting) => {...} // 可覆盖默认脚步（默认播 config.footstepSfx）
game.player.setYawPitch(yaw, pitch)
game.player.giveFlashlight() / setFlashlight(bool) / addBattery(sec) // 仅 config.flashlight 时
game.player.batteryFraction
```

## 6. 输入

- WASD 移动、鼠标视角（pointer lock）、Shift 快走、E 交互（引擎分发给 `game.interact`）、Esc 暂停。
- 需要额外的键（例如《夜路》的「回头看」不需要专门键，用视角即可）时用 `window.addEventListener('keydown', ...)`，但只在 `game.state === 'playing'` 时响应。

## 7. Audio

manifest 在 `assets/audio/<id>/manifest.json`，由音频 agent 生成。引擎按 manifest 的 `music / ambience / sfx / ui` 分类读取。

```js
game.audio.ready                                  // 是否有音频可用
game.audio.playMusic('main', { fade: 3 })         // 交叉淡化
game.audio.stopMusic(2)
game.audio.playAmbience('corridor', { channel: 'main', fade: 2, volume: 1 })
game.audio.playAmbience('rain', { channel: 'extra', fade: 2, volume: 0.4 })
game.audio.stopAmbience('extra', 2)
game.audio.sfx('stepTile', { volume: 0.8, rate: 1.0, pos: THREE.Vector3 })  // pos 可选，空间化
const h = game.audio.sfx('waterStream', { loop: true, volume: 0.4 });
h.setVolume(0.7); h.stop(1.5);
game.audio.ui('click');                           // 菜单音
game.audio.setThreat(0.7);                        // 心跳/呼吸层（引擎每帧用 game.setThreat 同步）
game.audio.duck(true);                            // 暂停时自动处理，一般不用
```

**防御式写法**（音频/贴图是并行生成的，键名可能缺失）：
```js
function playSfx(game, key, opts) {
  if (game.audio && game.audio.entries.sfx[key]) return game.audio.sfx(key, opts);
  return null;
}
```

## 8. UI

```js
game.ui.setObjective('让镜中的房间与现实一致');  // 顶部一行目标；null 隐藏
game.ui.setCounter('对齐 1 / 3');              // 右上角小计数
game.ui.subtitle('水还在流。', 3.2);           // 字幕队列
game.ui.setBattery(0..1 或 null);              // 右下角手电条（仅门后用）
game.ui.fade(1, 600) / fadeIn(ms) / fadeOut(ms) // 返回 Promise
game.ui.setHudVisible(bool); game.ui.setPrompt(null); game.ui.clearSubtitles();
game.ui.isPaperOpen();
```

**信纸/文件**：用 `game.openPaper({ head, lines, onClose })`。它会暂停移动与指针锁、恢复后调用 `onClose(game)`；关闭键 E 由引擎处理。

## 9. 交互与门

```js
const handle = game.interact.add(object, {
  prompt: '拿起毛巾',          // 中文字符串
  range: 2.9,                   // 可选
  enabled: true,
  onUse: (handle, game) => { ... },
});
handle.setPrompt('换一面'); handle.setEnabled(false); handle.remove();

// 门（自动开合动画 + 碰撞切换 + 音效）
const door = game.makeDoor(object, {
  prompt: '打开储物柜', locked: false,
  lockedText: '锁着。',          // 锁着时按 E 显示的字幕
  onOpen: (door) => {}, onClose: () => {}, onLocked: () => {},
});
door.open(true) / door.close() / door.setLocked(bool) / door.isOpen / door.isLocked
```

- 门的交互与碰撞由引擎处理；模型里 `INT_door_*` 的原点在合页轴底部，绕世界 Y 轴旋转即可。
- **隐藏物件注册交互**是安全的：射线检测会检查可见性，隐藏时不会触发；重新显示后自动可用。
- 需要“拾取后消失”：`game.setVisible(name, false)` 即可，交互 handle 保持注册也无害。

## 10. 镜子（《镜中》核心）

GLB 里有独立平板 `MIRROR_surface`（位于北墙，法线朝房间，UV 完整 0–1）。

```js
// setup 里创建：
const reflectionScene = game.createReflectionScene(); // 克隆 level + 灯光 + 雾
game.createMirror('MIRROR_surface', {
  scene: reflectionScene,
  tint: 0xa8b7ae,          // 镜面偏色
  grimeStrength: 0.5,      // 污渍强度
  resolutionScale: 0.55,
});

// 引擎每帧自动调用 mirror.update()；游戏代码只需：
//   修改 reflectionScene 里同名的 Object3D（位置/旋转/可见性/材质）来表达“镜中状态”
const refTowel = reflectionScene.getObjectByName('INT_towel');
refTowel.position.copy(...); refTowel.rotation.y = ...;
// 也可以给反射场景加/减灯、换材质（建议 clone 材质再改，避免影响现实场景）
```

- 反射场景中的物体与世界坐标一致，不要整体镜像；引擎用镜像相机 + 投影纹理渲染。
- 现实场景与反射场景的差异就是解谜内容。
- 镜子表面材质由引擎替换，不要自己改 `MIRROR_surface.material`。

## 11. 关卡约定（已由建模实现）

- 地面 y=0，玩家眼高 1.62，半径 0.32。
- 碰撞：`COL_*` 已自动提取；门洞没有 COL，门扇碰撞由 `makeDoor` 管理。
- 交互物名字与 `interact/prompt/id` 见 `docs/ASSET_SPEC.md` 各场景 §；已核对齐全。
- `ENTITY_*` 是根节点（可能有子网格），移动/显隐操作根节点即可。
- `SPAWN_*/LOOK_*` 是 Empty，用 `getMarker`/`teleportTo`。
- 灯光是 `LIGHT_*` Empty + `light_*` 属性，引擎建灯并有 flicker；`setLight(name, on, scale)`。
- 隐藏变体 `V2_/V3_`、实体、`userData.hidden` 物件引擎已默认隐藏。

## 12. 贴图/材质

- `assets/textures/manifest.json` 的 `MAT_*` 键 → 引擎按名字替换成 MeshLambertMaterial + 贴图。
- `transparent: true` 的贴花材质（霉斑/水渍/镜污/蒸汽）会启用透明混合、`depthWrite=false`；蒸汽等大面积透明片不要放在镜头正前方，避免遮挡。
- 发光材质（灯管/灯泡/灯笼/电视雪花）用 manifest 的 emissive；开关灯时建议同时 `setLight` 与替换对象材质（clone 材质后改 `emissiveIntensity`）。

## 13. 调试与 QA

```js
// 页面加载后
window.__SANGENG__              // 引擎实例
window.__MIRROR__ = { game, state, teleport(x,z){...}, face(x,z){...} };  // 建议每个 demo 暴露
```

Playwright CLI 测试（先用 `--session` 起独立会话，不要和 Lead 的 `sangeng` 会话混用）：
```powershell
$env:PLAYWRIGHT_CLI_SESSION="mirrorqa"
npx --yes @playwright/cli@latest open "http://127.0.0.1:8137/games/mirror/index.html"
npx --yes @playwright/cli@latest snapshot
npx --yes @playwright/cli@latest screenshot
```
截图在 `.playwright-cli/`；用 read_image 查看。控制台错误看 `.playwright-cli/console-*.log`。**不要提交截图，也不要改 `.playwright-cli/` 之外的 QA 产物。**

## 14. 验收（每个 demo）

1. 标题页 → 开始 → 完整玩法循环 → 结局页 → 再来一次/返回入口，全流程可达。
2. 无 console 报错（404 资源在音频/贴图未就绪阶段可接受，最终应全 200）。
3. 交互、碰撞、字幕、目标、声音、后处理、暂停/重试都工作。
4. 截图（标题/游戏中/结局）目视通过：构图、可读性、镜面/纸人效果。
5. 不改 engine/、vendor/、docs/、其它 demo、assets/。
