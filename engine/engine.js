/* 《三更》共享引擎：场景/材质/灯光/玩家/交互/音频/后处理/UI/镜子 */
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { PostFX } from './postfx.js';
import { AudioManager } from './audio.js';
import { UI } from './ui.js';
import { Player } from './player.js';
import { TouchControls, prefersTouch } from './touch.js';
import { PlanarMirror } from './mirror.js';
import { Progress } from './progress.js';
import { clamp, damp, loadJSON } from './utils.js';

const SETTINGS_KEY = 'sangeng-settings-v1';
const DEFAULT_SETTINGS = { sensitivity: 1.0, volume: 0.8, subtitles: true, renderScale: 0.6, inputMode: 'auto' };

class CollisionWorld {
  constructor() { this.boxes = []; }
  add(box) {
    const handle = { box: box.clone(), enabled: true };
    this.boxes.push(handle);
    return handle;
  }
  remove(handle) {
    const i = this.boxes.indexOf(handle);
    if (i >= 0) this.boxes.splice(i, 1);
  }
  setEnabled(handle, on) { if (handle) handle.enabled = !!on; }
}

class InteractionManager {
  constructor(game) {
    this.game = game;
    this.handles = [];
    this.current = null;
    this._raycaster = new THREE.Raycaster();
    this._center = new THREE.Vector2(0, 0);
    this._cooldown = 0;
  }

  add(object, opts = {}) {
    if (!object) return null;
    const handle = {
      object, prompt: opts.prompt || '查看', enabled: opts.enabled !== false,
      range: opts.range || 2.9, onUse: opts.onUse || null,
      setPrompt: (t) => { handle.prompt = t; },
      setEnabled: (on) => { handle.enabled = !!on; if (!on && this.current === handle) this._clear(); },
      remove: () => {
        const i = this.handles.indexOf(handle);
        if (i >= 0) this.handles.splice(i, 1);
        object.traverse((o) => { if (o.userData.__interact === handle) delete o.userData.__interact; });
        if (this.current === handle) this._clear();
      },
      _registered: true,
    };
    object.traverse((o) => { o.userData.__interact = handle; });
    this.handles.push(handle);
    if (opts.hidden) object.visible = false;
    return handle;
  }

  _clear() {
    this.current = null;
    this.game.ui.setPrompt(null);
  }

  update(dt = 0) {
    this._cooldown = Math.max(0, this._cooldown - dt);
    const g = this.game;
    if (!g.player.enabled) { if (this.current) this._clear(); return; }
    this._raycaster.setFromCamera(this._center, g.camera);
    this._raycaster.far = 3.2;
    let found = null;
    const hits = this._raycaster.intersectObject(g.level, true);
    for (const hit of hits) {
      // Three.js 射线仍会命中隐藏网格；已拾取/尚未出现的物件不能挡住后面的交互。
      if (!isObjectVisible(hit.object)) continue;
      let o = hit.object;
      while (o) {
        if (o.userData && o.userData.__interact) { found = o.userData.__interact; break; }
        o = o.parent;
      }
      if (found) {
        if (hit.distance > found.range || !found.enabled || !isObjectVisible(found.object)) found = null;
        break;
      }
    }
    if (found !== this.current) {
      this.current = found;
    }
    // 同一物件可能切换“拿起/放下”等提示，无需移开准星才能刷新。
    g.ui.setPrompt(found ? found.prompt : null);
  }

  use() {
    if (!this.current || !this.current.enabled || this._cooldown > 0) return false;
    this._cooldown = 0.28;
    const h = this.current;
    this.game.audio && this.game.audio.ui('click');
    try { h.onUse && h.onUse(h, this.game); } catch (err) { console.error('交互回调错误', err); }
    return true;
  }
}

function isObjectVisible(obj) {
  let o = obj;
  while (o) { if (o.visible === false) return false; o = o.parent; }
  return true;
}

