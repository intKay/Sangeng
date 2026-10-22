// Production renderer observations. Object framing is assisted, not a playthrough.
const {chromium}=require('playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const stage=process.argv[2]||'after';
const out=path.resolve('reports/av-v1.4',stage);fs.mkdirSync(out,{recursive:true});
const base=process.env.SANGENG_AV_URL||'http://127.0.0.1:8138';
(async()=>{
 const browser=await chromium.launch({headless:true});
 const context=await browser.newContext({viewport:{width:1280,height:800},deviceScaleFactor:1});
 await context.addInitScript(()=>{
  const original=AudioNode.prototype.connect;
  AudioNode.prototype.connect=function(destination,...args){
   const result=original.call(this,destination,...args);
   if(destination instanceof AudioDestinationNode)window.__SG_FINAL_AUDIO_NODE=this;
   return result;
  };
 });
 const page=await context.newPage(),errors=[],results=[];
 page.on('pageerror',e=>errors.push(e.message));
 try{
  for(const id of ['door','mirror','nightroad']){
   await page.goto(base+'/games/'+id+'/');
   await page.waitForFunction(()=>window.__SANGENG__?.state==='title',null,{timeout:90000});
   await page.evaluate(()=>{__SANGENG__.settings.pointerMode='drag';});
   await page.locator('[data-act="start"]').click();
   await page.waitForFunction(()=>__SANGENG__.state==='playing');
   await page.waitForTimeout(1300);
   const resources=await page.evaluate(()=>{
    const g=__SANGENG__,gl=g.renderer.getContext(),debug=gl.getExtension('WEBGL_debug_renderer_info');
    return {textures:g.textures.size,audioMissing:g.audio.missing,placeholder:!!g.placeholder,state:g.state,gpu:debug?gl.getParameter(debug.UNMASKED_RENDERER_WEBGL):'unavailable'};
   });
   assert.equal(resources.textures,62);assert.deepEqual(resources.audioMissing,[]);assert(!resources.placeholder);
   await page.screenshot({path:path.join(out,id+'-entry.jpg'),type:'jpeg',quality:88});
   const frames=await page.evaluate(async()=>{
    const r=__SANGENG__.renderer,times=[],autoReset=r.info.autoReset;r.info.autoReset=false;let last=performance.now(),calls=0,tris=0;
    for(let i=0;i<50;i++){r.info.reset();await new Promise(requestAnimationFrame);const now=performance.now();if(i>=5)times.push(now-last);last=now;calls=Math.max(calls,r.info.render.calls);tris=Math.max(tris,r.info.render.triangles);}
    r.info.autoReset=autoReset;times.sort((a,b)=>a-b);return {medianMs:times[22],p95Ms:times[42],calls,triangles:tris};
   });
   const audio=await page.evaluate(async()=>{
    const a=__SANGENG__.audio,an=a.ctx.createAnalyser();an.fftSize=2048;
    window.__SG_FINAL_AUDIO_NODE.connect(an);
    const read=async()=>{const values=[];for(let i=0;i<8;i++){await new Promise(r=>setTimeout(r,50));const x=new Float32Array(2048);an.getFloatTimeDomainData(x);values.push(Math.sqrt(x.reduce((s,v)=>s+v*v,0)/x.length));}return Math.max(...values);};
    const playing=await read();__SANGENG__.pause();await new Promise(r=>setTimeout(r,400));
    const pausedContext=a.ctx.state;
    // Force the context running in this isolated test to measure the final
    // gate independently; a suspended analyser may retain historical samples.
    if(a.ctx.state==='suspended'){await a.ctx.resume();await new Promise(r=>setTimeout(r,150));}
    const paused=await read();if(a.setPaused)await a.setPaused(true);
    // Button/user-gesture resume is exercised below outside evaluate.
    return {playing,paused,pausedContext,contextState:a.ctx.state,scope:'final gate measured even with context forcibly resumed while paused'};
   });
   assert(audio.playing>1e-5,'non-silent final output');
   if(stage!=='before')assert(audio.paused<1e-6,'pause must silence final output');
   await page.locator('[data-act="resume"]:visible').click();
   await page.waitForFunction(()=>__SANGENG__.state==='playing');
   await page.waitForTimeout(250);
   const resumed=await page.evaluate(()=>__SANGENG__.audio.ctx.state);assert.equal(resumed,'running');
   // Frame a real, named production asset; does not claim normal-route reachability.
   const framed=await page.evaluate(async id=>{
    const g=__SANGENG__,T=await import('../../vendor/three/three.module.js');
    const names=id==='door'?['INT_thermos']:id==='mirror'?['S_basin']:['INT_lantern_1','INT_lantern_01'];
    let target;g.level.traverse(o=>{if(names.includes(o.name)&&!target)target=o;});
    if(!target&&id==='nightroad')g.level.traverse(o=>{if(/lantern/i.test(o.name)&&o.isMesh&&!target)target=o;});
    if(!target)return null;
    const c=new T.Box3().setFromObject(target).getCenter(new T.Vector3());
    const pos=c.clone().add(id==='door'?new T.Vector3(.35,0,-.65):new T.Vector3(.65,0,1));pos.y=0;
    g.player.teleportToPos(pos,c);g.camera.updateMatrixWorld(true);return {name:target.name,center:c.toArray(),position:pos.toArray()};
   },id);
   if(framed){await page.waitForTimeout(250);await page.screenshot({path:path.join(out,id+'-detail.jpg'),type:'jpeg',quality:90});}
   results.push({id,resources,frames,audio,resumed,assistedFraming:framed});
  }
  assert.deepEqual(errors,[]);fs.writeFileSync(path.join(out,'result.json'),JSON.stringify({stage,errors,results,scope:'real production browser; detail framing is assisted; no human listening acceptance'},null,2));
  console.log(JSON.stringify(results.map(r=>({id:r.id,gpu:r.resources.gpu,frames:r.frames,audio:r.audio}))));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
