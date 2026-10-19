/* 《镜中》—— 二更。共享引擎 + 本作玩法。
 *
 * 核心：镜子实时渲染「反射场景」= 同一间更衣室的克隆。
 * 现实场景与反射场景里同名物件的状态差异，就是每回合要抹平的差别。
 * 玩家只能在镜子里看见「另一个房间」真实的样子。
 */
import * as THREE from 'three';
import { HorrorGame } from '../../engine/engine.js';
import { clamp } from '../../engine/utils.js';

/* ============================================================
 * 一、文本与数据
 * ============================================================ */

const INITIAL_WORLD = {
  towel: 'floor',       // floor | hook
  valve: 'closed',      // closed | open
  lights: 'on',         // on | off
  radio: 'off',         // off | on
  locker: 'closed',     // closed | open
  mannequin: 'corner',  // corner | mirror
  stool01: 'floor',     // floor | bench
  stool02: 'home',      // home | away
};

const NEXT_STATE = {
  towel: { floor: 'hook', hook: 'floor' },
  valve: { closed: 'open', open: 'closed' },
  lights: { on: 'off', off: 'on' },
  radio: { off: 'on', on: 'off' },
  locker: { closed: 'open', open: 'closed' },
  mannequin: { corner: 'mirror', mirror: 'corner' },
  stool01: { floor: 'bench', bench: 'floor' },
  stool02: { home: 'away', away: 'home' },
};

const PROMPT = {
  towel: { floor: '拿起毛巾', hook: '把毛巾放回地上' },
  valve: { closed: '拧开阀门', open: '关上阀门' },
  lights: { on: '关灯', off: '开灯' },
  radio: { off: '打开收音机', on: '关掉收音机' },
  locker: { closed: '打开柜门', open: '关上柜门' },
  mannequin: { corner: '搬动模特', mirror: '把模特搬回角落' },
  stool01: { floor: '把凳子放到长凳上', bench: '把凳子搬下来' },
  stool02: { home: '搬动凳子', away: '把凳子搬回去' },
};

/* 回合表：每回合 2–3 个二元差异。target 是「镜中的状态」。 */
const ROUNDS = [
  {
    target: { towel: 'hook', locker: 'open' },
    intro: '第一回合。先看一眼镜子——镜子里，有两处和这边不一样。',
    hint: '镜子里，毛巾搭在镜框上。柜门是开着的。',
  },
  {
    target: { lights: 'off', mannequin: 'mirror', radio: 'on' },
    intro: '第二回合。这次是三处。镜子里的房间，比这边暗。',
    hint: '镜子里没有开灯。模特站到了镜子前面。收音机亮着，但不出声。',
  },
  {
    target: { towel: 'floor', stool01: 'bench', valve: 'open' },
    intro: '最后一回合。它已经不在原来的地方了。',
    hint: '毛巾回到了地上。凳子被放到了长凳上。阀门是开着的，镜子里全是水汽。',
  },
];

/* 镜中身影的 5+1 个站位：从房间深处一步步逼近镜面。 */
const ENTITY_STEPS = [
  new THREE.Vector3(0.0, 0, 2.12),
  new THREE.Vector3(0.32, 0, 1.68),
  new THREE.Vector3(-0.18, 0, 1.02),
  new THREE.Vector3(0.34, 0, 0.30),
  new THREE.Vector3(-0.12, 0, -0.62),
  new THREE.Vector3(0.06, 0, -1.86),
];

const TEXTS = {
  ending: {
    chapter: '二更 · 镜中',
    title: '留下的人',
    lines: [
      '镜子里的人，把手从玻璃上挪开。',
      '他说：你每年只回来一次。我不一样，我一直在这里。',
      '澡堂的灯灭了，水汽散尽。更衣室里只剩下一个人。',
      '第二天，镜子擦得更亮了。它站在那里，等你回来。',
    ],
    footer: '三更 · 二更 完',
  },
  death: '你没有动。镜子里的人，替你动了。',
};

/* ============================================================
 * 二、全局状态
 * ============================================================ */

const state = {
  t: 0,
  round: 0,
  completed: 0,
  steps: 0,
  mistakes: 0,
  busy: false,
  dying: false,
  ended: false,
  seq: 0,
  world: { ...INITIAL_WORLD },
  mirror: { ...INITIAL_WORLD },
  roundSnapshot: { ...INITIAL_WORLD },
  roundStartedAt: 0,
  hintIndex: 0,
  threatTimer: 0,
  steamPhase: 0,
  sfxLoops: {},
  markers: {},
  entityMoving: false,
  debug: {},
};

let gameRef = null;
let refScene = null;
let mirror = null;

/* rig：两侧场景里要摆弄的物件 */
const rig = {
  real: {},
  ref: {},
  targets: { real: {}, ref: {} },
  steam: { real: null, ref: null },
  glow: { real: null, ref: null },
  refLights: {},
  lightsBase: {},
  entity: { ref: null, real: null, refLight: null, realLight: null, target: new THREE.Vector3() },
  handles: {},
};

const V3 = (x = 0, y = 0, z = 0) => new THREE.Vector3(x, y, z);
const MIRROR_SFX_POS = V3(0, 1.5, -2.5);

/* ============================================================
 * 三、小工具
 * ============================================================ */

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function playSfx(key, opts = {}) {
  const a = gameRef && gameRef.audio;
  if (!a || !a.entries || !a.entries.sfx || !a.entries.sfx[key]) return null;
  return a.sfx(key, opts);
}

function stopLoop(key, fade = 0.6) {
  const h = state.sfxLoops[key];
  if (h) {
    try { h.stop(fade); } catch (e) { /* ignore */ }
    delete state.sfxLoops[key];
  }
}

function syncLoop(key, on, makeOpts) {
  const cur = state.sfxLoops[key];
  if (on && !cur) {
    const h = playSfx(key, Object.assign({ loop: true }, makeOpts ? makeOpts() : {}));
    if (h) state.sfxLoops[key] = h;
  } else if (!on && cur) {
    stopLoop(key);
  }
}

function getMarkerV(name) {
  if (!state.markers[name]) {
    const v = gameRef.getMarker(name);
    state.markers[name] = v ? v.clone() : null;
  }
  return state.markers[name];
}

function levelRoot(side) {
  return side === 'real' ? gameRef.level : refScene.getObjectByName('level');
}

function findIn(side, name) {
  return side === 'real' ? gameRef.find(name) : refScene.getObjectByName(name);
}

