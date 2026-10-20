/* v1.4.0 内容侧发现目录。
 * 仅数据，不依赖引擎；引擎接入 progress 后读取 game.config.discovery。
 * 文案与触发点见 docs/DISCOVERY_SPEC.md。
 */

const e = (id, group, title, summary, hint, trigger) => ({ id, group, title, summary, hint, trigger });

export const DOOR_DISCOVERY = {
  version: 1,
  groups: [
    { id: 'main', label: '归家', total: 7 },
    { id: 'relics', label: '旧物', total: 18 },
    { id: 'her', label: '她', total: 3 },
  ],
  entries: [
    e('door.main.entry', 'main', '503 的门', '门没锁。门轴的声音和记忆里一样。', '走廊尽头，503。', 'INT_door_503'),
    e('door.main.flashlight', 'main', '手电', '还能用。光柱里全是灰。', '玄关或者客厅，应该有一支手电。', 'INT_flashlight'),
    e('door.main.letter1', 'main', '字条 · 一', '“你走的时候没关灯。我替你关了。”', '客厅里，有人常待的地方。', 'INT_letter_01'),
    e('door.main.letter2', 'main', '字条 · 二', '“楼道又漏水了。报修三次，没人来。”', '厨房里，碗柜附近。', 'INT_letter_02'),
    e('door.main.letter3', 'main', '字条 · 三', '“门我没锁。灯我也没关。”', '书架、卧室、或者她常坐的地方。', 'INT_letter_03'),
    e('door.main.bedroom', 'main', '卧室门', '门缝底下有光。里面有人。', '三张字条之后，卧室门会开。', 'INT_door_bedroom'),
    e('door.main.final', 'main', '一封信', '“别开灯。让我看看你。”', '床上有一封信。', 'INT_letter_final'),
    e('door.relic.photo1', 'relics', '全家福 · 一', '父亲的脸被闪光灯照白，母亲在笑。', '客厅墙上有一张照片。', 'INT_photo_1'),
    e('door.relic.photo2', 'relics', '全家福 · 二', '1999 年夏，孩子手里的冰棍快化了。', '客厅另一面墙上还有一张照片。', 'INT_photo_2'),
    e('door.relic.photo3', 'relics', '结婚照', '两个人都很年轻，照片被挪到最里面。', '卧室墙上有一张旧照片。', 'INT_photo_3'),
    e('door.relic.drawing', 'relics', '一张画', '“妈妈，我回来。”烟囱冒着蓝烟。', '墙上有孩子的蜡笔画。', 'INT_child_drawing'),
    e('door.relic.calendar', 'relics', '1999 年挂历', '3 月 12 日被红笔圈住：早点回家。', '卧室墙边挂着一本旧挂历。', 'INT_calendar'),
    e('door.relic.notice', 'relics', '公告栏', '寻人启事没有照片，只剩“五楼，穿白裙子”。', '走廊墙上的公告栏。', 'INT_notice_board'),
    e('door.relic.couplet', 'relics', '门框红纸', '对联褪成粉色，每年重贴，没有换新。', '503 门框上贴过红纸。', 'INT_couplet'),
    e('door.relic.shoes', 'relics', '门口的布鞋', '鞋尖朝里，鞋底是干的，像刚回来。', '进门的地方有一双女式布鞋。', 'INT_shoes_waiting'),
    e('door.relic.child_shoes', 'relics', '小布鞋', '比旁边小两号，鞋里塞着十年前的报纸。', '第二轮之后，门口会多一双小鞋。', 'V2_shoes_waiting'),
    e('door.relic.phone', 'relics', '旧电话', '听筒里是忙音；0 和 6 已经磨平。', '客厅角落有一台旧电话。', 'INT_phone'),
    e('door.relic.sewing', 'relics', '缝纫机', '停在一半，线还穿着。', '窗边有一台缝纫机。', 'INT_sewing_machine'),
    e('door.relic.thermos', 'relics', '暖水瓶', '还是满的，壶塞上缠着红绳。', '厨房或客厅桌上有一只暖水瓶。', 'INT_thermos'),
    e('door.relic.chair', 'relics', '窗边椅子', '坐垫上有一块凹痕，像刚有人站起来。', '客厅窗边有一把椅子。', 'INT_chair_final'),
    e('door.relic.bed', 'relics', '床', '被子叠得整齐，枕头上有白头发。', '卧室的床。', 'S_bed'),
    e('door.relic.wardrobe', 'relics', '衣柜', '男式外套尺码不对；旁边空了一整边。', '卧室的衣柜。', 'S_wardrobe'),
    e('door.relic.tv', 'relics', '电视雪花', '音量调到最小，雪花声没有变小。', '客厅一直开着的电视。', 'S_tv'),
    e('door.relic.frames', 'relics', '空相框', '两只相框都空了，玻璃后面有灰。', '墙上空着的相框。', 'S_photo'),
    e('door.relic.clock', 'relics', '停摆的钟', '三点十七分。那天你也在。', '走廊里有一只停了的钟。', 'INT_clock'),
    e('door.her.glimpse', 'her', '走廊尽头', '白裙子在灯下停了一下。你眨了眼，她不见了。', '第三轮，走廊尽头会有个人。', 'glimpse'),
    e('door.her.first_look', 'her', '第一次看清', '她的脸被湿发挡住。你不敢看第二眼。', '走廊里有人在等你回头。', 'chase'),
    e('door.her.sitting', 'her', '坐在椅子上', '她背对着窗。你认出了那张脸。', '卧室的椅子上坐着一个人。', 'bedroom_ending'),
  ],
  endings: [
    { id: 'door.ending.home', title: '你终于回来了', isTrue: false, hint: '读完床上的信。' },
  ],
};

