"""只打包游戏运行文件；生成网页 ZIP 与内嵌资源的 Windows 启动 EXE。"""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'dist'
VERSION = '1.0.1'


def main():
    OUT.mkdir(exist_ok=True)
    # 明确白名单，不从项目根目录、reports 或私人目录收集内容。
    files = [ROOT / 'index.html']
    for folder in ('engine', 'games', 'assets', 'vendor'):
        files.extend(p for p in (ROOT / folder).rglob('*') if p.is_file()
                     and (p.suffix.lower() in {'.html', '.js', '.css', '.json', '.glb',
                                               '.ogg', '.wav', '.jpg', '.jpeg', '.png', '.svg'}
                          or p.name == 'LICENSE'))
    files = sorted(set(files))
    assert all(p.is_relative_to(ROOT) for p in files)
    web = OUT / f'Sangeng-{VERSION}-web.zip'
    with zipfile.ZipFile(web, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for path in files:
            z.write(path, path.relative_to(ROOT).as_posix())
    compiler = Path(os.environ.get('WINDIR', r'C:\Windows')) / 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
    exe = OUT / f'Sangeng-{VERSION}-Windows.exe'
    subprocess.run([str(compiler), '/nologo', '/target:winexe', '/platform:anycpu', '/optimize+',
                    '/reference:System.Windows.Forms.dll', '/reference:System.Drawing.dll',
                    '/reference:System.IO.Compression.dll',
                    f'/resource:{web},game.zip', f'/out:{exe}',
                    str(ROOT / 'tools/desktop/Launcher.cs')], check=True)
    readme = OUT / '游玩说明.txt'
    readme.write_text('''三更 v1.0.1 · Windows 便携版

双击 Sangeng-1.0.1-Windows.exe，游戏会在 Edge/Chrome 的独立应用窗口打开。
免安装、免 Python、离线运行；需要 Windows 10/11、.NET Framework 4.8 和支持 WebGL2 的 Edge/Chrome。
游玩时保留“三更”启动器窗口，结束后点击“退出”关闭本地服务。
如果未自动打开，点击“打开游戏”。游戏窗口关闭后，可从启动器再次打开。

WASD 移动，鼠标环视，Shift 快走，E 交互，Esc 暂停，F 手电（仅门后，拾取后）。
E 需要松开再按；出现物件提示时，靠近并用准星对准物件。
点击“开始”后启用声音，可在设置中调整主音量。
心理恐怖、闪烁、幽闭空间、死亡意象。暂无存档和移动端适配。

这是内嵌游戏资源的 Windows 启动器，使用电脑已安装的浏览器渲染；没有内置 Chromium。
启动器只监听 127.0.0.1 随机端口，不向局域网开放、不上传数据。
未数字签名，Windows 可能显示未知发布者；请核对来源再运行。
程序没有安装器、自动更新或卸载步骤，删除下载文件即可。

分享给朋友：发送整个 Windows ZIP；对方解压后双击 EXE。
网页分享：将 web.zip 上传到支持静态 HTML 游戏的托管平台；不要双击 ZIP 中的 index.html。
three.js 使用 MIT 许可，完整声明已包含在游戏资源 vendor/three/LICENSE 中。
原创资产与录屏商业使用限制沿用 v1.0 发布说明；此包不重新授予商业许可。
''', encoding='utf-8-sig')
    windows = OUT / f'Sangeng-{VERSION}-Windows.zip'
    with zipfile.ZipFile(windows, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        z.write(exe, exe.name)
        z.write(readme, readme.name)
        z.write(ROOT / 'vendor/three/LICENSE', 'THIRD_PARTY_LICENSE.txt')
    manifest = {
        'version': VERSION, 'runtime_files': len(files),
        'files': [{'path': p.relative_to(ROOT).as_posix(), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
                  for p in files],
        'artifacts': [{'name': p.name, 'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
                      for p in (web, exe, windows)],
    }
    (OUT / 'build-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    for item in manifest['artifacts']:
        print(f"{item['name']}: {item['bytes']:,} bytes")


if __name__ == '__main__':
    main()