function canInteract() {
  return !!gameRef && gameRef.state === 'playing' && !state.busy && !state.dying && !state.ended;
}

function mirrorWorldPos() {
  return MIRROR_SFX_POS;
}

/* ============================================================
 * 四、场景装配
 * ============================================================ */

/** 给「原点被打包在世界坐标里」的物件（毛巾）套一个位于其中心的 pivot。 */
function makeCenterPivot(side, name) {
  const root = levelRoot(side);
  if (!root) return null;
  root.updateMatrixWorld(true);
  const obj = findIn(side, name);
  if (!obj) return null;
  const box = new THREE.Box3().setFromObject(obj);
  if (box.isEmpty()) return null;
  const center = box.getCenter(new THREE.Vector3());
  const pivot = new THREE.Group();
  pivot.name = `PIVOT_${name}_${side}`;
  root.add(pivot);
  pivot.position.copy(center);
  pivot.updateMatrixWorld(true);
  pivot.attach(obj);
  pivot.updateMatrixWorld(true);
  return { pivot, center };
}

function snapshotObject(obj) {
  if (!obj) return null;
  return { pos: obj.position.clone(), quat: obj.quaternion.clone() };
}

function setupRig() {
  for (const side of ['real', 'ref']) {
    const sideRig = rig[side];
    const towel = makeCenterPivot(side, 'INT_towel');
    sideRig.towel = towel;
    sideRig.stool01 = findIn(side, 'INT_stool_01');
    sideRig.stool02 = findIn(side, 'INT_stool_02');
    sideRig.mannequin = findIn(side, 'INT_mannequin');
    sideRig.valve = findIn(side, 'INT_valve');
    sideRig.locker = findIn(side, 'INT_locker_02');
    sideRig.movers = {
      towel: towel ? towel.pivot : null,
      stool01: sideRig.stool01,
      stool02: sideRig.stool02,
      mannequin: sideRig.mannequin,
    };
    sideRig.home = {
      towel: towel ? towel.center.clone() : V3(),
      stool01: snapshotObject(sideRig.stool01),
      stool02: snapshotObject(sideRig.stool02),
      mannequin: snapshotObject(sideRig.mannequin),
    };
    const t = rig.targets[side];
    t.towel = { pos: sideRig.home.towel.clone(), quat: new THREE.Quaternion() };
    t.stool01 = { pos: sideRig.home.stool01.pos.clone(), quat: sideRig.home.stool01.quat.clone() };
    t.stool02 = { pos: sideRig.home.stool02.pos.clone(), quat: sideRig.home.stool02.quat.clone() };
    t.mannequin = { pos: sideRig.home.mannequin.pos.clone(), quat: sideRig.home.mannequin.quat.clone() };
    t.valve = 0;
    t.locker = 0;
  }
}

/* ------------------------------------------------------------------
 * 镜面自检：engine/mirror.js 的 PlanarMirror 用世界包围盒中心求镜面位置、
 * 法线朝向相机。启动时检查一次，若引擎实现回归（镜面全黑）会在 console 报警。
 * ------------------------------------------------------------------ */
function verifyMirror(game) {
  const m = mirror;
  if (!m) return;
  try { m.update(game.time, 0); } catch (err) { console.warn('[mirror] 引擎镜面更新异常', err); return; }
  const mesh = m.mesh;
  const box = new THREE.Box3().setFromObject(mesh);
  const center = new THREE.Vector3();
  if (!box.isEmpty()) box.getCenter(center);
  const camPos = game.camera.getWorldPosition(new THREE.Vector3());
  const planeOk = m._mirrorPos.distanceTo(center) < 0.25;
  const normalOk = m._normal.dot(camPos.sub(center)) > 0;
  if (!planeOk || !normalOk) {
    console.warn('[mirror] 引擎镜面位置/法线异常，镜子可能全黑', {
      planeOk, normalOk, mirrorPos: m._mirrorPos.toArray(), center: center.toArray(),
    });
  }
}

function refLightNear(name) {
  const empty = gameRef.lights.get(name);
  if (!empty) return null;
  const p = empty.getWorldPosition(new THREE.Vector3());
  let best = null;
  let bestD = 1e9;
  refScene.traverse((o) => {
    if (!o.isLight) return;
    const d = o.position.distanceTo(p);
    if (d < bestD) { bestD = d; best = o; }
  });
  return bestD < 0.35 ? best : null;
}

function setupLights() {
  for (const name of ['LIGHT_tube_01', 'LIGHT_tube_02', 'LIGHT_bench', 'LIGHT_bath', 'LIGHT_window']) {
    const l = refLightNear(name);
    rig.refLights[name] = l;
    if (l) rig.lightsBase[name] = l.intensity;
  }
  // 镜中世界整体偏冷、雾更重
  refScene.traverse((o) => {
    if (o.isAmbientLight) {
      o.color.setHex(0x2c4240);
      o.intensity = 0.26;
    }
  });
  if (refScene.fog) refScene.fog.density = Math.max(0.05, (gameRef.config.fog.density || 0.05)) * 1.12;

  // 低照度补光：关灯回合里仍能看清路（两侧参数一致，镜内外观感一致）
  rig.fill = rig.fill || { real: null, ref: null };
  rig.mirrorLamp = rig.mirrorLamp || { real: null, ref: null };
  const fillReal = new THREE.PointLight(0x7f9a94, 0.6, 11, 1.25);
  fillReal.position.set(0, 2.7, 0.5);
  fillReal.visible = false;
  gameRef.scene.add(fillReal);
  const fillRef = new THREE.PointLight(0x7f9a94, 0.6, 11, 1.25);
  fillRef.position.set(0, 2.7, 0.5);
  fillRef.visible = false;
  refScene.add(fillRef);
  rig.fill.real = fillReal;
  rig.fill.ref = fillRef;
  // 镜前的一盏小灯：让镜面两侧的毛巾/人影看得清
  const lampReal = new THREE.PointLight(0xdcebe2, 0.55, 5, 1.4);
  lampReal.position.set(-1.1, 2.45, -2.15);
  gameRef.scene.add(lampReal);
  const lampRef = new THREE.PointLight(0xdcebe2, 0.55, 5, 1.4);
  lampRef.position.set(-1.1, 2.45, -2.15);
  refScene.add(lampRef);
  rig.mirrorLamp.real = lampReal;
  rig.mirrorLamp.ref = lampRef;
}