export class HorrorGame {
  constructor(config) {
    this.config = Object.assign({
      title: '三更',
      chapter: '',
      titleEn: '',
      warning: '本作包含心理恐怖、闪烁画面与幽闭空间描写。建议戴耳机，在安静环境游玩。',
      cameraFov: 72,
      renderScale: 0.6,
      ambient: { color: 0x2a3330, intensity: 0.35 },
      fog: { color: 0x070a09, density: 0.055 },
      footstepSfx: null,
      flashlight: null,
      theme: {},
      playerStart: { spawn: 'SPAWN_main', look: 'LOOK_main' },
      homeUrl: '../../index.html',
    }, config);
    this.canvas = document.getElementById('gl');
    this.state = 'boot';
    this.time = 0;
    this.clock = new THREE.Clock();
    this.markers = new Map();
    this.variants = new Map();
    this.hidden = new Map();
    this.entities = new Map();
    this.lights = new Map();
    this.settings = this._loadSettings();
    this.sanity = 0;
    this.threat = 0;
    this._sanitySmooth = 0;
    this._threatSmooth = 0;
    this._doorAnims = [];
    this._settingsReturn = 'title';
    this._lastTitleFrame = 0;
    this._levelReady = false;
    this.placeholder = false;
    this.colliders = new CollisionWorld();
    this.audio = new AudioManager();
    this.mirror = null;
    this.reflectionScene = null;
    this._fadeAlpha = 0;
    this._journalFromEnding = false;
    this._resizeHandler = () => this._onResize();
  }

  _loadSettings() {
    let s = Object.assign({}, DEFAULT_SETTINGS, prefersTouch() ? { renderScale: 0.45 } : {});
    try {
      const raw = localStorage.getItem(SETTINGS_KEY);
      if (raw) Object.assign(s, JSON.parse(raw));
    } catch (e) { /* ignore */ }
    return s;
  }

  _saveSettings() {
    try { localStorage.setItem(SETTINGS_KEY, JSON.stringify(this.settings)); } catch (e) { /* ignore */ }
  }

  /* ================= 初始化 ================= */
  async load() {
    this._initRenderer();
    this.ui = new UI(this);
    this.ui.setConfig(this.config);
    this.progress = new Progress(this);
    if (this.config.discovery) this.progress.define(this.config.discovery);
    this.ui.showLoading();
    this.ui.setLoading(0.01, '正在打开门…');
    this.audio = new AudioManager();

    // 1. 贴图
    await this._loadTextures();

    // 2. 音频
    this.ui.setLoading(0.25, '正在录下房间的声音…');
    try {
      await this.audio.load(this.config.audio, (p) => this.ui.setLoading(0.25 + p * 0.35, '正在录下房间的声音…'));
    } catch (err) { console.warn(err); }

    // 3. 场景
    this.ui.setLoading(0.62, '正在布置房间…');
    await this._loadLevel();

    // 4. 玩家与配置
    this.ui.setLoading(0.88, '正在关灯…');
    this._initPlayer();
    this.interact = new InteractionManager(this);
    this.touchControls = new TouchControls(this);
    this._applyAtmosphere();
    this.applySettings();
    this._bindGlobalEvents();
    try {
      if (this.config.setup) await this.config.setup(this);
    } catch (err) { console.error('setup 出错', err); }

    this._levelReady = true;
    this.ui.setLoading(1, '');
    setTimeout(() => this.ui.hideLoading(), 260);
    this.state = 'title';
    this.ui.showTitle();
    this.ui.setHudVisible(false);
    this._loop();
    // 调试入口，QA 可用
    window.__SANGENG__ = this;
  }

  _initRenderer() {
    this.renderer = new THREE.WebGLRenderer({
      canvas: this.canvas, antialias: false, alpha: false,
      powerPreference: 'high-performance', stencil: false,
    });
    this.renderer.setPixelRatio(1);
    this.renderer.setSize(window.innerWidth, window.innerHeight, false);
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.toneMapping = THREE.NoToneMapping;
    try { this.renderer.useLegacyLights = true; } catch (e) { /* r160 */ }
    this.renderer.setClearColor(0x000000, 1);

    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(this.config.cameraFov, window.innerWidth / window.innerHeight, 0.04, 90);
    this.camera.rotation.order = 'YXZ';
    this.scene.add(this.camera);
    this.postfx = new PostFX(this.renderer, { renderScale: this.settings.renderScale });
    this.postfx.setSize(window.innerWidth, window.innerHeight);
  }

