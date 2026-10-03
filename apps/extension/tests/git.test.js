'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { execFileSync } = require('child_process');
const { collectChanges } = require('../src/host/git/collect');
const { snapshotId } = require('../src/host/git/snapshot');
const { exclusionReason } = require('../src/host/git/filter');

function git(cwd, ...args) {
  return execFileSync('git', args, { cwd, encoding: 'utf8' });
}

function makeRepo({ commit = true } = {}) {
  const dir = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'dc-ext-')));
  git(dir, 'init', '-q');
  git(dir, 'config', 'user.email', 'test@example.invalid');
  git(dir, 'config', 'user.name', 'Test');
  git(dir, 'config', 'commit.gpgsign', 'false');
  fs.writeFileSync(path.join(dir, 'app.py'), 'print(1)\n');
  if (commit) {
    git(dir, 'add', '.');
    git(dir, 'commit', '-q', '-m', 'init');
  }
  return dir;
}

test('filter excludes secrets, binaries and generated files', () => {
  assert.equal(exclusionReason('.env', false), 'secret');
  assert.equal(exclusionReason('config/.env.local', false), 'secret');
  assert.equal(exclusionReason('certs/server.pem', false), 'secret');
  assert.equal(exclusionReason('logo.png', false), 'binary');
  assert.equal(exclusionReason('data.custom', true), 'binary');
  assert.equal(exclusionReason('package-lock.json', false), 'generated');
  assert.equal(exclusionReason('web/dist/app.js', false), 'generated');
  assert.equal(exclusionReason('src/app.min.js', false), 'generated');
  assert.equal(exclusionReason('src/auth.py', false), null);
  assert.equal(exclusionReason('src/environment.ts', false), null);
});

test('non-Git folder is reported', async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'dc-nogit-'));
  await assert.rejects(collectChanges({ cwd: dir, scope: 'unstaged' }), { code: 'NOT_A_REPO' });
});

test('repository without commits is reported', async () => {
  const dir = makeRepo({ commit: false });
  await assert.rejects(collectChanges({ cwd: dir, scope: 'unstaged' }), { code: 'NO_COMMITS' });
});

test('empty diff returns no files and no snapshot', async () => {
  const dir = makeRepo();
  const result = await collectChanges({ cwd: dir, scope: 'unstaged' });
  assert.equal(result.files.length, 0);
  assert.equal(result.snapshotId, null);
  assert.equal(result.diff, '');
});

test('unstaged diff: filters, context, snapshot separate from base SHA', async () => {
  const dir = makeRepo();
  fs.writeFileSync(path.join(dir, 'app.py'), 'print(2)\n');
  fs.writeFileSync(path.join(dir, '.env'), 'SECRET=1\n');
  fs.writeFileSync(path.join(dir, 'logo.png'), Buffer.from([0, 1, 2, 3]));
  git(dir, 'add', '-N', '.env', 'logo.png');
  fs.writeFileSync(path.join(dir, 'untracked.txt'), 'x');

  const result = await collectChanges({ cwd: dir, scope: 'unstaged' });
  assert.deepEqual(result.files.map((f) => f.path), ['app.py']);
  assert.deepEqual(result.excluded.map((f) => [f.path, f.reason]), [['.env', 'secret'], ['logo.png', 'binary']]);
  assert.ok(!result.diff.includes('SECRET'));
  assert.equal(result.snapshotId, snapshotId(result.diff));
  assert.equal(result.baseCommitSha, git(dir, 'rev-parse', 'HEAD').trim());
  assert.notEqual(result.snapshotId, result.baseCommitSha);
  assert.deepEqual(result.context, [{ path: 'app.py', content: 'print(2)\n', truncated: false }]);
  assert.equal(result.untrackedCount, 1);
});

test('staged and unstaged scopes are separate', async () => {
  const dir = makeRepo();
  fs.writeFileSync(path.join(dir, 'app.py'), 'print("staged")\n');
  git(dir, 'add', 'app.py');
  fs.writeFileSync(path.join(dir, 'app.py'), 'print("worktree")\n');

  const staged = await collectChanges({ cwd: dir, scope: 'staged' });
  const unstaged = await collectChanges({ cwd: dir, scope: 'unstaged' });
  assert.ok(staged.diff.includes('+print("staged")'));
  assert.ok(!staged.diff.includes('worktree'));
  assert.equal(staged.context[0].content, 'print("staged")\n');
  assert.ok(unstaged.diff.includes('+print("worktree")'));
  assert.notEqual(staged.snapshotId, unstaged.snapshotId);
});

test('large diffs are bounded and omitted files are listed', async () => {
  const dir = makeRepo();
  fs.writeFileSync(path.join(dir, 'a.py'), 'a = 1\n');
  fs.writeFileSync(path.join(dir, 'b.py'), `${'x = 1\n'.repeat(500)}`);
  git(dir, 'add', '.');
  const limits = { maxFiles: 10, maxDiffBytes: 1_000, maxContextFileChars: 100, maxContextTotalChars: 150, maxReadBytes: 10_000 };
  const result = await collectChanges({ cwd: dir, scope: 'staged', limits });
  assert.deepEqual(result.files.map((f) => f.path), ['a.py']);
  assert.deepEqual(result.omitted, [{ path: 'b.py', reason: 'size' }]);
  assert.ok(result.diffBytes <= 1_000);
});

test('snapshot is recomputed when code changes (stale detection input)', async () => {
  const dir = makeRepo();
  fs.writeFileSync(path.join(dir, 'app.py'), 'print(2)\n');
  const first = await collectChanges({ cwd: dir, scope: 'unstaged' });
  fs.writeFileSync(path.join(dir, 'app.py'), 'print(3)\n');
  const second = await collectChanges({ cwd: dir, scope: 'unstaged' });
  assert.notEqual(first.snapshotId, second.snapshotId);
});
