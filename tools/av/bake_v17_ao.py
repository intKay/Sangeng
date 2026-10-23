"""Bake the three freshly built models; fixed raw inputs prevent compounded AO."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import bake_v15_ao as bake
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'reports/av-v1.7'
bake.SOURCE=OUT/'model-before';bake.REPORT=OUT/'ao.json';bake.SOURCE.mkdir(parents=True,exist_ok=True)
for name in ['door','mirror','nightroad']:
    target=bake.SOURCE/(name+'.glb')
    if not target.exists() or '--refresh' in sys.argv:target.write_bytes((ROOT/'assets/models'/(name+'.glb')).read_bytes())
bake.main()
