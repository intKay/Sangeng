/* 《夜路》—— 三更 · 三更。共享引擎 + 本作玩法。
 *
 * 玩法：
 *  - 沿乡道向土地庙走，点亮五盏灯笼（E）。每盏灯是重生点，并让纸人定身 6 秒。
 *  - 纸人只在你没看它时移动；看向它时它静止。连续注视约 2.5 秒 → 夺灯（最近已点亮的灯熄灭 + 理智下降）。
 *  - 被纸人碰到（< 1.0m 且视线通畅）→ 死亡，重试回到上一盏已点亮的灯。
 *  - 五盏灯全亮后到土地庙上香；然后选择「按 E 回头」或「按 W 继续向前」，两种结局。
 */
import * as THREE from 'three';
import { HorrorGame } from '../../engine/engine.js';
import { clamp, damp } from '../../engine/utils.js';

/* ================= 文本 ================= */
const OBJECTIVE = {
  lanterns: '点亮沿途的五盏灯笼',
  shrine: '到土地庙上香',
  choose: '回头看 —— 或者继续向前',
};

const LANTERN_LINES = [
  '火折子一亮，纸罩里就有了暖。',
  '你想起出殡那天，棺木轻得不像话。',
  '风从稻田那边过来。你听见身后有纸响。',
  '火苗立着，一动不动。',
  '最后一盏。前面就是土地庙了。',
];

const DEATH_TEXT = '纸贴上了你的背。很轻，也很凉。';

const ENDING_LOOK = {
  title: '你回头了',
  lines: [
    '它站在一步之外。纸做的脸被夜露打湿，墨线往下淌。',
    '你认得这身衣裳。送葬那天，走在最后的人穿的就是它。',
    '它抬起手，把一张纸放进你的掌心。',
    '纸上写着你的名字。墨还没有干。',
  ],
};

const ENDING_WALK = {
  title: '你没有回头',
  lines: [
    '你没有回头。身后的脚步声一直跟着，和你一样快。',
    '你数着路边的灯笼：五盏，都亮着。',
    '走到村口的时候，鸡叫了。',
    '第二天，土地庙的香炉边多了一盏没点亮的灯笼。',
    '香灰上有一行脚印，朝着你回家的方向。',
  ],
};

/* ================= 运行状态 ================= */
const SHRINE_POS = new THREE.Vector3(0, 0, 97.4);
const SPAWN_POS = new THREE.Vector3(0, 0, -1.2);

const state = {
  game: null,
  phase: 'walk',            // walk | incense | decision | ending
  t: 0,
  threat: 0,
  sanityPenalty: 0,
  calm: 0,
  litCount: 0,
  lastSafeIndex: -1,
  lanterns: [],
  safeSpots: [],
  incenseHandles: [],
  incenseDone: false,
  allLit: false,
  ending: false,
  timers: [],
  hints: {},
  ambient: { wind: 14, crow: 0, dog: 0 },
  sanityShown: 0,
  decision: { active: false, forward: 0, waitRelease: true },
  cutscene: { t: 0, stage: 0 },
  entity: {
    root: null,
    active: false,
    started: false,
    grace: 0,
    freeze: 0,
    gaze: 0,
    unseen: 0,
    dist: 99,
    looked: false,
    rustle: 3,
  },
  startPos: new THREE.Vector3(0, 0, -1.2),
  sky: null,
  playerLight: null,
  shrineLight: null,
  shrineGlow: null,
  dom: { flash: null, gaze: null, choice: null },
  debug: null,
};

const _v1 = new THREE.Vector3();
const _v2 = new THREE.Vector3();
const _v3 = new THREE.Vector3();
const _eye = new THREE.Vector3();

/* ================= 小工具 ================= */
let gameRef = null;

function obj(name) { return gameRef ? gameRef.find(name) : null; }

function hasSfx(key) {
  return !!(gameRef && gameRef.audio && gameRef.audio.entries.sfx[key]);
}

function playSfx(key, opts = {}) {
  if (!hasSfx(key)) return null;
  try { return gameRef.audio.sfx(key, opts); } catch (err) { return null; }
}

function playAmb(key, opts) {
  if (!gameRef || !gameRef.audio) return null;
  if (!gameRef.audio.entries.ambience || !gameRef.audio.entries.ambience[key]) return null;
  try { return gameRef.audio.playAmbience(key, opts); } catch (err) { return null; }
}

function horizDist(a, b) { return Math.hypot(a.x - b.x, a.z - b.z); }

function after(delay, fn) { state.timers.push({ t: delay, fn }); }

function vec(x, y, z) { return new THREE.Vector3(x, y, z); }