function setRefLight(name, on, scale = 1) {
  const l = rig.refLights[name];
  if (!l) return;
  const base = rig.lightsBase[name] == null ? l.intensity : rig.lightsBase[name];
  l.intensity = on ? base * scale : 0;
}

function applyRealLights(value) {
  const on = value === 'on';
  gameRef.setLight('LIGHT_tube_01', on, 1);
  gameRef.setLight('LIGHT_tube_02', on, 1);
  gameRef.setLight('LIGHT_bench', on, 1);
  gameRef.setLight('LIGHT_bath', true, on ? 0.85 : 2.2);
  gameRef.setLight('LIGHT_window', true, on ? 1.0 : 2.0);
  if (rig.fill && rig.fill.real) rig.fill.real.visible = !on;
}

function applyRefLights(value) {
  const on = value === 'on';
  setRefLight('LIGHT_tube_01', on, 1);
  setRefLight('LIGHT_tube_02', on, 1);
  setRefLight('LIGHT_bench', on, 1);
  setRefLight('LIGHT_bath', true, on ? 0.85 : 2.2);
  setRefLight('LIGHT_window', true, on ? 1.0 : 2.0);
  if (rig.fill && rig.fill.ref) rig.fill.ref.visible = !on;
}

/* 蒸汽：阀门开着时从阀门/台面上升起的水汽（两侧各一份） */
function makeSteam(root, pos) {
  const group = new THREE.Group();
  group.position.copy(pos);
  const tex = gameRef.textures ? gameRef.textures.get('MAT_steam') : null;
  const mat = new THREE.MeshBasicMaterial({
    color: 0xb9d2c8,
    transparent: true,
    opacity: 0.22,
    depthWrite: false,
    side: THREE.DoubleSide,
  });
  if (tex) mat.map = tex;
  for (let i = 0; i < 4; i++) {
    const w = 0.5 + Math.random() * 0.35;
    const h = 1.15 + Math.random() * 0.7;
    const plane = new THREE.Mesh(new THREE.PlaneGeometry(w, h), mat);
    plane.position.set((Math.random() - 0.5) * 0.5, 0.75 + i * 0.24, (Math.random() - 0.5) * 0.4);
    plane.rotation.y = Math.random() * Math.PI;
    group.add(plane);
  }
  group.visible = false;
  root.add(group);
  return group;
}

function makeRadioGlow(root, pos) {
  const group = new THREE.Group();
  group.position.copy(pos);
  const light = new THREE.PointLight(0xffb87a, 0.85, 2.6, 1.7);
  light.position.set(0, 0.16, 0);
  group.add(light);
  const bulb = new THREE.Mesh(
    new THREE.SphereGeometry(0.032, 6, 6),
    new THREE.MeshBasicMaterial({ color: 0xffd9a4 })
  );
  bulb.position.set(0, 0.1, 0);
  group.add(bulb);
  group.visible = false;
  root.add(group);
  return group;
}

function setupProps() {
  // 蒸汽放在洗手台右侧（阀门供的热水），这个位置在镜面反射里看得见
  const steamPos = V3(1.55, 0.4, -2.25);
  rig.steam.real = makeSteam(gameRef.scene, steamPos);
  rig.steam.ref = makeSteam(refScene, steamPos);
  const radioPos = V3(0.47, 0.98, 0.42);
  rig.glow.real = makeRadioGlow(gameRef.scene, radioPos);
  rig.glow.ref = makeRadioGlow(refScene, radioPos);
}

function setupEntity() {
  const refEntity = refScene.getObjectByName('ENTITY_reflection');
  if (refEntity) {
    refEntity.visible = true;
    refEntity.position.copy(ENTITY_STEPS[0]);
    refEntity.rotation.y = Math.PI; // 面朝镜面（玩家看见它的正面）
    rig.entity.ref = refEntity;
  }
  const realEntity = gameRef.entities.get('ENTITY_reflection');
  if (realEntity) {
    realEntity.visible = false;
    realEntity.position.copy(ENTITY_STEPS[0]);
    realEntity.rotation.y = 0;
    rig.entity.real = realEntity;
  }
  const refLight = new THREE.PointLight(0xcfe0d8, 0.75, 4.2, 1.6);
  refLight.position.set(0, 2.0, 2.4);
  refScene.add(refLight);
  rig.entity.refLight = refLight;
  const realLight = new THREE.PointLight(0xcfe0d8, 1.1, 5.5, 1.5);
  realLight.position.set(0, 2.0, 0);
  realLight.visible = false;
  gameRef.scene.add(realLight);
  rig.entity.realLight = realLight;
  rig.entity.target.copy(ENTITY_STEPS[0]);
}

/* ============================================================
 * 五、状态应用（现实 / 镜中）
 * ============================================================ */

function setTowelTarget(side, value) {
  const t = rig.targets[side];
  const home = rig[side].home.towel;
  if (value === 'hook') {
    // MARK_towel_hook 在镜子左侧墙（x=-2.55），那块位置在镜面反射里看不到；
    // 把它夹进镜面可见范围，表现成「搭在镜框左上角」。
    const hook = getMarkerV('MARK_towel_hook') || V3(-2.55, 1.55, -2.68);
    const x = clamp(hook.x, -1.75, 1.75);
    t.towel.pos.set(x, 2.35 - 0.32, -2.6);
    t.towel.quat.setFromEuler(new THREE.Euler(Math.PI / 2, 0.1, 0.06, 'YXZ'));
  } else {
    t.towel.pos.copy(home);
    t.towel.quat.identity();
  }
}

function setStool01Target(side, value) {
  const t = rig.targets[side];
  if (value === 'bench') {
    t.stool01.pos.set(-0.18, 0.48, 0.4);
    t.stool01.quat.setFromEuler(new THREE.Euler(0, 0.85, 0));
  } else {
    t.stool01.pos.copy(rig[side].home.stool01.pos);
    t.stool01.quat.copy(rig[side].home.stool01.quat);
  }
}

function setStool02Target(side, value) {
  const t = rig.targets[side];
  if (value === 'away') {
    // MARK_stool_away 在洗手台下方（会被台体挡住），往外挪到镜子正前方才看得见
    const away = getMarkerV('MARK_stool_away') || V3(0, 0, -2.35);
    t.stool02.pos.set(away.x, 0, Math.max(away.z + 0.95, -1.55));
    t.stool02.quat.setFromEuler(new THREE.Euler(0, 0.6, 0));
  } else {
    t.stool02.pos.copy(rig[side].home.stool02.pos);
    t.stool02.quat.copy(rig[side].home.stool02.quat);
  }
}

