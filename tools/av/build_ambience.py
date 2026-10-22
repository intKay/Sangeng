"""Blend a low-level local neural texture under the authored ambience beds."""
import json
import argparse
from pathlib import Path
import subprocess
import numpy as np
from comfy_client import ComfyClient,node

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'reports/av-v1.4'
RAW=OUT/'raw'
SR=44100
SPECS=[
 ('door','rain_window','Quiet gentle rain heard from inside an old apartment through a closed window, soft distant rainfall, subdued continuous ambience, no thunder, no voices, no music'),
 ('mirror','distant_water','Soft distant water trickling through pipes in an empty tiled public bathhouse, diffuse watery room resonance, subtle continuous background ambience, no voices, no speech, no music'),
 ('nightroad','wind_field','Soft night wind blowing gently through rice grass and sparse trees in the distance, subdued rural air movement, continuous quiet ambience, no animals close by, no voices, no music'),
]

def decode(path):
    raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-f','f32le','-acodec','pcm_f32le','-ar',str(SR),'-ac','2','-'])
    return np.frombuffer(raw,dtype='<f4').reshape(-1,2).astype(np.float64)

def neural_loop(source,n):
    """Circular overlap-add: all grains taper smoothly, including wrapped ones."""
    source=source-source.mean(axis=0)
    bins=np.fft.rfftfreq(len(source),1/SR)
    spectrum=np.fft.rfft(source,axis=0)
    weight=(1-np.exp(-(bins/90)**4))*np.exp(-(bins/5200)**4)
    source=np.fft.irfft(spectrum*weight[:,None],n=len(source),axis=0)
    length=min(len(source),int(10*SR));window=np.hanning(length)
    output=np.zeros((n,2));weights=np.zeros(n)
    for fraction in [0,.237,.493,.747]:
        start=int(fraction*n);indices=(np.arange(length)+start)%n
        np.add.at(output,indices,source[:length]*window[:,None]);np.add.at(weights,indices,window)
    return output/np.maximum(weights[:,None],1e-9)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--from-sources',action='store_true');args=parser.parse_args()
    client=ComfyClient();reports=[]
    for index,(chapter,name,text) in enumerate(SPECS):
        prompt={
          '1':node('CheckpointLoaderSimple',ckpt_name='stable-audio-open-1.0.safetensors'),
          '2':node('CLIPLoader',clip_name='t5-base.safetensors',type='stable_audio',device='default'),
          '3':node('CLIPTextEncode',clip=['2',0],text=text),
          '4':node('CLIPTextEncode',clip=['2',0],text='speech, singing, voices, music, melody, rhythm, drums, harsh noise, impact, thunder, distortion'),
          '5':node('EmptyLatentAudio',seconds=12.0,batch_size=1),
          '6':node('ConditioningStableAudio',positive=['3',0],negative=['4',0],seconds_start=0.,seconds_total=12.),
          '7':node('KSampler',model=['1',0],positive=['6',0],negative=['6',1],latent_image=['5',0],seed=2026102170+index,steps=40,cfg=4.,sampler_name='dpmpp_3m_sde_gpu',scheduler='exponential',denoise=1.),
          '8':node('VAEDecodeAudio',samples=['7',0],vae=['1',2]),
          '9':node('SaveAudio',audio=['8',0],filename_prefix='sangeng_av/'+chapter+'_'+name),
        }
        source=ROOT/'tools/av/sources'/(chapter+'-'+name+'.flac');source.parent.mkdir(parents=True,exist_ok=True)
        if args.from_sources:
            job={'mode':'retained-source','seed':2026102170+index}
        else:
            generated,job=client.run(prompt,RAW,chapter+'-'+name)
            source.write_bytes(generated[0].read_bytes())
        relative=f'assets/audio/{chapter}/ambience/{name}.ogg'
        original=RAW/(chapter+'-'+name+'-baseline.ogg')
        original.write_bytes(subprocess.check_output(['git','show','18df312:'+relative],cwd=ROOT))
        base=decode(original);ai=neural_loop(decode(source),len(base))
        ai*=np.sqrt(np.mean(base**2))/max(1e-9,np.sqrt(np.mean(ai**2)))
        mixed=base*.92+ai*.24
        mixed-=mixed.mean(axis=0)
        mixed*=10**(-21.2/20)/max(1e-9,np.sqrt(np.mean(mixed**2)))
        mixed*=min(1.,10**(-2/20)/max(1e-9,np.max(np.abs(mixed))))
        target=ROOT/relative
        process=subprocess.run(['ffmpeg','-v','error','-y','-f','f32le','-ar',str(SR),'-ac','2','-i','-','-c:a','libvorbis','-q:a','4',str(target)],input=mixed.astype('<f4').tobytes(),check=True)
        decoded=decode(target);rms=float(np.sqrt(np.mean(decoded**2)));peak=float(np.max(np.abs(decoded)))
        jump=float(np.max(np.abs(decoded[0]-decoded[-1]))/max(1e-12,np.sqrt(np.mean(np.diff(decoded,axis=0)**2))))
        assert np.isfinite(decoded).all() and peak<10**(-1/20) and -23<20*np.log10(rms)<-18
        assert jump<6, f'Loop seam failed: {chapter} {jump}'
        reports.append(dict(chapter=chapter,file=relative,job=job,seconds=len(decoded)/SR,rmsDbFS=float(20*np.log10(rms)),peakDbFS=float(20*np.log10(peak)),loopJumpRelative=jump,neuralMix=.24,authoredMix=.92,source=str(source.relative_to(ROOT)),listeningAccepted=False))
        print('AMBIENCE READY '+chapter+' '+json.dumps(reports[-1]),flush=True)
    (OUT/'ambience.json').write_text(json.dumps(reports,indent=2),encoding='utf-8')

if __name__=='__main__':main()