  /* ---------- 贴图 ---------- */
  async _loadTextures() {
    this.textures = new Map();
    this.textureDefs = {};
    this.materials = new Map();
    if (!this.config.textures) return;
    let manifest;
    try {
      manifest = await loadJSON(this.config.textures);
    } catch (err) {
      console.warn('[textures] manifest 加载失败：', this.config.textures, err);
      return;
    }
    this.textureDefs = manifest.materials || {};
    const loader = new THREE.TextureLoader();
    const entries = Object.entries(this.textureDefs);
    const manifestUrl = new URL(this.config.textures, location.href).href;
    let done = 0;
    await Promise.all(entries.map(([key, def]) => new Promise((resolve) => {
      if (!def || !def.file) { done++; resolve(); return; }
      const url = new URL(def.file, manifestUrl).href;
      loader.load(url, (tex) => {
        tex.colorSpace = def.colorSpace === 'none' ? THREE.NoColorSpace : THREE.SRGBColorSpace;
        tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
        tex.magFilter = THREE.NearestFilter;
        tex.minFilter = THREE.LinearMipmapLinearFilter;
        tex.anisotropy = 1;
        tex.generateMipmaps = true;
        this.textures.set(key, tex);
        done++;
        resolve();
      }, undefined, (err) => {
        console.warn('[textures] 缺失：', key, url);
        done++;
        resolve();
      });
    })));
    this.ui.setLoading(0.18, `正在晒干 ${done} 张墙纸…`);
  }

  getMaterial(name) {
    if (this.materials.has(name)) return this.materials.get(name);
    const def = this.textureDefs[name] || {};
    const tex = this.textures.get(name);
    const params = { color: new THREE.Color(def.tint || '#ffffff') };
    if (tex) params.map = tex;
    if (def.emissive) {
      params.emissive = new THREE.Color(def.emissive);
      params.emissiveIntensity = def.emissiveIntensity == null ? 1 : def.emissiveIntensity;
      if (tex) params.emissiveMap = tex;
    }
    if (def.transparent) {
      params.transparent = true;
      params.depthWrite = false;
      params.alphaTest = 0.02;
    }
    const mat = new THREE.MeshLambertMaterial(params);
    mat.name = name;
    // 未知材质兜底颜色
    if (!tex && !def.tint) mat.color.setHex(0x6f6a60);
    this.materials.set(name, mat);
    return mat;
  }

  /* ---------- 场景 ---------- */
  async _loadLevel() {
    this.level = null;
    if (this.config.model) {
      try {
        const loader = new GLTFLoader();
        const gltf = await loader.loadAsync(this.config.model);
        this.level = gltf.scene;
        this.level.name = 'level';
        this.scene.add(this.level);
      } catch (err) {
        console.warn('[level] GLB 加载失败，使用占位场景：', this.config.model, err);
      }
    }
    if (!this.level) {
      this.placeholder = true;
      this.level = this._buildPlaceholderLevel();
      this.scene.add(this.level);
    }
    this.level.updateMatrixWorld(true);
    this._applyMaterials(this.level);
    this._extractLevelData();
    this._setupLights();
  }

  _applyMaterials(root) {
    const seen = new Set();
    root.traverse((o) => {
      if (!o.isMesh) return;
      const oldMats = Array.isArray(o.material) ? o.material : [o.material];
      const mats = oldMats.map((m) => {
        let name = (m && m.name) || '';
        if (!name.startsWith('MAT_')) name = 'MAT_fallback';
        seen.add(name);
        return this.getMaterial(name);
      });
      o.material = Array.isArray(o.material) ? mats : mats[0];
    });
    this.usedMaterials = seen;
  }

  _extractLevelData() {
    this.markers.clear();
    this.variants.clear();
    this.hidden.clear();
    this.entities.clear();
    this.lights.clear();
    this._lightEntries = [];
    const colMeshes = [];
    const interactHidden = [];
    const level = this.level;
    level.traverse((o) => {
      const n = o.name || '';
      if (n.startsWith('COL_')) { colMeshes.push(o); return; }
      if (n.startsWith('V2_') || n.startsWith('V3_')) { this.variants.set(n, o); o.visible = false; return; }
      if (n.startsWith('ENTITY_')) {
        let parentIsEntity = false;
        let p = o.parent;
        while (p) { if ((p.name || '').startsWith('ENTITY_')) { parentIsEntity = true; break; } p = p.parent; }
        if (!parentIsEntity) { this.entities.set(n, o); o.visible = false; }
        return;
      }
      if (n.startsWith('SPAWN_') || n.startsWith('LOOK_') || n.startsWith('MARK_')) { this.markers.set(n, o); return; }
      if (n.startsWith('LIGHT_')) { this.lights.set(n, o); return; }
      if (n.startsWith('INT_') && o.userData && o.userData.hidden) { interactHidden.push(o); return; }
    });
    // 碰撞
    for (const m of colMeshes) {
      m.updateWorldMatrix(true, false);
      const box = new THREE.Box3().setFromObject(m);
      if (!box.isEmpty()) this.colliders.add(box);
      m.visible = false;
      m.layers.set(2);
      if (m.parent) m.parent.remove(m);
    }
    this.colMeshes = colMeshes;
    // 初始隐藏的交互物
    for (const o of interactHidden) { o.visible = false; this.hidden.set(o.name, o); }
    if (this.config.hideEntities !== false) {
      for (const o of this.entities.values()) o.visible = false;
    }
  }

