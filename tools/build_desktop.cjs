// Build outside the source checkout: generated executables exited early in this workspace.
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const { spawnSync } = require('node:child_process');
const { createHash } = require('node:crypto');
const root = path.resolve(__dirname, '..');
const stage = fs.mkdtempSync(path.join(os.tmpdir(), 'Sangeng-Build-'));
const build = spawnSync(process.execPath, [require.resolve('electron-builder/cli.js'),
  '--win', 'nsis', 'portable', '--x64', '--config.directories.output=' + stage], { cwd: root, stdio: 'inherit' });
if (build.status !== 0) process.exit(build.status || 1);
const out = path.join(root, 'dist/desktop'); fs.mkdirSync(out, { recursive: true });
const files = fs.readdirSync(stage).filter(n => /^Sangeng-.*\.exe$/.test(n));
const artifacts = files.map(name => {
  const p = path.join(out, name); fs.copyFileSync(path.join(stage, name), p);
  return { name, bytes: fs.statSync(p).size, sha256: createHash('sha256').update(fs.readFileSync(p)).digest('hex') };
});
fs.writeFileSync(path.join(out, 'SHA256SUMS.txt'), artifacts.map(a => `${a.sha256}  ${a.name}\n`).join(''));
fs.writeFileSync(path.join(out, 'desktop-manifest.json'), JSON.stringify({ version: require('../package.json').version,
  electron: require('../package.json').devDependencies.electron, platform: 'win32-x64', artifacts }, null, 2));
console.log('构建完成；验收运行目录：' + path.join(stage, 'win-unpacked'));
