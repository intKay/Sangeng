/* Local surface dressing: no collision, interaction or story state changes. */
import * as THREE from 'three';

function softTexture() {
  const c=document.createElement('canvas');c.width=c.height=64;
  const ctx=c.getContext('2d'),g=ctx.createRadialGradient(32,32,1,32,32,32);
  g.addColorStop(0,'#ffffff');g.addColorStop(.35,'#888888');g.addColorStop(1,'#000000');
  ctx.fillStyle=g;ctx.fillRect(0,0,64,64);
  const t=new THREE.CanvasTexture(c);t.colorSpace=THREE.NoColorSpace;return t;
}

export class Atmosphere {
  constructor(game) {
    this.game=game;this.time=0;this.seed=22015;
    this.group=new THREE.Group();this.group.name='AV_surface_dressing';
    game.level.add(this.group);
    this.mask=softTexture();
    const id=game.config.id;
    if(id==='door') {
      // Damp patches under the leaking corridor and near the window.
      this.puddles([[.65,14.0,.35,.7]],0x424b3d);
      this.dust(70,[-.9,.5,1],[.9,2.5,17],0xb5c9b2,.018);
    } else if(id==='mirror') {
      this.puddles([[-1.4,-.4,.8,.55],[1.1,.8,.9,.65],[-.5,-1.6,.6,.45],[2.3,-.4,.4,.65]],0x7a9790);
      this.dust(65,[-2.5,.3,-2],[2.5,2.4,2],0xc7d8cf,.06);
    } else {
      this.puddles([[.4,7,.7,1.2],[-.3,19,.65,1.3],[.5,38,.5,1.2],[-.4,64,.6,1.0]],0x40546c);
      this.dust(140,[-6,.1,0],[6,1.6,65],0x8ba7b0,.045);
    }
  }

  random() { this.seed=(Math.imul(this.seed,1664525)+1013904223)>>>0;return this.seed/4294967296; }

  puddles(specs,color) {
    const material=new THREE.MeshPhongMaterial({color,specular:0x9eb2af,shininess:110,
      transparent:true,opacity:.16,alphaMap:this.mask,depthWrite:false,
      polygonOffset:true,polygonOffsetFactor:-1,polygonOffsetUnits:-1});
    for(const [x,z,w,h] of specs) {
      const mesh=new THREE.Mesh(new THREE.PlaneGeometry(w*2,h*2),material);
      mesh.name='AV_damp_patch';mesh.rotation.x=-Math.PI/2;mesh.rotation.z=this.random()*.7;
      mesh.position.set(x,.012,z);mesh.receiveShadow=true;
      // A transparent decorative plane must never consume gameplay rays.
      mesh.raycast=()=>{};this.group.add(mesh);
    }
  }

  dust(count,min,max,color,opacity) {
    this.min=min;this.max=max;this.positions=new Float32Array(count*3);this.phases=[];
    for(let i=0;i<count;i++) {
      this.phases.push(this.random()*Math.PI*2);
      for(let a=0;a<3;a++)this.positions[i*3+a]=min[a]+this.random()*(max[a]-min[a]);
    }
    const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.BufferAttribute(this.positions,3));
    this.motes=new THREE.Points(geometry,new THREE.PointsMaterial({color,size:.035,map:this.mask,
      transparent:true,opacity,blending:THREE.AdditiveBlending,depthWrite:false}));
    this.motes.name='AV_air_particles';this.motes.raycast=()=>{};this.group.add(this.motes);
  }

  update(dt) {
    this.time+=dt;if(!this.motes)return;
    for(let i=0;i<this.phases.length;i++) {
      const k=i*3;
      this.positions[k]+=Math.sin(this.time*.23+this.phases[i])*.012*dt;
      this.positions[k+1]+=.012*dt;
      if(this.positions[k+1]>this.max[1])this.positions[k+1]=this.min[1];
    }
    this.motes.geometry.attributes.position.needsUpdate=true;
  }
}
