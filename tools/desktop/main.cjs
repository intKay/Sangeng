const { app, BrowserWindow, protocol, session, dialog } = require('electron');
const path = require('node:path');
const fs = require('node:fs');

protocol.registerSchemesAsPrivileged([{ scheme: 'sangeng', privileges: {
  standard: true, secure: true, supportFetchAPI: true, stream: true
} }]);
const root = path.resolve(__dirname, '../..');
function localURL(value) {
  try { const u = new URL(value); return u.protocol === 'sangeng:' && u.host === 'game'; }
  catch { return false; }
}
app.whenReady().then(async () => {
  protocol.handle('sangeng', request => {
    if (!localURL(request.url)) return new Response('Forbidden', { status: 403 });
    let relative;
    try { relative = decodeURIComponent(new URL(request.url).pathname); }
    catch { return new Response('Bad path', { status: 400 }); }
    if (relative.endsWith('/')) relative += 'index.html';
    const target = path.resolve(root, '.' + relative);
    const rel = path.relative(root, target);
    const allowed = rel === 'index.html' || /^(engine|games|assets|vendor)[\\/]/.test(rel);
    if (!allowed || rel.startsWith('..') || path.isAbsolute(rel)) return new Response('Forbidden', { status: 403 });
    if (!fs.existsSync(target) || !fs.statSync(target).isFile()) return new Response('Not found', { status: 404 });
    const types = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8',
      '.css': 'text/css; charset=utf-8', '.json': 'application/json', '.glb': 'model/gltf-binary',
      '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.svg': 'image/svg+xml',
      '.ogg': 'audio/ogg', '.wav': 'audio/wav' };
    return new Response(fs.readFileSync(target), { headers: {
      'Content-Type': types[path.extname(target).toLowerCase()] || 'application/octet-stream'
    } });
  });
  session.defaultSession.setPermissionRequestHandler((contents, permission, callback) => {
    callback(localURL(contents.getURL()) && permission === 'pointerLock');
  });
  session.defaultSession.webRequest.onBeforeRequest((details, callback) => {
    callback({ cancel: !localURL(details.url) && !/^(data|blob):/.test(details.url) });
  });
  const win = new BrowserWindow({
    width: 1280, height: 800, minWidth: 800, minHeight: 600,
    title: '三更', backgroundColor: '#060807', autoHideMenuBar: true,
    webPreferences: { nodeIntegration: false, contextIsolation: true, sandbox: true }
  });
  win.setMenu(null);
  win.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));
  win.webContents.on('will-navigate', (event, url) => { if (!localURL(url)) event.preventDefault(); });
  win.webContents.on('render-process-gone', () => dialog.showErrorBox('三更', '画面进程已退出，请重新启动游戏。'));
  await win.loadURL('sangeng://game/');
}).catch(error => { dialog.showErrorBox('三更启动失败', error.message); app.quit(); });
app.on('window-all-closed', () => app.quit());
