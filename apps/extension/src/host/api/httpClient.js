'use strict';
const { ApiClientError } = require('./errors');
const { assertAnalysisResult, assertEvaluationResult, isError } = require('./validate');

const LOCAL_HOSTS = new Set(['localhost', '127.0.0.1', '[::1]']);
const MAX_MESSAGE_CHARS = 300;

/** https everywhere; plain http only for loopback development servers. */
function parseBaseUrl(raw) {
  let url;
  try {
    url = new URL(String(raw));
  } catch {
    throw new ApiClientError('INVALID_CONFIG', 'devcomprehend.apiBaseUrl geçerli bir URL değil.');
  }
  if (url.username || url.password) {
    throw new ApiClientError('INVALID_CONFIG', 'API adresi kullanıcı adı/parola içeremez.');
  }
  const secure = url.protocol === 'https:';
  const localHttp = url.protocol === 'http:' && LOCAL_HOSTS.has(url.hostname);
  if (!secure && !localHttp) {
    throw new ApiClientError('INVALID_CONFIG', 'Uzak API adresleri için https zorunludur.');
  }
  return url.origin + url.pathname.replace(/\/+$/, '');
}

function createHttpClient({ baseUrl, getToken, fetchImpl = globalThis.fetch, timeoutMs = 20_000 }) {
  const origin = parseBaseUrl(baseUrl);

  async function call(method, path, body) {
    const token = await getToken();
    if (!token) {
      throw new ApiClientError('UNAUTHENTICATED', "API token ayarlı değil. 'DevComprehend: Set API Token' komutunu çalıştırın.");
    }
    let response;
    try {
      response = await fetchImpl(origin + path, {
        method,
        headers: {
          Accept: 'application/json',
          Authorization: `Bearer ${token}`,
          ...(body ? { 'Content-Type': 'application/json' } : {}),
        },
        body: body ? JSON.stringify(body) : undefined,
        redirect: 'error',
        signal: AbortSignal.timeout(timeoutMs),
      });
    } catch (error) {
      if (error && (error.name === 'TimeoutError' || error.name === 'AbortError')) {
        throw new ApiClientError('TIMEOUT', 'API zamanında yanıt vermedi.', true);
      }
      throw new ApiClientError('NETWORK_ERROR', 'API adresine ulaşılamadı.', true);
    }

    let data = null;
    try {
      data = await response.json();
    } catch {
      data = null;
    }
    if (!response.ok) {
      const envelope = data && data.error;
      if (isError(envelope)) {
        throw new ApiClientError(envelope.code, envelope.message.slice(0, MAX_MESSAGE_CHARS), envelope.retryable, response.status);
      }
      throw new ApiClientError('HTTP_ERROR', `API isteği başarısız oldu (HTTP ${response.status}).`, response.status >= 500, response.status);
    }
    return data;
  }

  return {
    mode: 'http',
    origin,
    // contracts/README.md says 202 for POST; services/api currently returns 200. Both are accepted.
    async createAnalysis(request) {
      return assertAnalysisResult(await call('POST', '/v1/analyses', request));
    },
    async getAnalysis(id) {
      return assertAnalysisResult(await call('GET', `/v1/analyses/${encodeURIComponent(id)}`));
    },
    async submitAnswer(analysisId, answerRequest) {
      const result = await call('POST', `/v1/analyses/${encodeURIComponent(analysisId)}/answers`, answerRequest);
      return assertEvaluationResult(result, answerRequest.question_id);
    },
  };
}

module.exports = { createHttpClient, parseBaseUrl };
