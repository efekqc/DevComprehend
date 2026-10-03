'use strict';
const { ApiClientError } = require('./errors');

// services/api rejects bodies above 64 KB; keep headroom for headers/escaping.
const MAX_REQUEST_BYTES = 60_000;
const PIPELINE_VERSION = 'pilot-1';

function byteLength(value) {
  return Buffer.byteLength(JSON.stringify(value), 'utf8');
}

/**
 * Builds a bounded analysis_request. Context files are dropped from the end
 * until the body fits; returns which context paths were dropped.
 */
function buildAnalysisRequest(collected, repositoryId, pipelineVersion = PIPELINE_VERSION) {
  const context = collected.context.map(({ path, content }) => ({ path, content }));
  const request = {
    kind: 'analysis_request',
    contract_version: '1',
    repository_id: repositoryId,
    base_commit_sha: collected.baseCommitSha,
    snapshot_id: collected.snapshotId,
    scope: collected.scope,
    diff: collected.diff,
    context,
    pipeline_version: pipelineVersion,
  };
  const droppedContext = [];
  while (byteLength(request) > MAX_REQUEST_BYTES && request.context.length > 0) {
    droppedContext.unshift(request.context.pop().path);
  }
  if (byteLength(request) > MAX_REQUEST_BYTES) {
    throw new ApiClientError('PAYLOAD_TOO_LARGE', 'Diff gönderim sınırını aşıyor. Daha küçük bir değişiklik seçin.', false);
  }
  return { request, droppedContext, bytes: byteLength(request) };
}

function buildAnswerRequest(questionId, answer, submissionId) {
  return {
    kind: 'answer_request',
    contract_version: '1',
    question_id: questionId,
    answer,
    submission_id: submissionId,
  };
}

module.exports = { buildAnalysisRequest, buildAnswerRequest, MAX_REQUEST_BYTES, PIPELINE_VERSION };
