"""Small localhost-only ComfyUI client shared by CPython and Blender Python."""
import json
from pathlib import Path
import time
import urllib.parse
import urllib.request
import uuid

class ComfyClient:
    def __init__(self, base='http://127.0.0.1:8188'):
        parsed=urllib.parse.urlparse(base)
        if parsed.scheme!='http' or parsed.hostname not in ('127.0.0.1','localhost','::1'):
            raise ValueError('This project bridge only accepts a local ComfyUI endpoint')
        self.base=base.rstrip('/')
        self.http=urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def api(self,path,payload=None):
        data=None if payload is None else json.dumps(payload).encode()
        request=urllib.request.Request(self.base+path,data=data,headers={'Content-Type':'application/json'})
        with self.http.open(request,timeout=45) as response:
            return json.load(response)

    def upload(self,path):
        path=Path(path)
        boundary='sangeng-'+uuid.uuid4().hex
        filename='sangeng-av-'+uuid.uuid4().hex+'.png'
        body=(f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="{filename}"\r\nContent-Type: image/png\r\n\r\n').encode()+path.read_bytes()+f'\r\n--{boundary}--\r\n'.encode()
        request=urllib.request.Request(self.base+'/upload/image',data=body,headers={'Content-Type':f'multipart/form-data; boundary={boundary}'})
        with self.http.open(request,timeout=60) as response:
            result=json.load(response)
        return '/'.join(p for p in (result.get('subfolder'),result['name']) if p)

    def run(self,prompt,out_dir,label,timeout=1200):
        out_dir=Path(out_dir); out_dir.mkdir(parents=True,exist_ok=True)
        (out_dir/(label+'.api.json')).write_text(json.dumps(prompt,indent=2),encoding='utf-8')
        submitted=self.api('/prompt',{'prompt':prompt,'client_id':'sangeng-av-'+uuid.uuid4().hex})
        pid=submitted['prompt_id']
        (out_dir/(label+'.job.json')).write_text(json.dumps(submitted,indent=2),encoding='utf-8')
        started=time.monotonic()
        while time.monotonic()-started<timeout:
            history=self.api('/history/'+pid)
            if pid in history:
                entry=history[pid]
                (out_dir/(label+'.history.json')).write_text(json.dumps(entry,indent=2),encoding='utf-8')
                if entry['status']['status_str']!='success':
                    raise RuntimeError('ComfyUI task failed; see recorded history: '+pid)
                files=[]
                for node in entry['outputs'].values():
                    for group in node.values():
                        if not isinstance(group,list): continue
                        for item in group:
                            if not isinstance(item,dict) or 'filename' not in item: continue
                            query=urllib.parse.urlencode({k:item[k] for k in ('filename','subfolder','type') if k in item})
                            target=out_dir/(label+Path(item['filename']).suffix)
                            with self.http.open(self.base+'/view?'+query,timeout=60) as response:
                                target.write_bytes(response.read())
                            files.append(target)
                if not files: raise RuntimeError('Successful job returned no saved files')
                return files,{'prompt_id':pid,'elapsed_seconds':round(time.monotonic()-started,2)}
            time.sleep(2)
        raise TimeoutError('Observation timeout; existing ComfyUI job was not cancelled: '+pid)

def node(kind,**inputs):
    return {'class_type':kind,'inputs':inputs}

def material_workflow(image,text,seed=20261021,denoise=.27):
    return {
      '1':node('CheckpointLoaderSimple',ckpt_name='DreamShaper_8_pruned.safetensors'),
      '2':node('CLIPTextEncode',clip=['1',1],text=text+', flat diffuse material swatch, frontal orthographic, muted aged painted surface, fine irregular material wear, no object, no perspective'),
      '3':node('CLIPTextEncode',clip=['1',1],text='text, letters, logo, scene, room, person, object, perspective, glossy, dramatic lighting, spotlight, strong shadow, high contrast, photorealism'),
      '4':node('LoadImage',image=image),
      '5':node('VAEEncode',pixels=['4',0],vae=['1',2]),
      '6':node('KSampler',model=['1',0],positive=['2',0],negative=['3',0],latent_image=['5',0],seed=seed,steps=22,cfg=5.5,sampler_name='dpmpp_2m',scheduler='karras',denoise=denoise),
      '7':node('VAEDecode',samples=['6',0],vae=['1',2]),
      '8':node('SaveImage',images=['7',0],filename_prefix='sangeng_av/material_'+str(seed)),
    }
