"""Build the same relative-path HTML5 ZIP for itch.io desktop and mobile browsers."""
from pathlib import Path
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = json.loads((ROOT / 'package.json').read_text(encoding='utf-8'))['version']
SUFFIXES = {'.html', '.js', '.css', '.json', '.glb', '.ogg', '.mp3', '.wav', '.jpg', '.jpeg', '.png', '.svg'}

def main():
    out = ROOT / 'dist/web'
    out.mkdir(parents=True, exist_ok=True)
    sources = [ROOT / 'index.html']
    for name in ('engine', 'games', 'assets', 'vendor'):
        sources += [p for p in (ROOT/name).rglob('*') if p.is_file() and (p.suffix.lower() in SUFFIXES or p.name == 'LICENSE')]
    sources = sorted(sources)
    for source in (ROOT/'assets/audio').rglob('*.ogg'):
        assert source.with_suffix('.mp3').exists(), f'Run build_audio_fallbacks.py: {source.name}'
    archive = out / f'Sangeng-{VERSION}-web.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for source in sources:
            z.write(source, source.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        names = z.namelist()
        assert 'index.html' in names and len(names) <= 1000
        assert len({n.casefold() for n in names}) == len(names)
        assert max(map(len, names)) <= 240
        assert max(i.file_size for i in z.infolist()) <= 200_000_000
        assert sum(i.file_size for i in z.infolist()) <= 500_000_000
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    manifest = {'version': VERSION, 'name': archive.name, 'sha256': digest, 'bytes': archive.stat().st_size,
                'files': [{'path': p.relative_to(ROOT).as_posix(), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in sources],
                'itch_limits_checked': True, 'runtime_files': len(sources)}
    (out/'web-manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    (out/'SHA256SUMS.txt').write_text(f'{digest}  {archive.name}\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in manifest.items() if k != 'files'}))

if __name__ == '__main__':
    main()
