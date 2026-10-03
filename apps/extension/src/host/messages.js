'use strict';
// Webview → host allowlist. Anything else is dropped; webview never sends paths or URLs.

const MAX_ID_CHARS = 200;
const MAX_ANSWER_CHARS = 4_000;

const isId = (value) => typeof value === 'string' && value.length > 0 && value.length <= MAX_ID_CHARS;

const SCHEMAS = {
  ready: {},
  startAnalysis: {},
  showDemo: {},
  cancelPreview: {},
  retry: {},
  confirmPreview: { previewId: isId },
  submitAnswer: {
    questionId: isId,
    answer: (value) => typeof value === 'string' && value.trim().length > 0 && value.length <= MAX_ANSWER_CHARS,
  },
  openSource: {
    questionId: isId,
    sourceIndex: (value) => Number.isInteger(value) && value >= 0 && value < 50,
  },
};

/** @returns {object | null} the validated message, or null when it is not allowed */
function validateWebviewMessage(raw) {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null;
  const schema = Object.prototype.hasOwnProperty.call(SCHEMAS, raw.type) ? SCHEMAS[raw.type] : null;
  if (!schema) return null;
  const keys = Object.keys(raw).filter((key) => key !== 'type');
  if (keys.length !== Object.keys(schema).length) return null;
  const message = { type: raw.type };
  for (const key of keys) {
    const check = schema[key];
    if (!check || !check(raw[key])) return null;
    message[key] = raw[key];
  }
  return message;
}

module.exports = { validateWebviewMessage, MAX_ANSWER_CHARS };
