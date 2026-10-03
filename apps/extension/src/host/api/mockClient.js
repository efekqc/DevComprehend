'use strict';
// Mock API adapter: never sends data; serves contracts/v1 fixtures (synced into fixtures/).
const fs = require('fs');
const path = require('path');
const { ApiClientError } = require('./errors');

const FIXTURE_DIR = path.resolve(__dirname, '../../../fixtures');
const PROGRESS = ['fetching', 'generating', 'ready'];

function loadFixtures(dir = FIXTURE_DIR) {
  const read = (name) => JSON.parse(fs.readFileSync(path.join(dir, name), 'utf8'));
  return {
    queued: read('analysis-queued.json'),
    ready: read('analysis-ready.json'),
    evaluation: read('evaluation-result.json'),
  };
}

const clone = (value) => JSON.parse(JSON.stringify(value));

function createMockClient({ fixtures = loadFixtures(), delay = (ms) => new Promise((r) => setTimeout(r, ms)), latencyMs = 250 } = {}) {
  const analyses = new Map();
  let counter = 0;

  function readyFor(id, snapshotId) {
    const ready = clone(fixtures.ready);
    ready.id = id;
    if (snapshotId) {
      // Bind fixture sources to the local snapshot so stale detection is meaningful in mock mode.
      for (const question of ready.questions) {
        for (const source of question.sources) source.snapshot_id = snapshotId;
      }
    }
    return ready;
  }

  return {
    mode: 'mock',

    /** request === null starts the fixture-only demo (no Git needed). */
    async createAnalysis(request) {
      await delay(latencyMs);
      counter += 1;
      const id = `mock-analysis-${counter}`;
      analyses.set(id, { snapshotId: request ? request.snapshot_id : null, polls: 0 });
      return { ...clone(fixtures.queued), id };
    },

    async getAnalysis(id) {
      await delay(latencyMs);
      const entry = analyses.get(id);
      if (!entry) throw new ApiClientError('NOT_FOUND', 'Analiz bulunamadı.', false, 404);
      const status = PROGRESS[Math.min(entry.polls, PROGRESS.length - 1)];
      entry.polls += 1;
      if (status === 'ready') return readyFor(id, entry.snapshotId);
      return { ...clone(fixtures.queued), id, status };
    },

    async submitAnswer(analysisId, answerRequest) {
      await delay(latencyMs);
      if (!analyses.has(analysisId)) throw new ApiClientError('NOT_FOUND', 'Analiz bulunamadı.', false, 404);
      if (answerRequest.question_id === fixtures.evaluation.question_id) return clone(fixtures.evaluation);
      return {
        kind: 'evaluation_result',
        contract_version: '1',
        question_id: answerRequest.question_id,
        assessment_state: 'unassessed',
        rubric_results: [],
        feedback: 'Mock modu: bu soru için örnek değerlendirme yok. Cevap değerlendirilmedi.',
        uncertain: true,
        due_at: null,
      };
    },
  };
}

module.exports = { createMockClient, loadFixtures };
