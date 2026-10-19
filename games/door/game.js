/* 《门后》—— 一更。共享引擎 + 本作玩法。 */
import * as THREE from 'three';
import { HorrorGame } from '../../engine/engine.js';
import { clamp } from '../../engine/utils.js';

/* ---------------- 文本 ---------------- */
const LETTERS = {
  1: {
    head: '字条 · 一',
    lines: [
      '你走的时候没关灯。我替你关了。',
      '钥匙还在鞋柜上，老地方。',
      '下次回来，别在楼下站着。',
    ],
  },
  2: {
    head: '字条 · 二',
    lines: [
      '楼道又漏水了。报修三次，没人来。',
      '你小时候说过，五楼的走廊比别的楼长。',
      '现在我也这么觉得。',
    ],
  },
  3: {
    head: '字条 · 三',
    lines: [
      '我看见你上楼了。',
      '脚步声停在门口，又走开。',
      '门我没锁。灯我也没关。',
    ],
  },
  final: {
    head: '一封信',
    lines: [
      '我不怪你。',
      '你每年回来一次，我就当你每年都回来过。',
      '卧室的椅子上，一直有人坐着。',
      '如果你读到这封信，说明你终于进来了。',
      '别开灯。让我看看你。',
    ],
  },
};

const LOOP_HINTS = {
  2: '灯灭了。你又站在楼道里。',
  3: '这次，走廊比刚才长。',
};

const state = {
  loop: 1,
  letters: [],
  enteredApartment: false,
  hasFlashlight: false,
  entity: {
    active: false,
    root: null,
    home: new THREE.Vector3(),
    grace: 0,
    unseen: 0,
    freeze: 0,
    stepTimer: 0,
    breath: null,
    done: false,
  },
  doors: {},
  switches: { living: true, corridor: true },
  finalStarted: false,
  ended: false,
  t: 0,
  hintTimer: 0,
};

let gameRef = null;

/* ---------------- 小工具 ---------------- */
function obj(name) { return gameRef ? gameRef.find(name) : null; }

function hasSfx(key) {
  return gameRef && gameRef.audio && gameRef.audio.entries.sfx[key];
}

function playSfx(key, opts = {}) {
  if (!hasSfx(key)) return null;
  return gameRef.audio.sfx(key, opts);
}

function setVis(name, v) { gameRef.setVisible(name, v); }

function horizontalDist(a, b) { return Math.hypot(a.x - b.x, a.z - b.z); }

/** 从 from 到 to 之间是否有可见几何遮挡 */
function clearLine(from, to, ignore) {
  const dir = new THREE.Vector3().subVectors(to, from);
  const dist = dir.length();
  if (dist < 0.01) return true;
  dir.normalize();
  const ray = new THREE.Raycaster(from.clone(), dir, 0.05, Math.max(0.1, dist - 0.2));
  const hits = ray.intersectObject(gameRef.level, true);
  for (const h of hits) {
    let o = h.object;
    let hidden = false;
    let isIgnore = false;
    while (o) {
      if (o === ignore) { isIgnore = true; break; }
      if (o.visible === false) { hidden = true; break; }
      o = o.parent;
    }
    if (isIgnore) continue;
    if (hidden) continue;
    return false;
  }
  return true;
}

