"""Check the delivered files without invoking a model or rewriting evidence."""
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'reports/av-v1.4'
manifest = json.loads((ROOT / 'assets/textures/manifest.json').read_text(encoding='utf-8'))
assert len(manifest['materials']) == 62
checks = []
for record in json.loads((OUT / 'materials.json').read_text(encoding='utf-8')):
    entry = manifest['materials'][record['material']]
    assert entry['file'] == record['file'] and entry['av14Source'] == record['source']
    before = np.asarray(Image.open(ROOT / 'assets/textures' / record['source']).convert('RGB'), dtype=np.int16)
    after = np.asarray(Image.open(ROOT / 'assets/textures' / record['file']).convert('RGB'), dtype=np.int16)
    assert before.shape == after.shape
    for a, b in [(before[0], after[0]), (before[-1], after[-1]), (before[:, 0], after[:, 0]), (before[:, -1], after[:, -1])]:
        assert np.array_equal(a, b)
    assert np.max(np.abs(after-before)) <= 11
    checks.append({'material': record['material'], 'maxDelta': int(np.max(np.abs(after-before))), 'edgesIdentical': True})
bundle = json.loads((ROOT / 'dist/web/web-manifest.json').read_text(encoding='utf-8'))
for entry in bundle['files']:
    assert hashlib.sha256((ROOT / entry['path']).read_bytes()).hexdigest() == entry['sha256'], entry['path']
assert hashlib.sha256((ROOT / 'dist/web' / bundle['name']).read_bytes()).hexdigest() == bundle['sha256']
sources = [{'file': str(p.relative_to(ROOT)).replace('\\', '/'), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted((ROOT / 'tools/av/sources').iterdir()) if p.is_file()]
assert len(sources) == 9
report = {'materials': checks, 'sources': sources, 'webBundle': {k: v for k, v in bundle.items() if k != 'files'}, 'runtimeMatchesBundle': True}
(OUT / 'artifact-verification.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('PASS: six bounded materials, nine retained sources, runtime and final ZIP hashes')
