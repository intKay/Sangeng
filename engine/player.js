/* 第一人称控制器：鼠标视角 / WASD / Shift 快走 / AABB 碰撞 / 头部摆动 / 脚步 / 手电 */
import * as THREE from 'three';
import { clamp, damp, randRange } from './utils.js';

export class Player {
  constructor(game) {
    this.game = game;
    this.camera = game.camera;
    this.cfg = game.config;
    this.eyeHeight = 1.62;
    this.radius = 0.32;
    this.walkSpeed = 2.4;
    this.runSpeed = 4.35;
    this.pos = new THREE.Vector3(0, 0, 0);
    this.vel = new THREE.Vector3();
    this.yaw = 0;
    this.pitch = 0;
    this.roll = 0;
    this.bobPhase = 0;
    this.enabled = false;
    this.sprinting = false;
    this.keys = Object.create(null);
    this.touch = { x: 0, y: 0, run: false };
    this._stepAccum = 0;
    this.onFootstep = null;
    this.flashlightOn = false;
    this.hasFlashlight = false;
    this.battery = 0;
    this.maxBattery = 0;
    this._lowWarned = false;
    this._flicker = 1;
    this._bindInput();
    if (this.cfg.flashlight) this._initFlashlight();
  }

  _bindInput() {
    window.addEventListener('keydown', (e) => {
      if (e.repeat) return;
      this.keys[e.code] = true;
      if (!this.enabled) return;
      if (e.code === 'KeyF' && this.hasFlashlight) { e.preventDefault(); this.toggleFlashlight(); }
    });
    window.addEventListener('keyup', (e) => { this.keys[e.code] = false; });
    window.addEventListener('blur', () => { this.keys = Object.create(null); });
    window.addEventListener('mousemove', (e) => {
      if (!this.enabled) return;
      if (document.pointerLockElement !== this.game.canvas) return;
      const s = this.game.settings.sensitivity * 0.0022;
      this.yaw -= e.movementX * s;
      this.pitch -= e.movementY * s;
      this.pitch = clamp(this.pitch, -1.45, 1.45);
    });
  }

  _initFlashlight() {
    const cfg = this.cfg.flashlight;
    this.maxBattery = cfg.batterySeconds || 120;
    this.battery = this.maxBattery;
    this.hasFlashlight = false;
    this.spot = new THREE.SpotLight(0xffe2b8, 0, 19, 0.5, 0.62, 1.15);
    this.spot.position.set(0.16, -0.1, 0);
    this.spot.target.position.set(0, 0, -1);
    this.spot.castShadow = false;
    this.camera.add(this.spot);
    this.camera.add(this.spot.target);
    this._baseIntensity = cfg.intensity || 2.4;
  }

  giveFlashlight() {
    this.hasFlashlight = true;
    if (this.spot) this.spot.visible = true;
    this.setFlashlight(true);
  }

  setFlashlight(on) {
    if (!this.hasFlashlight) on = false;
    if (this.battery <= 0) on = false;
    const changed = this.flashlightOn !== on;
    this.flashlightOn = on;
    if (this.spot) this.spot.visible = on;
    if (changed && this.game.audio) this.game.audio.sfx('flashlightClick', { volume: 0.5 });
    return changed;
  }

  toggleFlashlight() {
    if (!this.hasFlashlight) return;
    if (this.battery <= 0) {
      this.game.audio && this.game.audio.sfx('batteryLow', { volume: 0.35 });
      this.game.ui.subtitle('手电没有电了。', 1.8);
      return;
    }
    this.setFlashlight(!this.flashlightOn);
  }

  addBattery(seconds) {
    this.battery = clamp(this.battery + seconds, 0, this.maxBattery);
    this._lowWarned = false;
    if (this.battery > 0 && this.hasFlashlight) this.setFlashlight(true);
  }

  get batteryFraction() { return this.maxBattery ? this.battery / this.maxBattery : 0; }

  teleportTo(spawnName, lookName) {
    const spawn = this.game.getMarker(spawnName);
    if (spawn) this.pos.copy(spawn);
    else this.pos.set(0, 0, 0);
    this.vel.set(0, 0, 0);
    const look = this.game.getMarker(lookName);
    if (look) this.lookAt(look);
    this._syncCamera(0, true);
  }

  teleportToPos(pos, lookAt) {
    this.pos.copy(pos);
    this.vel.set(0, 0, 0);
    if (lookAt) this.lookAt(lookAt);
    this._syncCamera(0, true);
  }

  lookAt(v) {
    const eye = new THREE.Vector3(this.pos.x, this.pos.y + this.eyeHeight, this.pos.z);
    const d = new THREE.Vector3(v.x - eye.x, v.y - eye.y, v.z - eye.z);
    if (d.lengthSq() < 1e-6) return;
    d.normalize();
    this.yaw = Math.atan2(-d.x, -d.z);
    this.pitch = Math.asin(clamp(d.y, -1, 1));
  }

  setYawPitch(yaw, pitch) { this.yaw = yaw; this.pitch = clamp(pitch, -1.45, 1.45); }

