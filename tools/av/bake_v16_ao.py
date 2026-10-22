"""Bake the corrected door model, keeping a fixed raw input for repeatable runs."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import bake_v15_ao as bake

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'reports/av-v1.6'
bake.SOURCE=OUT/'model-before'
bake.REPORT=OUT/'ao.json'
bake.SOURCE.mkdir(parents=True,exist_ok=True)
door=bake.SOURCE/'door.glb'
if not door.exists() or '--refresh-door' in sys.argv:
    door.write_bytes((ROOT/'assets/models/door.glb').read_bytes())
bake.main()