function setMannequinTarget(side, value) {
  const t = rig.targets[side];
  if (value === 'mirror') {
    // 站到镜子正前方，面朝镜面（这样在镜中可见，且现实里能看到它的背）
    t.mannequin.pos.set(1.35, 0, -1.3);
    t.mannequin.quat.setFromEuler(new THREE.Euler(0, Math.PI + 0.08, 0));
  } else {
    t.mannequin.pos.copy(rig[side].home.mannequin.pos);
    t.mannequin.quat.copy(rig[side].home.mannequin.quat);
  }
}

function syncLoops() {
  if (!gameRef || gameRef.state !== 'playing') return;
  syncLoop('waterStream', state.world.valve === 'open', () => ({ volume: 0.55, pos: V3(2.4, 1.0, -2.4) }));
  syncLoop('radioStatic', state.world.radio === 'on', () => ({ volume: 0.42, pos: V3(0.47, 0.9, 0.42) }));
  syncLoop('waterStreamMirror', state.mirror.valve === 'open', () => ({ volume: 0.16, pos: mirrorWorldPos() }));
  syncLoop('radioStaticMirror', state.mirror.radio === 'on' && state.world.radio !== 'on', () => ({ volume: 0.14, pos: mirrorWorldPos() }));
  syncLoop('doppelBreath', state.steps >= 2, () => ({ volume: Math.min(0.5, 0.08 + state.steps * 0.08), pos: mirrorWorldPos() }));
}

function applyRealRadio(value) {
  const on = value === 'on';
  if (rig.glow.real) rig.glow.real.visible = on;
  syncLoops();
}

function applyRefRadio(value) {
  const on = value === 'on';
  if (rig.glow.ref) rig.glow.ref.visible = on;
  syncLoops();
}

function applyValveVisual(side, value) {
  const on = value === 'open';
  if (rig.steam[side]) rig.steam[side].visible = on;
}

function applySide(side, key, value) {
  const t = rig.targets[side];
  switch (key) {
    case 'towel': setTowelTarget(side, value); break;
    case 'stool01': setStool01Target(side, value); break;
    case 'stool02': setStool02Target(side, value); break;
    case 'mannequin': setMannequinTarget(side, value); break;
    case 'valve':
      t.valve = value === 'open' ? -1.75 : 0;
      applyValveVisual(side, value);
      if (side === 'real') syncLoops();
      else syncLoops();
      break;
    case 'locker':
      t.locker = value === 'open' ? (100 * Math.PI) / 180 : 0;
      break;
    case 'lights':
      if (side === 'real') applyRealLights(value); else applyRefLights(value);
      break;
    case 'radio':
      if (side === 'real') applyRealRadio(value); else applyRefRadio(value);
      break;
    default: break;
  }
}

function snapSide(side) {
  const t = rig.targets[side];
  for (const key of ['towel', 'stool01', 'stool02', 'mannequin']) {
    const node = rig[side].movers[key];
    const target = t[key];
    if (!node || !target) continue;
    node.position.copy(target.pos);
    node.quaternion.copy(target.quat);
  }
  if (rig[side].valve) rig[side].valve.rotation.z = t.valve || 0;
  if (rig[side].locker) rig[side].locker.rotation.y = t.locker || 0;
}

function applyAll(side, states, snap = true) {
  for (const key of Object.keys(INITIAL_WORLD)) applySide(side, key, states[key]);
  if (snap) snapSide(side);
}

/* ============================================================
 * 六、交互
 * ============================================================ */

function updatePrompt(key) {
  const h = rig.handles[key];
  if (!h) return;
  const p = PROMPT[key] && PROMPT[key][state.world[key]];
  if (p) h.setPrompt(p);
}

function registerInteractions() {
  const add = (name, key) => {
    const obj = findIn('real', name);
    if (!obj) { console.warn('[mirror] 交互物缺失：', name); return null; }
    const handle = gameRef.interact.add(obj, {
      prompt: (PROMPT[key] && PROMPT[key][state.world[key]]) || '查看',
      range: 3.0,
      onUse: () => onUseObject(key),
    });
    rig.handles[key] = handle;
    return handle;
  };

  add('INT_towel', 'towel');
  add('INT_valve', 'valve');
  add('INT_switch', 'lights');
  add('INT_locker_02', 'locker');
  add('INT_radio', 'radio');
  add('INT_mannequin', 'mannequin');
  add('INT_stool_01', 'stool01');
  add('INT_stool_02', 'stool02');

  // 挂钟：只是看，不计错误
  const clock = gameRef.find('INT_clock');
  if (clock) {
    gameRef.interact.add(clock, {
      prompt: '看钟',
      range: 3.2,
      onUse: () => onLookClock(),
    });
  }

  // 镜面本身：可以摸，不计错误（但会得到提示 / 更近一步的幻觉）
  const surface = gameRef.find('MIRROR_surface');
  if (surface) {
    gameRef.interact.add(surface, {
      prompt: '摸一摸镜面',
      range: 2.6,
      onUse: () => onTouchMirror(),
    });
  }

  for (const key of Object.keys(PROMPT)) updatePrompt(key);
}

function playKeySfx(key, value) {
  switch (key) {
    case 'towel': playSfx('towelPick', { volume: 0.7, pos: V3(-1.0, 1.2, -1.5) }); break;
    case 'valve': playSfx('valveTurn', { volume: 0.85, pos: V3(2.4, 1.2, -2.5) }); break;
    case 'lights':
      playSfx('switchClick', { volume: 0.75 });
      playSfx('lightFlicker', { volume: 0.5, rate: 0.9 + Math.random() * 0.2 });
      break;
    case 'radio':
      if (value === 'on') playSfx('radioOn', { volume: 0.8, pos: V3(0.47, 0.8, 0.42) });
      else playSfx('switchClick', { volume: 0.6 });
      break;
    case 'locker': playSfx('lockerCreak', { volume: 0.85, pos: V3(-2.4, 1.0, 2.3) }); break;
    case 'mannequin': playSfx('stoolDrag', { volume: 0.55, rate: 0.7, pos: V3(3.0, 0.8, 1.6) }); break;
    case 'stool01':
    case 'stool02': playSfx('stoolDrag', { volume: 0.8, pos: V3(0.5, 0.4, -0.2) }); break;
    default: break;
  }
}