/** 从 from 到 to 之间是否没有几何遮挡（忽略 ignore 子树） */
function clearLine(from, to, ignore) {
  _v1.subVectors(to, from);
  const dist = _v1.length();
  if (dist < 0.01) return true;
  _v1.normalize();
  const ray = new THREE.Raycaster(from.clone(), _v1.clone(), 0.05, Math.max(0.1, dist - 0.2));
  const hits = ray.intersectObject(gameRef.level, true);
  for (const h of hits) {
    let o = h.object;
    let isIgnore = false;
    let hidden = false;
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

function triggerWhiteFlash() {
  const el = state.dom.flash;
  if (!el) return;
  el.classList.remove('on');
  void el.offsetWidth;
  el.classList.add('on');
}

function showChoice(on) {
  const el = state.dom.choice;
  if (!el) return;
  el.classList.toggle('show', !!on);
}

/* ================= 配置 ================= */
const config = {
  id: 'nightroad',
  title: '夜路',
  chapter: '三更 · NIGHTROAD',
  titleEn: 'THE NIGHT ROAD',
  poster: '../../assets/art/poster-night.jpg',
  warning: '本作包含心理恐怖、闪烁画面、纸张与死亡意象。没有血腥画面。建议戴耳机，在安静、光线较暗的环境游玩。',
  homeUrl: '../../index.html',
  model: '../../assets/models/nightroad.glb',
  textures: '../../assets/textures/manifest.json',
  audio: '../../assets/audio/nightroad/manifest.json',
  footstepSfx: 'stepDirt',
  flashlight: null,
  ambient: { color: 0x6c82aa, intensity: 3.2 },
  fog: { color: 0x080d18, density: 0.03 },
  directional: { color: 0xa8c0e8, intensity: 1.15, position: [-26, 34, 30] },
  tint: '#c6d2e4',
  theme: { accent: '#9db8d8', ink: '#d8d2c0', bg: '#05070c' },
  playerStart: { spawn: 'SPAWN_night_start', look: 'LOOK_night_start' },
  renderScale: 0.6,

  /* ---------------- 初始化（标题页之前一次） ---------------- */
  async setup(game) {
    gameRef = game;
    state.game = game;

    game.ui.setObjective(OBJECTIVE.lanterns);
    game.ui.setCounter('灯笼 0 / 5');

    setupDom(game);
    setupSky(game);
    setupPlayerLight(game);
    setupLanterns(game);
    setupShrineLighting(game);
    setupIncense(game);
    setupEntity(game);

    // 初始威胁/理智
    game.setThreat(0.15);
    game.setSanity(0.03);

    // 脚步：土路
    game.player.onFootstep = (speed, sprinting) => {
      const key = hasSfx('stepDirt') ? 'stepDirt' : 'stepGrass';
      if (!hasSfx(key)) return;
      playSfx(key, { volume: sprinting ? 0.75 : 0.5, rate: 0.9 + Math.random() * 0.2 });
    };

    window.addEventListener('keydown', onKeyDown);

    // 结局选择提示在暂停/结束时隐藏
    setInterval(() => {
      if (!gameRef) return;
      const on = !!state.decision.active && gameRef.state === 'playing';
      showChoice(on);
    }, 260);
  },

  /* ---------------- 开始一局 ---------------- */
  start(game) {
    gameRef = game;
    resetRun(game);

    game.player.teleportTo('SPAWN_night_start', 'LOOK_night_start');
    game.player.enabled = true;
    game.audio.playMusic('main', { fade: 3 });
    playAmb('windField', { channel: 'main', fade: 2.5, volume: 1 });
    playAmb('insects', { channel: 'extra', fade: 2.5, volume: 0.9 });
    playAmb('distantDog', { channel: 'dog', fade: 2.5, volume: 0.6 });

    game.ui.setObjective(OBJECTIVE.lanterns);
    game.ui.setCounter('灯笼 0 / 5');

    // 纸人：落在身后。玩家先读完开场字幕；走出 1.5m 后它才醒来开始跟随
    const e = state.entity;
    if (e.root) {
      e.root.visible = true;
      e.root.position.set(0, 0, -8.5);
    }
    e.active = true;
    e.started = false;
    e.grace = 5.0;
    e.freeze = 0;
    e.gaze = 0;
    e.unseen = 0;
    e.dist = 8.5;
    state.startPos.copy(game.player.pos);

    after(0.6, (g) => g.ui.subtitle('送完葬，天已经黑透了。', 4.2));
    after(5.0, (g) => g.ui.subtitle('沿着这条路走。点亮五盏灯笼，到土地庙上一炷香。', 5.0));
    after(10.4, (g) => g.ui.subtitle('路上别停太久。', 3.4));

    game.setThreat(0.18);
    game.setSanity(0.05);
  },

  /* ---------------- 每帧 ---------------- */
  update(game, dt) {
    state.t += dt;
    runTimers(game, dt);
    updateLanterns(game, dt);
    updatePlayerLight(game);
    updateShrine(game);
    updateSky(game);
    updateEntity(game, dt);
    updateThreat(game, dt);
    updateAmbient(game, dt);
    if (state.phase === 'incense') updateIncenseCutscene(game, dt);
    if (state.decision.active && !state.ending) updateDecision(decisionInput(game), dt);
  },

  /* ---------------- 死亡重试 ---------------- */
  respawn(game) {
    gameRef = game;
    const e = state.entity;
    state.ending = false;
    state.phase = 'walk';
    state.decision.active = false;
    state.decision.forward = 0;
    state.decision.waitRelease = true;
    state.cutscene.t = 0;
    state.cutscene.stage = 0;
    showChoice(false);
    clearTimers();

    // 重生点：上一盏已点亮的灯；没有就回起点
    let idx = -1;
    for (let i = state.lanterns.length - 1; i >= 0; i--) {
      if (state.lanterns[i].lit) { idx = i; break; }
    }
    state.lastSafeIndex = idx;
    let pos = idx >= 0 && state.safeSpots[idx] ? state.safeSpots[idx].clone() : SPAWN_POS.clone();
    const look = vec(pos.x, 1.5, pos.z + 14);
    game.player.teleportToPos(pos, look);

    // 纸人出现在来路上
    let back = null;
    if (idx >= 1 && state.safeSpots[idx - 1]) back = state.safeSpots[idx - 1].clone();
    if (!back || back.distanceTo(pos) < 4.5) back = vec(pos.x, 0, pos.z - 9);
    if (e.root) {
      e.root.visible = true;
      e.root.position.copy(back);
    }
    e.active = true;
    e.started = true;
    e.grace = 3.0;
    e.freeze = 1.0;
    e.gaze = 0;
    e.unseen = 0;
    state.startPos.copy(pos);

    state.sanityPenalty = Math.max(state.sanityPenalty, 0.22);
    game.setThreat(0.4);
    game.setSanity(0.3);
    game.ui.setObjective(state.litCount >= 5 ? OBJECTIVE.shrine : OBJECTIVE.lanterns);
    game.ui.setCounter(`灯笼 ${state.litCount} / 5`);
    game.ui.subtitle('你又站起来了。前面的灯还亮着。', 3.4);
    game.audio.playMusic('main', { fade: 2 });
    playAmb('windField', { channel: 'main', fade: 2, volume: 1 });
    playAmb('insects', { channel: 'extra', fade: 2, volume: 0.9 });
  },

  onFail(game) {
    state.entity.active = false;
    state.decision.active = false;
    showChoice(false);
    clearTimers();
    if (state.dom.gaze) state.dom.gaze.style.opacity = '0';
    game.setThreat(0);
    game.setSanity(0);
  },

  onFinish() {
    state.decision.active = false;
    showChoice(false);
    if (state.dom.gaze) state.dom.gaze.style.opacity = '0';
  },
};

/* ================= 状态重置 ================= */
function resetRun(game) {
  state.phase = 'walk';
  state.t = 0;
  state.threat = 0;
  state.sanityPenalty = 0;
  state.calm = 0;
  state.litCount = 0;
  state.lastSafeIndex = -1;
  state.safeSpots = [];
  state.incenseDone = false;
  state.allLit = false;
  state.ending = false;
  state.hints = {};
  state.ambient = { wind: 14, crow: 0, dog: 0 };
  state.sanityShown = 0;
  state.decision = { active: false, forward: 0, waitRelease: true };
  state.cutscene = { t: 0, stage: 0 };
  clearTimers();
  if (state.entityBreath) { state.entityBreath.stop(0.3); state.entityBreath = null; }

  if (state.dom.gaze) state.dom.gaze.style.opacity = '0';
  showChoice(false);

    for (const L of state.lanterns) {
    L.lit = false;
    L.level = 0;
    if (L.light) { L.light.visible = false; L.light.intensity = 0; }
    if (L.glow) { L.glow.visible = false; L.glow.material.opacity = 0; }
    if (L.handle) L.handle.setEnabled(true);
    for (const m of L.mats) {
      m.emissiveIntensity = 0.02;
      if (m.userData.baseColor) m.color.copy(m.userData.baseColor).multiplyScalar(0.42);
    }
  }
  for (const h of state.incenseHandles) h.setEnabled(true);

  const e = state.entity;
  e.active = false;
  e.started = false;
  e.grace = 0;
  e.freeze = 0;
  e.gaze = 0;
  e.unseen = 0;
  e.dist = 99;
  if (e.root) e.root.visible = false;

  game.ui.setObjective(OBJECTIVE.lanterns);
  game.ui.setCounter('灯笼 0 / 5');
}

function runTimers(game, dt) {
  if (!state.timers.length) return;
  const due = [];
  for (const item of state.timers) {
    item.t -= dt;
    if (item.t <= 0) due.push(item);
  }
  for (const item of due) {
    const i = state.timers.indexOf(item);
    if (i >= 0) state.timers.splice(i, 1);
    try { item.fn(game); } catch (err) { console.error('[nightroad] timer', err); }
  }
}

function clearTimers() { state.timers.length = 0; }

/* ================= DOM 辅助层 ================= */
function setupDom(game) {
  const root = document.body;

  const flash = document.createElement('div');
  flash.id = 'nr-flash';
  root.appendChild(flash);
  state.dom.flash = flash;

  const gaze = document.createElement('div');
  gaze.id = 'nr-gaze';
  root.appendChild(gaze);
  state.dom.gaze = gaze;

  const choice = document.createElement('div');
  choice.id = 'nr-choice';
  const rowE = document.createElement('div');
  rowE.className = 'row';
  rowE.innerHTML = '<b>E</b><span>回头看</span>';
  const rowW = document.createElement('div');
  rowW.className = 'row';
  rowW.innerHTML = '<b>W</b><span>继续向前，不回头</span>';
  choice.appendChild(rowE);
  choice.appendChild(rowW);
  // 放进引擎 HUD 层：暂停/死亡时自动被更高层覆盖
  const hud = game.ui.el && game.ui.el.hud;
  (hud || root).appendChild(choice);
  state.dom.choice = choice;
}

/* ================= 天空 / 月亮 ================= */
function setupSky(game) {
  const fog = new THREE.Color(game.config.fog.color);

  const canvas = document.createElement('canvas');
  canvas.width = 4; canvas.height = 128;
  const ctx = canvas.getContext('2d');
  const grad = ctx.createLinearGradient(0, 0, 0, 128);
  grad.addColorStop(0.0, '#0a1424');
  grad.addColorStop(0.42, '#081020');
  grad.addColorStop(0.72, '#070d18');
  grad.addColorStop(1.0, '#' + fog.getHexString());
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, 4, 128);
  const skyTex = new THREE.CanvasTexture(canvas);
  skyTex.colorSpace = THREE.SRGBColorSpace;

  const dome = new THREE.Mesh(
    new THREE.SphereGeometry(82, 20, 12),
    new THREE.MeshBasicMaterial({ map: skyTex, side: THREE.BackSide, fog: false, depthWrite: false })
  );
  dome.name = 'NR_sky';
  dome.renderOrder = -20;
  dome.frustumCulled = false;
  game.scene.add(dome);

  // 星星
  const starPos = [];
  for (let i = 0; i < 110; i++) {
    const theta = Math.random() * Math.PI * 2;
    const y = 0.16 + Math.random() * 0.82;
    const r = Math.sqrt(Math.max(0, 1 - y * y)) * 78;
    starPos.push(Math.cos(theta) * r, y * 78, Math.sin(theta) * r);
  }
  const starGeo = new THREE.BufferGeometry();
  starGeo.setAttribute('position', new THREE.Float32BufferAttribute(starPos, 3));
  const stars = new THREE.Points(starGeo, new THREE.PointsMaterial({
    color: 0x9fb8dc, size: 1.6, sizeAttenuation: false,
    transparent: true, opacity: 0.55, fog: false, depthWrite: false,
  }));
  stars.frustumCulled = false;
  dome.add(stars);

  // 月亮 + 极淡月晕
  const moonDir = new THREE.Vector3(-0.34, 0.42, 0.84).normalize();
  const moon = new THREE.Mesh(
    new THREE.CircleGeometry(1.5, 24),
    new THREE.MeshBasicMaterial({ color: 0xdde8f8, fog: false, transparent: true, opacity: 0.85, depthWrite: false })
  );
  moon.renderOrder = -19;
  const halo = new THREE.Mesh(
    new THREE.CircleGeometry(3.4, 28),
    new THREE.MeshBasicMaterial({
      color: 0x7fa4d8, fog: false, transparent: true, opacity: 0.07,
      blending: THREE.AdditiveBlending, depthWrite: false,
    })
  );
  halo.renderOrder = -19;
  game.scene.add(moon);
  game.scene.add(halo);

  state.sky = { dome, moon, halo, dir: moonDir };
}

function updateSky(game) {
  const sky = state.sky;
  if (!sky) return;
  const cam = game.camera;
  sky.dome.position.copy(cam.position);
  _v1.copy(cam.position).addScaledVector(sky.dir, 68);
  sky.moon.position.copy(_v1);
  sky.moon.lookAt(cam.position);
  sky.halo.position.copy(_v1);
  sky.halo.lookAt(cam.position);
}

/* ================= 灯笼 ================= */
let _glowTex = null;
function lanternGlowTexture() {
  if (_glowTex) return _glowTex;
  const c = document.createElement('canvas');
  c.width = 128; c.height = 128;
  const ctx = c.getContext('2d');
  const g = ctx.createRadialGradient(64, 64, 2, 64, 64, 64);
  g.addColorStop(0.0, 'rgba(255, 214, 150, 0.95)');
  g.addColorStop(0.22, 'rgba(255, 166, 88, 0.55)');
  g.addColorStop(0.55, 'rgba(255, 120, 46, 0.16)');
  g.addColorStop(1.0, 'rgba(255, 90, 30, 0)');
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, 128, 128);
  _glowTex = new THREE.CanvasTexture(c);
  _glowTex.colorSpace = THREE.SRGBColorSpace;
  return _glowTex;
}

