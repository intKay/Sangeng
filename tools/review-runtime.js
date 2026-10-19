async (page) => {
  const base = new URL(page.url()).origin;
  const results = [];
  const errors = [];
  page.on('pageerror', e => errors.push(String(e)));
  const aim = async (name) => page.evaluate(async (name) => {
    const g = __SANGENG__;
    const THREE = await import('/vendor/three/three.module.js');
    const h = g.interact.handles.find(h => h.object.name === name);
    if (!h) throw Error('No interaction: '+name);
    g.level.updateMatrixWorld(true);
    const center = new THREE.Box3().setFromObject(h.object).getCenter(new THREE.Vector3());
    // QA 放置到目标附近；交互触发仍使用真实键盘，不直接调用 onUse。
    for (let i=0;i<16;i++) {
      const angle = i*Math.PI/8;
      g.player.teleportToPos(new THREE.Vector3(center.x+Math.cos(angle)*1.2,0,center.z+Math.sin(angle)*1.2), center);
      g.camera.updateMatrixWorld(true);
      g.interact.update(.3);
      if (g.interact.current === h) return {name, prompt:g.ui.el.prompt.textContent};
    }
    throw Error('Cannot aim: '+name);
  }, name);
  for (const id of ['door','mirror','nightroad']) {
    await page.goto(base+'/games/'+id+'/');
    await page.waitForFunction(() => window.__SANGENG__?.state === 'title');
    await page.evaluate(() => { __SANGENG__.settings.volume=.8; __SANGENG__.applySettings(); });
    await page.locator('[data-act="start"]').click();
    await page.waitForFunction(() => __SANGENG__.state === 'playing');
    const audio = await page.evaluate(async () => {
      const a = __SANGENG__.audio, n = a.ctx.createAnalyser();
      a.master.connect(n);
      const samples = new Float32Array(n.fftSize);
      let peak=0, sum=0, count=0;
      for(let i=0;i<25;i++) {
        n.getFloatTimeDomainData(samples);
        for(const s of samples){peak=Math.max(peak,Math.abs(s));sum+=s*s;count++;}
        await new Promise(r=>setTimeout(r,20));
      }
      a.master.disconnect(n);
      return {ctx:a.ctx.state,ready:a.ready,missing:a.missing.length,peak,rms:Math.sqrt(sum/count)};
    });
    if (!(audio.peak > .00001) || audio.missing) throw Error(id+': silent/missing audio');
    const name = await page.evaluate(id => {
      if(id==='door') return 'INT_door_503';
      if(id==='mirror') return 'INT_towel';
      return __SANGENG__.interact.handles.find(h=>/lantern/i.test(h.object.name)).object.name;
    },id);
    const target = await aim(name);
    const before = await page.evaluate(id => id==='door' ? __DOOR__.state.doors['503'].isOpen : id==='mirror' ? __MIRROR__.debug.info().world.towel : __NIGHT__.state.litCount,id);
    await page.keyboard.press('e');
    await page.waitForTimeout(350);
    const after = await page.evaluate(id => id==='door' ? __DOOR__.state.doors['503'].isOpen : id==='mirror' ? __MIRROR__.debug.info().world.towel : __NIGHT__.state.litCount,id);
    if(before===after) throw Error(id+': E had no effect');
    let flashlight;
    if(id==='door') {
      await page.evaluate(()=>__DOOR__.giveFlashlight());
      await page.keyboard.press('f');
      flashlight = await page.evaluate(()=>__SANGENG__.player.flashlightOn===false);
      await page.keyboard.press('f');
      if(!flashlight || !await page.evaluate(()=>__SANGENG__.player.flashlightOn)) throw Error('F failed');
    }
    await page.keyboard.press('Escape');
    await page.waitForFunction(()=>__SANGENG__.state==='paused');
    await page.locator('#sg-pause [data-act="settings"]').click();
    await page.locator('[data-set="volume"]').press('Home');
    await page.locator('[data-set="volume"]').press('ArrowRight');
    const volume = await page.evaluate(()=>__SANGENG__.settings.volume);
    await page.locator('[data-act="settings-back"]').click();
    await page.locator('[data-act="resume"]').click();
    await page.waitForFunction(()=>__SANGENG__.state==='playing');
    if(volume!==.02) throw Error('Volume setting failed');
    await page.evaluate(() => { __SANGENG__.settings.volume=.8; __SANGENG__.applySettings(); });
    // 持有 E 时打开测试信纸：系统重复 keydown 不应立即把它合上。
    await page.keyboard.down('e');
    await page.evaluate(() => __SANGENG__.openPaper({head:'QA',lines:['键盘重复事件测试']}));
    await page.waitForFunction(()=>__SANGENG__.state==='paper' && !document.pointerLockElement);
    await page.keyboard.down('e');
    if(!await page.evaluate(()=>__SANGENG__.state==='paper')) throw Error('Held E closed paper');
    await page.keyboard.up('e');
    await page.keyboard.press('e');
    await page.waitForFunction(()=>__SANGENG__.state==='playing');
    await page.screenshot({path:'output/playwright/'+id+'-review.png'});
    results.push({id,audio,target,before,after,flashlight,pauseResume:true,volume,heldE:true});
  }
  if(errors.length) throw Error(errors.join('\n'));
  return {results,errors};
}