  _setupLights() {
    this.ambient = new THREE.AmbientLight(this.config.ambient.color, this.config.ambient.intensity);
    this.scene.add(this.ambient);

    for (const [name, empty] of this.lights) {
      const ud = empty.userData || {};
      const kind = ud.light_kind || 'point';
      const power = typeof ud.light_power === 'number' ? ud.light_power : 20;
      const color = new THREE.Color(ud.light_color || '#ffffff');
      const radius = typeof ud.light_radius === 'number' ? ud.light_radius : 8;
      const flicker = typeof ud.light_flicker === 'number' ? ud.light_flicker : 0;
      const pos = empty.getWorldPosition(new THREE.Vector3());
      let light;
      if (kind === 'spot') {
        const cone = ((typeof ud.light_cone_deg === 'number' ? ud.light_cone_deg : 60) * Math.PI) / 180;
        light = new THREE.SpotLight(color, 1, radius, cone, 0.5, 1.2);
        const target = new THREE.Object3D();
        target.position.copy(pos).add(new THREE.Vector3(0, -3, 0));
        this.scene.add(target);
        light.target = target;
      } else {
        light = new THREE.PointLight(color, 1, radius, 1.25);
      }
      light.position.copy(pos);
      this.scene.add(light);
      const intensity = Math.max(0.05, power / (kind === 'spot' ? 30 : 28));
      light.intensity = intensity;
      const entry = { light, base: intensity, flicker, seed: Math.random() * 10, name, kind };
      this._lightEntries.push(entry);
      entry.handle = entry;
    }
    if (this.config.directional) {
      const d = this.config.directional;
      this.directional = new THREE.DirectionalLight(d.color || 0x4a6a8a, d.intensity == null ? 0.25 : d.intensity);
      this.directional.position.set(...(d.position || [-20, 30, -10]));
      this.scene.add(this.directional);
    }
  }

  _buildPlaceholderLevel() {
    const group = new THREE.Group();
    group.name = 'level';
    const floor = new THREE.Mesh(new THREE.BoxGeometry(4.4, 0.1, 22), new THREE.MeshLambertMaterial({ color: 0x3a3630 }));
    floor.position.set(0, -0.05, -10);
    group.add(floor);
    const w1 = new THREE.Mesh(new THREE.BoxGeometry(0.2, 3, 22)); w1.name = 'COL_wall_l'; w1.position.set(-2.2, 1.5, -10); group.add(w1);
    const w2 = new THREE.Mesh(new THREE.BoxGeometry(0.2, 3, 22)); w2.name = 'COL_wall_r'; w2.position.set(2.2, 1.5, -10); group.add(w2);
    const w3 = new THREE.Mesh(new THREE.BoxGeometry(4.4, 3, 0.2)); w3.name = 'COL_wall_end'; w3.position.set(0, 1.5, -21); group.add(w3);
    const w4 = new THREE.Mesh(new THREE.BoxGeometry(4.4, 3, 0.2)); w4.name = 'COL_wall_back'; w4.position.set(0, 1.5, 1); group.add(w4);
    const spawn = new THREE.Object3D(); spawn.name = 'SPAWN_main'; spawn.position.set(0, 0, -1); group.add(spawn);
    const look = new THREE.Object3D(); look.name = 'LOOK_main'; look.position.set(0, 1.5, -10); group.add(look);
    const lamp = new THREE.Object3D(); lamp.name = 'LIGHT_main'; lamp.position.set(0, 2.6, -6);
    lamp.userData = { light_kind: 'point', light_power: 25, light_color: '#cfe0d8', light_radius: 9, light_flicker: 0.1 };
    group.add(lamp);
    return group;
  }

  _initPlayer() {
    this.player = new Player(this);
    const start = this.config.playerStart || {};
    this.player.teleportTo(start.spawn || 'SPAWN_main', start.look || 'LOOK_main');
    this.player.enabled = false;
  }

  _applyAtmosphere() {
    const fogColor = new THREE.Color(this.config.fog.color);
    this.scene.fog = new THREE.FogExp2(fogColor, this.config.fog.density);
    this.scene.background = fogColor.clone();
    this.postfx.uniforms.uTint.value.set(this.config.tint || '#ffffff');
  }

