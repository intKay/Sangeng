// Record the actual final WebAudio output. No assumed approval from signal metrics.
const {chromium}=require('playwright'),fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),{execFileSync}=require('node:child_process');
const stage=process.argv[2]||'after',base=process.env.SANGENG_AV_URL||'http://127.0.0.1:8139',out=path.resolve('reports/av-v1.7/audio',stage);fs.mkdirSync(out,{recursive:true});
(async()=>{
 const b=await chromium.launch({channel:'msedge',headless:true,args:['--use-angle=d3d11','--enable-gpu']});
 const c=await b.newContext();await c.addInitScript(()=>{
  localStorage.setItem('sangeng-settings-v1',JSON.stringify({inputMode:'drag',renderScale:.8,volume:.5}));
  let seed=17023;Math.random=()=>((seed=(Math.imul(seed,1664525)+1013904223)>>>0)/4294967296);
  const connect=AudioNode.prototype.connect;AudioNode.prototype.connect=function(dest,...args){const result=connect.call(this,dest,...args);if(dest instanceof AudioDestinationNode)window.__MIX_FINAL=this;return result;};
 });
 const p=await c.newPage(),report=[];
 try{for(const chapter of ['door','mirror','nightroad']){
  await p.goto(base+'/games/'+chapter+'/');await p.waitForFunction(()=>window.__SANGENG__?.state==='title',null,{timeout:90000});await p.locator('[data-act="start"]').click();await p.waitForTimeout(2200);
  const data=await p.evaluate(async()=>{
   const a=__SANGENG__.audio,d=a.ctx.createMediaStreamDestination();window.__MIX_FINAL.connect(d);
   const recorder=new MediaRecorder(d.stream,{mimeType:'audio/webm;codecs=opus'}),chunks=[];
   const done=new Promise(resolve=>{recorder.ondataavailable=e=>chunks.push(e.data);recorder.onstop=async()=>resolve(Array.from(new Uint8Array(await new Blob(chunks).arrayBuffer())));});
   recorder.start();await new Promise(r=>setTimeout(r,10000));recorder.stop();const bytes=await done;window.__MIX_FINAL.disconnect(d);
   return {bytes,profile:a.roomProfile,channels:[...a.ambiences.keys()],context:a.ctx.state};
  });
  assert.equal(data.context,'running');const webm=path.join(out,chapter+'.webm');fs.writeFileSync(webm,Buffer.from(data.bytes));
  execFileSync('ffmpeg',['-v','error','-y','-i',webm,'-c:a','libmp3lame','-q:a','3',path.join(out,chapter+'.mp3')]);
  report.push({chapter,roomProfile:data.profile,channels:data.channels,file:chapter+'.mp3',seconds:10});
 }fs.writeFileSync(path.join(out,'result.json'),JSON.stringify({stage,report,scope:'actual production final WebAudio bus, seeded random source, 10 seconds at chapter start; no human listening acceptance'},null,2));console.log('Captured actual mixes '+stage);
 }finally{await b.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
