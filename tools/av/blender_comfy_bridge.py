"""Real Blender -> ComfyUI -> Blender material round trip in a fresh process.

blender -b --factory-startup --python tools/av/blender_comfy_bridge.py
No startup files, user settings, or existing scenes are opened or overwritten.
"""
import bpy
from pathlib import Path
import json
import sys
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from comfy_client import ComfyClient, material_workflow

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'reports/av-v1.4'
RAW=OUT/'raw'
RAW.mkdir(parents=True,exist_ok=True)
client=ComfyClient()
stats=client.api('/system_stats')
scene=bpy.context.scene
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
scene.render.engine='BLENDER_EEVEE'
scene.render.resolution_x=512;scene.render.resolution_y=512;scene.render.resolution_percentage=100
scene.view_settings.view_transform='Standard'
scene.render.image_settings.file_format='PNG'
scene.render.film_transparent=False
bpy.ops.mesh.primitive_plane_add(size=2)
plane=bpy.context.object;plane.name='Sangeng_Comfy_Material_Proof'
mat=bpy.data.materials.new('MAT_bridge_proof');mat.use_nodes=True
nodes=mat.node_tree.nodes;nodes.clear()
tex=nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(ROOT/'assets/textures/wood_pale.jpg'))
emission=nodes.new('ShaderNodeEmission');emission.inputs['Strength'].default_value=1
output=nodes.new('ShaderNodeOutputMaterial')
mat.node_tree.links.new(tex.outputs['Color'],emission.inputs['Color'])
mat.node_tree.links.new(emission.outputs[0],output.inputs['Surface'])
plane.data.materials.append(mat)
bpy.ops.object.camera_add(location=(0,0,3))
camera=bpy.context.object;camera.rotation_euler=(0,0,0);camera.data.type='ORTHO';camera.data.ortho_scale=2
scene.camera=camera
scene.render.filepath=str(RAW/'blender-source.png')
bpy.ops.render.render(write_still=True)
uploaded=client.upload(RAW/'blender-source.png')
files,job=client.run(material_workflow(uploaded,'Old pale plywood, small natural scratches and worn varnish, 1990s modest Chinese household furniture',2026102140,.25),RAW,'blender-roundtrip')
generated=bpy.data.images.load(str(files[0]));generated.pack();tex.image=generated
plane['comfy_prompt_id']=job['prompt_id']
plane['source']='original project texture, rendered in isolated Blender then processed by local ComfyUI'
scene.render.filepath=str(OUT/'blender-roundtrip.png')
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'blender-comfy-proof.blend'))
bpy.ops.object.select_all(action='DESELECT');plane.select_set(True);bpy.context.view_layer.objects.active=plane
bpy.ops.export_scene.gltf(filepath=str(OUT/'blender-comfy-proof.glb'),export_format='GLB',use_selection=True,export_cameras=False,export_lights=False)
report={'blender_version':bpy.app.version_string,'comfy_version':stats['system']['comfyui_version'],'job':job,'rendered_input':str((RAW/'blender-source.png').relative_to(ROOT)),'generated_image':str(files[0].relative_to(ROOT)),'returned_material_image':generated.name,'packed':bool(generated.packed_file),'saved_blend':'reports/av-v1.4/blender-comfy-proof.blend','saved_glb':'reports/av-v1.4/blender-comfy-proof.glb','scope':'isolated background Blender, local HTTP API round trip; not a live UI addon'}
(OUT/'bridge-proof.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('BLENDER_COMFY_ROUNDTRIP_OK '+json.dumps(job),flush=True)
