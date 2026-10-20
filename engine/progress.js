/* 《三更》v1.4.0 本地进度 / 发现 / 结局收集。
 * 只写 localStorage，不联网；失败时静默回退，不影响游戏流程。
 */

const KEY = 'sangeng.progress.v1';

function emptyData() {
  return { version: 1, games: {}, meta: { seals: {}, allComplete: false } };
}

function safeParse(raw) {
  if (!raw) return emptyData();
  try {
    const d = JSON.parse(raw);
    if (!d || typeof d !== 'object' || d.version !== 1) return emptyData();
    d.games = d.games && typeof d.games === 'object' ? d.games : {};
    d.meta = d.meta && typeof d.meta === 'object' ? d.meta : { seals: {}, allComplete: false };
    d.meta.seals = d.meta.seals && typeof d.meta.seals === 'object' ? d.meta.seals : {};
    return d;
  } catch (err) {
    return emptyData();
  }
}

export class Progress {
  constructor(game) {
    this.game = game;
    this.catalogs = {};
    this.data = this._load();
  }

  _load() {
    try { return safeParse(localStorage.getItem(KEY)); } catch (err) { return emptyData(); }
  }

  _save() {
    try { localStorage.setItem(KEY, JSON.stringify(this.data)); } catch (err) { /* ignore */ }
  }

  _game(id) {
    if (!this.data.games[id]) {
      this.data.games[id] = { discovered: {}, endings: [], plays: 0, deaths: 0, completed: false };
    }
    const g = this.data.games[id];
    g.discovered = g.discovered && typeof g.discovered === 'object' ? g.discovered : {};
    g.endings = Array.isArray(g.endings) ? g.endings : [];
    return g;
  }

  _catalog(id) {
    return this.catalogs[id] || (id === this.game.config.id ? this.game.config.discovery : null);
  }

  define(catalog, id = this.game.config.id) {
    if (!catalog || !Array.isArray(catalog.entries)) return;
    this.catalogs[id] = catalog;
    this._game(id);
  }

  get(id = this.game.config.id) {
    return this._game(id);
  }

  entryById(catalog, id) {
    if (!catalog) return null;
    return catalog.entries.find((e) => e.id === id) || null;
  }

  mark(id) {
    const gameId = this.game.config.id;
    const catalog = this._catalog(gameId);
    const entry = this.entryById(catalog, id);
    const g = this._game(gameId);
    if (!entry) return { first: false, count: Object.keys(g.discovered).length, entry: null };
    const first = !g.discovered[id];
    g.discovered[id] = true;
    if (first) {
      this._save();
      if (this.game.ui && typeof this.game.ui.showDiscovery === 'function') {
        this.game.ui.showDiscovery(entry.title);
      }
    }
    return { first, count: Object.keys(g.discovered).length, entry };
  }

  ending(id) {
    const gameId = this.game.config.id;
    const catalog = this._catalog(gameId);
    const g = this._game(gameId);
    const first = !g.endings.includes(id);
    if (first) g.endings.push(id);
    g.completed = true;
    this.data.meta.seals[gameId] = true;
    this.data.meta.allComplete = ['door', 'mirror', 'nightroad'].every((k) => this.data.meta.seals[k]);
    if (first) this._save();
    return {
      first,
      endings: g.endings.slice(),
      total: (catalog?.endings || []).length,
      meta: this.meta(),
    };
  }

  summary(id = this.game.config.id) {
    const catalog = this._catalog(id);
    const g = this._game(id);
    const entries = (catalog?.entries || []).map((e) => ({
      ...e,
      discovered: !!g.discovered[e.id],
    }));
    const groups = (catalog?.groups || []).map((group) => {
      const list = entries.filter((e) => e.group === group.id);
      return {
        id: group.id,
        label: group.label,
        got: list.filter((e) => e.discovered).length,
        total: list.length,
      };
    });
    const endings = (catalog?.endings || []).map((e) => ({
      ...e,
      unlocked: g.endings.includes(e.id),
    }));
    const discovered = entries.filter((e) => e.discovered).length;
    return {
      id,
      entries,
      groups,
      discovered,
      total: entries.length,
      endings,
      unlockedEndings: g.endings.slice(),
      endingTotal: endings.length,
      completed: !!g.completed,
    };
  }

  meta() {
    const all = ['door', 'mirror', 'nightroad'];
    const seals = {};
    for (const id of all) {
      const g = this.data.games[id];
      seals[id] = !!(g && (g.completed || (g.endings && g.endings.length)));
    }
    this.data.meta.seals = seals;
    this.data.meta.allComplete = all.every((id) => seals[id]);
    return { seals, allComplete: this.data.meta.allComplete };
  }

  reset(id = null) {
    if (id) {
      delete this.data.games[id];
      if (this.data.meta.seals) delete this.data.meta.seals[id];
      this.data.meta.allComplete = false;
    } else {
      this.data = emptyData();
    }
    this._save();
  }

  debug() { return JSON.parse(JSON.stringify(this.data)); }
}
