// Controlled production-renderer studies. Placement/time are assisted; not gameplay acceptance.
const {chromium}=require('playwright'),fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const stage=process.argv[2]||'study-a',base=process.env.SANGENG_AV_URL||'http://127.0.0.1:8139';
const out=path.resolve('reports/av-v1.6',stage);fs.mkdirSync(out,{recursive:true});
const views=[
 {id:'01-corridor',pos:[0,0,1],look:[0,1.55,10]},
 {id:'02-living',pos:[2.06,0,5.4],look:[5.8,1.48,5.4]},
 {id:'03-kitchen',pos:[3.9,0,8.35],look:[3.62,1.12,9.05]},
 {id:'04-window',pos:[4.5,0,6.15],look:[5.4,1.35,7.7]},
 {id:'05-door',pos:[0,0,5.35],look:[1.15,1.08,5.4]},
 {id:'06-bookshelf',pos:[4.1,0,4.8],look:[4.1,1.0,3.08]},
 {id:'07-sofa',pos:[4.6,0,5.1],look:[3.0,.65,5.5]},
];
(async()=>{
 const b=await chromium.launch({channel:'msedge',headless:true,args:['--use-angle=d3d11','--enable-gpu']});
 const c=await b.newContext({viewport:{width:1440,height:900}});
 await c.addInitScript(()=>localStorage.setItem('sangeng-settings-v1',JSON.stringify({inputMode:'drag',renderScale:.8,volume:.5})));
 const p=await c.newPage(),errors=[];p.on('pageerror',e=>errors.push(e.message));
 p.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
 try{
  await p.goto(base+'/games/door/');await p.waitForFunction(()=>window.__SANGENG__?.state==='title',null,{timeout:90000});
  await p.locator('[data-act="start"]').click();await p.waitForTimeout(1600);
  const records=[];
  for(const view of views){
   const info=await p.evaluate(async view=>{
    const g=__SANGENG__,T=await import('../../vendor/three/three.module.js');
    g.state='playing';g.clock.getDelta=()=>1/60;
    g.player.teleportToPos(new T.Vector3(...view.pos),new T.Vector3(...view.look));
    return {position:g.player.pos.toArray(),materials:g.materials.size,textures:g.textures.size};
   },view);
   await p.waitForTimeout(250);
   await p.evaluate(view=>{
    const g=__SANGENG__;g.state='art-review';g.clock.getDelta=()=>0;g.time=12;
    for(const e of g._lightEntries)e.seed=.5;
    g.player.teleportToPos({x:view.pos[0],y:view.pos[1],z:view.pos[2]}, {x:view.look[0],y:view.look[1],z:view.look[2]});
    g.ui.clearSubtitles();
   },view);
   await p.waitForTimeout(220);
   await p.screenshot({path:path.join(out,view.id+'.jpg'),type:'jpeg',quality:95});records.push({...view,...info});
  }
  assert.deepEqual(errors,[]);fs.writeFileSync(path.join(out,'result.json'),JSON.stringify({stage,records,errors,scope:'real production renderer at fixed assisted camera positions, frozen time and deterministic flicker; not normal-route play'},null,2));
  console.log('REVIEW CAPTURED '+stage);
 }finally{await b.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
