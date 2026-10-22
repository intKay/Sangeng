"""Static contract and bundle integrity; browser and aesthetic evidence are separate."""
import json,hashlib,subprocess,sys
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parent))
from verify_v15 import glb,nodes,bounds
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'reports/av-v1.6'
def main():
    refs=OUT/'reference-models';refs.mkdir(exist_ok=True);results=[]
    for chapter,cap in [('door',10000),('mirror',7000),('nightroad',12000)]:
        ref=refs/(chapter+'.glb');ref.write_bytes(subprocess.check_output(['git','show',f'a655483:assets/models/{chapter}.glb'],cwd=ROOT))
        before,after=glb(ref),glb(ROOT/f'assets/models/{chapter}.glb');old,new=nodes(before),nodes(after);checked=collisions=0
        for name,(n,m) in old.items():
            if not name.startswith(('COL_','INT_','MARK_','SPAWN_','LOOK_','LIGHT_','ENTITY_','V2_','V3_')):continue
            assert name in new,name
            n2,m2=new[name]
            assert np.allclose(m,m2,atol=1e-5),name
            if chapter=='door' and name=='INT_letter_03':
                # Joined pickup vertices carry the placement; the node matrix stays identity.
                assert np.allclose(bounds(after,n2,m2).mean(axis=0),[4.32,1.12,3.225],atol=1e-5),name
            for k,v in n.get('extras',{}).items():assert n2.get('extras',{}).get(k)==v,(name,k)
            if name.startswith('COL_'):
                assert np.allclose(bounds(before,n,m),bounds(after,n2,m2),atol=1e-5),name
                collisions+=1
            checked+=1
        tris=lambda d:sum(d['accessors'][p['indices']]['count']//3 for m in d['meshes'] for p in m['primitives'])
        assert tris(after)<=cap
        if chapter!='door':assert tris(after)==tris(before)
        results.append(dict(chapter=chapter,gameplayNodesChecked=checked,collisionBoundsPreserved=collisions,triangles=tris(after),previousTriangles=tris(before),cap=cap))
    manifest=json.loads((ROOT/'assets/textures/manifest.json').read_text(encoding='utf-8'))['materials'];assert len(manifest)==65
    bumped=[]
    for key,d in manifest.items():
        assert (ROOT/'assets/textures'/d['file']).exists(),key
        if not d.get('bump'):continue
        a=np.asarray(Image.open(ROOT/'assets/textures'/d['bump']));assert a.shape==(512,512)
        assert np.array_equal(a[0],a[-1]) and np.array_equal(a[:,0],a[:,-1]),key
        bumped.append(key)
    assert len(bumped)==18
    bundle=json.loads((ROOT/'dist/web/web-manifest.json').read_text(encoding='utf-8'));assert bundle['version']=='1.6.0'
    for entry in bundle['files']:
        assert hashlib.sha256((ROOT/entry['path']).read_bytes()).hexdigest()==entry['sha256'],entry['path']
    assert hashlib.sha256((ROOT/'dist/web'/bundle['name']).read_bytes()).hexdigest()==bundle['sha256']
    qa=json.loads((ROOT/'reports/qa/release-1.6.0/web/result.json').read_text(encoding='utf-8'));assert len({r['profile'] for r in qa['results']})==6
    result=dict(models=results,bumpMaterials=bumped,knownChanges=['INT_letter_03 moved from behind backboard to visible shelf front','door hard cap 9000 to 10000 for near-view geometry; target 6000 warning retained'],bundle={k:v for k,v in bundle.items() if k!='files'},runtimeMatchesBundle=True,scope='static contracts and hashes, not aesthetic or play acceptance')
    (OUT/'structural-verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print('PASS',json.dumps(results))
if __name__=='__main__':main()
