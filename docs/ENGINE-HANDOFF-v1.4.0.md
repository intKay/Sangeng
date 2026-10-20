# v1.4.0 引擎交接 · 手记 / 发现 / 指引

> 给 Codex：内容侧已完成第一批数据与埋点（本地分支 `plan/v1.4.0-guidance`，提交 `0845ad4` 起）。
> 本文件只描述**引擎/集成**范围；内容侧不修改 `engine/`。
> 方案见 `docs/PLAN-v1.4.0-guidance.md`，目录见 `docs/DISCOVERY_SPEC.md`。

## 1. 现状（内容侧已就绪）

- 三篇 `config.discovery` 已存在：
  - door：28 条发现 + 1 个结局
  - mirror：16 条发现 + 1 个结局
  - nightroad：10 条发现 + 2 个结局
- 内容侧在交互/事件处调用（引擎未接入时 no-op）：
  - `game.progress.mark(id)`
  - `game.progress.ending(id)`
  - `game.progress.define(config.discovery)`（setup 时）
- 结局 `finish` 调用已带 `endingId`（door/mirror/nightroad）。
- 夜路新增 4 个路边查看交互（路牌/牌位/纸钱/旧自行车），不影响主线。
- 默认提示等级：**沉浸**（不自动弹提示）。

## 2. 需要引擎实现的模块

### 2.1 `engine/progress.js`

职责：版本化本地进度、清除、迁移、结局收集。

```js
// localStorage key: sangeng.progress.v1
{
  version: 1,
  games: {
    door:      { discovered: {id:true}, endings: ['door.ending.home'], plays: 1, deaths: 0, bestTime: 0 },
    mirror:    { ... },
    nightroad: { ... }
  },
  meta: { seals: { door:true, mirror:true, nightroad:true }, allComplete:false }
}
```

API：

```js
game.progress.define(catalog)     // setup 时注册目录
game.progress.mark(id)            // 首次/重复安全；返回 {first:boolean, count}
game.progress.ending(id)          // 记录结局；返回 {first:boolean, unlocked, total}
game.progress.get(gameId)         // 读取一篇
game.progress.summary(gameId)     // {discovered, byGroup:[{id,label,got,total}], endings, endingTotal}
game.progress.meta()              // 三篇 seal / allComplete
game.progress.reset(gameId?)      // 设置页“清除进度”
```

要求：
- 损坏/禁用 `localStorage` 时不崩溃，游戏照常可完成。
- 只在浏览器本地；不联网。
- 不阻塞加载；读取失败回退空进度。
- 提供 `window` 调试入口（沿用现有 debug 风格，如 `game.progress.debug()`）。

### 2.2 发现/提示状态

- `game.discovery` 或并入 `progress`：
  - `define(catalog)`、`mark(id)`、`counts()`。
  - 目录结构见 `docs/DISCOVERY_SPEC.md`。
- 首次 `mark`：左下角墨迹 toast `记下：<title>`，2.5s；设置里可关闭。
- 重复查看不重复 toast，但可更新 `summary`。
- 未发现条目不显示 `summary`，只显示 `hint`。

### 2.3 指引（默认沉浸）

- 设置项 `hintLevel: 'immersive' | 'standard' | 'guide'`，默认 `immersive`，持久化。
- **沉浸**：无自动字幕提示；玩家在暂停 → 手记 → 线索里点“要一句提示”时，取当前区域/目标的一条 `hint` 显示。
- **标准**：停留 35s 给模糊提示，75s 指向类别，120s 一次环境回调（内容侧提供）。
- **引导**：20/45/70s，允许一次短暂方向指示。
- 提示不暴露解法；同一提示不重复超过两次；玩家在移动/新交互时暂停计时。
- 卡住检测：90s 无新发现时暂停菜单手记图标点一个小墨点；180s 手记出现“要一句提示吗？”。
- 提供 `game.hints.request()`（手记按钮调用）；内容侧提供 hint 文本，不需要引擎硬编码。

## 3. UI 改动

### 3.1 暂停菜单

在“继续 / 设置 / 返回入口”中加入 **手记**：

```
继续
手记        ← 新
设置
返回入口
```

手记三栏：
- 当前：目标、第二行位置、轮次/进度
- 发现：按 group 分组卡片 + 计数；未发现显示 `hint`
- 线索：已读字条/照片/海报摘要；底部“要一句提示”
- 关闭返回暂停；触屏与安全区沿用现有样式。

### 3.2 结局页

在现有结局文字下方增加：
- `发现 X / Y`、分组计数
- `结局 1 / 2`（夜路）或 `1 / 1`（门后/镜中）
- 按钮：`再走一遍` / `看手记` / `返回入口`

夜路第一次结局后：
- 若已解锁《你回头了》→ “另一条路：这次别回头。”
- 若已解锁《你没有回头》→ “另一条路：这次回头看看。”
- 在结局页与下次开局载入处各显示一次（一次性）；不提前剧透按键。

### 3.3 入口页

- 读取 `game.progress.meta()`：
  - 每张卡片显示 `尚未还家 / 已还家 · 发现 14/28`；夜路额外显示 `结局 1/2`。
  - 通关卡片盖朱红小印。
  - 三篇通关显示“三更已满”；全结局加“全结局”小字。
- 清理进度：设置或入口页的“清除进度”二次确认。

### 3.4 设置

- 提示等级：沉浸（默认）/ 标准 / 引导。
- 发现提示开关（墨迹 toast）。
- 清除进度（二次确认）。

## 4. 内容侧接口约定

- 内容侧已在 `setup` 调用 `game.progress.define(...)`；若引擎尚未暴露，内容侧会静默跳过。
- 内容侧 `mark`/`ending` 调用点见 `docs/DISCOVERY_SPEC.md` §6；请保持 id 稳定。
- 夜路两个结局是平级的，`isTrue` 均为 false；当前没有真结局，不要自行造“真结局”门槛。
- door/mirror 各 1 个结局，不显示“另一条路”。
- 内容侧不修改 `engine/`；请引擎侧实现后由 Codex 负责构建/回归/发布。

## 5. 验收

- 默认沉浸：不自动弹提示；手记可主动取一条；标准/引导档位按阈值出现。
- 发现计数、分组、结局计数与 `docs/DISCOVERY_SPEC.md` 一致。
- 三篇走完后入口页印章/进度正确；清除进度恢复。
- `localStorage` 禁用/损坏不崩溃；0 console error。
- 触屏/键鼠都能打开手记、切换提示等级、看结局统计。
- 夜路第一次结局后重开出现“另一条路”提示；门后/镜中不出现。
- 现有 v1.3.0 流程、移动/触屏、字幕、死亡重试无回归。

## 6. 建议实现顺序

1. `progress.js` + 手记 UI + 结局统计（先接 door，验证数据）。
2. 入口页进度/印章 + 设置。
3. mirror/nightroad 接入；夜路重开提示。
4. 提示引擎（沉浸/标准/引导）与卡住检测。
5. 打包、移动端、验收。

## 7. 内容侧下一步

- 继续补 mirror 的 `diffs` 触发、nightroad 的 hint 文本、入口页文案。
- 提供手记/印章的小美术增量（不新增场景）。
- 等 Codex 确认接口后，按 `docs/DISCOVERY_SPEC.md` 做联调；不抢跑改 `engine/`。