function setupLanterns(game) {
  for (let k = 0; k < 5; k++) {
    const name = `INT_lantern_0${k + 1}`;
    const root = game.find(name);
    if (!root) { console.warn('[nightroad] 缺少灯笼节点', name); continue; }
    root.updateMatrixWorld(true);
    const pos = root.getWorldPosition(new THREE.Vector3());

    const mats = cloneLanternPaper(root);

    const light = new THREE.PointLight(0xffa15c, 0, 10.5, 1.35);
    light.position.copy(pos);
    light.position.y += 0.06;
    light.visible = false;
    game.scene.add(light);

    // 雾里的暖色光晕（灯笼可读性）
    const glowMat = new THREE.SpriteMaterial({
      map: lanternGlowTexture(),
      transparent: true, opacity: 0, depthWrite: false,
      blending: THREE.AdditiveBlending, fog: true,
    });
    const glow = new THREE.Sprite(glowMat);
    glow.position.copy(pos);
    glow.scale.set(2.8, 2.8, 1);
    glow.visible = false;
    game.scene.add(glow);

    const handle = game.interact.add(root, {
      prompt: '点灯',
      range: 3.0,
      onUse: () => lightLantern(game, k),
    });

    state.lanterns.push({ index: k, name, root, pos, mats, light, glow, handle, lit: false, level: 0 });
  }
}