/* ---------------- 玩法 ---------------- */
const config = {
  id: 'door',
  title: '门后',
  chapter: '一更 · DOOR',
  titleEn: 'BEHIND THE DOOR',
  poster: '../../assets/art/poster-door.jpg',
  warning: '本作包含心理恐怖、闪烁画面、幽闭空间与死亡意象。没有血腥画面。建议戴耳机，在安静、光线较暗的环境游玩。',
  homeUrl: '../../index.html',
  model: '../../assets/models/door.glb',
  textures: '../../assets/textures/manifest.json',
  audio: '../../assets/audio/door/manifest.json',
  footstepSfx: 'stepWood',
  flashlight: { batterySeconds: 120, intensity: 2.2 },
  ambient: { color: 0x232f28, intensity: 0.36 },
  fog: { color: 0x070a08, density: 0.05 },
  theme: { accent: '#c9a55a', ink: '#d8d2c0', bg: '#060807' },
  playerStart: { spawn: 'SPAWN_corridor', look: 'LOOK_corridor' },
  renderScale: 0.6,

  async setup(game) {
    gameRef = game;
    game.ui.setObjective('回到 503');

    // 初始隐藏：后两张字条、结局信件、实体
    setVis('INT_letter_02', false);
    setVis('INT_letter_03', false);
    setVis('INT_letter_final', false);

    const entity = game.entities.get('ENTITY_she');
    if (entity) {
      state.entity.root = entity;
      state.entity.home.copy(entity.position);
      entity.visible = false;
    }

    // 门
    const door503 = game.makeDoor(obj('INT_door_503'), {
      prompt: '打开 503 的门',
      onOpen: () => {
        game.ui.subtitle('门没锁。', 2.2);
        game.ui.setObjective('进去看看');
        if (game.audio && game.audio.ready) playSfx('doorUnlock', { volume: 0.5 });
      },
    });
    state.doors['503'] = door503;

    const doorBed = game.makeDoor(obj('INT_door_bedroom'), {
      prompt: '打开卧室门',
      locked: true,
      lockedText: '门锁着。门缝底下透出一点光。',
      onLocked: () => tryUnlockBedroom(game),
    });
    state.doors.bedroom = doorBed;

    for (const name of ['INT_door_501', 'INT_door_502', 'INT_door_504']) {
      const d = game.makeDoor(obj(name), {
        prompt: '试着开门',
        locked: true,
        lockedText: '锁着。里面没有声音。',
      });
      state.doors[name] = d;
    }

    // 其它交互
    game.interact.add(obj('INT_fire_door'), {
      prompt: '查看防火门',
      onUse: () => game.ui.subtitle('防火门被铁丝从外面缠死了。', 2.8),
    });
    game.interact.add(obj('INT_elevator_button'), {
      prompt: '按电梯',
      onUse: () => {
        playSfx('lightFlicker', { volume: 0.4 });
        game.ui.subtitle('电梯没有反应。灯还亮着。', 2.8);
      },
    });
    game.interact.add(obj('INT_clock'), {
      prompt: '看钟',
      onUse: () => game.ui.subtitle(`钟停在三点十七分。`, 2.6),
    });

    // 手电
    game.interact.add(obj('INT_flashlight'), {
      prompt: '拿起手电',
      onUse: () => pickupFlashlight(game),
    });

    // 电池
    for (const name of ['INT_battery_01', 'INT_battery_02']) {
      const target = obj(name);
      game.interact.add(target, {
        prompt: '捡起电池',
        onUse: () => pickupBattery(game, target),
      });
    }

    // 字条
    const letterNames = ['INT_letter_01', 'INT_letter_02', 'INT_letter_03'];
    letterNames.forEach((name, i) => {
      game.interact.add(obj(name), {
        prompt: '捡起字条',
        onUse: () => pickupLetter(game, i + 1),
      });
    });

    // 结局信件
    game.interact.add(obj('INT_letter_final'), {
      prompt: '读那封信',
      onUse: () => readFinalLetter(game),
    });

    // 灯开关
    if (obj('INT_switch_living')) {
      game.interact.add(obj('INT_switch_living'), {
        prompt: '按开关',
        onUse: () => toggleLivingLight(game),
      });
    }
    if (obj('INT_switch_corridor')) {
      game.interact.add(obj('INT_switch_corridor'), {
        prompt: '按开关',
        onUse: () => {
          playSfx('lightSwitch', { volume: 0.4 });
          game.ui.subtitle('走廊的灯早就坏了。', 2.2);
        },
      });
    }

    // 环境音与灯光初始状态
    for (const l of ['LIGHT_living', 'LIGHT_entry', 'LIGHT_kitchen']) game.setLight(l, false);
    game.setLight('LIGHT_tv', true, 0.8);
    game.setLight('LIGHT_floor_lamp', false);
    game.setLight('LIGHT_bedroom', false);
    game.setLight('LIGHT_moon_bed', true, 0.4);

    game.player.onFootstep = (speed, sprinting) => {
      const key = game.player.pos.x > 1.2 ? 'stepWood' : 'stepCarpet';
      if (hasSfx(key)) playSfx(key, { volume: sprinting ? 0.8 : 0.5, rate: 0.92 + Math.random() * 0.16 });
    };
  },

  start(game) {
    gameRef = game;
    state.t = 0;
    state.loop = 1;
    state.letters = [];
    state.enteredApartment = false;
    state.hasFlashlight = false;
    state.entity.active = false;
    state.entity.done = false;
    state.finalStarted = false;
    state.ended = false;
    state.hintTimer = 6;

    game.player.enabled = true;
    game.player.teleportTo('SPAWN_corridor', 'LOOK_corridor');
    game.audio.playMusic('main', { fade: 3 });
    game.audio.playAmbience('corridor', { channel: 'main', fade: 2 });
    game.audio.playAmbience('rainWindow', { channel: 'extra', fade: 2, volume: 0.4 });
    game.ui.setObjective('回到 503');
    game.ui.setBattery(null);
    game.ui.subtitle('每年回来一次。今年，门没锁。', 4.4);
    game.setThreat(0);
    game.setSanity(0);
    if (state.doors['503'] && state.doors['503'].isOpen) state.doors['503'].close();
    // 确保门状态
    for (const k of ['INT_door_501', 'INT_door_502', 'INT_door_504']) {
      const d = state.doors[k];
      if (d) d.setLocked(true);
    }
    if (state.doors.bedroom) state.doors.bedroom.setLocked(true);
  },

  update(game, dt) {
    state.t += dt;

    // 手电 HUD
    if (state.hasFlashlight) game.ui.setBattery(game.player.batteryFraction);
    else game.ui.setBattery(null);

    // 区域切换
    if (!state.enteredApartment && game.player.pos.x > 1.35) {
      state.enteredApartment = true;
      game.audio.playAmbience('roomTone', { channel: 'main', fade: 2.5 });
      game.audio.playAmbience('tvStatic', { channel: 'extra', fade: 2, volume: 0.35 });
      game.setLight('LIGHT_entry', true, 0.8);
      game.setLight('LIGHT_living', true, 0.7);
      game.ui.setObjective('找到三张字条');
      game.ui.subtitle('三年没回来了。屋里还是那个味道。', 3.8);
    }

    // 实体
    updateEntity(game, dt);

    // 压力值
    if (state.entity.active && !state.entity.done) {
      const dist = horizontalDist(game.player.pos, state.entity.root.position);
      const threat = clamp(1 - dist / 13, 0, 1) * (state.entity.freeze > 0 ? 0.65 : 1);
      game.setThreat(threat * 0.9);
      game.setSanity(clamp(0.15 + threat * 0.7, 0, 1));
    } else {
      game.setThreat(0);
      game.setSanity(0);
    }

    // 结局触发：进入卧室
    if (state.entity.active && !state.entity.done && game.player.pos.x > 6.75 && !state.finalStarted) {
      enterBedroomEnding(game);
    }

    // 开局提示
    if (state.hintTimer > 0) {
      state.hintTimer -= dt;
      if (state.hintTimer <= 0) {
        game.ui.subtitle('走廊尽头有扇门。你的。', 3.2);
      }
    }
  },

  respawn(game) {
    gameRef = game;
    state.entity.done = false;
    state.entity.grace = 2.6;
    state.finalStarted = false;
    game.player.teleportTo('SPAWN_corridor', 'LOOK_corridor');
    game.setThreat(0);
    game.setSanity(0);
    game.audio.duck(false);
    game.audio.playMusic('tension', { fade: 1 });
    game.ui.setObjective('回卧室');
    if (state.entity.root) {
      state.entity.root.position.set(0, 0, 17.2);
      state.entity.root.visible = true;
      state.entity.active = true;
      state.entity.freeze = 1.2;
    }
    game.ui.subtitle('你还能听见她的呼吸。', 2.8);
  },
};

