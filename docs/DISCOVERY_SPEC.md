# v1.4.0 发现与指引 · 内容规格（DISCOVERY SPEC）

> 配套方案：`docs/PLAN-v1.4.0-guidance.md`
> 版本基线：v1.3.0。本文是内容侧交付物，供 Codex 的 `engine/progress|discovery|hints` 与手记 UI 接入。
> 默认提示等级：**沉浸**（无自动文字；手记里可主动取提示）。

## 1. 共用数据约定

```js
// 每个游戏在 config 上暴露；引擎在 setup 时读取
discovery: {
  version: 1,
  groups: [{ id, label, total }],
  entries: [{
    id,            // 全局唯一，点号命名，如 door.relic.photo1
    group,         // 组 id
    title,         // 手记卡片标题
    summary,       // 已发现后的短摘要
    hint,          // 未发现时的模糊位置提示（不剧透）
    trigger,       // 内容侧说明：哪个对象/事件触发
    markOn,        // 'interact' | 'enter' | 'event'
  }],
  endings: [{
    id, title, isTrue: false, hint, // 结局页/收集用
  }],
}
```

- 引擎 API 建议：`game.progress.define(config.discovery)`、`game.progress.mark(id)`、`game.progress.ending(id)`、`game.progress.summary()`。
- 内容侧会在对应交互/事件处调用 `mark(id)`；引擎未接入时是 no-op，不影响现有玩法。
- 默认沉浸：不自动显示 `hint`。只有玩家在暂停 → 手记里点“要一句提示”，才按“未发现条目 + 当前区域”取一条。
- 手记未发现条目只显示 `hint`；已发现显示 `title + summary`。
- 结局单独计数，不混入发现数。

## 2. 《门后》发现目录

### 组

| 组 id | 标签 | 数量 |
|---|---|---:|
| `main` | 归家 | 7 |
| `relics` | 旧物 | 18 |
| `her` | 她 | 3 |
| 合计 | | 28 |

### 主线（7）

| id | 标题 | 摘要 | 触发 |
|---|---|---|---|
| `door.main.entry` | 503 的门 | 门没锁。门轴的声音和记忆里一样。 | 打开 503 |
| `door.main.flashlight` | 手电 | 还能用。光柱里全是灰。 | 拿起手电 |
| `door.main.letter1` | 字条 · 一 | “你走的时候没关灯。我替你关了。” | 拾取字条 1 |
| `door.main.letter2` | 字条 · 二 | “楼道又漏水了。报修三次，没人来。” | 拾取字条 2 |
| `door.main.letter3` | 字条 · 三 | “门我没锁。灯我也没关。” | 拾取字条 3 |
| `door.main.bedroom` | 卧室门 | 门缝底下有光。里面有人。 | 解锁卧室门 |
| `door.main.final` | 一封信 | “别开灯。让我看看你。” | 读完床上信件 |

### 旧物（18）

| id | 标题 | 摘要 | 触发对象 |
|---|---|---|---|
| `door.relic.photo1` | 全家福 · 一 | 父亲的脸被闪光灯照白，母亲在笑。 | `INT_photo_1` |
| `door.relic.photo2` | 全家福 · 二 | 1999 年夏，孩子手里的冰棍快化了。 | `INT_photo_2` |
| `door.relic.photo3` | 结婚照 | 两个人都很年轻，照片被挪到最里面。 | `INT_photo_3` |
| `door.relic.drawing` | 一张画 | “妈妈，我回来。”烟囱冒着蓝烟。 | `INT_child_drawing` / `V2_drawing_corr` |
| `door.relic.calendar` | 1999 年挂历 | 3 月 12 日被红笔圈住：早点回家。 | `INT_calendar` |
| `door.relic.notice` | 公告栏 | 寻人启事没有照片，只剩“五楼，穿白裙子”。 | `INT_notice_board` |
| `door.relic.couplet` | 门框红纸 | 对联褪成粉色，每年重贴，没有换新。 | `INT_couplet` |
| `door.relic.shoes` | 门口的布鞋 | 鞋尖朝里，鞋底是干的，像刚回来。 | `INT_shoes_waiting` |
| `door.relic.child_shoes` | 小布鞋 | 比旁边小两号，鞋里塞着十年前的报纸。 | `V2_shoes_waiting` |
| `door.relic.phone` | 旧电话 | 听筒里是忙音；0 和 6 已经磨平。 | `INT_phone` |
| `door.relic.sewing` | 缝纫机 | 停在一半，线还穿着。 | `INT_sewing_machine` |
| `door.relic.thermos` | 暖水瓶 | 还是满的，壶塞上缠着红绳。 | `INT_thermos` |
| `door.relic.chair` | 窗边椅子 | 坐垫上有一块凹痕，像刚有人站起来。 | `INT_chair_final` |
| `door.relic.bed` | 床 | 被子叠得整齐，枕头上有白头发。 | `S_bed*` |
| `door.relic.wardrobe` | 衣柜 | 男式外套尺码不对；旁边空了一整边。 | `S_wardrobe` |
| `door.relic.tv` | 电视雪花 | 音量调到最小，雪花声没有变小。 | `S_tv*` |
| `door.relic.frames` | 空相框 | 两只相框都空了，玻璃后面有灰。 | `S_photo_1` / `S_photo_2` |
| `door.relic.clock` | 停摆的钟 | 三点十七分。那天你也在。 | `INT_clock` |

