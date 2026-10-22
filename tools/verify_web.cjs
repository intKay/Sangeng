// Runs against the built ZIP in a sandboxed, nested-path iframe. No live-site writes.
const { chromium, webkit } = require('playwright');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const http = require('node:http');
const extracted = path.resolve(process.env.SANGENG_WEB_QA_ROOT || 'dist/web/qa-build');
const files = new Map();
function collect(dir) {
  for (const item of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir,item.name);
    if (item.isDirectory()) collect(p); else files.set(path.relative(extracted,p).replaceAll('\\','/'),p);
  }
}
collect(extracted);
const server = http.createServer((req,res) => {
  const u = new URL(req.url, 'http://localhost');
  if (u.pathname === '/embed.html') {
    res.setHeader('Content-Type','text/html');
    res.end('<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{margin:0}iframe{width:100vw;height:100dvh;border:0;display:block}</style><iframe src="/itch/game/index.html" sandbox="allow-scripts allow-same-origin allow-pointer-lock" allow="autoplay; fullscreen" allowfullscreen></iframe>'); return;
  }
  const p = files.get(u.pathname.replace(/^\/itch\/game\//,''));
  if (!u.pathname.startsWith('/itch/game/') || !p) { res.writeHead(404);res.end();return; }
  const mime = {'.js':'text/javascript','.html':'text/html','.css':'text/css','.json':'application/json','.glb':'model/gltf-binary','.png':'image/png','.jpg':'image/jpeg','.ogg':'audio/ogg','.mp3':'audio/mpeg'};
  res.setHeader('Content-Type',mime[path.extname(p)]||'application/octet-stream');
  res.end(fs.readFileSync(p));
});
let base;
const out = path.resolve(process.env.SANGENG_QA_OUT || 'reports/qa/release-1.3.0/web'); fs.mkdirSync(out, { recursive: true });
const results = [];

async function aim(frame, id) {
  return frame.evaluate(async id => {
    const g = __SANGENG__;
    const THREE = await import(new URL('../../vendor/three/three.module.js', location.href).href);
    const name = id === 'door' ? 'INT_door_503' : id === 'mirror' ? 'INT_towel' : g.interact.handles.find(h => /lantern/i.test(h.object.name)).object.name;
    const h = g.interact.handles.find(h => h.object.name === name);
    g.level.updateMatrixWorld(true);
    const c = new THREE.Box3().setFromObject(h.object).getCenter(new THREE.Vector3());
    for (let i = 0; i < 16; i++) {
      const angle = i * Math.PI / 8;
      g.player.teleportToPos(new THREE.Vector3(c.x + Math.cos(angle)*1.2, 0, c.z + Math.sin(angle)*1.2), c);
      g.camera.updateMatrixWorld(true); g.interact.update(.3);
      if (g.interact.current === h) return name;
    }
    throw Error('Cannot aim at ' + name);
  }, id);
}
const interactionState = (frame, id) => frame.evaluate(id => id === 'door' ? __DOOR__.state.doors['503'].isOpen : id === 'mirror' ? __MIRROR__.debug.info().world.towel : __NIGHT__.state.litCount, id);

async function run(profile) {
  const browser = await (profile.webkit ? webkit : chromium).launch({ headless: true });
  const context = await browser.newContext({ viewport: profile.size, isMobile: !!profile.touch, hasTouch: !!profile.touch, deviceScaleFactor: 1 });
  if (profile.mp3) await context.addInitScript(() => {
    const original = HTMLMediaElement.prototype.canPlayType;
    HTMLMediaElement.prototype.canPlayType = function(type) { return /ogg/.test(type) ? '' : original.call(this, type); };
  });
  const page = await context.newPage(), errors = [], failures = [];
  if (profile.webkit) page.on('console', m => { if (['error','warning'].includes(m.type())) console.log('webkit:',m.text()); });
  page.on('pageerror', e => errors.push(e.message));
  page.on('requestfailed', r => { if (r.failure()?.errorText !== 'net::ERR_ABORTED') failures.push(r.url()); });
  try {
    await page.goto(base+'/embed.html');
    const frame = page.frames().find(f => f.parentFrame());
    await frame.waitForSelector('a.card');
    assert(await frame.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    await page.screenshot({ path: path.join(out, profile.name + '-home.png') });
    for (const id of profile.all ? ['door','mirror','nightroad'] : ['door']) {
      await frame.locator(`a[href*="games/${id}/"]`).click();
      await frame.waitForFunction(() => window.__SANGENG__?.state === 'title', null, { timeout: 60000 });
      await frame.waitForTimeout(400);
      const resources = await frame.evaluate(() => ({ textures: __SANGENG__.textures.size, missing: __SANGENG__.audio.missing.length, touch: __SANGENG__.touchEnabled,
        scale: __SANGENG__.settings.renderScale, mp3: [...__SANGENG__.audio.buffers.keys()].every(k => k.endsWith('.mp3')) }));
      assert.equal(resources.touch, !!profile.touch);
      assert.equal(resources.textures, 62); assert.equal(resources.missing, 0);
      if (profile.touch && id === 'door') assert.equal(resources.scale, 0.45);
      if (profile.mp3) assert(resources.mp3);
      await frame.locator('[data-act="start"]').click();
      await frame.waitForFunction(() => __SANGENG__.state === 'playing');
      await frame.waitForTimeout(500);
      if (profile.touch) {
        assert.equal(await frame.evaluate(() => !!document.pointerLockElement), false);
        await frame.locator('#sg-touch.show').waitFor();
        const stick = await frame.locator('.sg-stick').boundingBox();
        const look = await frame.locator('.sg-look-zone').boundingBox();
        const x = stick.x + stick.width/2, y = stick.y + stick.height/2;
        const lx = look.x + look.width*.5, ly = look.y + look.height*.45;
        const before = await frame.evaluate(() => ({x:__SANGENG__.player.pos.x,z:__SANGENG__.player.pos.z,yaw:__SANGENG__.player.yaw}));
        if (!profile.webkit) {
          const cdp = await context.newCDPSession(page);
          const move = {x,y:y-30,id:1}, view = {x:lx,y:ly,id:2};
          await cdp.send('Input.dispatchTouchEvent', { type:'touchStart', touchPoints:[{x,y,id:1},{x:lx,y:ly,id:2}] });
          await cdp.send('Input.dispatchTouchEvent', { type:'touchMove', touchPoints:[move,{...view,x:lx+30}] });
          await frame.waitForTimeout(500);
          const during = await frame.evaluate(() => ({x:__SANGENG__.player.pos.x,z:__SANGENG__.player.pos.z,yaw:__SANGENG__.player.yaw}));
          assert(Math.hypot(during.x-before.x,during.z-before.z) > .01, 'touch movement');
          assert(Math.abs(during.yaw-before.yaw) > .01, 'simultaneous touch look');
          await cdp.send('Input.dispatchTouchEvent', {type:'touchCancel', touchPoints:[]});
          await cdp.detach();
        } else {
          await page.mouse.move(x,y); await page.mouse.down(); await page.mouse.move(x,y-30); await frame.waitForTimeout(300); await page.mouse.up();
          await page.mouse.move(lx,ly); await page.mouse.down(); await page.mouse.move(lx+30,ly); await page.mouse.up();
          assert(Math.abs(await frame.evaluate(() => __SANGENG__.player.yaw)-before.yaw) > .01);
        }
        assert(await frame.evaluate(() => __SANGENG__.player.touch.x === 0 && __SANGENG__.player.touch.y === 0));
      } else {
        await frame.waitForFunction(() => !!document.pointerLockElement);
        assert.equal(await frame.locator('#sg-touch').isVisible(), false);
        await page.keyboard.down('w'); await frame.waitForTimeout(200); await page.keyboard.up('w');
      }
      const target = await aim(frame,id), before = await interactionState(frame,id);
      await frame.waitForTimeout(60);
      if (profile.touch) await frame.locator('[data-touch="use"]').tap(); else await page.keyboard.press('e');
      await frame.waitForTimeout(350);
      const after = await interactionState(frame,id); assert.notEqual(after,before);
      if (id === 'door' && profile.touch) {
        await frame.evaluate(() => __DOOR__.giveFlashlight());
        await frame.locator('[data-touch="light"]').tap();
        assert.equal(await frame.evaluate(() => __SANGENG__.player.flashlightOn), false);
        await frame.locator('[data-touch="light"]').tap();
        assert.equal(await frame.evaluate(() => __SANGENG__.player.flashlightOn), true);
      }
      const audio = await frame.evaluate(async () => {
        const g = __SANGENG__;
        if (!g.audio.ctx) return {supported:false,reason:'AudioContext is absent in this browser runtime'};
        const n = g.audio.ctx.createAnalyser(); g.audio.master.connect(n);
        let peak = 0;
        for (let i=0;i<12;i++) { const a = new Float32Array(n.fftSize); n.getFloatTimeDomainData(a); for(const v of a) peak=Math.max(peak,Math.abs(v)); await new Promise(r=>setTimeout(r,30)); }
        g.audio.master.disconnect(n); return {supported:true,peak,state:g.audio.ctx.state};
      });
      if (audio.supported) assert(audio.peak > 0 && audio.state === 'running');
      else assert(profile.webkit, 'audio unavailable');
      await page.screenshot({ path:path.join(out,profile.name+'-'+id+'.png') });
      if (profile.touch) await frame.locator('.sg-touch-pause').tap(); else await page.keyboard.press('Escape');
      await frame.waitForFunction(() => __SANGENG__.state === 'paused');
      assert(await frame.evaluate(() => __SANGENG__.player.touch.x === 0 && __SANGENG__.player.touch.y === 0 && !__SANGENG__.player.touch.run));
      await frame.locator('#sg-pause [data-act="settings"]').click();
      await frame.locator('[data-set="renderScale"]').selectOption('0.6');
      await frame.locator('[data-act="settings-back"]').click();
      await frame.locator('[data-act="resume"]').click();
      await frame.waitForFunction(() => __SANGENG__.state === 'playing');
      if (profile.touch) {
        await frame.locator('[data-touch="run"]').tap();
        assert(await frame.evaluate(()=>__SANGENG__.player.touch.run));
        await frame.evaluate(()=>__SANGENG__.openPaper({head:'触控检查',lines:['阅读后点击合上。']}));
        await frame.locator('[data-act="paper-close"]').tap();
        await frame.waitForFunction(()=>__SANGENG__.state==='playing');
        await page.setViewportSize({width:profile.size.height,height:profile.size.width});
        await frame.waitForTimeout(250);
        assert(await frame.evaluate(() => __SANGENG__.camera.aspect === innerWidth/innerHeight));
        await page.screenshot({path:path.join(out,profile.name+'-rotated.png')});
        await frame.locator('.sg-touch-pause').tap();
      } else await page.keyboard.press('Escape');
      await frame.locator('#sg-pause [data-act="back"]').click();
      await frame.waitForSelector('a.card');
      if (profile.touch) await page.setViewportSize(profile.size);
      results.push({profile:profile.name,chapter:id,resources,target,before,after,audio,iframe:true,rotation:!!profile.touch});
    }
    assert.deepEqual(errors, []); assert.deepEqual(failures, []);
  } catch(e) {
    await page.screenshot({path:path.join(out,profile.name+'-failure.png')}).catch(()=>{});
    console.error(profile.name, errors, failures); throw e;
  } finally { await browser.close(); }
  console.log(profile.name+' passed');
}
(async()=>{
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  base = 'http://127.0.0.1:'+server.address().port;
  const profiles = [
    {name:'android-landscape',size:{width:844,height:390},touch:true,all:true},
    {name:'phone-portrait',size:{width:390,height:844},touch:true},
    {name:'small-phone',size:{width:320,height:568},touch:true,mp3:true},
    {name:'tablet',size:{width:768,height:1024},touch:true},
    {name:'desktop',size:{width:1280,height:720},all:true},
    {name:'webkit-phone',size:{width:390,height:844},touch:true,webkit:true,mp3:true}
  ];
  for (const p of profiles.filter(p=>!process.argv[2] || p.name===process.argv[2])) await run(p);
  fs.writeFileSync(path.join(out,process.argv[2] ? process.argv[2]+'-result.json' : 'result.json'),JSON.stringify({results,limits:['browser emulation, no physical phone','local sandboxed iframe, not live itch.io']},null,2));
})().catch(e=>{ console.error(e); fs.writeFileSync(path.join(out,'partial.json'),JSON.stringify(results,null,2));process.exitCode=1;}).finally(()=>server.close());
