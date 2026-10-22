/* Location-dependent age for architectural surfaces. Textures keep material identity. */
export function applySurfaceWear(material, definition, sceneId) {
  const kind=definition.surfaceClass;
  if(!['paper','plaster','ceiling','tileFloor','floor','cloth','doorWood'].includes(kind))return;
  const mode={paper:1,plaster:1,ceiling:2,tileFloor:3,floor:3,cloth:4,doorWood:5}[kind];
  const scene=sceneId==='door'?1:sceneId==='mirror'?2:0;
  if(!scene)return;
  material.customProgramCacheKey=()=>`surface-wear-v16-${mode}-${scene}`;
  material.onBeforeCompile=shader=>{
    shader.vertexShader='varying vec3 vAgeWorld;\nvarying vec2 vAgeUV;\n'+shader.vertexShader;
    shader.vertexShader=shader.vertexShader.replace('#include <worldpos_vertex>',
      '#include <worldpos_vertex>\nvAgeWorld=(modelMatrix*vec4(transformed,1.0)).xyz;vAgeUV=uv;');
    shader.fragmentShader=`varying vec3 vAgeWorld;
varying vec2 vAgeUV;
float ageHash(vec3 p){return fract(sin(dot(p,vec3(127.1,311.7,74.7)))*43758.5453);}
float ageNoise(vec3 p){vec3 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);
return mix(mix(mix(ageHash(i),ageHash(i+vec3(1,0,0)),f.x),mix(ageHash(i+vec3(0,1,0)),ageHash(i+vec3(1,1,0)),f.x),f.y),
mix(mix(ageHash(i+vec3(0,0,1)),ageHash(i+vec3(1,0,1)),f.x),mix(ageHash(i+vec3(0,1,1)),ageHash(i+vec3(1,1,1)),f.x),f.y),f.z);}
`+shader.fragmentShader;
    shader.fragmentShader=shader.fragmentShader.replace('#include <map_fragment>',`#include <map_fragment>
vec3 wp=vAgeWorld;
float broad=ageNoise(wp*1.8)+.35*ageNoise(wp*5.7);
float streak=ageNoise(vec3(wp.x*13.0,wp.y*.55,wp.z*13.0));
float grime=0.0;
${mode===1?`
float rising=(1.0-smoothstep(.02,.62,wp.y+(broad-.65)*.35))*.34;
float wet=0.0;
${scene===1?`wet=exp(-distance(wp.xz,vec2(6.18,7.62))*3.0)+.8*exp(-distance(wp.xz,vec2(1.02,14.1))*3.0);`:
`wet=exp(-abs(wp.z+.2)*2.0)*smoothstep(.6,2.5,abs(wp.x));`}
grime=rising+wet*smoothstep(.3,2.6,wp.y)*(.3+.5*streak);
float fracture=ageNoise(wp*9.0)+.35*ageNoise(wp*3.1);
float exposure=smoothstep(.58,.72,fracture)*clamp(wet,0.0,1.0)*smoothstep(.25,1.4,wp.y);
float rim=smoothstep(.49,.57,fracture)*(1.0-smoothstep(.57,.64,fracture));
diffuseColor.rgb=mix(diffuseColor.rgb,vec3(.31,.29,.245)*(.82+.18*broad),exposure*.7);
grime+=rim*wet*.28;
` : mode===2?`
float d=distance(wp.xz,vec2(6.0,7.6));
${scene===1?`d=min(d,distance(wp.xz,vec2(.85,14.0)));`:`d=distance(wp.xz,vec2(-2.7,.3));`}
float seep=1.0-smoothstep(.15,1.25,d+(broad-.6)*.75);
float tide=smoothstep(.30,.52,seep)*(1.0-smoothstep(.55,.72,seep));
grime=seep*.50+tide*.20;
` : mode===3?`
float edge=0.0;
${scene===1?`edge=(1.0-smoothstep(.04,.4,1.08-abs(wp.x)))*step(abs(wp.x),1.2);`:
`edge=smoothstep(2.4,3.0,abs(wp.x));`}
grime=edge*(.2+.2*broad);
` : mode===4?`grime=(1.0-smoothstep(.12,.65,wp.y))*(.1+.15*broad);` : `
// Exported UVs retain the original two-metre planar coordinates when a leaf rotates.
// Anchor handling wear there, so opening a door cannot slide its wear through the room.
wp=vec3(1.1,vAgeUV.y*2.0,-vAgeUV.x*2.0);
float hand=exp(-pow((wp.z-5.68)/.18,2.0)-pow((wp.y-1.02)/.16,2.0));
float kick=exp(-pow((wp.z-5.35)/.34,2.0)-pow((wp.y-.18)/.15,2.0));
float loss=(hand*.68+kick*.42)*smoothstep(.38,.7,ageNoise(wp*32.0));
diffuseColor.rgb=mix(diffuseColor.rgb,vec3(.22,.16,.095),loss);
grime=0.0;
`}
grime=clamp(grime,0.0,.78);
diffuseColor.rgb*=mix(vec3(1.0),vec3(.51,.46,.37),grime);
`);
  };
}
