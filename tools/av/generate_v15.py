"""Generate actual replacement surfaces using the user's local Z-Image Turbo."""
import argparse
import json
from pathlib import Path
from comfy_client import ComfyClient, node

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'reports/av-v1.5'
SOURCES=ROOT/'tools/av/sources-v15'
SPECS={
 'plaster':'Weathered lime plaster from a 1980s Chinese residential stairwell. Faded warm ivory paint, broad irregular peeling areas exposing grey lime, soft damp tide marks, small chips and hairline cracks. No graffiti. Large quiet patches between wear. Authentic unrenovated building material.',
 'wallpaper':'Faded vintage Chinese apartment wallpaper, small sparse sage green floral sprigs on yellowed cream paper. Frayed paper fibers, curling small tears and pale damp marks. Quiet modest 1980s home. Small repeated flowers, no large central motif.',
 'tile_green':'Old square jade green glazed ceramic tiles in a Chinese public bathhouse, straight uniform horizontal and vertical dark grout, worn glossy glaze, white mineral tide marks, subtle fine cracks, damp mottling. Four by four square tiles filling the entire image.',
 'tile_floor':'Old small square ivory and dark green ceramic mosaic floor in a Chinese apartment stairwell, broad repeated checker pattern, chipped corners, dirty dark grout and grey dust along seams. Flat top view, uniform tile scale. Four by four tiles filling the entire image.',
 'wood_door':'Aged reddish brown Chinese plywood apartment door surface. Vertical straight wood veneer grain, broad worn varnish, shallow scratches and rubbed lighter patches, muted dark red brown. No handle, no frame, no numbers.',
 'wood_pale':'Old honey beige plywood cabinet veneer, straight narrow grain, water rings, worn amber varnish, light grey scratches and a few chipped flakes. Cheap familiar domestic furniture. No handle, no frame.',
 'soil':'Damp compacted dark brown rural footpath earth. Uneven fine gravel, small muddy clods, a few embedded pale stones, shallow irregular footprints and pressed straw fibers. Ground fills frame, natural quiet scale, no plants.',
 'bark':'Rough aged tree bark, deep vertical fissures, charcoal brown and cool grey ridges, occasional dusty green lichen. Broad irregular natural ridges and fine fibrous details. Bark surface fills image.',
 'curtain':'Old faded beige woven cotton cloth with a very small subtle muted green repeating floral print, visible coarse soft fabric weave, sun faded irregular patches and light brown age marks. Flat fabric surface with no folds, no scene, no vertical striped pattern.',
 'grass':'A top down ground material of short dark rural field grass, small thin sparse blades growing through brown earth, natural patchy ground coverage, subdued moss olive green, dry pale straw mixed into grass. No tall plants, no individual large leaves.',
 'tile_white':'Old small square off-white glazed ceramic tiles from a Chinese bathhouse sink, straight regular four by four grid with narrow dark grey grout. Ivory worn glaze, tiny crazing, subtle pale mineral stains, realistic scale. Surface fills frame.'
}

def workflow(text,seed):
    prompt=text+' Material texture swatch for an atmospheric realistic low-poly game. Flat orthographic close-up, surface completely fills the square, evenly lit diffuse light, no perspective, no room, no objects, no text, no letters, no dramatic cast shadows. Restrained natural colors, coherent wear at medium and fine scales.'
    return {
     '1':node('UNETLoader',unet_name='z_image_turbo_bf16.safetensors',weight_dtype='fp8_e4m3fn'),
     '2':node('CLIPLoader',clip_name='qwen_3_4b.safetensors',type='lumina2',device='default'),
     '3':node('VAELoader',vae_name='ae.safetensors'),
     '4':node('CLIPTextEncode',clip=['2',0],text=prompt),
     '5':node('ConditioningZeroOut',conditioning=['4',0]),
     '6':node('EmptySD3LatentImage',width=768,height=768,batch_size=1),
     '7':node('ModelSamplingAuraFlow',model=['1',0],shift=3.0),
     '8':node('KSampler',model=['7',0],positive=['4',0],negative=['5',0],latent_image=['6',0],seed=seed,steps=9,cfg=1.,sampler_name='euler',scheduler='simple',denoise=1.),
     '9':node('VAEDecode',samples=['8',0],vae=['3',0]),
     '10':node('SaveImage',images=['9',0],filename_prefix='sangeng_v15/surface_'+str(seed)),
    }

def main():
    p=argparse.ArgumentParser();p.add_argument('--only',nargs='*');args=p.parse_args()
    SOURCES.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
    client=ComfyClient();records=[]
    for i,(name,text) in enumerate(SPECS.items()):
        if args.only and name not in args.only:continue
        target=SOURCES/(name+'.png');record=SOURCES/(name+'.json')
        if target.exists() and record.exists():print('RETAINED '+name,flush=True);continue
        prompt=workflow(text,2026102200+i)
        print('GENERATING '+name,flush=True)
        files,job=client.run(prompt,OUT/'raw',name,timeout=3600)
        target.write_bytes(files[0].read_bytes())
        record.write_text(json.dumps({'name':name,'model':'Z-Image-Turbo bf16 loaded as fp8_e4m3fn','seed':2026102200+i,'prompt':text,'job':job},indent=2),encoding='utf-8')
        print('READY '+name+' '+json.dumps(job),flush=True)

if __name__=='__main__':main()
