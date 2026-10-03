'use strict';
// Analysis flow state machine. No vscode import: UI, Git and API are injected.
const { buildAnalysisRequest, buildAnswerRequest } = require('./api/request');

const BUSY = new Set(['collecting', 'sending', 'polling']);
const TERMINAL = new Set(['ready', 'failed']);

function toError(error) {
  return {
    code: (error && error.code) || 'UNKNOWN',
    message: (error && error.message) || 'Beklenmeyen hata.',
    retryable: Boolean(error && error.retryable),
  };
}

class AnalysisController {
  /**
   * @param {object} deps
   * @param {() => {client: object, mode: 'mock'|'http', target: string}} deps.getClient
   * @param {() => Promise<{cwd: string, folderName: string, scope: 'staged'|'unstaged'} | null>} deps.pickTarget
   * @param {(cwd: string, scope: string) => Promise<object>} deps.collect
   * @param {(root: string) => string} deps.repositoryIdFor
   * @param {(root: string, source: object) => Promise<void>} deps.openSource
   * @param {(state: object) => void} deps.post
   * @param {(level: 'info'|'warning'|'error', message: string) => void} deps.notify
   * @param {(ms: number) => Promise<void>} deps.sleep
   * @param {() => string} deps.newId
   */
  constructor(deps, { pollIntervalMs = 1500, maxPolls = 80 } = {}) {
    this.deps = deps;
    this.pollIntervalMs = pollIntervalMs;
    this.maxPolls = maxPolls;
    this.run = 0;
    this.pending = null; // confirmed-not-yet request; never sent before confirmPreview
    this.session = null;
    this.attempts = new Map();
    this.state = { phase: 'idle', preview: null, analysis: null, answers: {}, stale: false, error: null, empty: null };
  }

  snapshotState() {
    const { mode, target } = this.deps.getClient();
    return { ...this.state, mode, target };
  }

  update(patch) {
    this.state = { ...this.state, ...patch };
    this.deps.post(this.snapshotState());
  }

  reset() {
    this.run += 1;
    this.pending = null;
    this.session = null;
    this.attempts.clear();
  }

  async analyze() {
    if (BUSY.has(this.state.phase)) return;
    let target;
    try {
      target = await this.deps.pickTarget();
    } catch (error) {
      this.update({ phase: 'error', error: toError(error) });
      return;
    }
    if (!target) return;
    this.reset();
    this.update({ phase: 'collecting', preview: null, analysis: null, answers: {}, stale: false, error: null, empty: null });
    try {
      const collected = await this.deps.collect(target.cwd, target.scope);
      if (collected.files.length === 0) {
        this.update({
          phase: 'empty',
          empty: { scope: collected.scope, excluded: collected.excluded, omitted: collected.omitted, untrackedCount: collected.untrackedCount },
        });
        return;
      }
      const { request, droppedContext, bytes } = buildAnalysisRequest(collected, this.deps.repositoryIdFor(collected.root));
      const previewId = this.deps.newId();
      this.pending = { previewId, request, root: collected.root, scope: collected.scope };
      this.update({
        phase: 'preview',
        preview: {
          previewId,
          folderName: target.folderName,
          scope: collected.scope,
          baseCommitSha: collected.baseCommitSha,
          snapshotId: collected.snapshotId,
          files: collected.files,
          excluded: collected.excluded,
          omitted: collected.omitted,
          context: collected.context
            .filter((item) => !droppedContext.includes(item.path))
            .map((item) => ({ path: item.path, truncated: item.truncated })),
          droppedContext,
          untrackedCount: collected.untrackedCount,
          bytes,
          diff: request.diff,
        },
      });
    } catch (error) {
      this.update({ phase: 'error', error: toError(error) });
    }
  }

  cancelPreview() {
    if (this.state.phase !== 'preview') return;
    this.pending = null;
    this.update({ phase: 'idle', preview: null });
  }

  async confirmPreview(previewId) {
    if (this.state.phase !== 'preview' || !this.pending || this.pending.previewId !== previewId) return;
    const { request, root, scope } = this.pending;
    this.pending = null;
    await this.start(request, { root, scope, snapshotId: request.snapshot_id });
  }

  async showDemo() {
    if (BUSY.has(this.state.phase) || this.deps.getClient().mode !== 'mock') return;
    this.reset();
    this.update({ phase: 'sending', preview: null, analysis: null, answers: {}, stale: false, error: null, empty: null });
    await this.start(null, { root: null, scope: null, snapshotId: null });
  }

