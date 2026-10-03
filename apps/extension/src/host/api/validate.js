'use strict';
// Structural checks for untrusted API responses (contracts/v1/message.schema.json).
const { ApiClientError } = require('./errors');

const STATUSES = new Set(['queued', 'fetching', 'generating', 'ready', 'failed']);
const ASSESSMENTS = new Set(['unassessed', 'developing', 'demonstrated']);
const RUBRIC_RESULTS = new Set(['met', 'partial', 'missing']);
const SNAPSHOT = /^[a-f0-9]{64}$/;

const isString = (value) => typeof value === 'string' && value.length > 0;
const isLine = (value) => Number.isInteger(value) && value >= 1;

function invalid() {
  return new ApiClientError('INVALID_RESPONSE', 'API beklenmeyen biçimde yanıt verdi.', false);
}

function isError(value) {
  return value && isString(value.code) && isString(value.message) && typeof value.retryable === 'boolean';
}

function isSource(source) {
  return source && isString(source.path) && isLine(source.start_line) && isLine(source.end_line) && SNAPSHOT.test(source.snapshot_id);
}

function isQuestion(question) {
  return (
    question &&
    isString(question.id) &&
    isString(question.concept) &&
    isString(question.prompt) &&
    Array.isArray(question.sources) &&
    question.sources.length > 0 &&
    question.sources.every(isSource) &&
    Array.isArray(question.rubric) &&
    question.rubric.length > 0 &&
    question.rubric.every(isString)
  );
}

function assertAnalysisResult(value) {
  const ok =
    value &&
    value.kind === 'analysis_result' &&
    value.contract_version === '1' &&
    isString(value.id) &&
    STATUSES.has(value.status) &&
    Array.isArray(value.questions) &&
    value.questions.length <= 5 &&
    value.questions.every(isQuestion) &&
    (value.error === null || isError(value.error)) &&
    (value.status !== 'ready' || (value.questions.length >= 3 && value.error === null)) &&
    (value.status !== 'failed' || isError(value.error));
  if (!ok) throw invalid();
  return value;
}

function assertEvaluationResult(value, questionId) {
  const ok =
    value &&
    value.kind === 'evaluation_result' &&
    value.contract_version === '1' &&
    value.question_id === questionId &&
    ASSESSMENTS.has(value.assessment_state) &&
    Array.isArray(value.rubric_results) &&
    value.rubric_results.every((item) => item && isString(item.criterion) && RUBRIC_RESULTS.has(item.result)) &&
    isString(value.feedback) &&
    typeof value.uncertain === 'boolean' &&
    (value.due_at === null || (isString(value.due_at) && !Number.isNaN(Date.parse(value.due_at))));
  if (!ok) throw invalid();
  return value;
}

module.exports = { assertAnalysisResult, assertEvaluationResult, isError };
