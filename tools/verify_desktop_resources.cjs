const asar = require('@electron/asar');
const fs = require('node:fs');
const path = require('node:path');
const { createHash } = require('node:crypto');
const assert = require('node:assert/strict');
const archive = path.resolve(process.argv[2]);
const baseline = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
const sha = b => createHash('sha256').update(b).digest('hex');
const files = asar.listPackage(archive).map(p => p.replace(/^[/\\]/, ''))
  .filter(p => !asar.statFile(archive, p).files).map(p => p.replaceAll('\\', '/'));
for (const file of baseline.files) assert.equal(sha(asar.extractFile(archive, path.normalize(file.path))), file.sha256, file.path);
const extraFiles = files.filter(p => !baseline.files.some(f => f.path === p));
assert.deepEqual(extraFiles.sort(), ['NOTICE.md', 'package.json', 'tools/desktop/main.cjs'].sort());
const result = { baselineFilesVerified: baseline.files.length, archiveFiles: files.length, extraFiles, archiveSha256: sha(fs.readFileSync(archive)) };
fs.writeFileSync('reports/qa/release-1.3.0/resources.json', JSON.stringify(result, null, 2));
console.log(result);