function onUseObject(key) {
  if (!canInteract()) return;
  const prev = state.world[key];
  const next = NEXT_STATE[key][prev];
  if (!next) return;
  state.world[key] = next;
  applySide('real', key, next);
  updatePrompt(key);
  playKeySfx(key, next);

  const def = ROUNDS[state.round];
  const relevant = Object.prototype.hasOwnProperty.call(def.target, key);
  if (!relevant) {
    gameRef.ui.subtitle('镜子里，没有跟着动。', 2.0);
    penalty('invalid');
    return;
  }
  if (state.world[key] === state.mirror[key]) {
    if (allAligned()) {
      completeRound();
    } else {
      gameRef.ui.subtitle('有一处对上了。', 1.8);
      mirror && mirror.glitchPulse(0.18);
    }
  } else {
    penalty('wrong');
  }
}

function allAligned() {
  const def = ROUNDS[state.round];
  return Object.entries(def.target).every(([k, v]) => state.world[k] === v);
}

function onLookClock() {
  if (!canInteract()) return;
  playSfx('clockTick', { volume: 0.5, loop: false });
  const lines = [
    '三点十七分。镜子里那面钟，秒针一直没动。',
    '钟停了。可你还是能听见秒针在走——从镜子那边。',
    '分针和时针都指着你。',
  ];
  gameRef.ui.subtitle(lines[Math.min(state.steps, lines.length - 1)], 3.4);
}

function onTouchMirror() {
  if (!canInteract()) return;
  if (mirror) mirror.glitchPulse(0.55);
  playSfx('mirrorTouch', { volume: 0.8, pos: mirrorWorldPos() });
  const lines = [
    '镜面比水还凉。你的手，在里面慢了一点点。',
    '里面的人也在摸。他的手比你的大。',
    '他贴上来。玻璃后面，一点温度都没有。',
    '你摸到的不是玻璃。是另一只手。',
  ];
  gameRef.ui.subtitle(lines[Math.min(state.steps, lines.length - 1)], 3.2);
  if (state.steps >= 3) {
    if (mirror) mirror.glitchPulse(0.35);
  }
}

/* ============================================================
 * 七、镜中身影 / 惩罚 / 死亡
 * ============================================================ */

function applyEntityStep(step, animate = false) {
  const idx = clamp(step, 0, ENTITY_STEPS.length - 1);
  rig.entity.target.copy(ENTITY_STEPS[idx]);
  state.entityMoving = !!animate;
  const e = rig.entity.ref;
  if (e) {
    e.scale.setScalar(1 + step * 0.022);
    if (!animate) e.position.copy(rig.entity.target);
  }
  syncLoops();
}

function penalty(kind) {
  if (state.dying || state.ended) return;
  state.mistakes += 1;
  state.steps += 1;
  updateHudDanger();
  applyEntityStep(state.steps, true);
  if (mirror) mirror.glitchPulse(0.55 + state.steps * 0.12);
  playSfx('stinger', { volume: 0.55, rate: 0.95 + Math.random() * 0.1 });
  playSfx('doppelStep', { volume: 0.95, pos: mirrorWorldPos() });
  playSfx('whisper', { volume: 0.5, pos: mirrorWorldPos() });
  const text = kind === 'invalid'
    ? '镜子里的人，往前挪了一步。'
    : '它看见你动错了。它又近了一步。';
  gameRef.ui.subtitle(text, 2.6);
  flickerTube();
  if (state.steps >= 5) triggerDeath();
}

function flickerTube() {
  if (state.world.lights !== 'on') return;
  gameRef.setLight('LIGHT_tube_01', false);
  setTimeout(() => {
    if (gameRef.state === 'playing' && state.world.lights === 'on') {
      gameRef.setLight('LIGHT_tube_01', true, 1);
      if (Math.random() < 0.6) {
        gameRef.setLight('LIGHT_tube_02', false);
        setTimeout(() => {
          if (gameRef.state === 'playing' && state.world.lights === 'on') gameRef.setLight('LIGHT_tube_02', true, 1);
        }, 140);
      }
    }
  }, 110);
}

function triggerDeath() {
  if (state.dying || state.ended) return;
  state.dying = true;
  state.busy = true;
  state.ended = true;
  gameRef.player.enabled = false;
  gameRef.ui.clearSubtitles();
  gameRef.ui.setObjective(null);
  applyEntityStep(5, false);
  if (mirror) mirror.glitchPulse(2.5);
  gameRef.setThreat(1);
  gameRef.setSanity(1);
  playSfx('doppelBreath', { volume: 1, pos: mirrorWorldPos() });
  playSfx('stinger', { volume: 1 });
  playSfx('whisper', { volume: 0.95, pos: mirrorWorldPos() });
  gameRef.ui.subtitle('它到你背后了。', 2.0);
  gameRef.audio.stopAll(1.6);
  setTimeout(() => {
    try { gameRef.fail(TEXTS.death); } catch (e) { console.error(e); }
  }, 1900);
}

/* ============================================================
 * 八、回合流程
 * ============================================================ */

function updateHudDanger() {
  gameRef.setSanity(clamp(state.steps * 0.16 + (state.completed >= 2 ? 0.08 : 0), 0, 1));
}

function startRound(index, mySeq) {
  state.round = index;
  primeMirrorRound(index);
  state.roundSnapshot = { ...state.world };
  state.roundStartedAt = state.t;
  state.hintIndex = 0;
  gameRef.ui.setObjective('让镜中的房间与现实一致');
  gameRef.ui.setCounter(`对齐 ${state.completed} / 3`);
  gameRef.ui.subtitle(ROUNDS[index].intro, 4.4);
  syncLoops();
  if (mySeq === undefined) state.seq += 1;
}

/** 把某一回合的「镜中目标状态」写进反射场景（黑屏期间直接切换） */
function primeMirrorRound(index) {
  const def = ROUNDS[index];
  for (const [k, v] of Object.entries(def.target)) state.mirror[k] = v;
  for (const key of Object.keys(INITIAL_WORLD)) applySide('ref', key, state.mirror[key]);
  snapSide('ref');
  syncLoops();
}