/* ---------------- 交互行为 ---------------- */
function pickupFlashlight(game) {
  const f = obj('INT_flashlight');
  if (f) f.visible = false;
  state.hasFlashlight = true;
  game.player.giveFlashlight();
  playSfx('pickupLetter', { volume: 0.5 });
  game.ui.subtitle('手电还能用。省着点。', 2.8);
  if (state.letters.length < 3) game.ui.setObjective('找到三张字条');
}

function pickupBattery(game, target) {
  if (!target || !target.visible) return;
  target.visible = false;
  game.player.addBattery(60);
  playSfx('pickupBattery', { volume: 0.7 });
  game.ui.subtitle('半截电池。还能撑一会儿。', 2.4);
  if (!state.hasFlashlight) {
    state.hasFlashlight = true;
    game.player.giveFlashlight();
  }
}

function pickupLetter(game, index) {
  if (state.letters.includes(index)) return;
  const name = `INT_letter_0${index}`;
  const o = obj(name);
  if (!o || !o.visible) return;
  state.letters.push(index);
  o.visible = false;
  playSfx('pickupLetter', { volume: 0.8 });
  game.setThreat(0);
  game.setSanity(0);
  const data = LETTERS[index];
  game.openPaper({
    head: data.head,
    lines: data.lines,
    onClose: (g) => afterLetter(g, index),
  });
}