function cloneLanternPaper(root) {
  const out = [];
  root.traverse((o) => {
    if (!o.isMesh) return;
    const list = Array.isArray(o.material) ? o.material : [o.material];
    let changed = false;
    const next = list.map((m) => {
      if (!m || m.name !== 'MAT_lantern_paper') return m;
      const c = m.clone();
      c.userData = Object.assign({}, c.userData);
      c.userData.baseColor = c.color.clone();
      c.userData.baseEmissive = c.emissiveIntensity;
      c.color.multiplyScalar(0.42);
      c.emissiveIntensity = 0.02;
      out.push(c);
      changed = true;
      return c;
    });
    if (changed) o.material = Array.isArray(o.material) ? next : next[0];
  });
  return out;
}

/* ================= 玩家随身暖光（火折子 / 提灯） ================= */
function setupPlayerLight(game) {
  const light = new THREE.PointLight(0xffb877, 1.55, 13.5, 1.3);
  light.position.set(0.32, -0.3, -0.45);
  game.camera.add(light);
  state.playerLight = light;
}

function updatePlayerLight(game) {
  if (!state.playerLight) return;
  const f = 0.9 + 0.1 * Math.sin(game.time * 8.3) * Math.sin(game.time * 3.7 + 0.7);
  state.playerLight.intensity = 1.55 * f;
}

/* ================= 土地庙灯光 ================= */
function setupShrineLighting(game) {
  game.setLight('LIGHT_shrine', true, 2.6);
  const light = new THREE.PointLight(0xff9a5a, 1.5, 5.6, 1.3);
  light.position.set(0, 1.25, 96.9);
  game.scene.add(light);
  state.shrineLight = light;

  const glowMat = new THREE.SpriteMaterial({
    map: lanternGlowTexture(),
    transparent: true, opacity: 0.2, depthWrite: false,
    blending: THREE.AdditiveBlending, fog: true,
  });
  const glow = new THREE.Sprite(glowMat);
  glow.position.set(0, 1.15, 97.3);
  glow.scale.set(4.0, 4.0, 1);
  game.scene.add(glow);
  state.shrineGlow = glow;
}

function updateShrine(game) {
  const t = game.time;
  const flick = 0.86 + 0.14 * Math.sin(t * 7.3) * Math.sin(t * 2.9 + 1.3);
  if (state.shrineLight) state.shrineLight.intensity = 1.5 * flick;
  if (state.shrineGlow) state.shrineGlow.material.opacity = 0.17 + 0.05 * flick;
}