async function completeRound() {
  if (state.busy || state.dying || state.ended) return;
  state.busy = true;
  state.seq += 1;
  const mySeq = state.seq;
  state.completed += 1;
  state.steps += 1;
  updateHudDanger();
  gameRef.player.enabled = false;
  gameRef.ui.clearSubtitles();
  gameRef.ui.setObjective('对齐了。');
  playSfx('blackout', { volume: 0.9 });
  if (mirror) mirror.glitchPulse(1.5);
  gameRef.ui.subtitle('全都对上了。', 2.0);
  updateMusic();
  await gameRef.ui.fade(1, 700);
  if (mySeq !== state.seq) return;
  applyEntityStep(state.steps, false);
  playSfx('doppelStep', { volume: 1, pos: mirrorWorldPos() });
  playSfx('whisper', { volume: 0.7, pos: mirrorWorldPos() });
  await sleep(850);
  if (mySeq !== state.seq) return;
  if (state.completed >= 3) {
    await endingSequence(mySeq);
    return;
  }
  startRound(state.completed, mySeq);
  await sleep(750);
  if (mySeq !== state.seq) return;
  gameRef.player.enabled = true;
  state.busy = false;
  gameRef.ui.fadeOut(1100);
  gameRef.ui.subtitle(`镜子里的房间，又变了。对齐 ${state.completed} / 3。`, 3.6);
}

function updateMusic() {
  const a = gameRef && gameRef.audio;
  if (!a || !a.ready) return;
  if (state.steps >= 3 && state.completed < 3) a.playMusic('tension', { fade: 2.2 });
  else a.playMusic('main', { fade: 3.5 });
}

function syncAudio() {
  const a = gameRef && gameRef.audio;
  if (!a) return;
  updateMusic();
  if (!a.ready) return;
  a.playAmbience('fluorescent', { channel: 'main', fade: 2.2 });
  a.playAmbience('waterDrip', { channel: 'extra', fade: 2.2, volume: 0.6 });
  a.playAmbience('distantWater', { channel: 'far', fade: 2.2, volume: 0.45 });
  syncLoops();
}

/* ============================================================
 * 九、结局
 * ============================================================ */

async function whiteFlash(count = 2) {
  const el = document.getElementById('mirror-flash');
  if (!el) return;
  const pulses = [
    { cls: 'on', ms: 70 },
    { cls: '', ms: 90 },
    { cls: 'soft', ms: 60 },
    { cls: '', ms: 110 },
  ];
  for (let i = 0; i < count; i++) {
    for (const p of pulses) {
      el.className = p.cls;
      await sleep(p.ms);
    }
  }
  el.className = '';
}

function showRealEntity() {
  const e = rig.entity.real;
  if (!e) return;
  e.visible = true;
  e.position.set(0.05, 0, -1.05);
  e.rotation.set(0, 0, 0);
  e.scale.setScalar(1.06);
  rig.entity.realLight.visible = true;
  rig.entity.realLight.position.set(0.0, 2.0, -0.8);
  gameRef.setLight('LIGHT_bath', true, 0.9);
  gameRef.setLight('LIGHT_window', true, 0.9);
}

async function endingSequence(mySeq) {
  if (state.ended) return;
  state.ended = true;
  state.busy = true;
  gameRef.player.enabled = false;
  gameRef.ui.clearSubtitles();
  gameRef.ui.setObjective(null);
  gameRef.ui.setCounter('');
  updateMusic();

  // 黑场结束前把玩家摆到镜子正前方
  gameRef.player.teleportToPos(V3(0, 0, 1.35), V3(0, 1.7, -2.74));
  applyEntityStep(5, false);
  if (mirror) mirror.glitchPulse(1.6);
  playSfx('doppelStep', { volume: 1, pos: mirrorWorldPos() });
  await gameRef.ui.fadeOut(1300);
  if (mySeq !== state.seq) return;
  gameRef.ui.subtitle('镜子里的人，把手贴在了玻璃上。', 4.0);
  await sleep(2000);
  if (mySeq !== state.seq) return;

  // 玻璃裂开
  if (mirror) mirror.glitchPulse(2.5);
  playSfx('glassCrack', { volume: 1, pos: mirrorWorldPos() });
  playSfx('stinger', { volume: 0.8 });
  await whiteFlash(2);
  gameRef.setSanity(1);
  gameRef.setThreat(1);

  // 它从镜子里走出来
  showRealEntity();
  playSfx('doppelBreath', { volume: 0.9, pos: V3(0, 1.4, -1.0) });
  playSfx('whisper', { volume: 0.9, pos: V3(0, 1.4, -1.0) });
  gameRef.ui.subtitle('它从镜子里走了出来，站到你面前。', 4.6);
  if (mirror) mirror.glitchPulse(1.2);
  await sleep(2400);
  if (mySeq !== state.seq) return;

  gameRef.audio.stopAll(2.5);
  if (gameRef.audio.entries.music.ending) gameRef.audio.playMusic('ending', { fade: 1.5 });
  await sleep(1200);
  await gameRef.ui.fade(1, 1100);
  await sleep(350);
  gameRef.finish(TEXTS.ending);
  // 黑幕在结局页之上，必须淡出才能看到结局页
  await sleep(120);
  gameRef.ui.fade(0, 1400);
}

/* ============================================================
 * 十、每帧更新
 * ============================================================ */

function updateTransforms(dt) {
  const k = 1 - Math.exp(-7 * dt);
  for (const side of ['real', 'ref']) {
    const movers = rig[side].movers;
    const t = rig.targets[side];
    for (const key of ['towel', 'stool01', 'stool02', 'mannequin']) {
      const node = movers[key];
      const target = t[key];
      if (!node || !target) continue;
      node.position.lerp(target.pos, k);
      node.quaternion.slerp(target.quat, k);
    }
    if (rig[side].valve) {
      rig[side].valve.rotation.z += (t.valve - rig[side].valve.rotation.z) * k;
    }
    if (rig[side].locker) {
      rig[side].locker.rotation.y += (t.locker - rig[side].locker.rotation.y) * k;
    }
  }
}

function updateSteam(dt) {
  state.steamPhase += dt;
  for (const side of ['real', 'ref']) {
    const g = rig.steam[side];
    if (!g || !g.visible) continue;
    g.children.forEach((m, i) => {
      m.position.y = 0.7 + i * 0.26 + Math.sin(state.steamPhase * 0.85 + i * 1.7) * 0.14;
      m.rotation.y += dt * (0.18 + i * 0.05);
      if (m.material) m.material.opacity = 0.14 + 0.1 * (0.5 + 0.5 * Math.sin(state.steamPhase * 1.1 + i));
    });
  }
}

