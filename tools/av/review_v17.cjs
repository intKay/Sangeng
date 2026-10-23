// Same production cameras before/after. Diagnostic placement, not a playthrough.
const {chromium}=require('playwright'),fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const stage=process.argv[2]||'before',base=process.env.SANGENG_AV_URL||'http://127.0.0.1:8139';
const views={
 door:[['01-corridor',[0,0,1],[0,1.55,10]],['02-living',[2.06,0,5.4],[5.8,1.48,5.4]],['03-kitchen',[3.9,0,8.35],[3.62,1.12,9.05]],['04-bedroom',[8.5,0,5.8],[7.85,.7,4.1]],['05-sewing',[8.15,0,6.2],[8.95,.92,6.78]]],
 mirror:[['01-room',[0,0,1.6],[0,1.5,-2.7]],['02-lockers',[0,0,.8],[-1.95,1.1,2.4]],['03-basins',[-.4,0,-1.4],[0,.9,-2.5]],['04-bench',[-1.4,0,.5],[.2,.55,.4]],['05-side',[1.9,0,-.8],[3.5,1.35,-.4]]],
 nightroad:[['01-road',[0,0,-1.2],[0,1.35,23]],['02-lantern',[1.7,0,10.7],[3.15,1.4,12]],['03-fields',[.5,0,30],[-7,1,43]],['04-shrine',[0,0,94.8],[0,1.2,98]],['05-road-return',[0,0,60],[1,1.35,42]]]
};
(async()=>{
 const b=await chromium.launch({channel:'msedge',headless:true,args:['--use-angle=d3d11','--enable-gpu']});
 const c=await b.newContext({viewport:{width:1440,height:900}});
 await c.addInitScript(()=>localStorage.setItem('sangeng-settings-v1',JSON.stringify({inputMode:'drag',renderScale:.8,volume:.5})));
 const p=await c.newPage(),errors=[],records=[];p.on('pageerror',e=>errors.push(e.message));p.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
 try{
  for(const [chapter,list] of Object.entries(views)){
   await p.goto(base+'/games/'+chapter+'/');await p.waitForFunction(()=>window.__SANGENG__?.state==='title',null,{timeout:90000});
   await p.locator('[data-act="start"]').click();await p.waitForTimeout(1200);
   const out=path.resolve('reports/av-v1.7',stage,chapter);fs.mkdirSync(out,{recursive:true});
   for(const [id,pos,look] of list){
    await p.evaluate(({pos,look})=>{const g=__SANGENG__;g.state='playing';g.clock.getDelta=()=>1/60;g.player.teleportToPos({x:pos[0],y:pos[1],z:pos[2]},{x:look[0],y:look[1],z:look[2]});},{pos,look});
    await p.waitForTimeout(250);
    const info=await p.evaluate(({chapter,id,pos,look})=>{
     const g=__SANGENG__;g.state='art-review';g.clock.getDelta=()=>0;g.time=12;
     if(chapter==='door'&&['04-bedroom','05-sewing'].includes(id)){g.setLight('LIGHT_bedroom',true,1.15);g.setLight('LIGHT_moon_bed',true,.75);g.setLight('LIGHT_sewing',true,.85);}
     for(const e of g._lightEntries)e.seed=.5;
     g.player.teleportToPos({x:pos[0],y:pos[1],z:pos[2]},{x:look[0],y:look[1],z:look[2]});g.ui.clearSubtitles();
     return {textures:g.textures.size,materials:g.materials.size,lightingCue:chapter==='door'&&['04-bedroom','05-sewing'].includes(id)?'late-bedroom production cue applied for material inspection':'normal scene state'};
    },{chapter,id,pos,look});
    await p.waitForTimeout(250);await p.screenshot({path:path.join(out,id+'.jpg'),type:'jpeg',quality:94});records.push({chapter,id,pos,look,...info});
   }
  }
  assert.deepEqual(errors,[]);fs.writeFileSync(path.resolve('reports/av-v1.7',stage,'result.json'),JSON.stringify({stage,records,errors,scope:'production renderer, assisted camera positions, frozen time; no story completion or human aesthetic acceptance'},null,2));console.log('Captured '+stage+' 15 views');
 }finally{await b.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
