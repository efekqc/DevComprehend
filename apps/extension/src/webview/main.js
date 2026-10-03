// Sidebar UI. Renders host state with textContent only; drafts survive errors and reloads.
(function () {
  'use strict';
  const vscode = acquireVsCodeApi();
  const app = document.getElementById('app');
  const saved = vscode.getState() || {};
  const drafts = saved.drafts || {};
  let state = null;

  const SCOPE = { staged: 'Staged', unstaged: 'Unstaged' };
  const STATUS = { queued: 'Sırada', fetching: 'Değişiklikler alınıyor', generating: 'Sorular üretiliyor' };
  const EXCLUDE_REASON = { secret: 'gizli bilgi olabilir', binary: 'binary dosya', generated: 'üretilmiş / bağımlılık dosyası' };
  const OMIT_REASON = { size: 'diff boyut sınırı', file_limit: 'dosya sayısı sınırı' };
  const ASSESSMENT = { unassessed: 'Değerlendirilmedi', developing: 'Gelişiyor', demonstrated: 'Gösterildi' };
  const RUBRIC = { met: 'Karşılandı', partial: 'Kısmen', missing: 'Eksik' };

  function el(tag, attrs, children) {
    const node = document.createElement(tag);
    for (const [key, value] of Object.entries(attrs || {})) {
      if (value === undefined || value === null || value === false) continue;
      if (key === 'text') node.textContent = value;
      else if (key === 'onClick') node.addEventListener('click', value);
      else node.setAttribute(key, value === true ? '' : String(value));
    }
    for (const child of [].concat(children || [])) if (child) node.appendChild(child);
    return node;
  }

  const send = (message) => vscode.postMessage(message);
  const button = (label, onClick, attrs) => el('button', { type: 'button', text: label, onClick, ...attrs });
  const short = (sha) => (sha ? sha.slice(0, 12) : '-');
  const persist = () => vscode.setState({ drafts });

  function modeBanner() {
    if (state.mode === 'mock') {
      return el('p', { class: 'banner mock', role: 'status' }, [
        el('strong', { text: 'MOCK MODU' }),
        document.createTextNode(' Kod hiçbir yere gönderilmez; sorular contracts/v1 örneklerinden gelir.'),
      ]);
    }
    return el('p', { class: 'banner', text: `API: ${state.target}` });
  }

  function pathList(title, items, reasons) {
    if (!items || items.length === 0) return null;
    return el('section', {}, [
      el('h3', { text: title }),
      el('ul', {}, items.map((item) => el('li', { text: `${item.path} — ${reasons[item.reason] || item.reason}` }))),
    ]);
  }

  function renderIdle() {
    return [
      el('p', { text: 'Yerel Git değişikliklerinden projeye özel sorular üretir. Göndermeden önce içeriği önizleyip onaylarsınız.' }),
      button('Değişiklikleri analiz et', () => send({ type: 'startAnalysis' }), { class: 'primary' }),
      state.mode === 'mock' ? button('Mock demo sorularını göster', () => send({ type: 'showDemo' }), { class: 'secondary' }) : null,
    ];
  }

  function renderPreview() {
    const p = state.preview;
    const sendLabel = state.mode === 'mock' ? 'Onayla (mock: gönderilmez)' : 'Onayla ve gönder';
    const notes = [];
    if (p.omitted.length) notes.push(`${p.omitted.length} dosya sınır nedeniyle gönderilmeyecek. Daha küçük bir değişiklik seçmek soruları iyileştirir.`);
    if (p.droppedContext.length) notes.push(`${p.droppedContext.length} bağlam dosyası istek boyutu sınırı nedeniyle çıkarıldı.`);
    if (p.untrackedCount) notes.push(`${p.untrackedCount} izlenmeyen (untracked) dosya dahil değil.`);
    return [
      el('h2', { text: 'Gönderim önizlemesi' }),
      el('p', { class: 'muted', text: 'Onaylamadan hiçbir veri gönderilmez.' }),
      el('dl', { class: 'meta' }, [
        el('dt', { text: 'Klasör' }), el('dd', { text: p.folderName }),
        el('dt', { text: 'Kapsam' }), el('dd', { text: SCOPE[p.scope] }),
        el('dt', { text: 'Base commit' }), el('dd', { text: short(p.baseCommitSha), title: p.baseCommitSha }),
        el('dt', { text: 'Snapshot (diff SHA-256)' }), el('dd', { text: short(p.snapshotId), title: p.snapshotId }),
        el('dt', { text: 'Boyut' }), el('dd', { text: `${(p.bytes / 1024).toFixed(1)} KB` }),
      ]),
      el('section', {}, [
        el('h3', { text: `Gönderilecek dosyalar (${p.files.length})` }),
        el('ul', {}, p.files.map((f) => el('li', { text: `${f.path} (+${f.additions} −${f.deletions})` }))),
      ]),
      p.context.length
        ? el('section', {}, [
            el('h3', { text: 'Bağlam olarak gönderilecek dosya içerikleri' }),
            el('ul', {}, p.context.map((c) => el('li', { text: c.truncated ? `${c.path} (kısaltıldı)` : c.path }))),
          ])
        : null,
      pathList('Hariç tutulanlar', p.excluded, EXCLUDE_REASON),
      pathList('Sınır nedeniyle gönderilmeyecekler', p.omitted, OMIT_REASON),
      notes.length ? el('ul', { class: 'notes' }, notes.map((n) => el('li', { text: n }))) : null,
      el('details', {}, [el('summary', { text: 'Gönderilecek diff içeriği' }), el('pre', { class: 'diff', text: p.diff })]),
      el('div', { class: 'actions' }, [
        button(sendLabel, () => send({ type: 'confirmPreview', previewId: p.previewId }), { class: 'primary' }),
        button('İptal', () => send({ type: 'cancelPreview' }), { class: 'secondary' }),
      ]),
    ];
  }

  function renderEmpty() {
    const e = state.empty;
    return [
      el('h2', { text: 'Gönderilecek değişiklik yok' }),
      el('p', { text: `${SCOPE[e.scope]} kapsamında analiz edilebilir değişiklik bulunamadı.` }),
      e.untrackedCount ? el('p', { class: 'muted', text: `${e.untrackedCount} izlenmeyen dosya var; dahil etmek için git add ile stage edin.` }) : null,
      pathList('Hariç tutulanlar', e.excluded, EXCLUDE_REASON),
      pathList('Sınır nedeniyle gönderilmeyecekler', e.omitted, OMIT_REASON),
      button('Tekrar dene', () => send({ type: 'retry' }), { class: 'primary' }),
    ];
  }

  function renderError() {
    const error = state.error || {};
    return [
      el('h2', { text: state.phase === 'failed' ? 'Analiz tamamlanamadı' : 'Analiz başlatılamadı' }),
      el('p', { role: 'alert', text: error.message || 'Beklenmeyen hata.' }),
      el('p', { class: 'muted', text: `Kod: ${error.code || 'UNKNOWN'}` }),
      button(error.retryable ? 'Tekrar dene' : 'Yeniden başlat', () => send({ type: 'retry' }), { class: 'primary' }),
    ];
  }

  function renderProgress() {
    const status = state.analysis ? state.analysis.status : null;
    return [el('p', { class: 'progress', role: 'status', text: status ? `${STATUS[status] || status}…` : state.phase === 'collecting' ? 'Değişiklikler okunuyor…' : 'Gönderiliyor…' })];
  }

  function renderEvaluation(evaluation) {
    const due = evaluation.due_at ? new Date(evaluation.due_at) : null;
    return el('section', { class: 'evaluation' }, [
      el('p', {}, [el('strong', { text: 'Sonuç: ' }), document.createTextNode(ASSESSMENT[evaluation.assessment_state] || evaluation.assessment_state)]),
      evaluation.uncertain ? el('p', { class: 'banner warn', text: 'Değerlendirme belirsiz; bu sonuç tekrar planını değiştirmez.' }) : null,
      evaluation.rubric_results.length
        ? el('ul', { class: 'rubric' }, evaluation.rubric_results.map((r) => el('li', { text: `${RUBRIC[r.result] || r.result}: ${r.criterion}` })))
        : null,
      el('p', { text: evaluation.feedback }),
      el('p', { class: 'muted', text: due ? `Tekrar tarihi: ${due.toLocaleString('tr-TR', { dateStyle: 'medium', timeStyle: 'short' })}` : 'Tekrar planlanmadı.' }),
      el('p', { class: 'muted small', text: 'Bu sonuç yalnız bu sorunun rubrik değerlendirmesidir; teknoloji sertifikası değildir.' }),
    ]);
  }

  function renderQuestion(question, index) {
    const answer = state.answers[question.id] || { status: 'idle' };
    const submitting = answer.status === 'submitting';
    const fieldId = `answer-${index}`;
    const draftKey = `${state.analysis.id}:${question.id}`;
    const textarea = el('textarea', { id: fieldId, rows: 4, maxlength: 4000, 'aria-describedby': `hint-${index}`, disabled: submitting });
    textarea.value = drafts[draftKey] || '';
    textarea.addEventListener('input', () => {
      drafts[draftKey] = textarea.value;
      persist();
    });
    const submit = () => {
      const text = textarea.value;
      if (!text.trim() || submitting) return;
      send({ type: 'submitAnswer', questionId: question.id, answer: text });
    };
    textarea.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) {
        event.preventDefault();
        submit();
      }
    });
    const form = el('form', {}, [
      el('label', { for: fieldId, text: 'Cevabınız' }),
      textarea,
      el('p', { id: `hint-${index}`, class: 'muted small', text: 'Göndermek için Ctrl/Cmd+Enter.' }),
      el('button', { type: 'submit', class: 'primary', disabled: submitting, 'aria-busy': submitting ? 'true' : null, text: submitting ? 'Gönderiliyor…' : answer.evaluation ? 'Yeniden gönder' : 'Cevabı gönder' }),
    ]);
    form.addEventListener('submit', (event) => {
      event.preventDefault();
      submit();
    });

    return el('article', { class: 'question', 'aria-labelledby': `q-title-${index}` }, [
      el('h3', { id: `q-title-${index}`, text: `${index + 1}. ${question.concept}` }),
      el('p', { text: question.prompt }),
      el('div', { class: 'sources' }, question.sources.map((source, sourceIndex) =>
        button(`${source.path}:${source.start_line}-${source.end_line}`, () => send({ type: 'openSource', questionId: question.id, sourceIndex }), {
          class: 'link',
          title: 'Kaynağı editörde aç',
        }),
      )),
      form,
      answer.status === 'error'
        ? el('p', { class: 'banner error', role: 'alert', text: `Cevap gönderilemedi: ${answer.error.message} Cevabınız korunuyor.` })
        : null,
      answer.evaluation ? renderEvaluation(answer.evaluation) : null,
    ]);
  }

  function renderReady() {
    for (const key of Object.keys(drafts)) {
      if (!key.startsWith(`${state.analysis.id}:`)) delete drafts[key];
    }
    persist();
    return [
      el('h2', { text: 'Sorular' }),
      el('p', { class: 'muted', text: 'Kaynak bağlantıları analiz edilen snapshot’a aittir.' }),
      ...state.analysis.questions.map(renderQuestion),
      el('div', { class: 'actions' }, [button('Yeni analiz', () => send({ type: 'startAnalysis' }), { class: 'secondary' })]),
    ];
  }

  function render() {
    if (!state) return;
    const active = document.activeElement;
    const focusId = active && active.id ? active.id : null;
    const selection = focusId && 'selectionStart' in active ? [active.selectionStart, active.selectionEnd] : null;
    const scrollTop = document.scrollingElement ? document.scrollingElement.scrollTop : 0;

    const body = {
      idle: renderIdle,
      collecting: renderProgress,
      sending: renderProgress,
      polling: renderProgress,
      preview: renderPreview,
      empty: renderEmpty,
      error: renderError,
      failed: renderError,
      ready: renderReady,
    }[state.phase] || renderIdle;

    const children = [modeBanner()];
    if (state.stale) {
      children.push(el('p', { class: 'banner warn', role: 'alert', text: 'Kod bu analizden sonra değişti. Kaynak satırları güncel olmayabilir; yeni analiz önerilir.' }));
    }
    app.replaceChildren(...children, ...body().filter(Boolean));

    if (focusId) {
      const next = document.getElementById(focusId);
      if (next) {
        next.focus();
        if (selection && 'setSelectionRange' in next) next.setSelectionRange(selection[0], selection[1]);
      }
    }
    if (document.scrollingElement) document.scrollingElement.scrollTop = scrollTop;
  }

  window.addEventListener('message', (event) => {
    const message = event.data;
    if (!message || message.type !== 'state' || typeof message.state !== 'object') return;
    state = message.state;
    render();
  });

  send({ type: 'ready' });
})();
