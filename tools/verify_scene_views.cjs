const {_electron:electron}=require('playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const out=path.resolve('reports/qa/release-1.3.0/visuals');fs.mkdirSync(out,{recursive:true});
const groups={door:['MAT_door_number_501','MAT_door_number_502','MAT_door_number_503','MAT_door_number_504','MAT_calendar','MAT_notice_board','MAT_photo_family_1'],
 mirror:['MAT_sign_bath','MAT_bath_poster','MAT_bath_notice'],nightroad:['MAT_sign_night_1','MAT_sign_night_2','MAT_shrine_tablet']};
(async()=>{
 const app=await electron.launch({executablePath:path.resolve(process.argv[2]),timeout:60000});
 const result=[];
 try{
  const page=await app.firstWindow();await page.waitForURL('sangeng://game/');await page.setViewportSize({width:1280,height:800});
  for(const [id,mats] of Object.entries(groups)){
   await page.locator('a[href*="games/'+id+'/"]').click();await page.waitForFunction(()=>window.__SANGENG__?.state==='title');
   await app.evaluate(({BrowserWindow})=>{const w=BrowserWindow.getAllWindows()[0];w.show();w.focus();w.webContents.focus();});
   await page.locator('[data-act="start"]').click();await page.waitForFunction(()=>__SANGENG__.state==='playing');
   await page.waitForFunction(()=>Number(getComputedStyle(__SANGENG__.ui.el.fade).opacity)<.01);
   const landmarks=[];
   for(const material of mats){
    const view=await page.evaluate(async material=>{
     const T=await import('/vendor/three/three.module.js'),g=__SANGENG__;let target;
     g.level.traverse(o=>{if(o.isMesh&&o.material?.name===material)target=o;});
     if(!target)throw Error('Missing sign material '+material);
     g.level.updateMatrixWorld(true);const c=new T.Box3().setFromObject(target).getCenter(new T.Vector3());
     // 贴图 slab 是六面盒，首个顶点法线未必是字牌正面；按最薄轴取朝房间的一侧。
     const bounds=new T.Box3().setFromObject(target),size=bounds.getSize(new T.Vector3());
     const front=size.x<size.z?new T.Vector3(c.x>0?-1:1,0,0):new T.Vector3(0,0,1);
     const pos=c.clone().addScaledVector(front,1.1);pos.y=0;
     g.player.teleportToPos(pos,c);g.camera.updateMatrixWorld(true);
     return {material,mesh:target.name,center:c.toArray(),normal:front.toArray()};
    },material);
    await page.waitForTimeout(180);await page.screenshot({path:path.join(out,id+'-'+material+'.png')});landmarks.push(view);
   }
   const frames=await page.evaluate(async()=>{
    const r=__SANGENG__.renderer,old=r.info.autoReset;r.info.autoReset=false;
    const times=[];let last=performance.now(),calls=0,tris=0;
    for(let i=0;i<45;i++){r.info.reset();await new Promise(requestAnimationFrame);const now=performance.now();times.push(now-last);last=now;calls=Math.max(calls,r.info.render.calls);tris=Math.max(tris,r.info.render.triangles);}
    r.info.autoReset=old;times.sort((a,b)=>a-b);return {medianMs:times[22],p95Ms:times[42],maxDrawCalls:calls,maxTriangles:tris};
   });
   result.push({id,landmarks,frames});await page.keyboard.press('Escape');await page.locator('#sg-pause [data-act="back"]').click();await page.waitForSelector('a.card');
  }
  fs.writeFileSync(path.join(out,'result.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
 }finally{await app.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
