/* DOM 界面：标题 / 加载 / HUD / 字幕 / 暂停 / 设置 / 死亡 / 结局 / 信纸 */
import { clamp } from './utils.js';

const TEMPLATE = `
<div id="sg-fade"></div>
<div id="sg-loading">
  <div class="sg-load-inner">
    <div class="sg-load-kicker">SANGENG · 三更</div>
    <div class="sg-load-title"></div>
    <div class="sg-load-bar"><i></i></div>
    <div class="sg-load-label">正在布置房间…</div>
  </div>
</div>
<div id="sg-title" class="sg-screen">
  <div class="sg-title-bg"></div>
  <div class="sg-title-grain"></div>
  <div class="sg-title-inner">
    <div class="sg-chapter"></div>
    <h1 class="sg-title-h1"></h1>
    <div class="sg-title-en"></div>
    <p class="sg-warning"></p>
    <div class="sg-buttons">
      <button data-act="start" class="sg-btn primary">开始</button>
      <button data-act="settings" class="sg-btn">设置</button>
      <button data-act="back" class="sg-btn">返回入口</button>
    </div>
    <div class="sg-title-hint">建议戴耳机 · 点击开始后鼠标锁定 · Esc 暂停</div>
  </div>
  <div class="sg-title-footer">三更 / SANGENG</div>
</div>
<div id="sg-hud">
  <div id="sg-objective"><span class="lbl">当前</span><span class="txt"></span></div>
  <div id="sg-counter"></div>
  <div id="sg-crosshair"></div>
  <div id="sg-prompt"></div>
  <div id="sg-subtitle"></div>
  <div id="sg-battery"><span class="cap">手电</span><div class="bar"><i></i></div></div>
</div>
<div id="sg-pause" class="sg-screen">
  <div class="sg-panel">
    <div class="sg-panel-kicker">PAUSED</div>
    <h2>暂停</h2>
    <div class="sg-buttons column">
      <button data-act="resume" class="sg-btn primary">继续</button>
      <button data-act="settings" class="sg-btn">设置</button>
      <button data-act="back" class="sg-btn">返回入口</button>
    </div>
    <p class="sg-panel-note">心跳还在继续。</p>
  </div>
</div>
<div id="sg-settings" class="sg-screen">
  <div class="sg-panel wide">
    <div class="sg-panel-kicker">SETTINGS</div>
    <h2>设置</h2>
    <label class="sg-field"><span>视角灵敏度</span><input type="range" data-set="sensitivity" min="0.2" max="3" step="0.05"><b class="val"></b></label>
    <label class="sg-field"><span>操作方式</span><select data-set="inputMode"><option value="auto">自动识别</option><option value="touch">触屏 / 拖动</option><option value="mouse">键盘 / 鼠标</option></select><b class="val"></b></label>
    <label class="sg-field"><span>主音量</span><input type="range" data-set="volume" min="0" max="1" step="0.02"><b class="val"></b></label>
    <label class="sg-field"><span>渲染颗粒度</span>
      <select data-set="renderScale">
        <option value="0.45">粗颗粒（低分辨率）</option>
        <option value="0.6">标准</option>
        <option value="0.8">清晰</option>
      </select><b class="val"></b></label>
    <label class="sg-field inline"><span>字幕</span><input type="checkbox" data-set="subtitles"></label>
    <div class="sg-buttons row">
      <button data-act="settings-back" class="sg-btn primary">返回</button>
    </div>
  </div>
</div>
<div id="sg-death" class="sg-screen">
  <div class="sg-panel">
    <div class="sg-panel-kicker">SOMETHING TOOK YOU</div>
    <h2 class="sg-death-title">你被留下了</h2>
    <p class="sg-death-text"></p>
    <div class="sg-buttons column">
      <button data-act="retry" class="sg-btn primary">再来一次</button>
      <button data-act="back" class="sg-btn">返回入口</button>
    </div>
  </div>
</div>
<div id="sg-ending" class="sg-screen">
  <div class="sg-ending-inner">
    <div class="sg-chapter"></div>
    <h1 class="sg-ending-title"></h1>
    <div class="sg-ending-lines"></div>
    <div class="sg-ending-footer"></div>
    <div class="sg-buttons row">
      <button data-act="replay" class="sg-btn primary">再走一遍</button>
      <button data-act="back" class="sg-btn">返回入口</button>
    </div>
  </div>
</div>
<div id="sg-paper" class="sg-screen">
  <div class="sg-paper-sheet">
    <div class="sg-paper-head"></div>
    <div class="sg-paper-body"></div>
    <div class="sg-paper-foot">按 E 或点击「合上」</div>
    <button data-act="paper-close" class="sg-btn primary">合上</button>
  </div>
</div>
<div id="sg-transition"></div>
`;