  /* ================= 配置 / 状态 ================= */
  applySettings() {
    const s = this.settings;
    this.audio.setMasterVolume(s.volume);
    this.postfx.setScale(s.renderScale);
    if (this.mirror) this.mirror.setResolutionScale(s.renderScale);
    this.ui.syncSettingsLabels();
    this.touchControls?.configure();
    // 切到拖动/触屏模式时主动释放指针锁定，避免鼠标继续被锁住。
    if ((s.inputMode === 'drag' || this.touchEnabled) && document.pointerLockElement) {
      document.exitPointerLock();
    }
    this._saveSettings();
  }

  openSettings() {
    this._settingsReturn = this.state === 'paused' ? 'paused' : this.state === 'playing' ? 'playing' : 'title';
    if (this.state === 'playing') this.pause();
    this.ui.showSettings();
  }

  closeSettings() {
    this.ui.hideSettings();
    if (this._settingsReturn === 'paused') {
      this.ui.showPause();
    } else if (this._settingsReturn === 'playing') {
      this.resume();
    } else {
      this.ui.showTitle();
    }
  }

  start() {
    if (this.state !== 'title') return;
    this.audio.unlock();
    this.audio.ui('confirm');
    this.ui.hideTitle();
    this.ui.setHudVisible(true);
    this.state = 'playing';
    this.player.enabled = true;
    document.body.classList.add('sg-playing');
    this._requestLock();
    this.ui.fade(0, 900);
    try { if (this.config.start) this.config.start(this); } catch (err) { console.error('start 出错', err); }
  }

  pause() {
    if (this.state !== 'playing') return;
    this.state = 'paused';
    this.player.enabled = false;
    this.ui.showPause();
    this.audio.duck(true);
    this.ui.setPrompt(null);
    if (document.pointerLockElement) document.exitPointerLock();
    document.body.classList.remove('sg-playing');
  }

  resume() {
    if (this.state !== 'paused') return;
    this.audio.unlock();
    this.state = 'playing';
    this.player.enabled = true;
    this.ui.hidePause();
    this.audio.duck(false);
    document.body.classList.add('sg-playing');
    this._requestLock();
  }

  retry() {
    this.ui.hideDeath();
    this.ui.fade(0, 300);
    this.state = 'playing';
    this.player.enabled = true;
    this.ui.setHudVisible(true);
    this.audio.duck(false);
    this.ui.clearSubtitles();
    document.body.classList.add('sg-playing');
    try { if (this.config.respawn) this.config.respawn(this); } catch (err) { console.error('respawn 出错', err); }
    this._requestLock();
  }

  fail(text) {
    if (this.state === 'dead' || this.state === 'ending') return;
    this.state = 'dead';
    this.player.enabled = false;
    if (document.pointerLockElement) document.exitPointerLock();
    this.ui.showDeath(text);
    this.audio.duck(true);
    document.body.classList.remove('sg-playing');
    try { if (this.config.onFail) this.config.onFail(this); } catch (err) { console.error(err); }
  }

  finish({ chapter, title, lines, footer, endingId } = {}) {
    if (this.state === 'ending') return;
    this.state = 'ending';
    this.player.enabled = false;
    if (document.pointerLockElement) document.exitPointerLock();
    let stats = null;
    if (this.progress) {
      if (endingId) this.progress.ending(endingId);
      stats = this.progress.summary();
    }
    this.ui.showEnding({ chapter: chapter || this.config.chapter, title: title || '', lines, footer, stats });
    this.audio.duck(false);
    document.body.classList.remove('sg-playing');
    try { if (this.config.onFinish) this.config.onFinish(this); } catch (err) { console.error(err); }
  }

  /* v1.4.0：暂停中的手记 / 玩家主动取提示；默认沉浸，不自动弹。 */
  openJournal() {
    if (this.state !== 'paused' || !this.progress) return false;
    this.ui.hidePause();
    this.ui.showJournal(this.progress.summary());
    return true;
  }

  closeJournal() {
    this.ui.hideJournal();
    if (this._journalFromEnding) {
      this._journalFromEnding = false;
      this.ui.showEndingPanel();
      return;
    }
    if (this.state === 'paused') this.ui.showPause();
  }

  openEndingJournal() {
    if (this.state !== 'ending' || !this.progress) return false;
    this._journalFromEnding = true;
    this.ui.hideEnding();
    this.ui.showJournal(this.progress.summary());
    return true;
  }

