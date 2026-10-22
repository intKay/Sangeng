// Actual WebAudio output with a deliberately bypassed gate as an isolated mutant.
const {chromium}=require('playwright'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
(async()=>{
 const browser=await chromium.launch({headless:true});
 const context=await browser.newContext({viewport:{width:1024,height:720}});
 await context.addInitScript(()=>{
  const connect=AudioNode.prototype.connect;
  AudioNode.prototype.connect=function(destination,...args){const result=connect.call(this,destination,...args);if(destination instanceof AudioDestinationNode)window.__AV_FINAL_NODE=this;return result;};
 });
 const page=await context.newPage();
 try{
  await page.goto((process.env.SANGENG_AV_URL||'http://127.0.0.1:8138')+'/games/door/');
  await page.waitForFunction(()=>window.__SANGENG__?.state==='title',null,{timeout:90000});
  await page.locator('[data-act="start"]').click();
  await page.waitForFunction(()=>__SANGENG__.state==='playing');
  await page.waitForTimeout(1200);
  const result=await page.evaluate(async()=>{
   const g=__SANGENG__,a=g.audio,ctx=a.ctx,an=ctx.createAnalyser();an.fftSize=2048;window.__AV_FINAL_NODE.connect(an);
   const wait=ms=>new Promise(r=>setTimeout(r,ms));
   const meter=async()=>{let rms=0;for(let i=0;i<8;i++){await wait(40);const x=new Float32Array(an.fftSize);an.getFloatTimeDomainData(x);rms=Math.max(rms,Math.sqrt(x.reduce((s,v)=>s+v*v,0)/x.length));}return rms;};
   a.setThreat(.8);a.sfx('stepWood',{delay:.2,wet:.7});
   const playing=await meter();g.pause();await wait(100);const pausedContext=ctx.state;
   const blockedUi=a.ui('click')===null;
   a.setMasterVolume(.4);a.unlock();await wait(60);const pausedAfterSlider=ctx.state;
   await ctx.resume();await wait(180);const pausedOutput=await meter();
   // One in-memory mutation: bypass just the final gate while the test has
   // forced a running context. No production source or live user page changes.
   a.outputGate.gain.cancelScheduledValues(ctx.currentTime);a.outputGate.gain.setValueAtTime(1,ctx.currentTime);
   await wait(150);const mutatedOutput=await meter();
   await a.setPaused(true);
   a.setMasterVolume(0);await a.setPaused(false);a.duck(false);await wait(1300);const muted=await meter();
   await a.setPaused(true);a.setMasterVolume(.7);a.unlock();await wait(60);const pausedAfterUnlock=ctx.state;
   // Deliberately race the requested context transitions.
   const p1=a.setPaused(false),p2=a.setPaused(true),p3=a.setPaused(false);await Promise.all([p1,p2,p3]);await wait(350);
   const resumed=await meter();const resumedContext=ctx.state;
   await a.setPaused(true);await wait(100);const finalContext=ctx.state;
   return {playing,pausedContext,blockedUi,pausedAfterSlider,pausedOutput,mutatedOutput,muted,pausedAfterUnlock,resumed,resumedContext,finalContext};
  });
  assert(result.playing>1e-5);assert.equal(result.pausedContext,'suspended');assert(result.blockedUi);
  assert.equal(result.pausedAfterSlider,'suspended');assert(result.pausedOutput<1e-6);
  assert.throws(()=>assert(result.mutatedOutput<1e-6));assert(result.mutatedOutput>1e-5);
  assert(result.muted<1e-6);assert.equal(result.pausedAfterUnlock,'suspended');
  assert(result.resumed>1e-5);assert.equal(result.resumedContext,'running');assert.equal(result.finalContext,'suspended');
  const report={...result,mutationRejected:true,scope:'production WebAudio graph in an isolated browser; final output sampled, no human listening acceptance'};
  fs.writeFileSync(path.resolve('reports/av-v1.4/audio-lifecycle.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