### 她（3）

| id | 标题 | 摘要 | 触发 |
|---|---|---|---|
| `door.her.glimpse` | 走廊尽头 | 白裙子在灯下停了一下。你眨了眼，她不见了。 | 第三轮 glimpse |
| `door.her.first_look` | 第一次看清 | 她的脸被湿发挡住。你不敢看第二眼。 | 追逐中第一次看见实体 |
| `door.her.sitting` | 坐在椅子上 | 她背对着窗。你认出了那张脸。 | 进入卧室结局 |

### 结局（1）

| id | 标题 | isTrue | 触发 |
|---|---|---|---|
| `door.ending.home` | 你终于回来了 | false | 读完最终信 |

### 沉浸档提示（手记里主动取）

- 无目标进度时：`503 在走廊尽头。门没锁。`
- 进入 503 后：`有人常待的地方：桌边、厨房、书架。`
- 第 2 轮：`门又开了。回去看看，屋里少了什么。`
- 第 3 轮：`看着她，她不会动。卧室门在走廊另一端。`
- 旧物：`客厅墙上、厨房碗柜、卧室床头，还有一些没看过的旧东西。`

## 3. 《镜中》发现目录

### 组

| 组 id | 标签 | 数量 |
|---|---|---:|
| `rounds` | 回合 | 3 |
| `relics` | 澡堂旧物 | 5 |
| `diffs` | 镜中差异 | 8 |
| 合计 | | 16 |

### 回合（3）

| id | 标题 | 摘要 | 触发 |
|---|---|---|---|
| `mirror.round1` | 第一回合 | 毛巾、柜门、凳子。镜子里是另一个摆法。 | 完成第一回合 |
| `mirror.round2` | 第二回合 | 灯灭了。镜中的人站到了镜子前。 | 完成第二回合 |
| `mirror.round3` | 第三回合 | 水汽、阀门、长凳。最后一次对齐。 | 完成第三回合 |

### 澡堂旧物（5）

| id | 标题 | 摘要 | 触发对象 |
|---|---|---|---|
| `mirror.relic.poster` | 1999 年海报 | 画上的人没有影子；十一点停止放水。 | `S_bath_poster` |
| `mirror.relic.notice` | 营业时间牌 | 票价被红漆改过三次，营业时间被抠掉。 | `S_bath_notice` |
| `mirror.relic.board` | 通知栏 | 寻人启事没有照片，“寻人”被描了很多遍。 | `S_ticket_board` |
| `mirror.relic.ticket` | 旧澡票 | 编号 0417，背面写着“给你留着”。 | `S_bath_ticket` |
| `mirror.relic.clothes` | 柜里的工装 | 口袋里有半根没点的烟。 | `S_open_locker_clothes` |

### 镜中差异（8）

| id | 标题 | 摘要 | 触发 |
|---|---|---|---|
| `mirror.diff.towel` | 毛巾 | 现实中挂在钩子上，镜中在地上。 | 对齐/错误使用毛巾 |
| `mirror.diff.valve` | 阀门 | 镜中开着，现实关着。 | 操作阀门 |
| `mirror.diff.lights` | 灯 | 镜中灯灭了。 | 操作灯光 |
| `mirror.diff.radio` | 收音机 | 亮着，不出声。 | 操作收音机 |
| `mirror.diff.locker` | 柜门 | 镜中开着，现实关着。 | 操作柜门 |
| `mirror.diff.mannequin` | 模特 | 镜中站到了镜子前。 | 移动模特 |
| `mirror.diff.stool01` | 凳子 · 一 | 镜中放在长凳上。 | 移动凳子 1 |
| `mirror.diff.stool02` | 凳子 · 二 | 这一只两边一样。 | 移动凳子 2 |

### 结局（1）

| id | 标题 | isTrue | 触发 |
|---|---|---|---|
| `mirror.ending.leave` | 留下的人 | false | 第三次对齐后镜面碎裂 |

### 沉浸档提示（手记里主动取）

- 每回合：`镜子里的房间和这边不一样。先找最显眼的那处。`
- 剩余 2 处：`还差两处。注意镜子里没有跟着动的东西。`
- 剩余 1 处：`最后一件：看看长凳、镜框和柜门。`
- 旧物：`海报、票价牌、通知栏、地上的票、开着的柜子。`

## 4. 《夜路》发现目录

### 组