function afterLetter(game, index) {
  if (state.letters.length >= 3) {
    startChase(game);
    return;
  }
  const next = index + 1;
  state.loop = next;
  applyLoop(game, next);
  // 下一张字条
  setVis(`INT_letter_0${next}`, true);
  game.ui.fadeIn(900).then(() => {
    game.player.teleportTo('SPAWN_corridor', 'LOOK_corridor');
    if (state.doors['503'] && !state.doors['503'].isOpen) state.doors['503'].open(true);
    game.audio.playAmbience('corridor', { channel: 'main', fade: 1.5 });
    game.audio.playAmbience('rainWindow', { channel: 'extra', fade: 1.5, volume: 0.4 });
    game.ui.setObjective('再回 503 看看');
    game.ui.subtitle(LOOP_HINTS[next] || '灯灭了。你又站在楼道里。', 3.6);
    setTimeout(() => game.ui.fadeOut(1200), 700);
  });
  setTimeout(() => {
    playSfx('blackout', { volume: 0.8 });
  }, 300);
}

function applyLoop(game, loop) {
  if (loop === 2) {
    game.setVariants('V2_', true);
    game.setLight('LIGHT_corr_02', false);
    game.setLight('LIGHT_corr_04', false);
    game.setLight('LIGHT_living', false);
    game.setLight('LIGHT_kitchen', false);
  } else if (loop >= 3) {
    game.setVariants('V2_', true);
    game.setVariants('V3_', true);
    for (const n of ['LIGHT_corr_01', 'LIGHT_corr_02', 'LIGHT_corr_04', 'LIGHT_corr_05']) game.setLight(n, false);
    game.setLight('LIGHT_corr_03', true, 0.55);
    game.setLight('LIGHT_entry', false);
    game.setLight('LIGHT_tv', false);
    game.setLight('LIGHT_moon_bed', true, 0.3);
  }
}

function tryUnlockBedroom(game) {
  if (state.letters.length >= 3) {
    state.doors.bedroom.setLocked(false);
    playSfx('doorUnlock', { volume: 0.8 });
    game.ui.subtitle('门开了。里面有人坐着。', 3);
    game.ui.setObjective('进去');
  }
}