  requestHint() {
    if (!this.progress) return false;
    const summary = this.progress.summary();
    // 沉浸档不自动提示；玩家主动取时按目录组顺序，先给主线，避免随机剧透后段。
    for (const group of summary.groups) {
      const pick = summary.entries.find((e) => e.group === group.id && !e.discovered);
      if (pick) {
        this.ui.showJournalHint(pick.hint || '再仔细看看这个房间。');
        return true;
      }
    }
    this.ui.showJournalHint('这一篇的东西，你已经都看过了。');
    return false;
  }

  openPaper({ head, lines, onClose }) {
    if (this.state !== 'playing') return;
    this.state = 'paper';
    this.player.enabled = false;
    if (document.pointerLockElement) document.exitPointerLock();
    this.ui.showPaper({ head, lines, onClose: () => {
      this.state = 'playing';
      this.player.enabled = true;
      this.ui.setHudVisible(true);
      this._requestLock();
      if (onClose) onClose(this);
    } });
    this.ui.setHudVisible(false);
  }

  closePaper() {
    this.ui.closePaper();
  }

  replay() { location.reload(); }
  goHome() { location.href = this.config.homeUrl; }

  _requestLock() {
    if (this.touchEnabled || this.settings.inputMode === 'drag') return;
    if (typeof this.canvas?.requestPointerLock !== 'function') return;
    if (!this.canvas || document.pointerLockElement === this.canvas) return;
    const p = this.canvas.requestPointerLock();
    if (p && p.catch) p.catch(() => {});
  }

  /* ================= 道具 / 交互 ================= */
  makeDoor(object, opts = {}) {
    if (!object) return null;
    const angle = (object.userData.open_angle == null ? 95 : Number(object.userData.open_angle)) * Math.PI / 180;
    const dir = (object.userData.open_dir == null ? 1 : Number(object.userData.open_dir));
    object.updateMatrixWorld(true);
    const closedBox = new THREE.Box3().setFromObject(object);
    const collider = this.colliders.add(closedBox);
    const baseRotation = object.rotation.y;
    const handle = {
      object, isOpen: false, busy: false, angle, dir, collider, baseRotation,
      isLocked: opts.locked != null ? opts.locked : !!object.userData.locked,
      setLocked: (v) => { handle.isLocked = !!v; },
      setPrompt: (p) => { if (handle.interact) handle.interact.setPrompt(p); },
      open: (silent = false) => {
        if (handle.isOpen || handle.busy) return;
        handle.busy = true;
        if (!silent && this.audio) this.audio.sfx('doorOpen', { pos: object.getWorldPosition(new THREE.Vector3()), volume: 0.9 });
        this.colliders.setEnabled(handle.collider, false);
        this._doorAnims.push({ handle, from: object.rotation.y, to: baseRotation + handle.angle * handle.dir, t: 0, dur: 0.9, opening: true });
        handle.isOpen = true;
        if (opts.onOpen) opts.onOpen(handle);
      },
      close: () => {
        if (!handle.isOpen || handle.busy) return;
        handle.busy = true;
        if (this.audio) this.audio.sfx('doorClose', { pos: object.getWorldPosition(new THREE.Vector3()), volume: 0.8 });
        this._doorAnims.push({ handle, from: object.rotation.y, to: baseRotation, t: 0, dur: 0.9, opening: false });
        if (opts.onClose) opts.onClose(handle);
      },
    };
    handle.interact = this.interact.add(object, {
      prompt: opts.prompt || '开门',
      onUse: () => {
        if (handle.isOpen) { handle.close(); return; }
        if (handle.isLocked) {
          if (this.audio) this.audio.sfx('doorLocked', { pos: object.getWorldPosition(new THREE.Vector3()), volume: 0.8 });
          if (opts.lockedText) this.ui.subtitle(opts.lockedText, 2.4);
          if (opts.onLocked) opts.onLocked(handle);
          return;
        }
        handle.open();
      },
    });
    return handle;
  }

  _updateDoors(dt) {
    for (let i = this._doorAnims.length - 1; i >= 0; i--) {
      const a = this._doorAnims[i];
      a.t += dt;
      const k = clamp(a.t / a.dur, 0, 1);
      const e = 1 - Math.pow(1 - k, 3);
      a.handle.object.rotation.y = a.from + (a.to - a.from) * e;
      if (k >= 1) {
        a.handle.busy = false;
        if (!a.opening) this.colliders.setEnabled(a.handle.collider, true);
        this._doorAnims.splice(i, 1);
      }
    }
  }

  /* ================= 关卡工具 ================= */
  find(name) { return this.level ? this.level.getObjectByName(name) : null; }

