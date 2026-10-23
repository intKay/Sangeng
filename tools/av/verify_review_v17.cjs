// Exercise the delivered review UI: all chapter/view buttons, real audio and layout.
const {chromium}=require('playwright'),assert=require('node:assert/strict'),fs=require('node:fs');
(async()=>{const b=await chromium.launch({channel:'msedge',headless:true});try{
 const p=await b.newPage({viewport:{width:1440,height:1000}}),errors=[];p.on('pageerror',e=>errors.push(e.message));
 await p.goto((process.env.SANGENG_AV_URL||'http://127.0.0.1:8139')+'/reports/av-v1.7/');let pairs=0;
 for(let c=0;c<3;c++){
  await p.locator('#chapters button').nth(c).click();
  for(let v=0;v<5;v++){
   await p.locator('#views button').nth(v).click();
   await p.waitForFunction(()=>['before','final'].every(id=>{const i=document.getElementById(id);return i.complete&&i.naturalWidth===1440&&i.naturalHeight===900}));pairs++;
  }
  await p.locator('#audio-before').evaluate(a=>a.play());await p.waitForFunction(()=>document.getElementById('audio-before').currentTime>.1);
  await p.locator('#audio-after').evaluate(a=>a.play());await p.waitForFunction(()=>document.getElementById('audio-after').currentTime>.1);
  assert(await p.locator('#audio-before').evaluate(a=>a.paused));
 }
 await p.locator('#chapters button').first().click();await p.locator('#views button').nth(2).click();
 await p.screenshot({path:'reports/av-v1.7/review-page.jpg',fullPage:true,type:'jpeg',quality:90});
 await p.setViewportSize({width:390,height:844});await p.waitForTimeout(100);
 assert(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
 assert.deepEqual(errors,[]);
 fs.writeFileSync('reports/av-v1.7/review-ui.json',JSON.stringify({pairs,audioABChapters:3,exclusivePlayback:true,mobileWidth:390,noHorizontalOverflow:true,errors,scope:'actual browser UI behavior and media playback; no human listening acceptance'},null,2));
 console.log('Review UI passed: 15 pairs, 3 audio A/B, mobile layout');
 }finally{await b.close();}})().catch(e=>{console.error(e);process.exitCode=1});