/* ---------------- 追逐 ---------------- */
function startChase(game) {
  state.loop = 3;
  state.entity.active = true;
  state.entity.done = false;
  state.entity.grace = 2.6;
  state.entity.unseen = 0;
  state.entity.freeze = 0;
  state.entity.stepTimer = 0;
  state.doors.bedroom.setLocked(false);
  game.ui.fadeIn(1000).then(() => {
    game.player.teleportTo('SPAWN_corridor', 'LOOK_corridor');
    applyLoop(game, 3);
    game.audio.playMusic('tension', { fade: 2 });
    game.ui.setObjective('回卧室');
    game.ui.subtitle('楼道里有呼吸声。她只在你看着她时停下。', 5.2);
    if (state.entity.root) {
      state.entity.root.position.set(0, 0, 17.2);
      state.entity.root.visible = true;
    }
    setTimeout(() => game.ui.fadeOut(1200), 700);
  });
  playSfx('blackout', { volume: 0.9 });
  if (state.doors['503'] && !state.doors['503'].isOpen) state.doors['503'].open(true);
  setTimeout(() => {
    if (hasSfx('entityBreath')) state.entity.breath = game.audio.sfx('entityBreath', { loop: true, volume: 0.25 });
  }, 2500);
}

function updateEntity(game, dt) {
  const st = state.entity;
  if (!st.active || st.done || !st.root) return;
  const root = st.root;
  const player = game.player;

  if (st.grace > 0) st.grace -= dt;

  const toPlayer = new THREE.Vector3().subVectors(player.pos, root.position);
  toPlayer.y = 0;
  const dist = toPlayer.length();
  if (dist > 0.001) root.lookAt(player.pos.x, root.position.y, player.pos.z);

  const looked = !st.done && game.isLookingAt(root, { maxDistance: 26, fovDot: 0.25 });
  st.freeze = looked ? 0.25 : Math.max(0, st.freeze - dt);

  let moving = false;
  if (st.grace <= 0 && !looked) {
    st.unseen += dt;
    // 靠近：基础速度 + 长时间未被注视时的"闪现"
    let speed = 2.45;
    if (st.unseen > 3.2 && dist > 4) {
      st.unseen = 0;
      const dash = Math.min(2.4, Math.max(0, dist - 2.8));
      if (dash > 0.2) {
        root.position.add(toPlayer.normalize().multiplyScalar(dash));
        playSfx('entityStep', { volume: 0.85, rate: 0.8 });
        if (hasSfx('stinger')) playSfx('stinger', { volume: 0.4 });
      }
    } else {
      // 简单寻路：先走到走廊中路，再穿过 503 门进室内
      let target = player.pos.clone();
      if (root.position.x < 1.15 && player.pos.x > 1.4) {
        target.set(0, 0, 5.5);
      }
      const dir = new THREE.Vector3().subVectors(target, root.position);
      dir.y = 0;
      const d = dir.length();
      if (d > 0.25) {
        dir.normalize();
        root.position.add(dir.multiplyScalar(speed * dt));
        moving = true;
      }
    }
  }

  if (moving) {
    st.stepTimer -= dt;
    if (st.stepTimer <= 0) {
      st.stepTimer = 0.55 + Math.random() * 0.25;
      playSfx('entityStep', {
        volume: 0.5,
        rate: 0.88 + Math.random() * 0.2,
        pos: root.position.clone().add(new THREE.Vector3(0, 1, 0)),
      });
    }
    st.root.position.y = Math.sin(game.time * 5) * 0.015;
  } else {
    st.root.position.y = 0;
  }

  // 抓到判定：距离近 + 视线通畅
  if (st.grace <= 0 && dist < 0.95) {
    const eye = game.camera.getWorldPosition(new THREE.Vector3());
    const chest = root.position.clone().add(new THREE.Vector3(0, 1.2, 0));
    if (clearLine(eye, chest, root)) {
      triggerDeath(game);
    }
  }

  // 呼吸层随距离变化
  if (st.breath) {
    const v = clamp(1 - dist / 16, 0, 1) * (looked ? 0.5 : 1);
    st.breath.setVolume(0.05 + v * 0.5);
  }
}

