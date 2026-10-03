'use strict';
// Copies contracts/v1/examples into the extension so the VSIX stays self-contained.
// `--check` fails when the copies drift from the shared contract fixtures.
const fs = require('fs');
const path = require('path');

const SOURCE = path.resolve(__dirname, '../../../contracts/v1/examples');
const TARGET = path.resolve(__dirname, '../fixtures');
const FILES = ['analysis-queued.json', 'analysis-ready.json', 'evaluation-result.json'];
const check = process.argv.includes('--check');

let drift = false;
fs.mkdirSync(TARGET, { recursive: true });
for (const name of FILES) {
  const source = fs.readFileSync(path.join(SOURCE, name), 'utf8');
  const targetPath = path.join(TARGET, name);
  const current = fs.existsSync(targetPath) ? fs.readFileSync(targetPath, 'utf8') : null;
  if (current === source) continue;
  if (check) {
    console.error(`Fixture drift: fixtures/${name} differs from contracts/v1/examples/${name}`);
    drift = true;
  } else {
    fs.writeFileSync(targetPath, source);
    console.log(`Synced fixtures/${name}`);
  }
}
if (drift) process.exit(1);