const actOf = (el) => el && el.closest ? el.closest('[data-act]') : null;

export class UI {
  constructor(game) {
    this.game = game;
    this.cfg = game.config;
    this.subtitleTimer = 0;
    this.subtitleQueue = [];
    this.paperOnClose = null;
    const root = document.createElement('div');
    root.id = 'sg-root';
    root.innerHTML = TEMPLATE;
    document.body.appendChild(root);
    this.root = root;
    this.el = {
      fade: root.querySelector('#sg-fade'),
      loading: root.querySelector('#sg-loading'),
      loadingTitle: root.querySelector('.sg-load-title'),
      loadingBar: root.querySelector('.sg-load-bar i'),
      loadingLabel: root.querySelector('.sg-load-label'),
      title: root.querySelector('#sg-title'),
      titleBg: root.querySelector('.sg-title-bg'),
      chapter: root.querySelector('#sg-title .sg-chapter'),
      titleH1: root.querySelector('#sg-title .sg-title-h1'),
      titleEn: root.querySelector('#sg-title .sg-title-en'),
      warning: root.querySelector('#sg-title .sg-warning'),
      hud: root.querySelector('#sg-hud'),
      objective: root.querySelector('#sg-objective .txt'),
      counter: root.querySelector('#sg-counter'),
      prompt: root.querySelector('#sg-prompt'),
      subtitle: root.querySelector('#sg-subtitle'),
      battery: root.querySelector('#sg-battery'),
      batteryFill: root.querySelector('#sg-battery .bar i'),
      pause: root.querySelector('#sg-pause'),
      settings: root.querySelector('#sg-settings'),
      death: root.querySelector('#sg-death'),
      deathText: root.querySelector('#sg-death .sg-death-text'),
      ending: root.querySelector('#sg-ending'),
      endingChapter: root.querySelector('#sg-ending .sg-chapter'),
      endingTitle: root.querySelector('#sg-ending .sg-ending-title'),
      endingLines: root.querySelector('#sg-ending .sg-ending-lines'),
      endingFooter: root.querySelector('#sg-ending .sg-ending-footer'),
      paper: root.querySelector('#sg-paper'),
      paperHead: root.querySelector('#sg-paper .sg-paper-head'),
      paperBody: root.querySelector('#sg-paper .sg-paper-body'),
    };
    this._applyTheme();
    this._bind();
  }

  _applyTheme() {
    const t = this.cfg.theme || {};
    const style = this.root.style;
    style.setProperty('--sg-accent', t.accent || '#c9a55a');
    style.setProperty('--sg-ink', t.ink || '#d8d2c0');
    style.setProperty('--sg-bg', t.bg || '#080a09');
  }