  async start(request, sessionInfo) {
    const run = this.run;
    const { client } = this.deps.getClient();
    this.update({ phase: 'sending', preview: null, error: null });
    try {
      let analysis = await client.createAnalysis(request);
      this.session = { ...sessionInfo, client, analysisId: analysis.id };
      let polls = 0;
      while (!TERMINAL.has(analysis.status)) {
        if (run !== this.run) return;
        this.update({ phase: 'polling', analysis });
        if (polls >= this.maxPolls) {
          throw { code: 'TIMEOUT', message: 'Analiz zamanında tamamlanmadı.', retryable: true };
        }
        await this.deps.sleep(this.pollIntervalMs);
        if (run !== this.run) return;
        analysis = await client.getAnalysis(analysis.id);
        polls += 1;
      }
      if (run !== this.run) return;
      if (analysis.status === 'failed') {
        this.update({ phase: 'failed', analysis, error: analysis.error });
        return;
      }
      this.update({ phase: 'ready', analysis, answers: {} });
    } catch (error) {
      if (run !== this.run) return;
      this.update({ phase: 'failed', error: toError(error) });
    }
  }

  findQuestion(questionId) {
    const analysis = this.state.analysis;
    if (this.state.phase !== 'ready' || !analysis) return null;
    return analysis.questions.find((question) => question.id === questionId) || null;
  }

  async submitAnswer(questionId, answer) {
    const question = this.findQuestion(questionId);
    if (!question || !this.session) return;
    const current = this.state.answers[questionId];
    if (current && current.status === 'submitting') return; // double-submit guard

    // Same text after a failure reuses submission_id so the server can de-duplicate.
    const previous = this.attempts.get(questionId);
    const submissionId = previous && !previous.done && previous.answer === answer ? previous.submissionId : this.deps.newId();
    this.attempts.set(questionId, { answer, submissionId, done: false });

    const run = this.run;
    const { client, analysisId } = this.session;
    this.setAnswer(questionId, { status: 'submitting', evaluation: current ? current.evaluation : null, error: null });
    try {
      const evaluation = await client.submitAnswer(analysisId, buildAnswerRequest(questionId, answer, submissionId));
      if (run !== this.run) return;
      this.attempts.set(questionId, { answer, submissionId, done: true });
      this.setAnswer(questionId, { status: 'evaluated', evaluation, error: null });
    } catch (error) {
      if (run !== this.run) return;
      const safe = toError(error);
      this.setAnswer(questionId, { status: 'error', evaluation: current ? current.evaluation : null, error: safe });
      if (safe.code === 'STALE_SNAPSHOT') this.update({ stale: true });
    }
  }

  setAnswer(questionId, value) {
    this.update({ answers: { ...this.state.answers, [questionId]: value } });
  }

  async openSource(questionId, sourceIndex) {
    const question = this.findQuestion(questionId);
    const source = question && question.sources[sourceIndex];
    if (!source) return;
    if (!this.session || !this.session.root) {
      this.deps.notify('info', `Demo kaynağı (${source.path}) bu workspace'te yok; mock demo yalnız örnek gösterir.`);
      return;
    }
    const stale = source.snapshot_id !== this.session.snapshotId || (await this.isStale());
    if (stale) {
      this.update({ stale: true });
      this.deps.notify('warning', 'Kod analizden sonra değişti; kaynak satırları güncel olmayabilir.');
    }
    try {
      await this.deps.openSource(this.session.root, source);
    } catch (error) {
      this.deps.notify('error', toError(error).message);
    }
  }

  /** Recomputes the snapshot for the analysed scope and flags drift. */
  async isStale() {
    if (!this.session || !this.session.root || this.state.phase !== 'ready') return false;
    try {
      const current = await this.deps.collect(this.session.root, this.session.scope);
      return current.snapshotId !== this.session.snapshotId;
    } catch {
      return true;
    }
  }

  async refreshStale() {
    if (this.state.stale) return;
    if (await this.isStale()) this.update({ stale: true });
  }

  async retry() {
    if (BUSY.has(this.state.phase)) return;
    this.update({ phase: 'idle', error: null, empty: null });
    await this.analyze();
  }

  async handleMessage(message) {
    switch (message.type) {
      case 'ready':
        this.deps.post(this.snapshotState());
        return;
      case 'startAnalysis':
        return this.analyze();
      case 'showDemo':
        return this.showDemo();
      case 'confirmPreview':
        return this.confirmPreview(message.previewId);
      case 'cancelPreview':
        return this.cancelPreview();
      case 'submitAnswer':
        return this.submitAnswer(message.questionId, message.answer);
      case 'openSource':
        return this.openSource(message.questionId, message.sourceIndex);
      case 'retry':
        return this.retry();
      default:
        return undefined;
    }
  }
}

module.exports = { AnalysisController };
