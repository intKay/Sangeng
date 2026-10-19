/* WebAudio 管理器：manifest 加载 / 音乐交叉淡化 / 环境层 / 空间音效 / 实时心跳与耳鸣 */
import { clamp, pick } from './utils.js';

export class AudioManager {
  constructor() {
    this.ctx = null;
    this.ready = false;
    this.manifest = null;
    this.manifestUrl = null;
    this.buffers = new Map();
    this.entries = { music: {}, ambience: {}, sfx: {}, ui: {} };
    this.missing = [];
    this.masterVolume = 0.8;
    this.threat = 0;
    this.music = null;
    this.ambiences = new Map();
    this.heartbeat = null;
    this.breath = null;
    this._hbTimer = 0;
    this._hbOn = false;
    this._lastListener = { pos: null, q: null };
  }

  /* ---------- 加载 ---------- */
  async load(manifestUrl, onProgress) {
    if (!manifestUrl) return;
    const absManifestUrl = new URL(manifestUrl, location.href).href;
    this.manifestUrl = absManifestUrl;
    let manifest;
    try {
      const res = await fetch(absManifestUrl, { cache: 'no-cache' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      manifest = await res.json();
    } catch (err) {
      console.warn('[audio] manifest 加载失败，将静音运行：', manifestUrl, err);
      this.missing.push(manifestUrl);
      return;
    }
    this.manifest = manifest;
    this._collect(manifest, absManifestUrl);

    const files = new Set();
    for (const cat of Object.keys(this.entries)) {
      for (const key of Object.keys(this.entries[cat])) {
        this.entries[cat][key].files.forEach((f) => files.add(f));
      }
    }
    let done = 0;
    const list = [...files];
    const raw = new Map();
    const limit = 6;
    let cursor = 0;
    const worker = async () => {
      while (cursor < list.length) {
        const url = list[cursor++];
        try {
          const res = await fetch(url, { cache: 'no-cache' });
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          raw.set(url, await res.arrayBuffer());
        } catch (err) {
          console.warn('[audio] 音频文件缺失：', url);
          this.missing.push(url);
        }
        done++;
        if (onProgress) onProgress(done / Math.max(1, list.length));
      }
    };
    await Promise.all(Array.from({ length: Math.min(limit, list.length) }, worker));
    if (!raw.size) return;

    try { this._initContext(); } catch (err) { console.warn('[audio] AudioContext 创建失败：', err); return; }

    const decodes = [];
    for (const [url, ab] of raw) {
      decodes.push(this.ctx.decodeAudioData(ab.slice(0)).then((buf) => {
        this.buffers.set(url, buf);
      }).catch((err) => {
        console.warn('[audio] 解码失败：', url, err);
        this.missing.push(url);
      }));
    }
    await Promise.all(decodes);
    this.ready = this.buffers.size > 0;
    if (!this.ready) console.warn('[audio] 没有可用音频 buffer');
  }

  _collect(manifest, manifestUrl) {
    // Older Safari can decode MP3 but not Ogg/Vorbis. Preserve variation arrays.
    const ogg = !!document.createElement('audio').canPlayType('audio/ogg; codecs="vorbis"');
    const cats = ['music', 'ambience', 'sfx', 'ui'];
    for (const cat of cats) {
      const src = manifest[cat] || {};
      for (const key of Object.keys(src)) {
        const def = src[key] || {};
        const files = (def.files || (def.file ? [def.file] : []))
          .map((f) => new URL(ogg ? f : f.replace(/\.ogg$/i, '.mp3'), manifestUrl).href);
        this.entries[cat][key] = {
          key, category: cat, files,
          volume: def.volume == null ? 1 : def.volume,
          loop: !!def.loop,
          fade: def.fade == null ? 2 : def.fade,
          rate: def.rate || 1,
        };
      }
    }
  }

  _initContext() {
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) throw new Error('no AudioContext');
    const ctx = new AC();
    this.ctx = ctx;

    this.master = ctx.createGain();
    this.master.gain.value = this.masterVolume;
    this.duckGain = ctx.createGain();
    this.duckGain.gain.value = 1;
    this.muffle = ctx.createBiquadFilter();
    this.muffle.type = 'lowpass';
    this.muffle.frequency.value = 20000;
    const comp = ctx.createDynamicsCompressor();
    comp.threshold.value = -18; comp.knee.value = 12; comp.ratio.value = 3;
    comp.attack.value = 0.005; comp.release.value = 0.3;
    this.master.connect(this.duckGain);
    this.duckGain.connect(this.muffle);
    this.muffle.connect(comp);
    comp.connect(ctx.destination);

    this.buses = {};
    for (const name of ['music', 'ambience', 'sfx', 'ui']) {
      const g = ctx.createGain();
      g.gain.value = name === 'ui' ? 0.7 : 1;
      g.connect(this.master);
      this.buses[name] = g;
    }

    // 混响：合成的暗房间脉冲
    this.reverb = ctx.createConvolver();
    this.reverb.buffer = this._impulse(2.6, 2.4);
    const wet = ctx.createGain();
    wet.gain.value = 0.5;
    this.reverb.connect(wet);
    wet.connect(this.master);
    this.reverbSend = {};
    for (const name of ['music', 'ambience', 'sfx']) {
      const s = ctx.createGain();
      s.gain.value = name === 'sfx' ? 0.16 : name === 'ambience' ? 0.12 : 0.1;
      this.buses[name].connect(s);
      s.connect(this.reverb);
      this.reverbSend[name] = s;
    }

    this.heartbeatGain = ctx.createGain();
    this.heartbeatGain.gain.value = 0;
    this.heartbeatGain.connect(this.master);
    this.breathGain = ctx.createGain();
    this.breathGain.gain.value = 0;
    this.breathGain.connect(this.master);
    this._setupListener();
  }

  _impulse(seconds, decay) {
    const ctx = this.ctx;
    const len = Math.max(1, Math.floor(ctx.sampleRate * seconds));
    const buf = ctx.createBuffer(2, len, ctx.sampleRate);
    for (let c = 0; c < 2; c++) {
      const d = buf.getChannelData(c);
      for (let i = 0; i < len; i++) {
        const t = i / len;
        d[i] = (Math.random() * 2 - 1) * Math.pow(1 - t, decay) * (i < 40 ? 0.2 : 1);
      }
    }
    return buf;
  }

  _setupListener() {
    const l = this.ctx.listener;
    if (l.positionX) {
      this._listenerModern = true;
      l.positionX.value = 0; l.positionY.value = 0; l.positionZ.value = 0;
      l.forwardX.value = 0; l.forwardY.value = 0; l.forwardZ.value = -1;
      l.upX.value = 0; l.upY.value = 1; l.upZ.value = 0;
    } else {
      this._listenerModern = false;
      l.setPosition(0, 0, 0);
      l.setOrientation(0, 0, -1, 0, 1, 0);
    }
  }

  unlock() {
    if (!this.ctx) return;
    if (this.ctx.state !== 'running' && this.ctx.state !== 'closed') this.ctx.resume().catch(() => {});
  }

  /* ---------- 基础播放 ---------- */
  _buffer(entry) {
    for (const url of entry.files) {
      const b = this.buffers.get(url);
      if (b) return b;
    }
    return null;
  }

  _entry(cat, key) {
    return this.entries[cat] && this.entries[cat][key] ? this.entries[cat][key] : null;
  }

  _makePanner(pos) {
    const p = this.ctx.createPanner();
    p.panningModel = 'HRTF';
    p.distanceModel = 'inverse';
    p.refDistance = 1.4;
    p.maxDistance = 30;
    p.rolloffFactor = 1.4;
    if (p.positionX) {
      p.positionX.value = pos.x; p.positionY.value = pos.y; p.positionZ.value = pos.z;
    } else {
      p.setPosition(pos.x, pos.y, pos.z);
    }
    return p;
  }

  /**
   * 播放一个音效。pos 为 THREE.Vector3 或 {x,y,z}（可选，空间化）。
   * 返回句柄：{ stop(fade), setVolume(v), source }
   */
  sfx(key, opts = {}) {
    const entry = this._entry(opts.category || 'sfx', key);
    if (!entry || !this.ready) return null;
    return this._play(entry, opts);
  }

  ui(key) {
    return this.sfx(key, { category: 'ui', volume: 0.55, wet: 0 });
  }

  _play(entry, opts = {}) {
    const ctx = this.ctx;
    const buffer = this._buffer(entry);
    if (!buffer) return null;
    const when = ctx.currentTime + (opts.delay || 0);
    const src = ctx.createBufferSource();
    src.buffer = buffer;
    src.loop = !!opts.loop;
    src.playbackRate.value = (opts.rate || 1) * (entry.rate || 1);
    const gain = ctx.createGain();
    // BufferSource 必须接入混音图；解码成功或 source.start() 本身不会输出声音。
    src.connect(gain);
    const target = Math.max(0.0001, (entry.volume == null ? 1 : entry.volume) * (opts.volume == null ? 1 : opts.volume));
    const attack = opts.attack == null ? 0.01 : opts.attack;
    gain.gain.setValueAtTime(0.0001, ctx.currentTime);
    gain.gain.linearRampToValueAtTime(target, ctx.currentTime + attack);
    let dest = gain;
    if (opts.pos) {
      const p = this._makePanner(opts.pos);
      gain.connect(p);
      dest = p;
    }
    if (opts.pan != null && !opts.pos) {
      const sp = ctx.createStereoPanner();
      sp.pan.value = clamp(opts.pan, -1, 1);
      gain.connect(sp);
      dest = sp;
    }
    dest.connect(opts.bus || this.buses[entry.category] || this.buses.sfx);
    if (opts.wet !== 0) {
      const send = ctx.createGain();
      send.gain.value = opts.wet == null ? 0.5 : opts.wet;
      dest.connect(send);
      send.connect(this.reverb);
    }
    const delay = opts.delay || 0;
    src.start(when);
    if (!src.loop && buffer.duration > 0) {
      // nothing; ended cleanup
    }
    const handle = {
      source: src, gain, entry,
      setVolume: (v) => gain.gain.setTargetAtTime(Math.max(0.0001, v), ctx.currentTime, 0.05),
      stop: (fade = 0.15) => {
        try {
          gain.gain.cancelScheduledValues(ctx.currentTime);
          gain.gain.setTargetAtTime(0.0001, ctx.currentTime, Math.max(0.01, fade / 3));
          src.stop(ctx.currentTime + fade + 0.05);
        } catch (e) { /* ignore */ }
      },
    };
    return handle;
  }

  /* ---------- 音乐 ---------- */
  playMusic(key, opts = {}) {
    const entry = this._entry('music', key);
    if (!entry || !this.ready) return null;
    if (this.music && this.music.key === key && !this.music.stopped) {
      if (opts.volume != null) this.music.handle.setVolume(entry.volume * opts.volume);
      return this.music.handle;
    }
    const fade = opts.fade == null ? entry.fade : opts.fade;
    if (this.music) this._fadeOutMusic(fade);
    const handle = this._play(entry, { loop: entry.loop !== false, volume: opts.volume == null ? 1 : opts.volume, attack: 0.8, wet: 0.4, category: 'music' });
    if (!handle) return null;
    this.music = { key, handle, stopped: false };
    return handle;
  }

  _fadeOutMusic(fade) {
    if (!this.music) return;
    const m = this.music;
    this.music = null;
    m.stopped = true;
    m.handle.stop(fade);
  }

  stopMusic(fade = 2) { this._fadeOutMusic(fade); }

  /* ---------- 环境层 ---------- */
  playAmbience(key, opts = {}) {
    const entry = this._entry('ambience', key);
    if (!entry || !this.ready) return null;
    const channel = opts.channel || 'main';
    const old = this.ambiences.get(channel);
    if (old && old.key === key) return old.handle;
    if (old) { old.handle.stop(opts.fade == null ? 2 : opts.fade); this.ambiences.delete(channel); }
    const handle = this._play(entry, { loop: true, volume: opts.volume == null ? 1 : opts.volume, attack: 1.2, wet: 0.35, category: 'ambience' });
    if (!handle) return null;
    this.ambiences.set(channel, { key, handle });
    return handle;
  }

  stopAmbience(channel = 'main', fade = 2) {
    const cur = this.ambiences.get(channel);
    if (!cur) return;
    this.ambiences.delete(channel);
    cur.handle.stop(fade);
  }

  /* ---------- 危险层：心跳 / 呼吸 / 耳鸣 ---------- */
  setThreat(v) {
    this.threat = clamp(v, 0, 1);
    if (!this.ready) return;
    const ctx = this.ctx;
    const now = ctx.currentTime;
    const hbEntry = this._entry('sfx', 'heartbeat');
    if (hbEntry && !this.heartbeat) {
      const h = this._play(hbEntry, { loop: true, volume: 0.0001, attack: 0.1, wet: 0.25 });
      if (h) { this.heartbeat = h; h.gain.gain.setValueAtTime(0.0001, now); }
    }
    if (this.heartbeat) {
      const target = 0.0001 + this.threat * 0.55;
      this.heartbeat.gain.gain.setTargetAtTime(target, now, 0.35);
      this.heartbeat.source.playbackRate.setTargetAtTime(0.9 + this.threat * 1.5, now, 0.5);
    }
    const brEntry = this._entry('sfx', 'breath');
    if (brEntry && !this.breath && this.threat > 0.05) {
      const b = this._play(brEntry, { loop: true, volume: 0.0001, attack: 1.2, wet: 0.4 });
      if (b) { this.breath = b; b.gain.gain.setValueAtTime(0.0001, now); }
    }
    if (this.breath) {
      const target = 0.0001 + Math.pow(this.threat, 2) * 0.4;
      this.breath.gain.gain.setTargetAtTime(target, now, 0.6);
      this.breath.source.playbackRate.setTargetAtTime(0.9 + this.threat * 0.5, now, 0.6);
    }
  }

  _synthHeartbeat(strength) {
    if (!this.ctx) return;
    const ctx = this.ctx;
    const t = ctx.currentTime;
    const thump = (freq, gain, dur) => {
      const o = ctx.createOscillator();
      const g = ctx.createGain();
      o.type = 'sine'; o.frequency.setValueAtTime(freq, t);
      o.frequency.exponentialRampToValueAtTime(freq * 0.55, t + dur);
      g.gain.setValueAtTime(0.0001, t);
      g.gain.linearRampToValueAtTime(gain, t + 0.012);
      g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
      o.connect(g); g.connect(this.heartbeatGain);
      o.start(t); o.stop(t + dur + 0.05);
    };
    thump(52, 0.5 * strength, 0.18);
    thump(44, 0.32 * strength, 0.22);
  }

  /* ---------- 更新 ---------- */
  update(dt, camera) {
    if (!this.ready) return;
    if (camera) this._updateListener(camera);
    // 没有心跳音频文件时用合成音
    if (!this.heartbeat && this.threat > 0.08) {
      this._hbTimer -= dt * (1 + this.threat * 1.8);
      if (this._hbTimer <= 0) {
        this._hbTimer = 0.85;
        this._synthHeartbeat(0.25 + this.threat * 0.75);
      }
    }
    if (this.heartbeatGain) {
      this.heartbeatGain.gain.setTargetAtTime(0.35 * this.threat, this.ctx.currentTime, 0.4);
    }
  }

  _updateListener(camera) {
    if (this._listenerModern == null) return;
    const l = this.ctx.listener;
    const pos = camera.position;
    const q = camera.quaternion;
    const fx = -2 * (q.x * q.z + q.w * q.y);
    const fy = 2 * (q.y * q.z - q.w * q.x);
    const fz = -(1 - 2 * (q.x * q.x + q.y * q.y));
    const ux = 2 * (q.x * q.y - q.w * q.z);
    const uy = 1 - 2 * (q.x * q.x + q.z * q.z);
    const uz = 2 * (q.y * q.z + q.w * q.x);
    const now = this.ctx.currentTime;
    if (this._listenerModern) {
      try {
        l.positionX.setTargetAtTime(pos.x, now, 0.02);
        l.positionY.setTargetAtTime(pos.y, now, 0.02);
        l.positionZ.setTargetAtTime(pos.z, now, 0.02);
        l.forwardX.setTargetAtTime(fx, now, 0.02);
        l.forwardY.setTargetAtTime(fy, now, 0.02);
        l.forwardZ.setTargetAtTime(fz, now, 0.02);
        l.upX.setTargetAtTime(ux, now, 0.02);
        l.upY.setTargetAtTime(uy, now, 0.02);
        l.upZ.setTargetAtTime(uz, now, 0.02);
      } catch (e) { /* ignore */ }
    } else {
      l.setPosition(pos.x, pos.y, pos.z);
      l.setOrientation(fx, fy, fz, ux, uy, uz);
    }
  }

  /* ---------- 控制 ---------- */
  setMasterVolume(v) {
    this.masterVolume = clamp(v, 0, 1);
    if (this.master) this.master.gain.setTargetAtTime(this.masterVolume, this.ctx.currentTime, 0.08);
  }

  duck(on) {
    if (!this.duckGain) return;
    this.duckGain.gain.setTargetAtTime(on ? 0.35 : 1, this.ctx.currentTime, 0.2);
  }

  muffleOn(on) {
    if (!this.muffle) return;
    this.muffle.frequency.setTargetAtTime(on ? 900 : 20000, this.ctx.currentTime, 0.2);
  }

  stopAll(fade = 1.5) {
    this._fadeOutMusic(fade);
    for (const [ch] of this.ambiences) this.stopAmbience(ch, fade);
    if (this.heartbeat) { this.heartbeat.stop(fade); this.heartbeat = null; }
    if (this.breath) { this.breath.stop(fade); this.breath = null; }
    this.setThreat(0);
  }
}

