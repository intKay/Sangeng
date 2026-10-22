"""Prepare visible, palette-matched tiling surfaces and bump maps from retained AI images."""
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'tools/av/sources-v15'
TEX=ROOT/'assets/textures'
SPECS={
 'plaster':(['MAT_plaster','MAT_paint_ceiling'],[173,175,158],.025,75),
 'wallpaper':(['MAT_wallpaper','MAT_wallpaper_dark'],[151,153,119],.018,55),
 'tile_green':(['MAT_tile_green'],[77,111,100],.035,28),
 'tile_floor':(['MAT_tile_floor'],[126,132,114],.028,44),
 'wood_door':(['MAT_wood_door','MAT_wood_dark','MAT_shrine_wood'],[102,69,48],.018,36),
 'wood_pale':(['MAT_wood_pale','MAT_wood_floor'],[155,120,76],.016,32),
 'soil':(['MAT_soil'],[87,78,62],.055,90),
 'bark':(['MAT_bark'],[76,77,65],.075,85),
 'curtain':(['MAT_curtain'],[152,143,110],.012,6),
 'grass':(['MAT_grass'],[50,62,41],.035,5),
 'tile_white':(['MAT_tile_white'],[180,182,162],.025,55),
}

def periodic(image):
    # Mirrored quadrants preserve broad texture structure while guaranteeing
    # exact periodic boundaries, including height derivatives at the seam.
    a=np.asarray(image.resize((256,256),Image.Resampling.LANCZOS))
    return np.concatenate([np.concatenate([a,a[:,::-1]],axis=1),np.concatenate([a[::-1],a[::-1,::-1]],axis=1)],axis=0)

def main():
    manifest=json.loads((TEX/'manifest.json').read_text(encoding='utf-8'));records=[]
    for name,(keys,mean,bump,shine) in SPECS.items():
        src=Image.open(SOURCE/(name+'.png')).convert('RGB')
        a=periodic(src).astype(float)
        # Match the authored palette but retain medium-scale chips, grout,
        # stains and real surface variation, rather than only high frequencies.
        a=(a-a.mean(axis=(0,1)))*1.15+np.array(mean)
        a=np.clip(a,0,255).astype('uint8')
        color=Image.fromarray(a);file='av15_'+name+'.jpg';color.save(TEX/file,quality=94,subsampling=0)
        gray=color.convert('L').filter(ImageFilter.GaussianBlur(.5))
        height=np.asarray(gray,dtype=float)
        height=np.clip((height-height.mean())*1.6+128,0,255).astype('uint8')
        heightfile='av15_'+name+'_height.png';Image.fromarray(height).save(TEX/heightfile,optimize=True)
        for key in keys:
            d=manifest['materials'][key]
            old=d.get('av15Source',d['file']);d['av15Source']=old
            baseline=np.asarray(Image.open(TEX/old).convert('RGB').resize((512,512)),dtype=float)
            d.update(file=file,bump=heightfile,bumpScale=bump,shininess=shine,specular='#202822' if 'tile' in name else '#11130f',filter='linear')
            if key=='MAT_wallpaper_dark':d['tint']='#b2b2a2'
            elif key=='MAT_tile_floor':d['tint']='#a4aca0'
            else:d['tint']='#ffffff'
            records.append({'material':key,'source':old,'file':file,'bump':heightfile,'meanPixelDifference':float(np.mean(np.abs(baseline-a))),'generatedSource':str((SOURCE/(name+'.png')).relative_to(ROOT))})
    (TEX/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    out=ROOT/'reports/av-v1.5';out.mkdir(parents=True,exist_ok=True)
    (out/'materials.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
    print('Prepared',len(records),'visible material replacements')

if __name__=='__main__':main()
