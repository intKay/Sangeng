// One real route through the shipped controller: no teleport, state setter or end shortcut.
const {chromium}=require('playwright'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
const stage=process.argv[2]||'after';
const out=path.resolve('reports/av-v1.5/route',stage);fs.mkdirSync(out,{recursive:true});
(async()=>{
 const b=await chromium.launch({channel:'msedge',headless:true,args:['--use-angle=d3d11','--enable-gpu']});
 const c=await b.newContext({viewport:{width:1280,height:800}});
 await c.addInitScript(()=>localStorage.setItem('sangeng-settings-v1',JSON.stringify({inputMode:'drag',renderScale:.8,volume:.8})));
 const p=await c.newPage(),errors=[];p.on('pageerror',e=>errors.push(e.message));
 try{
  await p.goto((process.env.SANGENG_AV_URL||'http://127.0.0.1:8139')+'/games/door/');
  await p.waitForFunction(()=>window.__SANGENG__?.state==='title',null,{timeout:90000});
  await p.locator('[data-act="start"]').click();await p.waitForFunction(()=>__SANGENG__.state==='playing');
  await p.waitForTimeout(1600);
  const start=await p.evaluate(()=>__SANGENG__.player.pos.toArray());
  await p.screenshot({path:path.join(out,'01-corridor.jpg'),type:'jpeg',quality:94});
  await p.keyboard.down('w');
  try{await p.waitForFunction(()=>__SANGENG__.player.pos.z>=5.23,null,{timeout:12000,polling:20});}finally{await p.keyboard.up('w');}
  await p.waitForTimeout(350);
  const atDoor=await p.evaluate(()=>({pos:__SANGENG__.player.pos.toArray(),yaw:__SANGENG__.player.yaw}));
  // Turn by the real drag-look sensitivity, based on the observed camera yaw.
  let delta=-Math.PI/2-atDoor.yaw;while(delta>Math.PI)delta-=Math.PI*2;while(delta<-Math.PI)delta+=Math.PI*2;
  await p.mouse.move(1000,310);await p.mouse.down();await p.mouse.move(1000-delta/.0034,310,{steps:18});await p.mouse.up();
  await p.waitForFunction(()=>__SANGENG__.interact.current?.object.name==='INT_door_503',null,{timeout:4000});
  await p.keyboard.press('e');await p.waitForFunction(()=>__DOOR__.state.doors['503'].isOpen);
  await p.waitForTimeout(900);await p.screenshot({path:path.join(out,'02-door-open.jpg'),type:'jpeg',quality:94});
  await p.keyboard.down('w');
  try{await p.waitForFunction(()=>__DOOR__.state.enteredApartment&&__SANGENG__.player.pos.x>=1.9,null,{timeout:10000,polling:20});}finally{await p.keyboard.up('w');}
  await p.waitForTimeout(1400);
  const end=await p.evaluate(()=>({pos:__SANGENG__.player.pos.toArray(),entered:__DOOR__.state.enteredApartment,open:__DOOR__.state.doors['503'].isOpen,
    objective:__SANGENG__.ui.el.objective?.textContent,channels:[...__SANGENG__.audio.ambiences.keys()]}));
  assert(end.entered&&end.open);
  if(stage==='after'){assert(end.channels.includes('window'));assert.equal(end.channels.filter(k=>k==='window').length,1);}
  await p.screenshot({path:path.join(out,'03-apartment.jpg'),type:'jpeg',quality:94});assert.deepEqual(errors,[]);
  fs.writeFileSync(path.join(out,'result.json'),JSON.stringify({start,atDoor,end,errors,scope:'real keys, drag look, collision and E interaction; first apartment only, no full playthrough'},null,2));
  console.log(JSON.stringify({start,atDoor,end,errors}));
 }catch(e){await p.screenshot({path:path.join(out,'failure.jpg')}).catch(()=>{});throw e;}finally{await b.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