function updateLanterns(game, dt) {  const t = game.time;
  for (const L of state.lanterns) {
    const target = L.lit ? 1 : 0;
    L.level = damp(L.level, target, 3.2, dt);
    if (!L.light) continue;
    L.light.visible = L.level > 0.012;
    if (L.light.visible) {
      const flick = 0.9 + 0.1 * Math.sin(t * 8.6 + L.index * 2.3) * Math.sin(t * 3.1 + L.index * 1.7);
      L.light.intensity = 3.0 * L.level * flick;
    }
    for (const m of L.mats) {
      m.emissive.setHex(0xffb066);
      m.emissiveIntensity = 0.02 + 1.45 * L.level * (0.95 + 0.05 * Math.sin(t * 7.3 + L.index * 3.1));
      if (m.userData.baseColor) {
        m.color.copy(m.userData.baseColor).multiplyScalar(0.42 + 0.58 * L.level);
      }
    }
    if (L.glow) {
      L.glow.visible = L.level > 0.02;
      L.glow.material.opacity = L.level * (0.62 + 0.08 * Math.sin(t * 6.1 + L.index * 2.7));
      L.glow.scale.setScalar(2.4 + L.level * 0.8);
    }
  }
}

/* ================= 点灯 / 夺灯 ================= */
function lightLantern(game, k) {
  const L = state.lanterns[k];
  if (!L || L.lit || state.ending) return false;
  L.lit = true;
  if (L.handle) L.handle.setEnabled(false);
  if (L.light) L.light.visible = true;

  state.litCount += 1;
  state.safeSpots[k] = game.player.pos.clone();
  state.lastSafeIndex = Math.max(state.lastSafeIndex, k);

  // 点灯安全时间：纸人定身 6 秒
  const e = state.entity;
  e.freeze = Math.max(e.freeze, 6.0);
  e.gaze = 0;

  playSfx('matchStrike', { volume: 0.7, rate: 1.02 + Math.random() * 0.04 });
  after(0.26, () => playSfx('lanternLight', { volume: 0.85, pos: L.pos.clone() }));

  game.ui.setCounter(`灯笼 ${state.litCount} / 5`);
  game.ui.subtitle(LANTERN_LINES[k] || '灯亮了。', 3.4);

  if (k === 0 && !state.hints.freeze) {
    state.hints.freeze = true;
    after(3.5, (g) => g.ui.subtitle('它停住了。灯亮着的时候，它不会动。', 4.0));
  }

  if (state.litCount >= 5) {
    state.allLit = true;
    game.ui.setObjective(OBJECTIVE.shrine);
    after(3.6, (g) => g.ui.subtitle('最后一盏亮了。土地庙就在前面。', 4.2));
    after(1.2, () => playSfx('metalBell', { volume: 0.42, rate: 0.9 }));
    game.setLight('LIGHT_shrine', true, 1.35);
    game.setThreat(Math.min(state.threat, 0.3));
  } else if (k > 0 && !state.hints.story && state.litCount === 3) {
    state.hints.story = true;
  }
  return true;
}

/** 连续注视超过 2.5 秒：夺走最近一盏已点亮的灯 */
function stealLantern(game) {
  const e = state.entity;
  e.freeze = Math.max(e.freeze, 2.8);
  e.gaze = 0;
  state.decision.active = false;

  let best = null;
  let bd = Infinity;
  for (const L of state.lanterns) {
    if (!L.lit) continue;
    const d = horizDist(game.player.pos, L.pos);
    if (d < bd) { bd = d; best = L; }
  }

  let stole = false;
  if (best) {
    best.lit = false;
    if (best.handle) best.handle.setEnabled(true);
    if (best.index != null) state.safeSpots[best.index] = null;
    state.litCount = Math.max(0, state.litCount - 1);
    stole = true;
    for (let i = state.lanterns.length - 1; i >= 0; i--) {
      if (state.lanterns[i].lit) { state.lastSafeIndex = i; break; }
      if (i === 0) state.lastSafeIndex = -1;
    }
    state.allLit = state.litCount >= 5;
    game.ui.setCounter(`灯笼 ${state.litCount} / 5`);
    if (state.litCount < 5) {
      game.ui.setObjective(OBJECTIVE.lanterns);
      if (state.lanterns[4].lit === false) game.setLight('LIGHT_shrine', true, 1.0);
    }
    game.ui.subtitle('离你最近的那盏灯，灭了。', 3.6);
    playSfx('blackout', { volume: 0.85 });
  } else {
    game.ui.subtitle('它在你耳边笑了一声。', 3.2);
    playSfx('whisper', { volume: 0.7 });
  }

  state.sanityPenalty = Math.min(0.7, state.sanityPenalty + 0.3);
  triggerWhiteFlash();
  playSfx('stinger', { volume: 0.55, rate: 0.9 });
  if (stole) after(1.4, (g) => g.ui.subtitle('不能一直看。纸会记住你的脸。', 3.6));
}

/* ================= 土地庙 / 上香 ================= */
function setupIncense(game) {
  const add = (node, prompt, range) => {
    if (!node) return;
    const h = game.interact.add(node, {
      prompt,
      range,
      onUse: () => startIncense(game),
    });
    if (h) state.incenseHandles.push(h);
  };
  add(game.find('INT_incense'), '上香', 3.4);
  add(game.find('S_incense_burner'), '上香', 3.2);
}

function startIncense(game) {
  if (state.incenseDone || state.ending) return;
  if (state.litCount < 5) {
    playSfx('metalBell', { volume: 0.38, rate: 0.86 });
    game.ui.subtitle('香插不稳。还有灯没亮。', 3.2);
    return;
  }
  state.incenseDone = true;
  state.phase = 'incense';
  state.cutscene = { t: 0, stage: 0 };
  for (const h of state.incenseHandles) h.setEnabled(false);

  playSfx('shrineBell', { volume: 0.85 });
  playSfx('metalBell', { volume: 0.3, rate: 0.9, delay: 0.5 });

  const fwd = game.player.getForward(new THREE.Vector3());
  const e = state.entity;
  if (e.root) {
    e.root.visible = true;
    e.root.position.set(
      game.player.pos.x - fwd.x * 3.3,
      0,
      game.player.pos.z - fwd.z * 3.3
    );
    e.root.lookAt(game.player.pos.x, 0, game.player.pos.z);
  }
  e.freeze = 999;
  e.gaze = 0;
  e.active = false;

  game.ui.setObjective(OBJECTIVE.choose);
  game.ui.clearSubtitles();
  applySanityShock(game, 0.08, 0.3);
  game.setThreat(0.55);
}