  update(dt) {
    if (!this.enabled) { this._syncCamera(dt, false); return; }
    const k = this.keys;
    const fwd = clamp((k.KeyW || k.ArrowUp ? 1 : 0) - (k.KeyS || k.ArrowDown ? 1 : 0) + this.touch.y, -1, 1);
    const strafe = clamp((k.KeyD || k.ArrowRight ? 1 : 0) - (k.KeyA || k.ArrowLeft ? 1 : 0) + this.touch.x, -1, 1);
    this.sprinting = !!(k.ShiftLeft || k.ShiftRight || this.touch.run) && fwd > 0;
    const targetSpeed = this.sprinting ? this.runSpeed : this.walkSpeed;
    const sin = Math.sin(this.yaw), cos = Math.cos(this.yaw);
    let wx = -sin * fwd + cos * strafe;
    let wz = -cos * fwd - sin * strafe;
    const wl = Math.hypot(wx, wz);
    if (wl > 1) { wx /= wl; wz /= wl; }
    this.vel.x = damp(this.vel.x, wx * targetSpeed, 14, dt);
    this.vel.z = damp(this.vel.z, wz * targetSpeed, 14, dt);

    this._move(this.vel.x * dt, this.vel.z * dt);

    const speed = Math.hypot(this.vel.x, this.vel.z);
    // 头部摆动与脚步
    this.bobPhase += speed * dt * 2.0;
    const bobAmp = 0.012 + speed * 0.0045;
    const bobY = Math.sin(this.bobPhase * 2) * bobAmp;
    this.roll = Math.sin(this.bobPhase) * 0.005 * Math.min(1, speed / 2.4);
    if (speed > 0.35) {
      this._stepAccum += speed * dt;
      const interval = this.sprinting ? 0.52 : 0.66;
      if (this._stepAccum >= interval) {
        this._stepAccum = 0;
        this._footstep(speed);
      }
    } else {
      this._stepAccum = Math.min(this._stepAccum, 0.3);
    }

    // 手电电量与闪烁
    if (this.flashlightOn) {
      this.battery = Math.max(0, this.battery - dt);
      if (this.battery <= 0) {
        this.setFlashlight(false);
        this.game.ui.subtitle('手电灭了。', 1.6);
      } else if (this.battery < this.maxBattery * 0.2) {
        if (!this._lowWarned) {
          this._lowWarned = true;
          this.game.audio && this.game.audio.sfx('batteryLow', { volume: 0.4 });
          this.game.ui.subtitle('手电快没电了。', 1.8);
        }
        this._flicker = 0.35 + 0.65 * Math.random();
      } else {
        this._flicker = 0.92 + Math.random() * 0.08;
      }
    } else {
      this._flicker = 0;
    }
    if (this.spot) {
      const intensity = this.flashlightOn ? this._baseIntensity * this._flicker : 0;
      this.spot.intensity += (intensity - this.spot.intensity) * Math.min(1, dt * 22);
    }

    this._syncCamera(dt, false, bobY);
  }

  _footstep(speed) {
    if (this.onFootstep) {
      this.onFootstep(speed, this.sprinting);
      return;
    }
    const key = this.cfg.footstepSfx;
    if (!key || !this.game.audio || !this.game.audio.ready) return;
    this.game.audio.sfx(key, {
      volume: this.sprinting ? 0.85 : 0.55,
      rate: randRange(0.92, 1.08),
    });
  }

  _move(dx, dz) {
    const boxes = this.game.colliders.boxes;
    const r = this.radius;
    const p = this.pos;
    if (dx !== 0) {
      p.x += dx;
      for (let i = 0; i < boxes.length; i++) {
        const c = boxes[i];
        if (!c.enabled) continue;
        const b = c.box;
        if (p.x > b.min.x - r && p.x < b.max.x + r && p.z > b.min.z - r && p.z < b.max.z + r) {
          p.x = dx > 0 ? b.min.x - r : b.max.x + r;
        }
      }
    }
    if (dz !== 0) {
      p.z += dz;
      for (let i = 0; i < boxes.length; i++) {
        const c = boxes[i];
        if (!c.enabled) continue;
        const b = c.box;
        if (p.x > b.min.x - r && p.x < b.max.x + r && p.z > b.min.z - r && p.z < b.max.z + r) {
          p.z = dz > 0 ? b.min.z - r : b.max.z + r;
        }
      }
    }
  }

  _syncCamera(dt, snap = false, bobY = 0) {
    const cam = this.camera;
    const baseY = this.pos.y + this.eyeHeight + (bobY || 0);
    if (snap || dt <= 0) {
      cam.position.set(this.pos.x, baseY, this.pos.z);
    } else {
      cam.position.x = this.pos.x;
      cam.position.z = this.pos.z;
      cam.position.y += (baseY - cam.position.y) * Math.min(1, dt * 12);
    }
    cam.rotation.order = 'YXZ';
    cam.rotation.y = this.yaw;
    cam.rotation.x = this.pitch;
    cam.rotation.z = this.roll;
  }

  get position() { return this.pos; }
  get eyePosition() { return this.camera.position; }

  /** 玩家正前方单位向量 */
  getForward(out = new THREE.Vector3()) {
    return out.set(-Math.sin(this.yaw), 0, -Math.cos(this.yaw));
  }
}
