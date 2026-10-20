// Verify the "no pointer lock" input modes: default mouse mode locks and Esc releases;
// drag mode never locks, left-drag rotates the view, and clicking the canvas does not re-lock.
const { _electron: electron } = require('playwright');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');

const out = path.resolve(process.env.SANGENG_QA_OUT || 'reports/qa/pointer-mode');
fs.mkdirSync(out, { recursive: true });
const flags = (process.env.SANGENG_QA_FLAGS || '').split(/\s+/).filter(Boolean);
const exeArg = process.argv[2];
const exe = exeArg ? path.resolve(exeArg) : path.resolve('dist/electron-runtime/electron.exe');
const source = !exeArg;
const result = { executable: exe, source };

(async () => {
  const app = await electron.launch({
    executablePath: exe,
    args: source ? [...flags, path.resolve('.')] : [...flags],
    timeout: 60000,
  });
  const page = await app.firstWindow();
  await page.waitForURL('sangeng://game/');
  await page.setViewportSize({ width: 1280, height: 800 });
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));

  await page.locator('a[href*="games/door/"]').click();
  await page.waitForFunction(() => window.__SANGENG__?.state === 'title', null, { timeout: 60000 });
  await page.locator('[data-act="start"]').click();
  await page.waitForFunction(() => __SANGENG__.state === 'playing' && !!document.pointerLockElement, null, { timeout: 20000 });
  result.defaultMode = await page.evaluate(() => __SANGENG__.settings.inputMode);
  result.defaultLocks = true;

  await page.keyboard.press('Escape');
  await page.waitForFunction(() => __SANGENG__.state === 'paused', null, { timeout: 10000 });
  result.escReleases = !(await page.evaluate(() => !!document.pointerLockElement));

  await page.locator('[data-act="settings"]:visible').first().click();
  await page.waitForFunction(() => document.querySelector('#sg-settings')?.classList.contains('show'), null, { timeout: 10000 });
  await page.screenshot({ path: path.join(out, 'settings-modes.png') });
  await page.evaluate(() => {
    const select = document.querySelector('[data-set="inputMode"]');
    select.value = 'drag';
    select.dispatchEvent(new Event('change', { bubbles: true }));
  });
  assert.equal(await page.evaluate(() => __SANGENG__.settings.inputMode), 'drag');
  result.dragModeSelected = true;
  result.bodyHasDragClass = await page.evaluate(() => document.body.classList.contains('sg-drag-mode'));
  assert.equal(result.bodyHasDragClass, true);

  await page.locator('[data-act="settings-back"]:visible').first().click();
  await page.locator('[data-act="resume"]:visible').first().click();
  await page.waitForFunction(() => __SANGENG__.state === 'playing', null, { timeout: 10000 });
  await page.waitForTimeout(400);
  result.lockAfterResume = await page.evaluate(() => !!document.pointerLockElement);
  assert.equal(result.lockAfterResume, false);

  const yaw0 = await page.evaluate(() => __SANGENG__.player.yaw);
  await page.mouse.move(640, 400);
  await page.mouse.down();
  await page.mouse.move(780, 400, { steps: 8 });
  await page.mouse.up();
  const yaw1 = await page.evaluate(() => __SANGENG__.player.yaw);
  result.dragYawDelta = +(yaw1 - yaw0).toFixed(4);
  assert(Math.abs(yaw1 - yaw0) > 0.05, 'left-drag should rotate the view');
  result.lockDuringDrag = await page.evaluate(() => !!document.pointerLockElement);
  assert.equal(result.lockDuringDrag, false);

  await page.mouse.click(640, 400);
  await page.waitForTimeout(400);
  result.lockAfterCanvasClick = await page.evaluate(() => !!document.pointerLockElement);
  result.stateAfterCanvasClick = await page.evaluate(() => __SANGENG__.state);
  assert.equal(result.lockAfterCanvasClick, false);
  assert.equal(result.stateAfterCanvasClick, 'playing');
  await page.screenshot({ path: path.join(out, 'drag-mode-playing.png') });

  // Switching back to pointer-lock mode should request the lock again on resume.
  await page.keyboard.press('Escape');
  await page.waitForFunction(() => __SANGENG__.state === 'paused', null, { timeout: 10000 });
  await page.locator('[data-act="settings"]:visible').first().click();
  await page.waitForFunction(() => document.querySelector('#sg-settings')?.classList.contains('show'), null, { timeout: 10000 });
  await page.evaluate(() => {
    const select = document.querySelector('[data-set="inputMode"]');
    select.value = 'mouse';
    select.dispatchEvent(new Event('change', { bubbles: true }));
  });
  await page.locator('[data-act="settings-back"]:visible').first().click();
  await page.locator('[data-act="resume"]:visible').first().click();
  await page.waitForFunction(() => __SANGENG__.state === 'playing' && !!document.pointerLockElement, null, { timeout: 15000 });
  result.mouseModeRelocks = true;

  result.errors = errors;
  assert.deepEqual(errors, []);
  fs.writeFileSync(path.join(out, 'result.json'), JSON.stringify(result, null, 2));
  console.log(JSON.stringify(result, null, 2));
  await app.close();
})().catch(async (e) => {
  result.failure = String(e);
  fs.writeFileSync(path.join(out, 'failure.json'), JSON.stringify(result, null, 2));
  console.error(e);
  process.exitCode = 1;
});