  _bind() {
    this.root.addEventListener('click', (e) => {
      const btn = actOf(e.target);
      if (!btn) return;
      const act = btn.dataset.act;
      this.game.audio && this.game.audio.ui('click');
      switch (act) {
        case 'start': this.game.start(); break;
        case 'settings': this.game.openSettings(); break;
        case 'settings-back': this.game.closeSettings(); break;
        case 'back': this.game.goHome(); break;
        case 'resume': this.game.resume(); break;
        case 'retry': this.game.retry(); break;
        case 'replay': this.game.replay(); break;
        case 'paper-close': this._closePaper(); break;
      }
    });
    this.root.addEventListener('mouseover', (e) => {
      const btn = actOf(e.target);
      if (btn && this.game.audio) this.game.audio.ui('hover');
    });
    // 设置控件
    this.root.querySelectorAll('[data-set]').forEach((input) => {
      const evt = input.tagName === 'SELECT' || input.type === 'checkbox' ? 'change' : 'input';
      input.addEventListener(evt, () => {
        const key = input.dataset.set;
        let val;
        if (input.type === 'checkbox') val = input.checked;
        else if (input.type === 'range') val = parseFloat(input.value);
        else val = input.tagName === 'SELECT' && key !== 'inputMode' ? parseFloat(input.value) : input.value;
        const s = this.game.settings;
        if (key === 'subtitles') s.subtitles = !!val;
        else if (key === 'inputMode') s.inputMode = val;
        else if (key === 'renderScale') s.renderScale = parseFloat(val);
        else if (key === 'sensitivity') s.sensitivity = parseFloat(val);
        else if (key === 'volume') s.volume = parseFloat(val);
        this.game.applySettings();
        this.syncSettingsLabels();
      });
    });
    this.syncSettingsLabels();
  }

  syncSettingsLabels() {
    const s = this.game.settings;
    this.root.querySelectorAll('[data-set]').forEach((input) => {
      const key = input.dataset.set;
      if (key === 'subtitles') input.checked = !!s.subtitles;
      else if (key === 'inputMode') input.value = s.inputMode;
      else if (key === 'renderScale') input.value = String(s.renderScale);
      else if (key === 'sensitivity') input.value = String(s.sensitivity);
      else if (key === 'volume') input.value = String(s.volume);
      const valEl = input.parentElement.querySelector('.val');
      if (valEl) {
        if (key === 'sensitivity') valEl.textContent = s.sensitivity.toFixed(2);
        else if (key === 'volume') valEl.textContent = Math.round(s.volume * 100) + '%';
        else if (key === 'renderScale') valEl.textContent = '';
      }
    });
  }

  setConfig(cfg) {
    this.cfg = cfg;
    this._applyTheme();
    this.el.chapter.textContent = cfg.chapter || '';
    this.el.titleH1.textContent = cfg.title || '';
    this.el.titleEn.textContent = cfg.titleEn || '';
    this.el.warning.textContent = cfg.warning || '';
    this.el.loadingTitle.textContent = cfg.title || '';
    if (cfg.poster) this.el.titleBg.style.backgroundImage = `url("${cfg.poster}")`;
  }

  /* ---------- 加载 / 标题 ---------- */
  showLoading() { this.el.loading.classList.add('show'); }
  hideLoading() { this.el.loading.classList.remove('show'); }
  setLoading(progress, label) {
    this.el.loadingBar.style.width = `${Math.round(clamp(progress, 0, 1) * 100)}%`;
    if (label) this.el.loadingLabel.textContent = label;
  }
  showTitle() {
    this.el.title.classList.add('show');
    document.body.classList.add('sg-at-title');
  }
  hideTitle() {
    this.el.title.classList.remove('show');
    document.body.classList.remove('sg-at-title');
  }
  setHudVisible(on) { this.el.hud.classList.toggle('show', !!on); }
  setCrosshair(on) { this.el.hud.classList.toggle('no-crosshair', !on); }

