import assert from 'node:assert/strict';
import { setTimeout as delay } from 'node:timers/promises';
import { UI } from '../engine/ui.js';

const makeUI = () => Object.assign(Object.create(UI.prototype), {
  game: {settings:{subtitles:true}}, subtitleTimer:0, subtitleQueue:[], _subtitleNextTimer:null,
  el:{subtitle:{textContent:'',classList:{add(){},remove(){}}}},
});
// A completed queue must accept the next subtitle after an overshooting frame.
let ui=makeUI(); ui.subtitle('first',.1);ui.update(.2);
assert.equal(ui.subtitleTimer,0);ui.subtitle('later',1);assert.equal(ui.el.subtitle.textContent,'later');
// A new enqueue during the inter-caption gap cannot skip an older queued line.
ui=makeUI();ui.subtitle('first',.1);ui.subtitle('second',1);ui.update(.2);ui.subtitle('third',1);
assert.equal(ui.subtitleQueue.length,2);await delay(150);assert.equal(ui.el.subtitle.textContent,'second');
assert.equal(ui.subtitleQueue[0].text,'third');ui.clearSubtitles();
// A pending callback must not consume or hide the fresh queue after a retry/transition.
ui=makeUI();ui.subtitle('old',.1);ui.subtitle('old queued',1);ui.update(.2);ui.clearSubtitles();
ui.subtitle('fresh',1);ui.subtitle('fresh queued',1);await delay(150);
assert.equal(ui.el.subtitle.textContent,'fresh');assert.equal(ui.subtitleQueue[0].text,'fresh queued');
ui.clearSubtitles();
console.log('PASS: expired timer recovery, ordered gap enqueue, clear cancels stale callback');