function triggerDeath(game) {
  const st = state.entity;
  if (st.done) return;
  st.done = true;
  st.active = false;
  if (st.breath) { st.breath.stop(0.4); st.breath = null; }
  playSfx('entityCatch', { volume: 1 });
  if (hasSfx('whisper')) playSfx('whisper', { volume: 0.8 });
  game.setThreat(0);
  game.setSanity(0);
  game.fail('她的手很凉。');
}

/* ---------------- 结局 ---------------- */
function enterBedroomEnding(game) {
  if (state.finalStarted) return;
  state.finalStarted = true;
  state.entity.done = true;
  state.entity.active = false;
  if (state.entity.breath) { state.entity.breath.stop(0.6); state.entity.breath = null; }
  game.setThreat(0);
  game.setSanity(0.15);
  game.audio.playMusic('main', { fade: 3 });
  game.audio.playAmbience('roomTone', { channel: 'main', fade: 2 });
  game.ui.setObjective('看看床上');
  // 她坐在原来的位置
  const root = state.entity.root;
  if (root) {
    root.position.copy(state.entity.home);
    root.visible = true;
    root.lookAt(game.player.pos.x, root.position.y, game.player.pos.z);
  }
  setVis('INT_letter_final', true);
  game.ui.subtitle('她坐在椅子上，背对着窗。床上有一封信。', 4.6);
  if (hasSfx('whisper')) setTimeout(() => playSfx('whisper', { volume: 0.6 }), 1200);
}

function readFinalLetter(game) {
  if (state.ended) return;
  state.ended = true;
  playSfx('paperRustle', { volume: 0.8 });
  const data = LETTERS.final;
  game.openPaper({
    head: data.head,
    lines: data.lines,
    onClose: () => {
      game.audio.stopAll(2.5);
      if (game.audio.entries.music.ending) game.audio.playMusic('ending', { fade: 1 });
      setTimeout(() => {
        game.finish({
          chapter: '一更 · 门后',
          title: '你终于回来了',
          lines: [
            '信纸上是你的字迹。你不记得自己写过。',
            '椅子上的她抬起头。你认出了那张脸。',
            '走廊的灯一盏一盏地灭下去。',
            '这一次，你没有走。',
          ],
          footer: '三更 · 一更 完',
        });
      }, 1400);
    },
  });
}

/* ---------------- 启动 ---------------- */
const game = new HorrorGame(config);
game.load().then(() => {
  // QA / 调试入口
  window.__DOOR__ = {
    game, state,
    teleport(x, z) { game.player.pos.set(x, 0, z); game.player._syncCamera(0, true); },
    face(x, z) { game.player.lookAt(new THREE.Vector3(x, 1.4, z)); },
    lookAt(x, y, z) { game.player.lookAt(new THREE.Vector3(x, y, z)); },
    giveFlashlight() { state.hasFlashlight = true; game.player.giveFlashlight(); },
    setLetters(n) { state.letters = [1, 2, 3].slice(0, n); },
    unlockBedroom() { tryUnlockBedroom(game); },
    startChase() { startChase(game); },
    enterBedroom() { enterBedroomEnding(game); },
  };
}).catch((err) => {
  console.error('加载失败', err);
  const div = document.createElement('div');
  div.style.cssText = 'position:fixed;inset:0;z-index:999;background:#000;color:#c9a55a;font:14px/1.8 monospace;padding:40px;white-space:pre-wrap;';
  div.textContent = '《门后》加载失败：\n' + (err && err.stack ? err.stack : err);
  document.body.appendChild(div);
});




