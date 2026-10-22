"""Bake local geometric occlusion into COLOR_0 without changing gameplay geometry.

blender -b --factory-startup --python tools/av/bake_v15_ao.py
Inputs are retained baseline GLBs, so rerunning never compounds occlusion.
"""
import bpy
import math
import json
import subprocess
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'reports/av-v1.5/model-before'
REPORT=ROOT/'reports/av-v1.5/ao.json'

def active(o):
    while o:
        if o.name.startswith(('COL_','V2_','V3_','ENTITY_')) or o.get('hidden',False):return False
        o=o.parent
    return True

def main():
    report=[]
    SOURCE.mkdir(parents=True,exist_ok=True)
    for chapter in ['door','mirror','nightroad']:
        baseline=SOURCE/(chapter+'.glb')
        if not baseline.exists():
            baseline.write_bytes(subprocess.check_output(['git','show','f669c15:assets/models/'+chapter+'.glb'],cwd=ROOT))
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(SOURCE/(chapter+'.glb')))
        meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
        verts=[];faces=[]
        for o in meshes:
            if not active(o):continue
            offset=len(verts);verts.extend([o.matrix_world@v.co for v in o.data.vertices])
            faces.extend([tuple(offset+i for i in p.vertices) for p in o.data.polygons])
        tree=BVHTree.FromPolygons(verts,faces,all_triangles=False)
        samples=24;values=[]
        for o in meshes:
            if not active(o):continue
            me=o.data
            for attr in list(me.color_attributes):me.color_attributes.remove(attr)
            color=me.color_attributes.new(name='COLOR_0',type='FLOAT_COLOR',domain='CORNER')
            me.color_attributes.active_color=color
            normal_matrix=o.matrix_world.to_3x3().inverted().transposed()
            cache={}
            for p in me.polygons:
                normal=(normal_matrix@p.normal).normalized()
                tangent=normal.cross(Vector((0,0,1)) if abs(normal.z)<.9 else Vector((0,1,0))).normalized()
                bitangent=normal.cross(tangent)
                for li in p.loop_indices:
                    vi=me.loops[li].vertex_index
                    key=(vi,tuple(round(n,3) for n in normal))
                    if key not in cache:
                        origin=o.matrix_world@me.vertices[vi].co+normal*.018
                        blocked=0
                        for i in range(samples):
                            r=math.sqrt((i+.5)/samples);phi=i*2.3999632297
                            direction=(tangent*(r*math.cos(phi))+bitangent*(r*math.sin(phi))+normal*math.sqrt(1-r*r)).normalized()
                            hit=tree.ray_cast(origin,direction,.65)
                            if hit[0] is not None:blocked+=(1-hit[3]/.65)**.65
                        cache[key]=max(.60,1-.45*blocked/samples)
                    v=cache[key];color.data[li].color=(v,v,v,1);values.append(v)
        # Blender's exporter omits even an active color attribute unless a
        # material node actually references it. The runtime replaces materials
        # by name, but COLOR_0 must still be present in the exported primitive.
        for material in bpy.data.materials:
            if not material.use_nodes:continue
            bsdf=next((n for n in material.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
            if bsdf:
                vertex=material.node_tree.nodes.new('ShaderNodeVertexColor');vertex.layer_name='COLOR_0'
                material.node_tree.links.new(vertex.outputs['Color'],bsdf.inputs['Base Color'])
        target=ROOT/'assets/models'/(chapter+'.glb')
        bpy.ops.export_scene.gltf(filepath=str(target),export_format='GLB',export_extras=True,
            export_yup=True,export_cameras=False,export_lights=False,export_materials='EXPORT',
            export_image_format='NONE',export_all_vertex_colors=True)
        report.append({'chapter':chapter,'samples':samples,'radiusMeters':.65,'min':min(values),'mean':sum(values)/len(values),'coloredCorners':len(values),'scope':'static geometric occlusion; no topology or collision modification'})
        print('AO READY',chapter,report[-1],flush=True)
    REPORT.write_text(json.dumps(report,indent=2),encoding='utf-8')

if __name__=='__main__':main()
