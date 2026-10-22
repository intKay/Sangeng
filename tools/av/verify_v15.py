"""Verify exported shading data and preserve world transforms/collision bounds."""
import json
import struct
import hashlib
from pathlib import Path
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'reports/av-v1.5'

def glb(path):
    b=path.read_bytes();length=struct.unpack_from('<I',b,12)[0]
    return json.loads(b[20:20+length])

def matrix(node):
    if 'matrix' in node:return np.array(node['matrix']).reshape((4,4),order='F')
    x,y,z,w=node.get('rotation',[0,0,0,1]);m=np.eye(4)
    m[:3,:3]=np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
      [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
      [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])@np.diag(node.get('scale',[1,1,1]))
    m[:3,3]=node.get('translation',[0,0,0]);return m

def nodes(data):
    result={}
    def walk(i,parent):
        n=data['nodes'][i];world=parent@matrix(n);result[n.get('name',str(i))]=(n,world)
        for child in n.get('children',[]):walk(child,world)
    for scene in data['scenes']:
        for i in scene['nodes']:walk(i,np.eye(4))
    return result

def bounds(data,node,world):
    corners=[]
    for p in data['meshes'][node['mesh']]['primitives']:
        accessor=data['accessors'][p['attributes']['POSITION']]
        lo,hi=accessor['min'],accessor['max']
        for x in [lo[0],hi[0]]:
            for y in [lo[1],hi[1]]:
                for z in [lo[2],hi[2]]:corners.append((world@np.array([x,y,z,1]))[:3])
    return np.array([np.min(corners,axis=0),np.max(corners,axis=0)])

def main():
    results=[]
    for chapter in ['door','mirror','nightroad']:
        before=glb(OUT/'model-before'/(chapter+'.glb'));after=glb(ROOT/'assets/models'/(chapter+'.glb'))
        old,new=nodes(before),nodes(after);checked=0;collisions=0
        for name,(n,m) in old.items():
            if not name.startswith(('COL_','INT_','MARK_','SPAWN_','LOOK_','LIGHT_','ENTITY_','V2_','V3_')):continue
            assert name in new,name
            n2,m2=new[name];assert np.allclose(m,m2,atol=1e-5),name
            for key,value in n.get('extras',{}).items():assert n2.get('extras',{}).get(key)==value,(name,key)
            if name.startswith('COL_'):
                assert np.allclose(bounds(before,n,m),bounds(after,n2,m2),atol=1e-5),name
                collisions+=1
            checked+=1
        tris=lambda d:sum(d['accessors'][p['indices']]['count']//3 for m in d['meshes'] for p in m['primitives'])
        assert tris(before)==tris(after)
        colored=sum('COLOR_0' in p['attributes'] for m in after['meshes'] for p in m['primitives'])
        assert colored>20
        results.append({'chapter':chapter,'gameplayNodesPreserved':checked,'collisionBoundsPreserved':collisions,'trianglesUnchanged':tris(after),'coloredPrimitives':colored})
    manifest=json.loads((ROOT/'assets/textures/manifest.json').read_text(encoding='utf-8'))
    assert len(manifest['materials'])==62
    materials=[]
    for key,d in manifest['materials'].items():
        assert (ROOT/'assets/textures'/d['file']).exists()
        if not d.get('bump'):continue
        p=ROOT/'assets/textures'/d['bump'];a=np.asarray(Image.open(p));assert a.shape==(512,512)
        assert np.array_equal(a[0],a[-1]) and np.array_equal(a[:,0],a[:,-1]),key
        materials.append(key)
    assert len(materials)==16
    sources=[{'file':str(p.relative_to(ROOT)).replace('\\','/'),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted((ROOT/'tools/av/sources-v15').iterdir()) if p.suffix in ['.png','.flac']]
    assert len(sources)==13
    bundle=json.loads((ROOT/'dist/web/web-manifest.json').read_text(encoding='utf-8'))
    assert bundle['version']=='1.5.0'
    for entry in bundle['files']:
        assert hashlib.sha256((ROOT/entry['path']).read_bytes()).hexdigest()==entry['sha256'],entry['path']
    assert hashlib.sha256((ROOT/'dist/web'/bundle['name']).read_bytes()).hexdigest()==bundle['sha256']
    qa=json.loads((ROOT/'reports/qa/release-1.5.0/web/result.json').read_text(encoding='utf-8'))
    assert len({r['profile'] for r in qa['results']})==6
    (OUT/'structural-verification.json').write_text(json.dumps({'models':results,'bumpMaterials':materials,'retainedSources':sources,'webBundle':{k:v for k,v in bundle.items() if k!='files'},'runtimeMatchesBundle':True,'scope':'static geometry, transform, collision and texture verification; browser evidence is separate'},indent=2),encoding='utf-8')
    print('PASS',json.dumps(results),'materials:',len(materials),'sources:',len(sources))

if __name__=='__main__':main()