| 组 id | 标签 | 数量 |
|---|---|---:|
| `lanterns` | 灯 | 5 |
| `shrine` | 土地庙 | 1 |
| `roadside` | 路边 | 4 |
| 合计 | | 10 |

### 灯（5）

| id | 标题 | 摘要 | 触发 |
|---|---|---|---|
| `nightroad.lantern1` | 第一盏灯 | 纸罩上有一个指印。 | 点亮 1 |
| `nightroad.lantern2` | 第二盏灯 | 灯芯是湿的，还是着了。 | 点亮 2 |
| `nightroad.lantern3` | 第三盏灯 | 灯下压着一张没写完的纸钱。 | 点亮 3 |
| `nightroad.lantern4` | 第四盏灯 | 从这里能看见土地庙的檐角。 | 点亮 4 |
| `nightroad.lantern5` | 第五盏灯 | 最后一盏。身后的纸响停了。 | 点亮 5 |

### 土地庙（1）

| id | 标题 | 摘要 | 触发 |
|---|---|---|---|
| `nightroad.shrine` | 土地庙 | 香灰是新的。牌位上没有名字。 | 上香 |

### 路边（4，本版新增）

| id | 标题 | 摘要 | 触发对象 |
|---|---|---|---|
| `nightroad.road.sign` | 路牌 | “土地庙”三个字还在，距离被人用指甲划掉。 | `S_sign_1`（`S_sign_2` 同条） |
| `nightroad.road.tablet` | 牌位 | 没有名字。香灰是新的。 | `S_shrine_tablet` |
| `nightroad.road.paper` | 纸钱 | 被风压在泥里，边缘还是热的。 | `S_paper_money_01` |
| `nightroad.road.bicycle` | 旧自行车 | 倒在田埂边，车筐里有一把湿透的伞。 | `S_bicycle` |

### 结局（2）

| id | 标题 | isTrue | 触发 |
|---|---|---|---|
| `nightroad.ending.look` | 你回头了 | false | 庙前按 E 回头 |
| `nightroad.ending.walk` | 你没有回头 | false | 庙前按 W 继续向前 |

> 当前没有真结局；两个平级结局。未来若加，`isTrue: true` 标在真结局上，重开提示只指向“还有一个结局”，不点名。

### 沉浸档提示（手记里主动取）

- 开局：`雾里有灯。先看见光，再看见路。`
- 找不到下一盏：`下一盏灯在你左/右前方。跟着暖光走。`
- 纸人靠近：`身后有纸响。别一直看它。`
- 结局后：`庙前还有另一条路。回头看，或者不回头。`

## 5. 结局收集与重开提示

- 结局页显示 `结局 1/2`（夜路）或 `1/1`（门后/镜中）。
- 已解锁结局标题可见；未解锁显示 `？？？`。
- 夜路第一次结局后，结局页 + “再走一遍”开局提示出现一次：
  - 已看《你回头了》→ `另一条路：这次别回头。`
  - 已看《你没有回头》→ `另一条路：这次回头看看。`
- 门后/镜中只有 1 个结局，不显示“另一条路”。
- 入口页夜路卡片显示 `结局 1/2`；三篇全通关显示“三更已满”，全结局再加“全结局”。

## 6. 内容侧触发点清单（给实现用）

### door
- `INT_door_503` onOpen → `door.main.entry`
- `INT_flashlight` onUse → `door.main.flashlight`
- 字条 1/2/3 拾取 → `door.main.letter1/2/3`
- 卧室门解锁/打开 → `door.main.bedroom`
- 最终信 read → `door.main.final` + `ending('door.ending.home')`
- `EXAMINE.photo1/2/3/drawing/calendar/notice/couplet/shoes/shoesChild` → 对应 relic
- `examineLine` 电话/缝纫机/暖水瓶/椅子/床/衣柜/电视/空相框/钟 → 对应 relic
- glimpse 显示 → `door.her.glimpse`
- 追逐中第一次看见实体 → `door.her.first_look`
- 进入卧室结局 → `door.her.sitting`

### mirror
- 5 个 `EXAMINES` → relic
- 8 个 `rig` 操作成功/失败 → diff
- 完成回合 1/2/3 → rounds
- `endingSequence` → `ending('mirror.ending.leave')`

### nightroad
- 5 个 `INT_lantern_0X` 点亮 → lantern
- `INT_incense` 上香 → shrine
- 新增 4 个 roadside 交互 → road.*
- `endingLookBack` → `ending('nightroad.ending.look')`
- `endingWalkOn` → `ending('nightroad.ending.walk')`

## 7. 验收（内容侧）

- 所有 id 唯一；组计数与条目数一致。
- 每条都有 `title / summary / hint`，未发现时可只显示 `hint`。
- 夜路 4 个新增交互在真实键鼠/触屏下都能触发，且不影响主线灯/香流程。
- 默认沉浸下不出现自动提示；手记里的“要一句提示”每次只返回 1 条。
- 结局计数与标题正确；门后/镜中 1/1，夜路 1/2 → 2/2。