function updateEntity(dt) {
  const e = rig.entity;
  const refEntity = e.ref;
  if (!refEntity) return;
  const k = 1 - Math.exp(-3.2 * dt);
  refEntity.position.lerp(e.target, k);
  refEntity.position.y = Math.sin(state.t * 1.15) * 0.012;
  refEntity.rotation.y = Math.PI + Math.sin(state.t * 0.55) * 0.045;
  state.entityMoving = refEntity.position.distanceTo(e.target) > 0.03;
  if (e.refLight) {
    e.refLight.position.set(refEntity.position.x * 0.7, 2.05, refEntity.position.z + 0.35);
  }
  if (e.real && e.real.visible && e.realLight) {
    e.realLight.position.set(e.real.position.x, 2.0, e.real.position.z + 0.4);
  }
  // 走近的脚步
  if (state.entityMoving) {
    state._stepTimer = (state._stepTimer || 0) - dt;
    if (state._stepTimer <= 0) {
      state._stepTimer = 0.42;
      playSfx('doppelStep', { volume: 0.7, pos: mirrorWorldPos(), rate: 0.92 + Math.random() * 0.12 });
    }
  }
}

function updateThreat(dt) {
  state.threatTimer -= dt;
  if (state.threatTimer > 0) return;
  state.threatTimer = 0.2;
  const p = gameRef.player.pos;
  const nearMirror = Math.hypot(p.x - 0, p.z + 2.2) < 2.8;
  let threat = 0.1 + state.steps * 0.15;
  if (nearMirror) threat += 0.1;
  if (state.entityMoving) threat += 0.12;
  gameRef.setThreat(clamp(threat, 0, 1));
  updateHudDanger();
}

function updateHints() {
  if (state.busy || state.dying || state.ended) return;
  const def = ROUNDS[state.round];
  const since = state.t - state.roundStartedAt;
  if (state.hintIndex < 1 && since > 38) {
    state.hintIndex = 1;
    gameRef.ui.subtitle(def.hint, 5.5);
  } else if (state.hintIndex < 2 && since > 82) {
    state.hintIndex = 2;
    gameRef.ui.subtitle('再站到镜子前面，看它和这边差在哪里。', 4.5);
  }
}

/* ============================================================
 * 十一、配置
 * ============================================================ */

const config = {
  id: 'mirror',
  title: '镜中',
  chapter: '二更 · MIRROR',
  titleEn: 'IN THE MIRROR',
  poster: '../../assets/art/poster-mirror.jpg',
  warning: '本作包含心理恐怖、闪烁画面、幽闭空间与死亡意象，没有血腥画面。建议戴耳机，在安静、光线较暗的环境游玩。',
  homeUrl: '../../index.html',
  model: '../../assets/models/mirror.glb',
  textures: '../../assets/textures/manifest.json',
  audio: '../../assets/audio/mirror/manifest.json',
  footstepSfx: 'stepTile',
  flashlight: null,
  ambient: { color: 0x2a3330, intensity: 0.3 },
  fog: { color: 0x070a09, density: 0.05 },
  theme: { accent: '#9fb0a8', ink: '#d8d2c0', bg: '#060807' },
  playerStart: { spawn: 'SPAWN_mirror', look: 'LOOK_mirror' },
  renderScale: 0.6,

  async setup(game) {
    gameRef = game;
    // 1. 反射场景：同一间更衣室的克隆（灯光/雾/环境光都带走）
    refScene = game.createReflectionScene();
    // 2. 镜面实时反射
    mirror = game.createMirror('MIRROR_surface', {
      scene: refScene,
      tint: 0xe2ece6,
      grimeStrength: 0.28,
      resolutionScale: 0.55,
    });
    if (!mirror) console.warn('[mirror] 镜面创建失败');
    else {
      // 镜面暗角压低一点，让镜中的另一间房 clearer
      if (mirror.uniforms && mirror.uniforms.uVignette) mirror.uniforms.uVignette.value = 0.18;
      verifyMirror(game);
    }

    // 3. 两侧物件的引用与初始状态
    setupRig();
    setupLights();
    setupProps();
    setupEntity();
    registerInteractions();

    state.world = { ...INITIAL_WORLD };
    state.mirror = { ...INITIAL_WORLD };
    applyAll('real', state.world, true);
    applyAll('ref', state.mirror, true);
    applyEntityStep(0, false);
    gameRef.ui.setObjective(null);
    gameRef.ui.setCounter('');
  },

  start(game) {
    gameRef = game;
    state.t = 0;
    state.round = 0;
    state.completed = 0;
    state.steps = 0;
    state.mistakes = 0;
    state.busy = false;
    state.dying = false;
    state.ended = false;
    state.seq += 1;
    state.hintIndex = 0;
    state.threatTimer = 0;
    state.world = { ...INITIAL_WORLD };
    state.mirror = { ...INITIAL_WORLD };
    state.roundSnapshot = { ...INITIAL_WORLD };

    // 现实场景复位
    applyAll('real', state.world, true);
    applyAll('ref', state.mirror, true);
    // 第一回合的镜中差异（开局就要在镜子里看得见）
    primeMirrorRound(0);
    state.roundSnapshot = { ...state.world };
    state.roundStartedAt = 0;
    for (const key of Object.keys(PROMPT)) updatePrompt(key);
    applyEntityStep(0, false);
    if (rig.entity.ref) rig.entity.ref.visible = true;
    if (rig.entity.real) rig.entity.real.visible = false;
    if (rig.entity.realLight) rig.entity.realLight.visible = false;

    game.player.enabled = true;
    game.player.teleportTo('SPAWN_mirror', 'LOOK_mirror');
    game.ui.setHudVisible(true);
    game.ui.setObjective('让镜中的房间与现实一致');
    game.ui.setCounter('对齐 0 / 3');
    game.ui.clearSubtitles();
    game.setThreat(0.1);
    game.setSanity(0);
    syncAudio();
    playSfx('mirrorTouch', { volume: 0.35, pos: mirrorWorldPos() });

    state.roundStartedAt = 0;
    game.ui.subtitle('澡堂早该关门了。更衣室的灯还亮着。', 4.2);
    setTimeout(() => {
      if (game.state === 'playing' || game.state === 'paused') {
        game.ui.subtitle('镜子擦得很干净。可镜子里的房间，好像不是这一间。', 4.8);
      }
    }, 4600);
    setTimeout(() => {
      if (game.state === 'playing' || game.state === 'paused') {
        game.ui.subtitle('镜子里，有人比你早到。', 3.6);
      }
    }, 9600);
  },

  update(game, dt) {
    state.t += dt;
    try {
      updateTransforms(dt);
      updateSteam(dt);
      updateEntity(dt);
      updateThreat(dt);
      updateHints();
    } catch (err) {
      console.error('mirror update 错误', err);
    }
  },

  respawn(game) {
    gameRef = game;
    state.busy = false;
    state.dying = false;
    state.ended = false;
    state.seq += 1;
    state.steps = state.completed;
    state.mistakes = 0;
    state.hintIndex = 0;
    state.entityMoving = false;
    state.sfxLoops = {};

    state.world = { ...state.roundSnapshot };
    applyAll('real', state.world, true);
    applyAll('ref', state.mirror, true);
    for (const key of Object.keys(PROMPT)) updatePrompt(key);

    applyEntityStep(state.steps, false);
    if (rig.entity.ref) rig.entity.ref.visible = true;
    if (rig.entity.real) rig.entity.real.visible = false;
    if (rig.entity.realLight) rig.entity.realLight.visible = false;

    game.player.enabled = true;
    game.player.teleportTo('SPAWN_mirror', 'LOOK_mirror');
    game.ui.setHudVisible(true);
    game.ui.setObjective('让镜中的房间与现实一致');
    game.ui.setCounter(`对齐 ${state.completed} / 3`);
    game.ui.clearSubtitles();
    game.setThreat(0.1 + state.steps * 0.15);
    game.setSanity(state.steps * 0.16);
    updateMusic();
    syncAudio();
    game.ui.subtitle('你还在原地。它还在镜子里。', 3.2);
  },

  onFail(game) {
    // 引擎已停止输入；保留镜面故障画面
    if (mirror) mirror.glitchPulse(1.2);
  },

  onFinish(game) {
    // 结局页要保留 ending 音乐（QA P2：之前 stopAll 会把刚起的结局曲停掉）。
    // 只收掉心跳/呼吸/环境这些仍在跑的危险层。
    try {
      const a = game.audio;
      if (!a) return;
      a.setThreat(0);
      a.stopAmbience('extra', 2);
      a.stopAmbience('far', 2);
      if (a.heartbeat) { a.heartbeat.stop(1.5); a.heartbeat = null; }
      if (a.breath) { a.breath.stop(1.5); a.breath = null; }
    } catch (e) { /* ignore */ }
  },
};

