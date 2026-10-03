'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');
const { AnalysisController } = require('../src/host/controller');
const { validateWebviewMessage } = require('../src/host/messages');
const { createMockClient } = require('../src/host/api/mockClient');

const SNAP = 'c'.repeat(64);

function collected(overrides = {}) {
  return {
    root: '/repo',
    scope: 'unstaged',
    baseCommitSha: '1'.repeat(40),
    snapshotId: SNAP,
    diff: 'diff --git a/x b/x\n+1\n',
    diffBytes: 20,
    files: [{ path: 'x', additions: 1, deletions: 0 }],
    excluded: [],
    omitted: [],
    context: [],
    untrackedCount: 0,
    ...overrides,
  };
}

function setup({ client, collect } = {}) {
  const posts = [];
  const notes = [];
  const opened = [];
  const sent = [];
  const base = client || createMockClient({ delay: async () => {} });
  const spy = {
    mode: base.mode,
    async createAnalysis(request) {
      sent.push(request);
      return base.createAnalysis(request);
    },
    getAnalysis: (id) => base.getAnalysis(id),
    submitAnswer: (id, body) => base.submitAnswer(id, body),
  };
  let ids = 0;
  const controller = new AnalysisController(
    {
      getClient: () => ({ client: spy, mode: 'mock', target: 'mock' }),
      pickTarget: async () => ({ cwd: '/repo', folderName: 'repo', scope: 'unstaged' }),
      collect: collect || (async () => collected()),
      repositoryIdFor: () => 'ws-test',
      openSource: async (root, source) => opened.push({ root, source }),
      post: (state) => posts.push(state),
      notify: (level, message) => notes.push({ level, message }),
      sleep: async () => {},
      newId: () => `id-${++ids}`,
    },
    { pollIntervalMs: 0, maxPolls: 10 },
  );
  return { controller, posts, notes, opened, sent, client: spy };
}

async function toReady(ctx) {
  await ctx.controller.analyze();
  await ctx.controller.confirmPreview(ctx.controller.state.preview.previewId);
  assert.equal(ctx.controller.state.phase, 'ready');
}

test('nothing is sent before the preview is confirmed', async () => {
  const ctx = setup();
  await ctx.controller.analyze();
  assert.equal(ctx.controller.state.phase, 'preview');
  assert.equal(ctx.sent.length, 0);
  await ctx.controller.confirmPreview('wrong-id');
  assert.equal(ctx.sent.length, 0);
  ctx.controller.cancelPreview();
  assert.equal(ctx.controller.state.phase, 'idle');
  await ctx.controller.confirmPreview('id-1');
  assert.equal(ctx.sent.length, 0, 'cancelled preview cannot be confirmed');
});

test('confirmed flow shows progress then ready questions', async () => {
  const ctx = setup();
  await toReady(ctx);
  assert.equal(ctx.sent.length, 1);
  assert.equal(ctx.sent[0].snapshot_id, SNAP);
  assert.equal(ctx.sent[0].repository_id, 'ws-test');
  const statuses = ctx.posts.filter((s) => s.phase === 'polling').map((s) => s.analysis.status);
  assert.deepEqual(statuses, ['queued', 'fetching', 'generating']);
  assert.ok(ctx.posts.every((s) => s.mode === 'mock'));
});

test('empty diff and Git errors are shown without sending', async () => {
  const empty = setup({ collect: async () => collected({ files: [], diff: '', snapshotId: null }) });
  await empty.controller.analyze();
  assert.equal(empty.controller.state.phase, 'empty');
  const noGit = setup({ collect: async () => Promise.reject(Object.assign(new Error('Git deposu değil'), { code: 'NOT_A_REPO' })) });
  await noGit.controller.analyze();
  assert.equal(noGit.controller.state.phase, 'error');
  assert.equal(noGit.controller.state.error.code, 'NOT_A_REPO');
  assert.equal(empty.sent.length + noGit.sent.length, 0);
});

