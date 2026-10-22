// Content acceptance through the actual desktop renderer. Placement is assisted;
// use/close/retry actions are real keys/buttons and are reported separately.
const { _electron: electron, chromium } = require('playwright');
const fs=require('node:fs'), path=require('node:path'), assert=require('node:assert/strict');
const out=path.resolve(process.env.SANGENG_QA_OUT || 'reports/qa/release-1.3.0/content');fs.mkdirSync(out,{recursive:true});
const exe=path.resolve(process.argv[2] || 'dist/electron-runtime/electron.exe');
const source=!process.argv[2] || process.argv.includes('--source');
const browserMode=!!process.env.SANGENG_CONTENT_URL;
const result={assistedPlacement:true,runtime:browserMode?'Edge browser':'Electron desktop',chapters:[],errors:[],failedRequests:[]};
let app,page;
async function focus(){if(!browserMode)await app.evaluate(({BrowserWindow})=>{const w=BrowserWindow.getAllWindows()[0];w.show();w.focus();w.webContents.focus();});}
async function shot(name){await page.screenshot({path:path.join(out,name+'.png')});}
async function load(id){
 if(!await page.locator('a[href*="games/"]').count()){
  await page.locator('[data-act="back"]:visible').first().click();
 }
 await page.locator('a[href*="games/'+id+'/"]').click();
 await page.waitForFunction(()=>window.__SANGENG__?.state==='title',null,{timeout:60000});
 await focus();await page.locator('[data-act="start"]').click();
 await page.waitForFunction(browserMode=>__SANGENG__.state==='playing'&&(browserMode||!!document.pointerLockElement),browserMode);
 const resources=await page.evaluate(()=>({textures:__SANGENG__.textures.size,expectedTextures:Object.keys(__SANGENG__.textureDefs).length,missing:__SANGENG__.audio.missing}));
 assert.equal(resources.textures,resources.expectedTextures);assert.deepEqual(resources.missing,[]);
 return resources;
}
async function aim(name){
 await page.evaluate(async name=>{
  const g=__SANGENG__,T=await import('/vendor/three/three.module.js');
  const h=g.interact.handles.find(h=>h.object.name===name);assertBrowser(!!h,'missing handle '+name);
  function assertBrowser(ok,msg){if(!ok)throw Error(msg);}
  g.level.updateMatrixWorld(true);const center=new T.Box3().setFromObject(h.object).getCenter(new T.Vector3());
  for(let i=0;i<24;i++){
   const angle=i*Math.PI/12;
   g.player.teleportToPos(new T.Vector3(center.x+Math.cos(angle)*1.1,0,center.z+Math.sin(angle)*1.1),center);
   g.camera.updateMatrixWorld(true);g.interact.update(.5);
   if(g.interact.current===h)return;
  }
  throw Error('Cannot target '+name);
 },name);
 await page.waitForTimeout(100);
 assert.equal(await page.evaluate(()=>__SANGENG__.interact.current?.object.name),name);
}
async function use(name){await ensurePlaying();await aim(name);await ensurePlaying();await page.keyboard.press('e');}
async function ensurePlaying(){
 // 自动化窗口可能被其他窗口遮挡而触发游戏内失焦暂停；这里只负责继续，暂停本身由 verify_desktop 单独覆盖。
 if(!page)return;
 const st=await page.evaluate(()=>window.__SANGENG__?.state).catch(()=>null);
 if(st==='paused'){
  await page.locator('[data-act="resume"]:visible').first().click();
  await page.waitForFunction(()=>__SANGENG__.state==='playing');
  await page.waitForTimeout(120);
 }
}
async function waitUntil(fn,timeout=30000){
 const end=Date.now()+timeout;
 while(Date.now()<end){
  await ensurePlaying();
  if(await page.evaluate(fn))return;
  await page.waitForTimeout(200);
 }
 throw new Error('timeout waiting: '+fn.toString().slice(0,80));
}
async function closePaper(){
 await page.waitForFunction(()=>__SANGENG__.state==='paper'&&!document.pointerLockElement);
 await page.keyboard.press('e');
 await page.waitForFunction(()=>__SANGENG__.state==='playing');
}
async function subtitles(){
 const seq=await page.evaluate(async()=>{
  const ui=__SANGENG__.ui;
  const waitText=(text,ms=2500)=>new Promise(resolve=>{
   const end=performance.now()+ms;
   const tick=()=>{
    if(ui.el.subtitle.textContent===text)return resolve(true);
    if(performance.now()>end)return resolve(false);
    setTimeout(tick,40);
   };
   tick();
  });
  ui.clearSubtitles();
  // 队列在两条字幕之间保留 120ms 间隔；等待第一条约 50ms 的短字幕过期后再读。
  ui.subtitle('QA first',.05);await waitText('QA first',1500);
  await new Promise(r=>setTimeout(r,250));
  ui.subtitle('QA later',.15);const laterOk=await waitText('QA later',2000);
  const later=ui.el.subtitle.textContent;ui.clearSubtitles();
  ui.subtitle('QA queued A',.05);ui.subtitle('QA queued B',.2);
  const orderedOk=await waitText('QA queued B',2500);
  const ordered=ui.el.subtitle.textContent;ui.clearSubtitles();
  return {later,ordered,laterOk,orderedOk};
 });
 assert.equal(seq.later,'QA later');assert.equal(seq.ordered,'QA queued B');return seq;
}
async function signal(){return page.evaluate(async()=>{
 const a=__SANGENG__.audio,n=a.ctx.createAnalyser(),s=new Float32Array(n.fftSize);a.master.connect(n);let peak=0;
 for(let i=0;i<10;i++){n.getFloatTimeDomainData(s);for(const x of s)peak=Math.max(peak,Math.abs(x));await new Promise(r=>setTimeout(r,30));}
 a.master.disconnect(n);return {peak,state:a.ctx.state};
});}
(async()=>{
 // Optional test-only flags for headless/CI hosts, e.g. SANGENG_QA_FLAGS="--no-sandbox --disable-gpu".
 const qaFlags=(process.env.SANGENG_QA_FLAGS||'').split(/\s+/).filter(Boolean);
 if(browserMode){
  app=await chromium.launch({channel:'msedge',headless:true,args:['--use-angle=d3d11','--enable-gpu']});
  const context=await app.newContext();
  await context.addInitScript(()=>localStorage.setItem('sangeng-settings-v1',JSON.stringify({inputMode:'drag',renderScale:.8,volume:.5})));
  page=await context.newPage();await page.goto(process.env.SANGENG_CONTENT_URL);
 }else{
  app=await electron.launch({executablePath:exe,args:[...qaFlags,...(source?[path.resolve('.')]:[])],timeout:60000});
  page=await app.firstWindow();await page.waitForURL('sangeng://game/');
 }
 await page.setViewportSize({width:1280,height:800});
 page.on('pageerror',e=>result.errors.push(e.message));
 page.on('requestfailed',r=>{if(r.failure()?.errorText!=='net::ERR_ABORTED')result.failedRequests.push(r.url());});
 // Door: new examinations, all three pickups/loops, actual chase death/retry and ending.
 const door={id:'door',resources:await load('door'),subtitles:await subtitles(),signal:await signal()};
 assert(door.signal.peak>0);
 await use('INT_door_503');assert(await page.evaluate(()=>__DOOR__.state.doors['503'].isOpen));
 await page.waitForTimeout(1100);
 assert.equal(await page.evaluate(()=>__DOOR__.state.doors['503'].interact.prompt),'关上 503 的门');
 await use('INT_flashlight');assert(await page.evaluate(()=>__SANGENG__.player.hasFlashlight));
 await page.keyboard.press('f');assert.equal(await page.evaluate(()=>__SANGENG__.player.flashlightOn),false);await page.keyboard.press('f');
 for(const name of ['INT_photo_1','INT_calendar','INT_notice_board','INT_child_drawing']){
  await use(name);assert.equal(await page.evaluate(()=>__SANGENG__.state),'paper');await shot('door-'+name);await closePaper();
 }
 for(let i=1;i<=3;i++){
  await use('INT_letter_0'+i);await closePaper();
  await page.waitForTimeout(3200);
  assert.equal(await page.evaluate(()=>__DOOR__.state.letters.length),i);
  if(i<3)assert.equal(await page.evaluate(()=>__DOOR__.state.loop),i+1);
 }
 // Let the real entity catch the player, rather than invoking a death debug method.
 await page.evaluate(()=>{const s=__DOOR__.state;s.entity.grace=0;s.entity.root.position.copy(__SANGENG__.player.pos);});
 await waitUntil(()=>__SANGENG__.state==='dead',20000);
 await page.locator('[data-act="retry"]').click();await page.waitForFunction(()=>__SANGENG__.state==='playing');
 assert.equal(await page.evaluate(()=>__DOOR__.state.letters.length),3);door.deathRetry=true;
 await page.evaluate(()=>{const g=__SANGENG__;g.player.pos.set(7.1,0,5.3);g.player._syncCamera(0,true);});
 await waitUntil(()=>__DOOR__.state.finalStarted,30000);
 assert(await page.evaluate(()=>__DOOR__.state.entity.sitting.visible&&!__DOOR__.state.entity.root.visible));
 await page.evaluate(async()=>{const T=await import('/vendor/three/three.module.js');const g=__SANGENG__;g.player.teleportToPos(new T.Vector3(7.6,0,5.5),new T.Vector3(7.6,.95,7));});
 await page.waitForTimeout(350);
 await shot('door-seated');await use('INT_letter_final');await closePaper();
 await waitUntil(()=>__SANGENG__.state==='ending',30000);
 await shot('door-ending');door.ending=true;door.pickups=3;door.newExaminations=4;result.chapters.push(door);
 // Mirror: deliberate wrong uses -> punishment/death, retry, then solve all rounds using E.
 const mirror={id:'mirror',resources:await load('mirror'),subtitles:await subtitles(),signal:await signal()};
 assert(mirror.signal.peak>0);
 assert(await page.evaluate(()=>__MIRROR__.state.handprints===0&&!__MIRROR__.state.crackShown));
 const examine=await page.evaluate(()=>__MIRROR__.debug.examineInfo().find(x=>x.exists&&x.visible)?.name);
 assert(examine);await use(examine);await page.waitForTimeout(300);if(await page.evaluate(()=>__SANGENG__.state==='paper'))await closePaper();
 for(let i=0;i<5;i++){
  if(await page.evaluate(()=>__SANGENG__.state==='dead'))break;
  await use('INT_valve');await page.waitForTimeout(900);
 }
 await waitUntil(()=>__SANGENG__.state==='dead',20000);
 await page.locator('[data-act="retry"]').click();await page.waitForFunction(()=>__SANGENG__.state==='playing');mirror.wrongUseDeathRetry=true;
 const names={towel:'INT_towel',locker:'INT_locker_02',lights:'INT_switch',mannequin:'INT_mannequin',radio:'INT_radio',stool01:'INT_stool_01',valve:'INT_valve'};
 for(let round=0;round<3;round++){
  await page.waitForFunction(()=>!__MIRROR__.debug.info().busy);
  const info=await page.evaluate(()=>__MIRROR__.debug.info());
  assert.equal(info.round,round);
  for(const [key,target] of Object.entries(info.target)){
   if(await page.evaluate(key=>__MIRROR__.debug.info().world[key],key)===target)continue;
   await use(names[key]);await page.waitForTimeout(450);
  }
  if(round<2){
   await page.waitForFunction(n=>__MIRROR__.debug.info().round===n&&!__MIRROR__.debug.info().busy,round+1,{timeout:15000});
   await page.waitForFunction(()=>Number(getComputedStyle(__SANGENG__.ui.el.fade).opacity)<.01);
   await page.evaluate(async()=>{const T=await import('/vendor/three/three.module.js');__SANGENG__.player.teleportToPos(new T.Vector3(0,0,1.35),new T.Vector3(0,1.7,-2.7));});
   await page.waitForTimeout(200);await shot('mirror-round-'+(round+2));
  }
 }
 await waitUntil(()=>__MIRROR__.state.crackShown,30000);await shot('mirror-crack');
 await waitUntil(()=>__SANGENG__.state==='ending',40000);await shot('mirror-ending');
 assert.equal(await page.evaluate(()=>__MIRROR__.state.handprints),3);mirror.roundsSolvedByE=3;mirror.ending=true;result.chapters.push(mirror);
 // Nightroad changed its model and subtitle integration too: test all lantern interactions.
 const night={id:'nightroad',resources:await load('nightroad'),subtitles:await subtitles(),signal:await signal()};
 const lanterns=await page.evaluate(()=>__SANGENG__.interact.handles.filter(h=>/INT_lantern/.test(h.object.name)).map(h=>h.object.name));
 assert.equal(lanterns.length,5);
 for(const name of lanterns){await use(name);await page.waitForTimeout(350);}
 assert.equal(await page.evaluate(()=>__NIGHT__.state.litCount),5);night.lanternsByE=5;await shot('night-lanterns');
 await use('INT_incense');
 await waitUntil(()=>__NIGHT__.state.decision.active,40000);
 await page.keyboard.up('w');await page.waitForTimeout(200);
 await page.keyboard.down('w');await page.waitForTimeout(2200);await page.keyboard.up('w');
 await waitUntil(()=>__SANGENG__.state==='ending',40000);
 night.shrineAndEndingByKeys=true;await shot('night-ending');
 result.chapters.push(night);assert.deepEqual(result.errors,[]);assert.deepEqual(result.failedRequests,[]);
 fs.writeFileSync(path.join(out,browserMode?'browser-result.json':source?'source-result.json':'packaged-result.json'),JSON.stringify(result,null,2));
 console.log(JSON.stringify(result));
})().catch(async e=>{result.failure=String(e);fs.writeFileSync(path.join(out,'failure.json'),JSON.stringify(result,null,2));if(page)await shot('failure').catch(()=>{});console.error(e);process.exitCode=1;}).finally(async()=>{if(app)await app.close();});
