"""Produce audible environmental beds; retain generated sources and baseline A/B."""
import json
import subprocess
from pathlib import Path
import numpy as np
from comfy_client import ComfyClient,node
from build_ambience import decode,neural_loop,SR

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'reports/av-v1.5'
SOURCES=ROOT/'tools/av/sources-v15'
GENERATE=[
 ('corridor','door/ambience/corridor_hum.ogg','Quiet old apartment corridor at night, steady low electrical fluorescent hum, distant ventilation rattling, a faint hollow indoor room tone, realistic field recording, no music no speech no voices no melody'),
 ('bathhouse','mirror/ambience/fluorescent_buzz.ogg','An empty tiled public bathhouse with low fluorescent electrical buzz, soft ventilation and faint distant dripping water, hollow spacious room resonance, realistic quiet interior soundscape, no music no speech no voices'),
]
REUSE=[
 ('rain','door/ambience/rain_window.ogg','door-rain_window.flac'),
 ('water','mirror/ambience/distant_water.ogg','mirror-distant_water.flac'),
 ('wind','nightroad/ambience/wind_field.ogg','nightroad-wind_field.flac'),
]

def workflow(text,seed):
    return {
      '1':node('CheckpointLoaderSimple',ckpt_name='stable-audio-open-1.0.safetensors'),
      '2':node('CLIPLoader',clip_name='t5-base.safetensors',type='stable_audio',device='default'),
      '3':node('CLIPTextEncode',clip=['2',0],text=text),
      '4':node('CLIPTextEncode',clip=['2',0],text='speech, singing, voices, music, melody, rhythm, drums, harsh noise, impact, thunder, distortion'),
      '5':node('EmptyLatentAudio',seconds=16.,batch_size=1),
      '6':node('ConditioningStableAudio',positive=['3',0],negative=['4',0],seconds_start=0.,seconds_total=16.),
      '7':node('KSampler',model=['1',0],positive=['6',0],negative=['6',1],latent_image=['5',0],seed=seed,steps=48,cfg=4.,sampler_name='dpmpp_3m_sde_gpu',scheduler='exponential',denoise=1.),
      '8':node('VAEDecodeAudio',samples=['7',0],vae=['1',2]),
      '9':node('SaveAudio',audio=['8',0],filename_prefix='sangeng_v15/environment_'+str(seed)),
    }

def main():
    client=ComfyClient();OUT.mkdir(parents=True,exist_ok=True);SOURCES.mkdir(parents=True,exist_ok=True)
    specs=[]
    for i,(name,relative,text) in enumerate(GENERATE):
        source=SOURCES/(name+'.flac');metadata=SOURCES/(name+'.json')
        if not source.exists():
            print('GENERATING SOUND '+name,flush=True)
            files,job=client.run(workflow(text,2026102280+i),OUT/'raw',name,timeout=1800)
            source.write_bytes(files[0].read_bytes());metadata.write_text(json.dumps({'model':'Stable Audio Open 1.0','seed':2026102280+i,'prompt':text,'job':job},indent=2),encoding='utf-8')
        specs.append((name,relative,source))
    for name,relative,source in REUSE:specs.append((name,relative,ROOT/'tools/av/sources'/source))
    report=[]
    for name,relative,source in specs:
        target=ROOT/'assets/audio'/relative
        baseline=OUT/'audio-before'/relative;baseline.parent.mkdir(parents=True,exist_ok=True)
        if not baseline.exists():baseline.write_bytes(subprocess.check_output(['git','show','f669c15:assets/audio/'+relative],cwd=ROOT))
        base=decode(baseline);generated=neural_loop(decode(source),len(base))
        generated*=np.sqrt(np.mean(base**2))/max(1e-10,np.sqrt(np.mean(generated**2)))
        result=base*.25+generated*.85
        result-=result.mean(axis=0)
        result*=10**(-20.8/20)/max(1e-10,np.sqrt(np.mean(result**2)))
        result*=min(1.,10**(-2/20)/max(1e-10,np.max(np.abs(result))))
        subprocess.run(['ffmpeg','-v','error','-y','-f','f32le','-ar',str(SR),'-ac','2','-i','-','-c:a','libvorbis','-q:a','5',str(target)],input=result.astype('<f4').tobytes(),check=True)
        x=decode(target);rms=np.sqrt(np.mean(x*x));peak=np.max(np.abs(x))
        seam=np.max(np.abs(x[0]-x[-1]))/max(1e-12,np.sqrt(np.mean(np.diff(x,axis=0)**2)))
        assert np.isfinite(x).all() and peak<10**(-1/20) and seam<6
        report.append({'file':relative,'source':str(source.relative_to(ROOT)),'seconds':len(x)/SR,'rmsDbFS':float(20*np.log10(rms)),'peakDbFS':float(20*np.log10(peak)),'seamRatio':float(seam),'neuralCoefficient':.85,'baselineCoefficient':.25,'humanListeningAccepted':False})
        print('SOUND READY '+name,flush=True)
    (OUT/'audio.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    # More environmental space between musical phrases; no new peaks or stingers.
    for chapter in ['door','mirror','nightroad']:
        path=ROOT/'assets/audio'/chapter/'manifest.json';d=json.loads(path.read_text(encoding='utf-8'))
        d['music']['main']['volume']=.34
        path.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')

if __name__=='__main__':main()
