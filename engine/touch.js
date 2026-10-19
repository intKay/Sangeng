/* Independent pointers for movement and looking; touch never requires pointer lock. */
import { clamp } from './utils.js';
export const prefersTouch = () => matchMedia('(pointer: coarse)').matches ||
  (navigator.maxTouchPoints > 0 && !matchMedia('(any-pointer: fine)').matches);

export class TouchControls {
  constructor(game) {
    this.game = game;
    this.movePointer = this.lookPointer = null;
    this.active = false;
    this.root = document.createElement('div');
    this.root.id = 'sg-touch';
    this.root.innerHTML = `
      <div class="sg-touch-note">建议横屏 · 左侧移动，右侧滑动环视</div>
      <button class="sg-touch-pause" aria-label="暂停游戏">暂停</button>
      <div class="sg-look-zone" aria-label="在此滑动环视"></div>
      <div class="sg-stick" aria-label="移动摇杆"><span></span><i></i></div>
      <div class="sg-touch-actions">
        <button data-touch="run" aria-pressed="false">快走</button>
        <button data-touch="light" hidden>手电</button>
        <button data-touch="use" class="sg-touch-use">交互</button>
      </div>`;
    document.body.appendChild(this.root);
    this.stick = this.root.querySelector('.sg-stick');
    this.knob = this.stick.querySelector('i');
    this.look = this.root.querySelector('.sg-look-zone');
    this.run = this.root.querySelector('[data-touch="run"]');
    this.light = this.root.querySelector('[data-touch="light"]');
    this.use = this.root.querySelector('[data-touch="use"]');
    this.root.querySelector('.sg-touch-pause').addEventListener('click', () => game.pause());
    this.run.addEventListener('click', () => {
      if (game.state !== 'playing') return;
      game.player.touch.run = !game.player.touch.run;
      this.run.setAttribute('aria-pressed', String(game.player.touch.run));
    });
    this.use.addEventListener('click', () => { if (game.state === 'playing') game.interact.use(); });
    this.light.addEventListener('click', () => { if (game.state === 'playing') game.player.toggleFlashlight(); });
    this.bindPad(this.stick, 'move');
    this.bindPad(this.look, 'look');
    window.addEventListener('blur', () => { this.reset(); if (game.state === 'playing') game.pause(); });
    window.addEventListener('resize', () => this.reset());
    document.addEventListener('visibilitychange', () => this.reset());
    this.configure();
  }
  configure() {
    const g = this.game;
    g.touchEnabled = g.settings.inputMode === 'touch' || (g.settings.inputMode !== 'mouse' &&
      (prefersTouch() || typeof g.canvas.requestPointerLock !== 'function'));
    document.body.classList.toggle('sg-touch-mode', g.touchEnabled);
    g.ui.root.querySelector('.sg-title-hint').textContent = g.touchEnabled ?
      '建议戴耳机 · 左侧移动，右侧滑动环视 · 点击暂停可调整设置' :
      '建议戴耳机 · 点击开始后鼠标锁定 · Esc 暂停';
    g.ui.root.querySelector('.sg-paper-foot').textContent = g.touchEnabled ? '点击「合上」继续' : '按 E 或点击「合上」';
    this.reset();
  }
  bindPad(pad, kind) {
    const slot = kind === 'move' ? 'movePointer' : 'lookPointer';
    pad.addEventListener('pointerdown', e => {
      if (!this.game.touchEnabled || this.game.state !== 'playing' || this[slot] !== null) return;
      e.preventDefault(); this[slot] = e.pointerId; pad.setPointerCapture(e.pointerId);
      if (kind === 'move') this.move(e);
      else this.lastLook = { x: e.clientX, y: e.clientY };
    });
    pad.addEventListener('pointermove', e => {
      if (e.pointerId !== this[slot] || this.game.state !== 'playing') return;
      e.preventDefault();
      if (kind === 'move') this.move(e);
      else {
        const p = this.game.player, s = this.game.settings.sensitivity * 0.004;
        p.yaw -= (e.clientX - this.lastLook.x) * s;
        p.pitch = clamp(p.pitch - (e.clientY - this.lastLook.y) * s, -1.45, 1.45);
        this.lastLook = { x: e.clientX, y: e.clientY };
      }
    });
    const release = e => {
      if (e.pointerId !== this[slot]) return;
      this[slot] = null;
      if (kind === 'move') this.clearMovement();
    };
    for (const event of ['pointerup', 'pointercancel', 'lostpointercapture']) pad.addEventListener(event, release);
  }
  move(e) {
    const r = this.stick.getBoundingClientRect(), radius = r.width * 0.34;
    let x = (e.clientX - r.left - r.width / 2) / radius;
    let y = (e.clientY - r.top - r.height / 2) / radius;
    const length = Math.hypot(x, y);
    if (length > 1) { x /= length; y /= length; }
    if (length < 0.1) x = y = 0;
    this.game.player.touch.x = x; this.game.player.touch.y = -y;
    this.knob.style.transform = `translate(${x * radius}px, ${y * radius}px)`;
  }
  clearMovement() {
    this.game.player.touch.x = this.game.player.touch.y = 0;
    this.knob.style.transform = '';
  }
  reset() {
    for (const [pad, id] of [[this.stick, this.movePointer], [this.look, this.lookPointer]]) {
      if (id !== null && pad.hasPointerCapture(id)) pad.releasePointerCapture(id);
    }
    this.movePointer = this.lookPointer = null;
    this.clearMovement(); this.game.player.touch.run = false;
    this.run.setAttribute('aria-pressed', 'false');
  }
  update() {
    const active = this.game.touchEnabled && this.game.state === 'playing';
    if (active !== this.active) {
      this.active = active; this.root.classList.toggle('show', active);
      if (!active) this.reset();
    }
    if (!active) return;
    this.light.hidden = !this.game.player.hasFlashlight;
    this.light.setAttribute('aria-pressed', String(this.game.player.flashlightOn));
    this.use.disabled = !this.game.interact.current;
  }
}
