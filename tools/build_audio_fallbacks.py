"""Generate MP3 alternatives for browsers without Ogg/Vorbis decoding (ffmpeg required)."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]

def convert(source):
    target = source.with_suffix('.mp3')
    if target.exists() and target.stat().st_mtime >= source.stat().st_mtime:
        return
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', str(source),
                    '-codec:a', 'libmp3lame', '-q:a', '4', str(target)], check=True)

if __name__ == '__main__':
    files = sorted((ROOT / 'assets/audio').rglob('*.ogg'))
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(convert, files))
    print(f'MP3 alternatives ready: {len(files)}')
