"""AI microdetail only: preserve authored palette, large forms, UVs and edges."""
import json
import argparse
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter
from comfy_client import ComfyClient, material_workflow

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'reports/av-v1.4'
RAW=OUT/'raw'
SPECS={
 'MAT_wallpaper':'Faded cream and moss green floral paper wallpaper, sparse tiny worn printed flowers, old modest Chinese apartment wall',
 'MAT_wallpaper_dark':'The same faded cream and moss green floral wallpaper in a neglected corridor, fine water marks and faded fibers',
 'MAT_plaster':'Warm grey worn lime plaster, small soft flakes, fine water marks, old interior wall',
 'MAT_tile_green':'Muted dark jade green square ceramic tiles with preserved straight grout lines, fine damp mineral deposits and worn glaze',
 'MAT_wood_pale':'Old pale plywood, thin worn varnish and fine scratches, inexpensive everyday household furniture',
 'MAT_lantern_paper':'Muted traditional red orange paper lantern material, thin bamboo rib shadows already in source, delicate paper fibers and small creases',
}

def restrained_detail(base,generated):
    """Inject bounded luminance detail; a zero/zero-slope border keeps tiling."""
    source=np.asarray(base.convert('RGB'),dtype=np.float32)
    ai=generated.convert('L').resize(base.size,Image.Resampling.LANCZOS)
    detail=np.asarray(ai,dtype=np.float32)-np.asarray(ai.filter(ImageFilter.GaussianBlur(5)),dtype=np.float32)
    detail-=detail.mean()
    detail=np.clip(detail,-18,18)
    height,width=detail.shape
    mask=np.sin(np.linspace(0,np.pi,width))**2
    mask=np.outer(np.sin(np.linspace(0,np.pi,height))**2,mask)
    result=np.clip(np.rint(source+detail[:,:,None]*mask[:,:,None]*.6),0,255).astype(np.uint8)
    # Do not rely on floating point sin(pi) becoming exactly zero.
    result[0]=source[0];result[-1]=source[-1];result[:,0]=source[:,0];result[:,-1]=source[:,-1]
    return Image.fromarray(result)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--from-sources',action='store_true');args=parser.parse_args()
    manifest_path=ROOT/'assets/textures/manifest.json'
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    client=ComfyClient();records=[]
    for index,(key,text) in enumerate(SPECS.items()):
        definition=manifest['materials'][key]
        source_name=definition.get('av14Source',definition['file'])
        source=Image.open(ROOT/'assets/textures'/source_name).convert('RGB')
        prepared=RAW/(key+'-input.png');prepared.parent.mkdir(parents=True,exist_ok=True)
        source.resize((512,512),Image.Resampling.NEAREST).save(prepared)
        retained=ROOT/'tools/av/sources'/(key+'.png');retained.parent.mkdir(parents=True,exist_ok=True)
        if args.from_sources:
            job={'mode':'retained-source','seed':2026102150+index}
        else:
            upload=client.upload(prepared)
            generated,job=client.run(material_workflow(upload,text,2026102150+index,.27),RAW,key)
            retained.write_bytes(generated[0].read_bytes())
        result=restrained_detail(source,Image.open(retained))
        name='av14_'+key.removeprefix('MAT_')+'.png'
        target=ROOT/'assets/textures'/name;result.save(target,optimize=True)
        before=np.asarray(source,dtype=np.float32);after=np.asarray(result,dtype=np.float32)
        assert np.array_equal(before[0],after[0]) and np.array_equal(before[-1],after[-1])
        assert np.array_equal(before[:,0],after[:,0]) and np.array_equal(before[:,-1],after[:,-1])
        assert np.max(np.abs(after-before))<=11
        definition.update(file=name,av14Source=source_name)
        records.append(dict(material=key,source=source_name,file=name,dimensions=list(source.size),maxChannelDelta=float(np.max(np.abs(after-before))),meanAbsoluteDelta=float(np.mean(np.abs(after-before))),borderPreserved=True,job=job))
        print('MATERIAL READY '+key,flush=True)
    manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (OUT/'materials.json').write_text(json.dumps(records,indent=2),encoding='utf-8')

if __name__=='__main__': main()