test('double submit is ignored and failed answers reuse submission_id', async () => {
  const bodies = [];
  let fail = true;
  const base = createMockClient({ delay: async () => {} });
  const ctx = setup({
    client: {
      ...base,
      async submitAnswer(id, body) {
        bodies.push(body);
        if (fail) throw Object.assign(new Error('Ağ hatası.'), { code: 'NETWORK_ERROR', retryable: true });
        return base.submitAnswer(id, body);
      },
    },
  });
  await toReady(ctx);
  const first = ctx.controller.submitAnswer('q-1', 'cevap');
  const second = ctx.controller.submitAnswer('q-1', 'cevap');
  await Promise.all([first, second]);
  assert.equal(bodies.length, 1, 'second click while submitting is ignored');
  assert.equal(ctx.controller.state.answers['q-1'].status, 'error');

  fail = false;
  await ctx.controller.submitAnswer('q-1', 'cevap');
  assert.equal(bodies[1].submission_id, bodies[0].submission_id);
  assert.equal(ctx.controller.state.answers['q-1'].status, 'evaluated');

  await ctx.controller.submitAnswer('q-1', 'yeni cevap');
  assert.notEqual(bodies[2].submission_id, bodies[0].submission_id);
});

test('opening a source after code changed warns about stale snapshot', async () => {
  let current = SNAP;
  const ctx = setup({ collect: async () => collected({ snapshotId: current }) });
  await toReady(ctx);
  await ctx.controller.openSource('q-1', 0);
  assert.equal(ctx.controller.state.stale, false);
  assert.equal(ctx.opened.length, 1);

  current = 'd'.repeat(64);
  await ctx.controller.openSource('q-1', 0);
  assert.equal(ctx.controller.state.stale, true);
  assert.ok(ctx.notes.some((n) => n.level === 'warning'));
  assert.equal(ctx.opened.length, 2);
  assert.equal(ctx.opened[1].root, '/repo');
});

test('mock demo works without Git', async () => {
  const ctx = setup({ collect: async () => assert.fail('demo must not read Git') });
  await ctx.controller.showDemo();
  assert.equal(ctx.controller.state.phase, 'ready');
  assert.equal(ctx.controller.state.analysis.questions.length, 3);
  await ctx.controller.openSource('q-1', 0);
  assert.equal(ctx.opened.length, 0);
});

test('webview messages are allowlisted', () => {
  assert.deepEqual(validateWebviewMessage({ type: 'ready' }), { type: 'ready' });
  assert.deepEqual(validateWebviewMessage({ type: 'submitAnswer', questionId: 'q-1', answer: 'a' }), { type: 'submitAnswer', questionId: 'q-1', answer: 'a' });
  assert.equal(validateWebviewMessage({ type: 'runCommand', command: 'rm' }), null);
  assert.equal(validateWebviewMessage({ type: 'ready', extra: 1 }), null);
  assert.equal(validateWebviewMessage({ type: 'submitAnswer', questionId: 'q-1', answer: '   ' }), null);
  assert.equal(validateWebviewMessage({ type: 'submitAnswer', questionId: 'q-1', answer: 'x'.repeat(4001) }), null);
  assert.equal(validateWebviewMessage({ type: 'openSource', questionId: 'q-1', sourceIndex: '../../etc' }), null);
  assert.equal(validateWebviewMessage({ type: 'toString' }), null);
  assert.equal(validateWebviewMessage(null), null);
});

test('package contributes only registered commands and no embedded secrets', () => {
  const root = path.resolve(__dirname, '..');
  const pkg = JSON.parse(fs.readFileSync(path.join(root, 'package.json'), 'utf8'));
  const source = fs.readFileSync(path.join(root, 'src/extension.js'), 'utf8');
  for (const { command } of pkg.contributes.commands) assert.ok(source.includes(`'${command}'`), command);
  assert.equal(pkg.contributes.configuration.properties['devcomprehend.apiMode'].default, 'mock');
  assert.ok(!JSON.stringify(pkg).toLowerCase().includes('dev-token'));
  assert.equal(pkg.capabilities.untrustedWorkspaces.supported, false);
});
