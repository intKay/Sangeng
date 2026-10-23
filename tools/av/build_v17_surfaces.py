"""Three-scene material identities, retained local generation sources, fixed seeds."""
import json,sys,subprocess
from pathlib import Path
import numpy as np
from PIL import Image,ImageFilter
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools/art'))
import artlib as A
from build_v16_surfaces import periodic_edges
TEX=ROOT/'assets/textures';OUT=ROOT/'reports/av-v1.7';OUT.mkdir(exist_ok=True)
def lum(a):return a@np.array([.299,.587,.114])
def source(name):return np.asarray(Image.open(ROOT/f'tools/av/sources-v15/{name}.png').convert('RGB').resize((512,512)),dtype=float)
def main():
 d=json.loads(subprocess.check_output(['git','show','8afbad8:assets/textures/manifest.json'],cwd=ROOT));records=[]
 n=512;y,x=np.mgrid[:n,:n]
 def save(key,a,kind,shine=10,spec='#060706',scale=.003):
  a=periodic_edges(a);rgb=np.clip(a,0,255).astype('uint8');name='av17_'+key[4:]
  Image.fromarray(rgb).save(TEX/(name+'.png'),optimize=True)
  g=Image.fromarray(rgb).convert('L');h=np.asarray(g.filter(ImageFilter.GaussianBlur(.7)),dtype=float)-np.asarray(g.filter(ImageFilter.GaussianBlur(4)),dtype=float)
  h=periodic_edges(h[:,:,None]*.7+128)[:,:,0];Image.fromarray(np.clip(h,0,255).astype('uint8')).save(TEX/(name+'_height.png'))
  entry=d['materials'].setdefault(key,{'colorSpace':'srgb','emissive':None})
  entry.update(file=name+'.png',tint='#ffffff',bump=name+'_height.png',bumpScale=scale,shininess=shine,specular=spec,filter='linear',surfaceClass=kind)
  records.append({'material':key,'class':kind,'file':name+'.png','shininess':shine})
 # Glaze rather than black-and-green camouflage; 25cm tiles at 2m UV scale.
 r=A.rng('v17-glaze');broad=A.fbm((n,n),4,4,r);fine=A.fbm((n,n),30,3,r)
 grid=r.uniform(-8,8,(8,8));value=grid[y//64,x//64]
 edge=np.minimum.reduce([x%64,63-x%64,y%64,63-y%64]);joint=np.clip((2.5-edge)/2.5,0,1)
 tile=np.array([76,96,83])+(broad[:,:,None]-.5)*13+value[:,:,None]+(fine[:,:,None]-.5)*5
 tile=tile*(1-joint[:,:,None])+np.array([37,40,33])*joint[:,:,None]
 save('MAT_tile_green',tile,'tile',40,'#17211d',.004)
 # Sheet metal has restrained paint variation; local rust is added at handles/vents in shader.
 src=source('wood_door');noise=A.fbm((n,n),4,5,A.rng('v17-locker'))
 metal=np.array([105,122,109])+(noise[:,:,None]-.5)*27+(lum(src)-lum(src).mean())[:,:,None]*.14
 save('MAT_metal_locker',metal,'locker',32,'#1d2420',.002)
 for key,srcname,mean,strength,kind in [
 ('MAT_bark','bark',[66,62,51],.48,'outdoor'),('MAT_grass','grass',[39,48,30],.24,'outdoor'),
 ('MAT_soil','soil',[89,74,53],.36,'outdoor'),('MAT_soil_road','soil',[100,86,65],.36,'road'),
 ('MAT_shrine_wood','wood_door',[75,54,40],.65,'outdoor')]:
  sl=lum(source(srcname));a=np.array(mean)+(sl-sl.mean())[:,:,None]*strength
  save(key,a,kind,3,'#000000',.004 if srcname=='bark' else .002)
 for key,mean in [('MAT_leaves',[34,45,31]),('MAT_stone',[102,103,91]),('MAT_red_cloth',[91,48,37])]:
  old=np.asarray(Image.open(TEX/d['materials'][key]['file']).convert('RGB').resize((512,512)).filter(ImageFilter.GaussianBlur(1)),dtype=float)
  a=np.array(mean)+(lum(old)-lum(old).mean())[:,:,None]*.34
  save(key,a,'outdoor' if key!='MAT_red_cloth' else 'cloth',4,'#000000',.002)
 noise=A.fbm((n,n),5,5,A.rng('v17-ceramic'));rim=np.exp(-((y/n-.46)/.035)**2)
 inner=np.clip((y/n-.73)/.2,0,1)
 ceramic=np.array([183,181,158])+(noise[:,:,None]-.5)*24-rim[:,:,None]*np.array([35,31,24])-inner[:,:,None]*np.array([22,24,24])
 save('MAT_ceramic_worn',ceramic,'ceramic',60,'#30352c',.0015)
 steel=np.array([118,126,119])+(noise[:,:,None]-.5)*24+np.sin(x*.6)[:,:,None]*1.5
 save('MAT_steel_worn',steel,'metal',70,'#333c37',.001)
 iron=np.array([62,66,59])+(noise[:,:,None]-.5)*18
 save('MAT_iron_painted',iron,'metal',18,'#242b21',.0015)
 trough=(.5+.5*np.cos(x/n*math_tau*12))**3;rows=(y%128<3).astype(float)
 roof=np.array([55,61,55])+trough[:,:,None]*13+(noise[:,:,None]-.5)*18-rows[:,:,None]*14
 save('MAT_roof_tile',roof,'outdoor',9,'#050605',.006)
 (TEX/'manifest.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\r\n')
 (OUT/'surfaces.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
 print('Prepared',len(records),'surfaces; total materials',len(d['materials']),'bumps',sum(bool(v.get('bump')) for v in d['materials'].values()))
math_tau=np.pi*2
if __name__=='__main__':main()