  getMarker(name) {
    if (!name) return null;
    const direct = this.markers.get(name);
    if (direct) return direct.getWorldPosition(new THREE.Vector3());
    for (const prefix of ['SPAWN_', 'LOOK_', 'MARK_']) {
      const o = this.markers.get(prefix + name);
      if (o) return o.getWorldPosition(new THREE.Vector3());
    }
    return null;
  }

  setVisible(name, visible) {
    const o = this.find(name);
    if (o) o.visible = !!visible;
    return o;
  }

  setVariants(prefix, visible) {
    for (const [name, o] of this.variants) {
      if (name.startsWith(prefix)) o.visible = !!visible;
    }
  }

  showEntity(name, visible = true) {
    const e = this.entities.get(name);
    if (e) e.visible = !!visible;
    return e;
  }

  setLight(name, on, intensityScale = 1) {
    const entry = this._lightEntries.find((l) => l.name === name);
    if (!entry) return null;
    entry.scale = on ? intensityScale : 0;
    entry.disabled = !on;
    entry.light.intensity = on ? entry.base * intensityScale : 0;
    return entry;
  }

  createReflectionScene() {
    const s = new THREE.Scene();
    s.background = this.scene.background ? this.scene.background.clone() : null;
    if (this.scene.fog) s.fog = this.scene.fog.clone();
    if (!this.level) return s;
    const clone = this.level.clone(true);
    s.add(clone);
    if (this.ambient) s.add(this.ambient.clone());
    if (this.directional) s.add(this.directional.clone());
    for (const entry of this._lightEntries) {
      const l = entry.light.clone();
      if (entry.light.isSpotLight) {
        const target = new THREE.Object3D();
        target.position.copy(entry.light.target.position);
        s.add(target);
        l.target = target;
      }
      l.intensity = entry.disabled ? 0 : entry.light.intensity;
      s.add(l);
    }
    this.reflectionScene = s;
    return s;
  }

  createMirror(meshName, opts = {}) {
    const mesh = this.find(meshName);
    if (!mesh) { console.warn('[mirror] 找不到镜面：', meshName); return null; }
    const refScene = opts.scene || this.createReflectionScene();
    const mirror = new PlanarMirror({
      mesh, renderer: this.renderer, camera: this.camera,
      getScene: () => refScene,
      resolutionScale: opts.resolutionScale || 0.55,
      grime: this.textures.get('MAT_mirror_grime') || null,
      tint: opts.tint || 0xa8b7ae,
      grimeStrength: opts.grimeStrength == null ? 0.55 : opts.grimeStrength,
    });
    this.mirror = mirror;
    return mirror;
  }

  /* ================= 危险 / 理智 ================= */
  setThreat(v) { this.threat = clamp(v, 0, 1); if (this.audio) this.audio.setThreat(this.threat); }
  setSanity(v) { this.sanity = clamp(v, 0, 1); }
  addSanity(d) { this.setSanity(this.sanity + d); }

  /** 简单视线检测：实体是否在玩家视野内且无遮挡 */
  isLookingAt(object, { maxDistance = 30, fovDot = 0.55 } = {}) {
    if (!object) return false;
    let vis = object;
    while (vis) { if (vis.visible === false) return false; vis = vis.parent; }
    const eye = this.camera.getWorldPosition(new THREE.Vector3());
    const target = new THREE.Vector3();
    if (object.isMesh) target.setFromMatrixPosition(object.matrixWorld);
    else object.getWorldPosition(target);
    target.y = Math.min(target.y + 1.15, eye.y + 0.55);
    const to = target.clone().sub(eye);
    const dist = to.length();
    if (dist > maxDistance) return false;
    to.normalize();
    const fwd = new THREE.Vector3();
    this.camera.getWorldDirection(fwd);
    if (fwd.dot(to) < fovDot) return false;
    // far 放大一点，避免射线停在被观察物表面之前（实体根节点在脚底，包围盒会略近/略远）
    const ray = new THREE.Raycaster(eye, to, 0.05, dist + 0.6);
    const hits = ray.intersectObject(this.level, true);
    for (const h of hits) {
      let o = h.object;
      let isTarget = false;
      let hidden = false;
      while (o) {
        if (o === object) { isTarget = true; break; }
        if (o.visible === false) { hidden = true; break; }
        o = o.parent;
      }
      if (hidden) continue;
      if (isTarget) return true;
      return false;
    }
    return false;
  }