function placeEntityBehind(game, distance) {
  const e = state.entity;
  if (!e.root) return;
  const fwd = game.player.getForward(new THREE.Vector3());
  e.root.visible = true;
  e.root.position.set(
    game.player.pos.x - fwd.x * distance,
    0,
    game.player.pos.z - fwd.z * distance
  );
  e.root.lookAt(game.player.pos.x, 0, game.player.pos.z);
  e.dist = horizDist(game.player.pos, e.root.position);
}

function updateIncenseCutscene(game, dt) {
  const c = state.cutscene;
  c.t += dt;
  if (c.stage === 0 && c.t > 0.9) {
    c.stage = 1;
    game.ui.subtitle('香插进炉里。烟直直地升上去。', 3.4);
  } else if (c.stage === 1 && c.t > 4.2) {
    c.stage = 2;
    placeEntityBehind(game, 3.3);
    game.ui.subtitle('身后有纸张的声音。它已经站在那儿了。', 3.6);
  } else if (c.stage === 2 && c.t > 8.0) {
    c.stage = 3;
    placeEntityBehind(game, 3.0);
    state.phase = 'decision';
    state.decision.active = true;
    state.decision.forward = 0;
    state.decision.waitRelease = true;
    game.ui.subtitle('按 E 回头看一眼。或者按 W 继续向前，别回头。', 5.4);
    showChoice(true);
    if (game.audio) {
      const h = playSfx('breath', { loop: true, volume: 0.22 });
      if (h) state.entityBreath = h;
    }
  }
}

function decisionInput(game) {
  const keys = game.player.keys || {};
  return !!(keys.KeyW || keys.ArrowUp);
}

function updateDecision(forwardDown, dt) {
  const d = state.decision;
  if (d.waitRelease) {
    if (!forwardDown) d.waitRelease = false;
    return;
  }
  if (forwardDown) {
    d.forward += dt;
    if (d.forward > 1.15) endingWalkOn(state.game);
  } else {
    d.forward = Math.max(0, d.forward - dt * 0.6);
  }
}

function onKeyDown(e) {
  if (!gameRef || gameRef.state !== 'playing') return;
  if (e.repeat) return;
  if (e.code === 'KeyE' && state.decision.active && !state.ending) {
    endingLookBack(gameRef);
  }
}

/* ================= 两种结局 ================= */
function endingLookBack(game) {
  if (state.ending) return;
  state.ending = true;
  state.phase = 'ending';
  state.decision.active = false;
  showChoice(false);
  clearTimers();
  if (state.entityBreath) { state.entityBreath.stop(0.6); state.entityBreath = null; }

  const e = state.entity;
  if (e.root) {
    e.root.visible = true;
    e.root.position.set(game.player.pos.x, 0, game.player.pos.z - 1.9);
    e.root.lookAt(game.player.pos.x, 0, game.player.pos.z);
  }
  // 强制回头
  game.player.lookAt(vec(game.player.pos.x, 1.5, game.player.pos.z - 3));
  game.setThreat(1);
  applySanityShock(game, 0.95, 0.9);
  playSfx('stinger', { volume: 0.85, rate: 0.86 });
  after(0.5, () => playSfx('whisper', { volume: 0.8 }));
  game.audio.stopMusic(2.5);
  if (game.audio.entries.music.ending) game.audio.playMusic('ending', { fade: 1.5 });
  game.ui.setObjective(null);
  game.ui.setCounter(null);

  after(0.9, (g) => g.ui.subtitle('它抬起头。你看清了那张脸。', 4.0));
  after(5.4, (g) => g.ui.subtitle('纸上写着你的名字。墨还没有干。', 4.2));
  after(9.8, (g) => {
    g.ui.fade(1, 1500);
    setTimeout(() => {
      g.finish({
        chapter: '三更 · 夜路',
        title: ENDING_LOOK.title,
        lines: ENDING_LOOK.lines,
        footer: '三更 · 夜路 · 完',
      });
      setTimeout(() => g.ui.fade(0, 1400), 320);
    }, 1700);
  });
}

function endingWalkOn(game) {
  if (state.ending) return;
  state.ending = true;
  state.phase = 'ending';
  state.decision.active = false;
  showChoice(false);
  clearTimers();
  if (state.entityBreath) { state.entityBreath.stop(1.0); state.entityBreath = null; }

  playSfx('windGust', { volume: 0.8 });
  game.ui.setObjective(null);
  game.ui.setCounter(null);
  game.ui.clearSubtitles();
  game.ui.subtitle('你没有回头。', 3.2);
  after(3.4, (g) => g.ui.subtitle('身后的脚步声一直跟着，和你一样快。', 3.8));
  after(7.6, (g) => g.ui.subtitle('走到村口的时候，鸡叫了。', 3.8));
  after(11.2, (g) => {
    if (game.audio.entries.music.ending) game.audio.playMusic('ending', { fade: 2.5 });
    else game.audio.stopMusic(2);
    g.ui.fade(1, 1700);
    setTimeout(() => {
      g.finish({
        chapter: '三更 · 夜路',
        title: ENDING_WALK.title,
        lines: ENDING_WALK.lines,
        footer: '三更 · 夜路 · 完',
      });
      setTimeout(() => g.ui.fade(0, 1500), 340);
    }, 1900);
  });
}

function applySanityShock(game, penalty, shown) {
  state.sanityPenalty = Math.max(state.sanityPenalty, clamp(penalty, 0, 1));
  if (shown != null) {
    state.sanityShown = Math.max(state.sanityShown, shown);
    game.setSanity(Math.max(game.sanity, clamp(shown, 0, 1)));
  }
}