/* 镜中：内容已就绪，等引擎 progress 接入。 */
export const MIRROR_DISCOVERY = {
  version: 1,
  groups: [
    { id: 'rounds', label: '回合', total: 3 },
    { id: 'relics', label: '澡堂旧物', total: 5 },
    { id: 'diffs', label: '镜中差异', total: 8 },
  ],
  entries: [
    e('mirror.round1', 'rounds', '第一回合', '毛巾、柜门、凳子。镜子里是另一个摆法。', '先看镜子里最显眼的不同。', 'round1'),
    e('mirror.round2', 'rounds', '第二回合', '灯灭了。镜中的人站到了镜子前。', '第二回合，注意灯和模特。', 'round2'),
    e('mirror.round3', 'rounds', '第三回合', '水汽、阀门、长凳。最后一次对齐。', '最后回合，注意水汽和长凳。', 'round3'),
    e('mirror.relic.poster', 'relics', '1999 年海报', '画上的人没有影子；十一点停止放水。', '墙上那张褪色的海报。', 'S_bath_poster'),
    e('mirror.relic.notice', 'relics', '营业时间牌', '票价被红漆改过三次，营业时间被抠掉。', '墙上的营业时间牌。', 'S_bath_notice'),
    e('mirror.relic.board', 'relics', '通知栏', '寻人启事没有照片，“寻人”被描了很多遍。', '角落的通知栏。', 'S_ticket_board'),
    e('mirror.relic.ticket', 'relics', '旧澡票', '编号 0417，背面写着“给你留着”。', '地上有一张没撕过的澡票。', 'S_bath_ticket'),
    e('mirror.relic.clothes', 'relics', '柜里的工装', '口袋里有半根没点的烟。', '开着的柜子里挂着一件工装。', 'S_open_locker_clothes'),
    e('mirror.diff.towel', 'diffs', '毛巾', '现实中挂在钩子上，镜中在地上。', '看看毛巾挂在哪里。', 'towel'),
    e('mirror.diff.valve', 'diffs', '阀门', '镜中开着，现实关着。', '阀门的两边不一样。', 'valve'),
    e('mirror.diff.lights', 'diffs', '灯', '镜中灯灭了。', '灯管的两边不一样。', 'lights'),
    e('mirror.diff.radio', 'diffs', '收音机', '亮着，不出声。', '收音机开着。', 'radio'),
    e('mirror.diff.locker', 'diffs', '柜门', '镜中开着，现实关着。', '柜门的两边不一样。', 'locker'),
    e('mirror.diff.mannequin', 'diffs', '模特', '镜中站到了镜子前。', '模特的位置变了。', 'mannequin'),
    e('mirror.diff.stool01', 'diffs', '凳子 · 一', '镜中放在长凳上。', '长凳上多了一只凳子。', 'stool01'),
    e('mirror.diff.stool02', 'diffs', '凳子 · 二', '这一只两边一样。', '另一只凳子。', 'stool02'),
  ],
  endings: [
    { id: 'mirror.ending.leave', title: '留下的人', isTrue: false, hint: '第三次对齐之后。' },
  ],
};