  /* ---------- HUD ---------- */
  setObjective(text) {
    const t = this.el.objective;
    if (!text) { t.textContent = ''; t.parentElement.classList.remove('show'); return; }
    if (t.textContent !== text) t.textContent = text;
    t.parentElement.classList.add('show');
  }
  setCounter(text) {
    this.el.counter.textContent = text || '';
    this.el.counter.classList.toggle('show', !!text);
  }
  setPrompt(text) {
    this.el.prompt.textContent = text || '';
    this.el.prompt.classList.toggle('show', !!text);
  }
  setBattery(frac) {
    if (frac == null) { this.el.battery.classList.remove('show'); return; }
    this.el.battery.classList.add('show');
    const pct = clamp(frac, 0, 1);
    this.el.batteryFill.style.width = `${Math.round(pct * 100)}%`;
    this.el.battery.classList.toggle('low', pct < 0.2);
  }
  subtitle(text, dur) {
    if (!this.game.settings.subtitles) return;
    const d = dur == null ? clamp(1.6 + text.length * 0.075, 1.8, 6.5) : dur;
    this.subtitleQueue.push({ text, dur: d });
    if (!this.subtitleTimer) this._nextSubtitle();
  }
  clearSubtitles() {
    this.subtitleQueue.length = 0;
    this.subtitleTimer = 0;
    this.el.subtitle.classList.remove('show');
    this.el.subtitle.textContent = '';
  }
  _nextSubtitle() {
    const item = this.subtitleQueue.shift();
    if (!item) {
      this.el.subtitle.classList.remove('show');
      this.el.subtitle.textContent = '';
      this.subtitleTimer = 0;
      return;
    }
    this.el.subtitle.textContent = item.text;
    this.el.subtitle.classList.add('show');
    this.subtitleTimer = item.dur;
  }

  /* ---------- 淡入淡出 ---------- */
  fade(alpha, ms = 600) {
    this.el.fade.style.transition = `opacity ${ms}ms ease`;
    this.el.fade.style.opacity = String(clamp(alpha, 0, 1));
    return new Promise((resolve) => setTimeout(resolve, ms + 30));
  }
  fadeIn(ms = 600) { return this.fade(1, ms); }
  fadeOut(ms = 600) { return this.fade(0, ms); }

  /* ---------- 暂停 / 设置 ---------- */
  showPause() { this.el.pause.classList.add('show'); this.setPrompt(null); }
  hidePause() { this.el.pause.classList.remove('show'); }
  showSettings() { this.el.settings.classList.add('show'); this.syncSettingsLabels(); }
  hideSettings() { this.el.settings.classList.remove('show'); }

  /* ---------- 死亡 / 结局 ---------- */
  showDeath(text) {
    this.el.deathText.textContent = text || '你听见自己的心跳，然后什么也听不见了。';
    this.el.death.classList.add('show');
    this.setHudVisible(false);
  }
  hideDeath() { this.el.death.classList.remove('show'); }
  showEnding({ chapter, title, lines, footer }) {
    this.el.endingChapter.textContent = chapter || '';
    this.el.endingTitle.textContent = title || '';
    this.el.endingLines.innerHTML = '';
    (lines || []).forEach((line, i) => {
      const p = document.createElement('p');
      p.textContent = line;
      p.style.animationDelay = `${0.5 + i * 0.9}s`;
      this.el.endingLines.appendChild(p);
    });
    this.el.endingFooter.textContent = footer || '';
    this.el.ending.classList.add('show');
    this.setHudVisible(false);
  }
  hideEnding() { this.el.ending.classList.remove('show'); }

  /* ---------- 信纸 ---------- */
  showPaper({ head, lines, onClose }) {
    this.el.paperHead.textContent = head || '一封信';
    this.el.paperBody.innerHTML = '';
    (lines || []).forEach((line) => {
      const p = document.createElement('p');
      p.textContent = line;
      this.el.paperBody.appendChild(p);
    });
    this.paperOnClose = onClose || null;
    this.el.paper.classList.add('show');
    this.setHudVisible(false);
    this.setPrompt(null);
  }
  _closePaper() {
    this.el.paper.classList.remove('show');
    const cb = this.paperOnClose;
    this.paperOnClose = null;
    this.setHudVisible(true);
    if (cb) cb();
  }
  closePaper() {
    if (this.el.paper.classList.contains('show')) this._closePaper();
  }
  isPaperOpen() { return this.el.paper.classList.contains('show'); }

  update(dt) {
    if (this.subtitleTimer > 0) {
      this.subtitleTimer -= dt;
      if (this.subtitleTimer <= 0) {
        this.el.subtitle.classList.remove('show');
        if (this.subtitleQueue.length) setTimeout(() => this._nextSubtitle(), 120);
        else this.el.subtitle.textContent = '';
      }
    }
  }
}