/* ================= 纸人 ================= */
function setupEntity(game) {
  const root = game.entities.get('ENTITY_paper');
  if (!root) { console.warn('[nightroad] 缺少 ENTITY_paper'); return; }
  state.entity.root = root;
  root.visible = false;
  root.position.set(0, 0, -8.5);
  root.updateMatrixWorld(true);

  // 纸人自发光：黑暗中也能看出一张纸的轮廓（保留贴图细节）
  const paperMats = /^MAT_(paper|fabric_white|entity_face|entity_hair|red_cloth)$/;
  root.traverse((o) => {
    if (!o.isMesh) return;
    const list = Array.isArray(o.material) ? o.material : [o.material];
    const next = list.map((m) => {
      if (!m || !paperMats.test(m.name || '')) return m;
      const c = m.clone();
      c.emissiveMap = c.map || null;
      c.emissive = new THREE.Color(0xd9d2c4);
      c.emissiveIntensity = 0.3;
      c.needsUpdate = true;
      return c;
    });
    o.material = Array.isArray(o.material) ? next : next[0];
  });
}

function updateEntity(game, dt) {
  const e = state.entity;
  const root = e.root;
  if (!root || !e.active || state.ending) return;

  if (e.grace > 0) e.grace -= dt;
  if (e.freeze > 0) e.freeze -= dt;

  const player = game.player;
  const dx = player.pos.x - root.position.x;
  const dz = player.pos.z - root.position.z;
  const dist = Math.hypot(dx, dz);
  e.dist = dist;

  root.lookAt(player.pos.x, root.position.y, player.pos.z);

  // 开局：玩家还没走出 1.5m 时，纸人只是站在身后——不追、不判抓、不积累注视
  // （避免玩家原地读开场字幕约 10–20s 就被追上杀死）
  if (!e.started) {
    if (horizDist(player.pos, state.startPos) > 1.5) {
      e.started = true;
      e.grace = Math.max(e.grace, 1.2);
      playSfx('paperFlutter', {
        volume: 0.4, rate: 0.9,
        pos: root.position.clone().add(vec(0, 1, 0)),
      });
    } else {
      e.gaze = 0;
      e.unseen = 0;
      e.looked = false;
      return;
    }
  }

  const canSense = e.grace <= 0 && e.freeze <= 0 && dist < 20;
  const looked = canSense ? game.isLookingAt(root, { maxDistance: 20, fovDot: 0.3 }) : false;
  e.looked = looked;

  // 注视计时
  if (looked) {
    e.gaze += dt;
    if (!state.hints.look && dist < 14) {
      state.hints.look = true;
      game.ui.subtitle('它站住了。你看它的时候，它不动。', 3.8);
    }
    if (!state.hints.gazeWarn && e.gaze > 1.2) {
      state.hints.gazeWarn = true;
      game.ui.subtitle('别一直看。纸会记住你的脸。', 3.4);
    }
    if (e.gaze > 2.5) stealLantern(game);
  } else {
    e.gaze = Math.max(0, e.gaze - dt * 1.9);
  }

  // 移动：只有没被看、没有定身时
  let moving = false;
  if (e.grace <= 0 && e.freeze <= 0 && !looked && dist > 0.02) {
    e.unseen += dt;
    const speed = 2.05 + Math.min(1.05, e.unseen * 0.11);
    const dir = _v1.set(dx, 0, dz).multiplyScalar(1 / (dist || 1));

    if (e.unseen > 3.8 && dist > 5.0) {
      // 长时间没被看：贴着雾靠近一大步
      e.unseen = 0;
      const dash = Math.min(3.1, Math.max(0, dist - 2.2));
      root.position.addScaledVector(dir, dash);
      playSfx('paperFlutter', {
        volume: clamp(1.1 - dist / 22, 0.15, 0.75),
        rate: 0.88 + Math.random() * 0.1,
        pos: root.position.clone().add(vec(0, 1, 0)),
      });
      moving = true;
    } else if (dist > 0.9) {
      root.position.addScaledVector(dir, speed * dt);
      moving = true;
    }
  } else {
    e.unseen = Math.max(0, e.unseen - dt * 0.25);
  }

  // 纸张摩擦声
  if (moving) {
    e.rustle -= dt;
    if (e.rustle <= 0) {
      e.rustle = 2.8 + Math.random() * 2.2;
      playSfx('entityRustle', {
        volume: clamp(1.15 - dist / 16, 0.12, 0.6),
        rate: 0.86 + Math.random() * 0.24,
        pos: root.position.clone().add(vec(0, 1.1, 0)),
      });
    }
    root.position.y = Math.abs(Math.sin(game.time * 6.2)) * 0.02;
  } else {
    root.position.y = 0;
    e.rustle = Math.min(e.rustle, 1.2);
  }

  // 靠近提示
  if (dist < 5.2 && !state.hints.near) {
    state.hints.near = true;
    game.ui.subtitle('你听见身后有纸张摩擦的声音。', 3.4);
  }
  if (dist < 2.7 && !state.hints.close) {
    state.hints.close = true;
    game.ui.subtitle('太近了。', 2.4);
  }

  // 被碰到 → 死亡
  if (e.grace <= 0 && e.freeze <= 0 && dist < 1.0 && !state.decision.active) {
    _eye.copy(game.camera.getWorldPosition(new THREE.Vector3()));
    const chest = _v2.copy(root.position).add(vec(0, 1.15, 0));
    if (clearLine(_eye, chest, root)) triggerDeath(game);
  }
}

function triggerDeath(game) {
  const e = state.entity;
  if (state.ending) return;
  e.active = false;
  e.freeze = 0;
  e.gaze = 0;
  if (state.entityBreath) { state.entityBreath.stop(0.4); state.entityBreath = null; }
  playSfx('entityCatch', { volume: 0.95 });
  setTimeout(() => playSfx('whisper', { volume: 0.7 }), 200);
  triggerWhiteFlash();
  game.setThreat(0);
  game.setSanity(0);
  game.ui.clearSubtitles();
  game.ui.subtitle('你听见纸在响。', 1.8);
  game.fail(DEATH_TEXT);
}

