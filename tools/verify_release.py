"""对正在运行的 EXE 便携服务器验收；比对打包文件字节与 HTTP 行为。"""
import hashlib
import json
from pathlib import Path
import socket
import sys
import urllib.error
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    base = sys.argv[1].rstrip('/')
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    def request(path, method='GET'):
        return opener.open(urllib.request.Request(base+path, method=method), timeout=10)
    with zipfile.ZipFile(ROOT/'dist/Sangeng-1.0.1-web.zip') as archive:
        names = archive.namelist()
        assert 'index.html' in names and 'vendor/three/LICENSE' in names
        assert not any(p.startswith(('reports/','tools/','data/','.')) for p in names)
        for name in names:
            with request('/'+name) as response:
                assert response.status == 200, name
                assert response.read() == archive.read(name), name
        for path in ('/','/games/door/','/games/mirror/','/games/nightroad/'):
            with request(path) as response:
                assert response.headers['Content-Type'].startswith('text/html')
        with request('/engine/engine.js','HEAD') as response:
            assert response.read() == b''
            assert response.headers['Content-Type'].startswith('text/javascript')
        for path, method, status in [('/missing','GET',404),('/%2e%2e/SECURITY.md','GET',403),('/', 'POST',405)]:
            try:
                request(path,method)
                raise AssertionError('Unexpected success: '+path)
            except urllib.error.HTTPError as e:
                assert e.code == status,(path,e.code)
        host = urllib.parse.urlsplit(base)
        with socket.create_connection((host.hostname,host.port),timeout=5) as client:
            client.sendall(b'GET / HTTP/1.1\r\nHost: untrusted.example\r\n\r\n')
            assert b' 403 ' in client.recv(1024)
    manifest = json.loads((ROOT/'dist/build-manifest.json').read_text(encoding='utf-8'))
    for artifact in manifest['artifacts']:
        path = ROOT/'dist'/artifact['name']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == artifact['sha256']
    result = {'http_files_verified':len(names),'directory_entries':4,'head':True,'not_found':404,
              'traversal':403,'post':405,'host_guard':403,'artifact_hashes':True}
    (ROOT/'reports/qa/release-package-check.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
