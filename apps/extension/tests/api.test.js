'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');
const { buildAnalysisRequest, buildAnswerRequest, MAX_REQUEST_BYTES } = require('../src/host/api/request');
const { assertAnalysisResult, assertEvaluationResult } = require('../src/host/api/validate');
const { createMockClient, loadFixtures } = require('../src/host/api/mockClient');
const { createHttpClient, parseBaseUrl } = require('../src/host/api/httpClient');
const { snapshotId } = require('../src/host/git/snapshot');

const CONTRACT_EXAMPLES = path.resolve(__dirname, '../../../contracts/v1/examples');
const example = (name) => JSON.parse(fs.readFileSync(path.join(CONTRACT_EXAMPLES, name), 'utf8'));

test('bundled fixtures match contracts/v1/examples', () => {
  for (const name of ['analysis-queued.json', 'analysis-ready.json', 'evaluation-result.json']) {
    const bundled = fs.readFileSync(path.resolve(__dirname, '../fixtures', name), 'utf8');
    assert.equal(bundled, fs.readFileSync(path.join(CONTRACT_EXAMPLES, name), 'utf8'), `${name} drifted; run npm run sync-fixtures`);
  }
});

test('analysis_request matches the contract example shape', () => {
  const expected = example('analysis-request.json');
  assert.equal(snapshotId(expected.diff), expected.snapshot_id, 'snapshot_id = SHA-256(diff)');
  const { request } = buildAnalysisRequest(
    {
      baseCommitSha: expected.base_commit_sha,
      snapshotId: expected.snapshot_id,
      scope: expected.scope,
      diff: expected.diff,
      context: expected.context.map((item) => ({ ...item, truncated: false })),
    },
    expected.repository_id,
  );
  assert.deepEqual(request, expected);
});

test('analysis_request drops context, then refuses oversized diffs', () => {
  const base = { baseCommitSha: '1'.repeat(40), snapshotId: 'a'.repeat(64), scope: 'staged' };
  const fits = buildAnalysisRequest({ ...base, diff: 'd'.repeat(30_000), context: [{ path: 'a', content: 'c'.repeat(40_000) }] }, 'ws');
  assert.deepEqual(fits.droppedContext, ['a']);
  assert.ok(fits.bytes <= MAX_REQUEST_BYTES);
  assert.throws(() => buildAnalysisRequest({ ...base, diff: 'd'.repeat(70_000), context: [] }, 'ws'), { code: 'PAYLOAD_TOO_LARGE' });
});

test('answer_request matches the contract example', () => {
  const expected = example('answer-request.json');
  assert.deepEqual(buildAnswerRequest(expected.question_id, expected.answer, expected.submission_id), expected);
});

test('validators accept contract fixtures and reject malformed responses', () => {
  const fixtures = loadFixtures();
  assert.ok(assertAnalysisResult(fixtures.queued));
  assert.ok(assertAnalysisResult(fixtures.ready));
  assert.ok(assertEvaluationResult(fixtures.evaluation, 'q-1'));
  assert.throws(() => assertAnalysisResult({ ...fixtures.ready, questions: [] }), { code: 'INVALID_RESPONSE' });
  assert.throws(() => assertEvaluationResult(fixtures.evaluation, 'q-2'), { code: 'INVALID_RESPONSE' });
});

test('mock client walks queued → fetching → generating → ready and binds snapshot', async () => {
  const client = createMockClient({ delay: async () => {} });
  const snap = 'b'.repeat(64);
  const queued = await client.createAnalysis({ snapshot_id: snap });
  assert.equal(queued.status, 'queued');
  const statuses = [];
  let result;
  do {
    result = await client.getAnalysis(queued.id);
    statuses.push(result.status);
  } while (result.status !== 'ready');
  assert.deepEqual(statuses, ['fetching', 'generating', 'ready']);
  assertAnalysisResult(result);
  assert.ok(result.questions.every((q) => q.sources.every((s) => s.snapshot_id === snap)));

  const evaluation = await client.submitAnswer(queued.id, buildAnswerRequest('q-1', 'x', 's'));
  assert.equal(evaluation.assessment_state, 'demonstrated');
  const uncertain = await client.submitAnswer(queued.id, buildAnswerRequest('q-2', 'x', 's'));
  assertEvaluationResult(uncertain, 'q-2');
  assert.equal(uncertain.uncertain, true);
});

test('base URL must be https unless loopback', () => {
  assert.equal(parseBaseUrl('http://127.0.0.1:8000/'), 'http://127.0.0.1:8000');
  assert.equal(parseBaseUrl('https://api.example.com/base/'), 'https://api.example.com/base');
  assert.throws(() => parseBaseUrl('http://api.example.com'), { code: 'INVALID_CONFIG' });
  assert.throws(() => parseBaseUrl('https://user:pw@api.example.com'), { code: 'INVALID_CONFIG' });
  assert.throws(() => parseBaseUrl('not a url'), { code: 'INVALID_CONFIG' });
});

function fakeFetch(responses, calls) {
  return async (url, init) => {
    calls.push({ url, init });
    const next = responses.shift();
    if (next instanceof Error) throw next;
    return { ok: next.status < 400, status: next.status, json: async () => next.body };
  };
}

test('http client sends bearer token and accepts 200/202 analysis responses', async () => {
  const calls = [];
  const fixtures = loadFixtures();
  const client = createHttpClient({
    baseUrl: 'http://127.0.0.1:8000',
    getToken: async () => 'dev-token',
    fetchImpl: fakeFetch([{ status: 202, body: fixtures.queued }, { status: 200, body: fixtures.ready }], calls),
  });
  await client.createAnalysis(example('analysis-request.json'));
  await client.getAnalysis('analysis demo');
  assert.equal(calls[0].url, 'http://127.0.0.1:8000/v1/analyses');
  assert.equal(calls[0].init.headers.Authorization, 'Bearer dev-token');
  assert.equal(calls[1].url, 'http://127.0.0.1:8000/v1/analyses/analysis%20demo');
});

test('http client surfaces error envelopes and refuses to run without a token', async () => {
  const calls = [];
  const client = createHttpClient({
    baseUrl: 'http://localhost:8000',
    getToken: async () => 'dev-token',
    fetchImpl: fakeFetch(
      [
        { status: 429, body: { error: { code: 'QUOTA_EXCEEDED', message: 'Günlük kota doldu.', retryable: false } } },
        { status: 500, body: null },
        new TypeError('fetch failed'),
      ],
      calls,
    ),
  });
  await assert.rejects(client.getAnalysis('x'), { code: 'QUOTA_EXCEEDED', status: 429 });
  await assert.rejects(client.getAnalysis('x'), { code: 'HTTP_ERROR', retryable: true });
  await assert.rejects(client.getAnalysis('x'), { code: 'NETWORK_ERROR', retryable: true });

  const noToken = createHttpClient({ baseUrl: 'http://localhost:8000', getToken: async () => undefined, fetchImpl: fakeFetch([], calls) });
  const before = calls.length;
  await assert.rejects(noToken.getAnalysis('x'), { code: 'UNAUTHENTICATED' });
  assert.equal(calls.length, before, 'no request without a token');
});