/* ================= 威胁 / 理智 / 环境音 ================= */
function updateThreat(game, dt) {
  const e = state.entity;
  const player = game.player;
  let dist = 30;
  if (e.root && e.root.visible && (e.active || state.phase === 'incense' || state.phase === 'decision')) {
    dist = horizDist(player.pos, e.root.position);
  }

  const near = Math.pow(clamp(1 - dist / 12, 0, 1), 2);

  // 黑暗：离最近一盏点亮的灯/庙多远
  let nearest = Infinity;
  for (const L of state.lanterns) {
    if (L.lit) nearest = Math.min(nearest, horizDist(player.pos, L.pos));
  }
  if (state.litCount >= 5) nearest = Math.min(nearest, horizDist(player.pos, SHRINE_POS));
  let dark;
  if (!isFinite(nearest)) dark = 0.85;
  else dark = clamp((nearest - 5) / 22, 0, 1);

  let threat = clamp(near * 0.9 + dark * 0.13, 0, 1);
  if (e.freeze > 0) threat *= 0.55;
  if (state.phase === 'incense') threat = Math.max(threat, 0.5);
  if (state.decision.active) threat = Math.max(threat, 0.56);
  if (state.ending) threat = Math.min(Math.max(threat, 0.45), 0.62);

  state.threat = damp(state.threat, threat, 1.3, dt);
  const gazeStress = clamp(e.gaze / 2.5, 0, 1) * 0.32;
  let sanity = clamp(state.threat * 0.7 + state.sanityPenalty + gazeStress, 0, 1);
  if (state.ending) sanity = Math.min(sanity, 0.55);
  game.setThreat(state.threat);
  game.setSanity(sanity);

  state.sanityPenalty = Math.max(0, state.sanityPenalty - dt * 0.012);

  // 注视压迫边缘
  const gazeEl = state.dom.gaze;
  if (gazeEl) {
    const v = clamp((e.gaze - 0.35) / 2.1, 0, 1);
    gazeEl.style.opacity = (v * 0.62).toFixed(3);
  }
}

function updateAmbient(game, dt) {
  // 风
  state.ambient.wind -= dt;
  if (state.ambient.wind <= 0) {
    state.ambient.wind = 17 + Math.random() * 15;
    playSfx('windGust', {
      volume: 0.3 + Math.random() * 0.25,
      rate: 0.85 + Math.random() * 0.2,
      pan: (Math.random() * 2 - 1) * 0.7,
    });
  }
  // 远处狗叫 / 乌鸦
  state.ambient.dog -= dt;
  if (state.ambient.dog <= 0) {
    state.ambient.dog = 34 + Math.random() * 30;
    playAmb('distantDog', { channel: 'dog', fade: 3, volume: 0.5 });
  }
  const z = game.player.pos.z;
  if (!state.ambient.crow && z > 40 && z < 92) {
    state.ambient.crow = 1;
    playSfx('crow', { volume: 0.35, pan: -0.5 });
  }
}

/* ================= 调试 / QA ================= */
function installDebug(game) {
  state.debug = {
    game,
    state,
    teleport(x, z) {
      game.player.pos.set(x, 0, z);
      game.player.vel.set(0, 0, 0);
      game.player._syncCamera(0, true);
    },
    face(x, z, y) {
      game.player.lookAt(new THREE.Vector3(x, y == null ? 1.45 : y, z));
    },
    faceObject(name) {
      const o = game.find(name) || (state.entity.root && name === 'ENTITY_paper' ? state.entity.root : null);
      if (!o) return false;
      const p = o.getWorldPosition(new THREE.Vector3());
      game.player.lookAt(new THREE.Vector3(p.x, p.y + 0.8, p.z));
      return true;
    },
    entityPos() {
      const r = state.entity.root;
      return r ? [r.position.x, r.position.y, r.position.z] : null;
    },
    moveEntity(x, z) {
      if (state.entity.root) state.entity.root.position.set(x, 0, z);
    },
    light(i) { return lightLantern(game, i); },
    lightAll() {
      for (let i = 0; i < state.lanterns.length; i++) {
        if (!state.lanterns[i].lit) lightLantern(game, i);
      }
      return state.litCount;
    },
    incense() { startIncense(game); },
    endingA() { if (state.decision.active) endingLookBack(game); },
    endingB() { if (state.decision.active) endingWalkOn(game); },
    status() {
      return {
        gameState: game.state,
        phase: state.phase,
        litCount: state.litCount,
        lit: state.lanterns.map((L) => L.lit),
        lastSafeIndex: state.lastSafeIndex,
        entity: {
          dist: +state.entity.dist.toFixed(2),
          freeze: +state.entity.freeze.toFixed(2),
          gaze: +state.entity.gaze.toFixed(2),
          looked: state.entity.looked,
          active: state.entity.active,
          started: state.entity.started,
        },
        threat: +state.threat.toFixed(2),
        sanity: +game.sanity.toFixed(2),
        decision: state.decision.active,
        pos: [ +game.player.pos.x.toFixed(2), +game.player.pos.z.toFixed(2) ],
        entityPos: state.entity.root ? [ +state.entity.root.position.x.toFixed(2), +state.entity.root.position.z.toFixed(2) ] : null,
      };
    },
  };
  window.__NIGHT__ = state.debug;
}

/* ================= 启动 ================= */
const game = new HorrorGame(config);
game.load().then(() => {
  installDebug(game);
}).catch((err) => {
  console.error('《夜路》加载失败', err);
  const div = document.createElement('div');
  div.style.cssText = 'position:fixed;inset:0;z-index:999;background:#000;color:#9db8d8;font:14px/1.8 monospace;padding:40px;white-space:pre-wrap;';
  div.textContent = '《夜路》加载失败：\n' + (err && err.stack ? err.stack : err);
  document.body.appendChild(div);
});
