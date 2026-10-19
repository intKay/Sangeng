// Exercises the real packaged Electron window. No installed browser is launched.
const { _electron: electron } = require('playwright');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const out = path.resolve('reports/qa/desktop-1.1.0');
fs.mkdirSync(out, { recursive: true });
(async () => {
  const exe = path.resolve(process.argv[2] || 'dist/desktop/win-unpacked/Sangeng.exe');
  const app = await electron.launch({ executablePath: exe, timeout: 60000 });
  const results = { executable: path.basename(exe), chapters: [], errors: [], failedRequests: [] };
  try {
    const page = await app.firstWindow();
    page.on('console', m => { if (m.type() === 'error') console.log('renderer:', m.text()); });
    page.on('pageerror', e => results.errors.push(e.message));
    page.on('requestfailed', r => results.failedRequests.push({ url: r.url(), error: r.failure()?.errorText }));
    await page.waitForURL('sangeng://game/');
    await page.screenshot({ path: path.join(out, 'home.png') });
    assert.equal(await page.locator('a[href*="games/"]').count(), 3);
    for (const chapter of ['door', 'mirror', 'nightroad']) {
      await page.locator(`a[href*="games/${chapter}/"]`).click();
      await page.waitForFunction(() => window.__SANGENG__?.state === 'title', { timeout: 60000 });
      const resources = await page.evaluate(() => {
        const g = window.__SANGENG__;
        return { textures: g.textures.size, textureDefs: Object.keys(g.textureDefs).length,
          audioMissing: g.audio.missing, meshes: g.level.children.length,
          webgl: g.renderer.capabilities.isWebGL2 };
      });
      assert(resources.textures > 0 && resources.meshes > 0);
      assert.equal(resources.textures, resources.textureDefs);
      assert.deepEqual(resources.audioMissing, []);
      await app.evaluate(({ BrowserWindow }) => { const w = BrowserWindow.getAllWindows()[0]; w.show(); w.focus(); w.webContents.focus(); });
      await page.locator('[data-act="start"]').click();
      await page.waitForTimeout(300);
      console.log(chapter, await page.evaluate(() => ({state: window.__SANGENG__.state, lock: !!document.pointerLockElement, focus: document.hasFocus(), hidden: document.hidden})));
      await page.waitForFunction(() => window.__SANGENG__.state === 'playing' && !!document.pointerLockElement);
      await page.waitForTimeout(1000);
      const signal = await page.evaluate(async () => {
        const g = window.__SANGENG__, a = g.audio.ctx.createAnalyser();
        a.fftSize = 2048; g.audio.master.connect(a);
        let peak = 0;
        for (let i = 0; i < 15; i++) {
          const b = new Float32Array(a.fftSize); a.getFloatTimeDomainData(b);
          peak = Math.max(peak, ...b.map(Math.abs)); await new Promise(r => setTimeout(r, 50));
        }
        g.audio.master.disconnect(a); return { peak, state: g.audio.ctx.state };
      });
      assert(signal.peak > 0 && signal.state === 'running');
      // Position the player at an existing interaction; actual E key invokes the game callback.
      const target = await page.evaluate(async chapter => {
        const g = window.__SANGENG__;
        const THREE = await import('/vendor/three/three.module.js');
        const name = chapter === 'door' ? 'INT_door_503' : chapter === 'mirror' ? 'INT_towel' : g.interact.handles.find(h => /lantern/i.test(h.object.name)).object.name;
        const h = g.interact.handles.find(h => h.object.name === name);
        g.level.updateMatrixWorld(true);
        const center = new THREE.Box3().setFromObject(h.object).getCenter(new THREE.Vector3());
        for (let i = 0; i < 16; i++) {
          const angle = i * Math.PI / 8;
          g.player.teleportToPos(new THREE.Vector3(center.x + Math.cos(angle)*1.2, 0, center.z + Math.sin(angle)*1.2), center);
          g.camera.updateMatrixWorld(true); g.interact.update(.3);
          if (g.interact.current === h) return name;
        }
        return null;
      }, chapter);
      assert(target, chapter + ': no raycast interaction');
      const getState = () => page.evaluate(id => id === 'door' ? __DOOR__.state.doors['503'].isOpen : id === 'mirror' ? __MIRROR__.debug.info().world.towel : __NIGHT__.state.litCount, chapter);
      const before = await getState();
      await page.keyboard.press('e');
      await page.waitForTimeout(350);
      const after = await getState();
      assert.notEqual(before, after);
      if (chapter === 'door') {
        await page.evaluate(() => __DOOR__.giveFlashlight());
        await page.keyboard.press('f');
        assert.equal(await page.evaluate(() => __SANGENG__.player.flashlightOn), false);
        await page.keyboard.press('f');
        assert.equal(await page.evaluate(() => __SANGENG__.player.flashlightOn), true);
      }
      await page.screenshot({ path: path.join(out, chapter + '.png') });
      await page.keyboard.press('Escape');
      await page.waitForFunction(() => window.__SANGENG__.state === 'paused');
      await page.locator('#sg-pause [data-act="settings"]').click();
      await page.locator('[data-set="volume"]').press('Home');
      await page.locator('[data-set="volume"]').press('ArrowRight');
      assert.equal(await page.evaluate(() => window.__SANGENG__.settings.volume), 0.02);
      await page.locator('[data-act="settings-back"]').click();
      await page.locator('[data-act="resume"]').click();
      await page.waitForFunction(() => window.__SANGENG__.state === 'playing' && !!document.pointerLockElement);
      await page.keyboard.press('Escape');
      await page.locator('#sg-pause [data-act="back"]').click();
      await page.waitForURL('sangeng://game/index.html');
      results.chapters.push({ chapter, ...resources, signal, interaction: target, before, after, pauseResumeSettings: true, pointerLock: true });
    }
    await app.evaluate(({ BrowserWindow }) => { const w = BrowserWindow.getAllWindows()[0]; w.focus(); w.webContents.focus(); });
    results.runtime = await app.evaluate(() => process.versions);
    assert.deepEqual(results.errors, []);
    assert.deepEqual(results.failedRequests, []);
    await app.close(); results.normalWindowClose = true;
    fs.writeFileSync(path.join(out, 'result.json'), JSON.stringify(results, null, 2));
    console.log(JSON.stringify(results));
  } catch (error) { fs.writeFileSync(path.join(out, 'failure.json'), JSON.stringify({...results, failure: String(error)}, null, 2)); await app.close(); throw error; }
})().catch(e => { console.error(e); process.exitCode = 1; });
