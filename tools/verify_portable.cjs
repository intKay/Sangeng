const { chromium } = require('playwright');
const { spawn } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
(async () => {
  const exe = path.resolve(process.argv[2]);
  const port = 19387;
  const launcher = spawn(exe, ['--remote-debugging-port=' + port], { stdio: 'ignore' });
  let browser;
  try {
    for (let i = 0; i < 90; i++) {
      try { browser = await chromium.connectOverCDP('http://127.0.0.1:' + port); break; }
      catch { await new Promise(r => setTimeout(r, 1000)); }
    }
    assert(browser, 'portable did not start');
    const page = browser.contexts()[0].pages()[0];
    await page.waitForURL('sangeng://game/');
    const pictures = await page.evaluate(async () => {
      await Promise.all([...document.images].map(i => i.decode()));
      return [...document.images].map(i => ({ width: i.naturalWidth, height: i.naturalHeight }));
    });
    assert(pictures.length && pictures.every(i => i.width > 0));
    await page.locator('a[href*="games/door/"]').click();
    await page.waitForFunction(() => window.__SANGENG__?.state === 'title');
    await page.waitForTimeout(500);
    await page.screenshot({ path: 'reports/qa/release-1.3.0/desktop/portable.png' });
    const result = await page.evaluate(() => ({ url: location.href, textures: __SANGENG__.textures.size, missingAudio: __SANGENG__.audio.missing.length, browser: navigator.userAgent }));
    assert(result.textures > 0 && result.missingAudio === 0);
    fs.writeFileSync('reports/qa/release-1.3.0/desktop/portable-result.json', JSON.stringify({ ...result, pictures, launchPassed: true, closeRequested: true }, null, 2));
    console.log(result);
    // Close the real window through CDP; verify the self-extracting launcher also exits.
    const cdp = await browser.newBrowserCDPSession();
    await cdp.send('Browser.close').catch(() => {});
    for (let i = 0; i < 30 && launcher.exitCode === null; i++) await new Promise(r => setTimeout(r, 500));
    assert.equal(launcher.exitCode, 0);
    fs.writeFileSync('reports/qa/release-1.3.0/desktop/portable-result.json', JSON.stringify({ ...result, pictures, launchPassed: true, normalExit: true }, null, 2));
  } finally { if (browser) await browser.close().catch(() => {}); }
})().catch(e => { console.error(e); process.exitCode = 1; });