/* ============================================================
 * 十二、启动 + 调试入口
 * ============================================================ */

const game = new HorrorGame(config);

game.load().then(() => {
  window.__MIRROR__ = {
    game,
    state,
    /** 传送到世界坐标 (x,z) */
    teleport(x, z) {
      game.player.pos.set(x, 0, z);
      game.player._syncCamera(0, true);
    },
    /** 转头看向世界坐标 (x,z)，y 默认 1.4 */
    face(x, z, y = 1.4) {
      game.player.lookAt(new THREE.Vector3(x, y, z));
      game.player._syncCamera(0, true);
    },
    /** QA / 自测用 */
    debug: {
      set(key, value) {
        if (!(key in INITIAL_WORLD)) return;
        state.world[key] = value;
        applySide('real', key, value);
        snapSide('real');
        updatePrompt(key);
      },
      setMirror(key, value) {
        if (!(key in INITIAL_WORLD)) return;
        state.mirror[key] = value;
        applySide('ref', key, value);
        snapSide('ref');
      },
      solveRound() {
        const def = ROUNDS[state.round];
        for (const [k, v] of Object.entries(def.target)) {
          state.world[k] = v;
          applySide('real', k, v);
          snapSide('real');
          updatePrompt(k);
        }
        completeRound();
      },
      nextRound() {
        if (!state.busy && !state.dying && !state.ended) completeRound();
      },
      steps(n) {
        state.steps = n;
        applyEntityStep(n, false);
        updateHudDanger();
      },
      mistakes(n) {
        state.mistakes = n;
        state.steps = state.completed + n;
        applyEntityStep(state.steps, false);
      },
      death() {
        state.steps = 4;
        penalty('debug');
      },
      ending() {
        if (state.ended) return;
        state.completed = 3;
        state.steps = Math.max(3, state.steps);
        endingSequence(++state.seq);
      },
      round() { return state.round; },
      /** 跳到第 i 回合（0..2），便于 QA 冒烟 */
      jump(i) {
        const idx = Math.max(0, Math.min(ROUNDS.length - 1, i | 0));
        state.completed = idx;
        state.steps = idx;
        state.mistakes = 0;
        state.busy = false;
        state.dying = false;
        state.ended = false;
        state.world = { ...INITIAL_WORLD };
        state.mirror = { ...INITIAL_WORLD };
        for (let r = 0; r < idx; r++) {
          for (const [k, v] of Object.entries(ROUNDS[r].target)) {
            state.world[k] = v;
            state.mirror[k] = v;
          }
        }
        applyAll('real', state.world, true);
        startRound(idx);
        game.ui.setCounter(`对齐 ${state.completed} / 3`);
        game.ui.setObjective('让镜中的房间与现实一致');
        game.player.teleportTo('SPAWN_mirror', 'LOOK_mirror');
        game.ui.fadeOut(700);
        return state.round;
      },
      info() {
        return {
          round: state.round,
          completed: state.completed,
          steps: state.steps,
          busy: state.busy,
          dying: state.dying,
          ended: state.ended,
          world: { ...state.world },
          mirror: { ...state.mirror },
          target: { ...ROUNDS[state.round].target },
          gameState: game.state,
          audioReady: !!(game.audio && game.audio.ready),
          mirrorReady: !!mirror,
        };
      },
    },
  };
  // 方便 QA 直接读
  window.__SANGENG__ = game;
}).catch((err) => {
  console.error('加载失败', err);
  const div = document.createElement('div');
  div.style.cssText = 'position:fixed;inset:0;z-index:999;background:#000;color:#9fb0a8;font:14px/1.8 monospace;padding:40px;white-space:pre-wrap;';
  div.textContent = '《镜中》加载失败：\n' + (err && err.stack ? err.stack : err);
  document.body.appendChild(div);
});