  /* ================= 循环 ================= */
  _loop() {
    requestAnimationFrame(() => this._loop());
    const dt = Math.min(0.05, this.clock.getDelta());
    this.time += dt;
    this.ui.update(dt);
    this.touchControls?.update();

    if (this.state === 'playing') {
      this.player.update(dt);
      this.interact.update(dt);
      try { if (this.config.update) this.config.update(this, dt); } catch (err) { console.error('update 出错', err); }
      this.audio.update(dt, this.camera);
    } else if (this.state === 'title') {
      this._titleIdle(dt);
    }

    this._updateDoors(dt);
    this._updateLightFlicker(dt);

    this._sanitySmooth = damp(this._sanitySmooth, this.sanity, 3.5, dt);
    this._threatSmooth = damp(this._threatSmooth, this.threat, 2.5, dt);
    const u = this.postfx.uniforms;
    u.uTime.value = this.time;
    u.uSanity.value = this._sanitySmooth;
    u.uThreat.value = this._threatSmooth;
    u.uGrain.value = 0.06 + this._sanitySmooth * 0.09 + this._threatSmooth * 0.04;
    u.uChroma.value = 0.8 + this._sanitySmooth * 2.6;
    u.uVignette.value = 0.5 + this._sanitySmooth * 0.25 + this._threatSmooth * 0.1;

    if (this.mirror && this.state !== 'title') {
      try { this.mirror.update(this.time, dt); } catch (err) { console.warn('mirror 渲染失败', err); this.mirror = null; }
    }
    this.postfx.render(this.scene, this.camera);
  }

  _titleIdle(dt) {
    // 标题界面背后：保持极慢的视角漂移
    if (!this.player) return;
    const cam = this.camera;
    const start = this.getMarker((this.config.playerStart || {}).spawn || 'SPAWN_main');
    if (start) {
      cam.position.set(start.x, start.y + 1.62, start.z);
      const look = this.getMarker((this.config.playerStart || {}).look || 'LOOK_main');
      if (look) {
        const yaw = Math.atan2(-(look.x - start.x), -(look.z - start.z));
        cam.rotation.set(-0.03, yaw + Math.sin(this.time * 0.06) * 0.06, 0, 'YXZ');
      }
    }
  }

  _updateLightFlicker(dt) {
    if (!this._lightEntries) return;
    const t = this.time;
    for (const e of this._lightEntries) {
      if (e.disabled) { e.light.intensity = 0; continue; }
      const scale = e.scale == null ? 1 : e.scale;
      if (!e.flicker) { e.light.intensity = e.base * scale; continue; }
      const n = Math.sin(t * 9.1 + e.seed) * Math.sin(t * 3.7 + e.seed * 2.3);
      let f = 1 - e.flicker * (0.35 + 0.65 * Math.abs(n));
      if (Math.random() < e.flicker * 0.006) f *= 0.25;
      e.light.intensity = e.base * scale * clamp(f, 0.1, 1);
    }
  }

  /* ================= 事件 ================= */
  _bindGlobalEvents() {
    window.addEventListener('resize', this._resizeHandler);
    document.addEventListener('pointerlockchange', () => {
      const locked = document.pointerLockElement === this.canvas;
      // 只有“自动/键鼠”模式依赖指针锁定；拖动与触屏模式丢锁不应触发暂停。
      const lockMode = !this.touchEnabled && this.settings.inputMode !== 'drag';
      if (!locked && this.state === 'playing' && lockMode) this.pause();
      if (locked && this.state === 'playing') document.body.classList.add('sg-playing');
    });
    this.canvas.addEventListener('click', () => {
      if (this.state === 'playing' && document.pointerLockElement !== this.canvas) this._requestLock();
    });
    document.addEventListener('visibilitychange', () => {
      if (document.hidden && this.state === 'playing') this.pause();
    });
    window.addEventListener('keydown', (e) => {
      if (e.code === 'KeyE') {
        if (e.repeat) return;
        if (this.state === 'paper') { e.preventDefault(); this.closePaper(); return; }
        if (this.state === 'playing') { e.preventDefault(); this.interact.use(); }
      }
      if (e.code === 'Escape' && this.ui.isJournalOpen()) {
        e.preventDefault();
        this.closeJournal();
        return;
      }
      if (e.code === 'Escape' && this.state === 'playing') {
        // pointerlock 退出会触发 pause，这里兜底
        setTimeout(() => { if (this.state === 'playing') this.pause(); }, 0);
      }
    });
  }

  _onResize() {
    const w = window.innerWidth, h = window.innerHeight;
    this.renderer.setSize(w, h, false);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.postfx.setSize(w, h);
    if (this.mirror) this.mirror.resize();
  }
}

export { CollisionWorld };
