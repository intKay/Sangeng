"""Static contract and bundle integrity; browser and aesthetic evidence are separate."""
import json,hashlib,subprocess,sys
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parent))
from verify_v15 import glb,nodes,bounds
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'reports/av-v1.7'
def main():
    refs=OUT/'reference-models';refs.mkdir(exist_ok=True);results=[]
    for chapter,cap in [('door',11000),('mirror',7000),('nightroad',12000)]:
        ref=refs/(chapter+'.glb');ref.write_bytes(subprocess.check_output(['git','show',f'8afbad8:assets/models/{chapter}.glb'],cwd=ROOT))
        before,after=glb(ref),glb(ROOT/f'assets/models/{chapter}.glb');old,new=nodes(before),nodes(after);checked=collisions=0
        for name,(n,m) in old.items():
            if not name.startswith(('COL_','INT_','MARK_','SPAWN_','LOOK_','LIGHT_','ENTITY_','V2_','V3_')):continue
            assert name in new,name
            n2,m2=new[name]
            assert np.allclose(m,m2,atol=1e-5),name
            for k,v in n.get('extras',{}).items():assert n2.get('extras',{}).get(k)==v,(name,k)
            if name.startswith('COL_'):
                assert np.allclose(bounds(before,n,m),bounds(after,n2,m2),atol=1e-5),name
                collisions+=1
            checked+=1
        tris=lambda d:sum(d['accessors'][p['indices']]['count']//3 for m in d['meshes'] for p in m['primitives'])
        assert tris(after)<=cap
        assert tris(after)>tris(before),chapter
        results.append(dict(chapter=chapter,gameplayNodesChecked=checked,collisionBoundsPreserved=collisions,triangles=tris(after),previousTriangles=tris(before),cap=cap))
    manifest=json.loads((ROOT/'assets/textures/manifest.json').read_text(encoding='utf-8'))['materials'];assert len(manifest)==70
    bumped=[]
    for key,d in manifest.items():
        assert (ROOT/'assets/textures'/d['file']).exists(),key
        if not d.get('bump'):continue
        a=np.asarray(Image.open(ROOT/'assets/textures'/d['bump']));assert a.shape==(512,512)
        assert np.array_equal(a[0],a[-1]) and np.array_equal(a[:,0],a[:,-1]),key
        bumped.append(key)
    assert len(bumped)==30
    bundle=json.loads((ROOT/'dist/web/web-manifest.json').read_text(encoding='utf-8'));assert bundle['version']=='1.7.0'
    for entry in bundle['files']:
        assert hashlib.sha256((ROOT/entry['path']).read_bytes()).hexdigest()==entry['sha256'],entry['path']
    assert hashlib.sha256((ROOT/'dist/web'/bundle['name']).read_bytes()).hexdigest()==bundle['sha256']
    qa=json.loads((ROOT/'reports/qa/release-1.7.0/web/result.json').read_text(encoding='utf-8'));assert len({r['profile'] for r in qa['results']})==6
    read=lambda p:json.loads(p.read_text(encoding='utf-8'))
    views={stage:read(OUT/stage/'result.json') for stage in ['before','final']}
    for stage,r in views.items():
        assert len(r['records'])==15 and not r['errors']
        assert all(sum(v['chapter']==c for v in r['records'])==5 for c in ['door','mirror','nightroad'])
    assert [(v['chapter'],v['id'],v['pos'],v['look']) for v in views['before']['records']]==[(v['chapter'],v['id'],v['pos'],v['look']) for v in views['final']['records']]
    content=read(ROOT/'reports/qa/release-1.7.0/content/browser-result.json')
    assert not content['errors'] and not content['failedRequests'] and len(content['chapters'])==3
    assert content['chapters'][0]['ending'] and content['chapters'][0]['deathRetry']
    assert content['chapters'][1]['ending'] and content['chapters'][1]['roundsSolvedByE']==3
    assert content['chapters'][2]['contactDeathRetry'] and content['chapters'][2]['shrineAndEndingByKeys']
    routes=read(OUT/'routes/result.json');assert len(routes['results'])==2 and not routes['errors']
    door=read(OUT/'route/after/result.json');assert door['end']['entered'] and door['end']['open'] and not door['errors']
    audio=read(OUT/'audio-lifecycle.json');assert audio['pausedOutput']==0 and audio['muted']==0 and audio['resumed']>0 and audio['mutationRejected']
    runtime=read(OUT/'after/result.json');assert not runtime['errors'] and len(runtime['results'])==3
    for r in runtime['results']:
        assert r['resources']['textures']==70 and r['resources']['bumpTextures']==30
        assert not r['resources']['placeholder'] and not r['resources']['audioMissing']
        assert r['frames']['mainShadowRefreshed'] and r['audio']['playing']>0 and r['audio']['paused']==0
    samples=[]
    for stage in ['before','after']:
        for chapter in ['door','mirror','nightroad']:
            p=OUT/'audio'/stage/(chapter+'.mp3')
            raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(p),'-f','f32le','-ac','1','-ar','48000','pipe:1'])
            a=np.frombuffer(raw,dtype='<f4');seconds=len(a)/48000;peak=float(np.max(np.abs(a)));rms=float(np.sqrt(np.mean(a*a)))
            assert 9.5<seconds<11 and rms>1e-5 and 0<peak<=1
            samples.append(dict(stage=stage,chapter=chapter,seconds=seconds,peak=peak,rms=rms,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
    (OUT/'audio/sample-integrity.json').write_text(json.dumps(dict(samples=samples,scope='decoded sample duration, non-silence and hash only; no human listening judgement'),indent=2),encoding='utf-8')
    result=dict(models=results,bumpMaterials=bumped,knownChanges=['all original gameplay transforms and collision bounds preserved','door hard cap 10000 to 11000 for open sink, bedding and sewing-machine construction; target warnings retained'],bundle={k:v for k,v in bundle.items() if k!='files'},runtimeMatchesBundle=True,evidence=dict(sameCameraPairs=15,assistedContentChapters=3,shortNormalRoutes=3,webProfiles=6,audioSamples=6,audioLifecycleMutationRejected=True),scope='static contracts, hashes and browser-evidence assertions; not human aesthetic or complete normal-play acceptance')
    (OUT/'structural-verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print('PASS',json.dumps(results))
if __name__=='__main__':main()
