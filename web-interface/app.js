/* Log Explainer dashboard logic. */

const API_BASE = window.API_BASE || `${location.protocol}//${location.hostname || 'localhost'}:8000`;

const SCENARIO_NAMES = {
  database_failure: 'Database failure',
  auth_breach: 'Brute-force login',
  memory_leak: 'Memory leak',
  api_overload: 'API overload',
  disk_failure: 'Disk failure',
  redis_cache_stampede: 'Cache stampede',
};

const SAMPLE_PASTE = [
  '2026-10-26T09:58:02Z INFO Request processed in 145ms: GET /api/orders',
  '2026-10-26T09:58:40Z WARN Connection pool near capacity: 48/50 connections in use',
  '2026-10-26T09:59:05Z WARN Slow query detected: SELECT took 3.2 seconds',
  '2026-10-26T09:59:31Z ERROR Database connection timeout after 30 seconds',
  '2026-10-26T09:59:32Z ERROR Deadlock detected in transaction processing',
  '2026-10-26T10:00:10Z ERROR Critical service dependency unavailable: database',
  '2026-10-26T10:00:12Z WARN Switching to degraded mode: read-only cache serving',
].join('\n');

const state = {
  entries: [],        // { log, a }
  incident: null,
  source: null,       // { kind: 'scenario' | 'random' | 'paste', scenario? }
  filter: 'ALL',
  query: '',
  openIndex: null,
  keyLines: new Set(),
  busy: false,
  llmAvailable: false,
};

const $ = (id) => document.getElementById(id);

document.addEventListener('DOMContentLoaded', () => {
  bind();
  checkServices();
  setInterval(checkServices, 20000);
});

function bind() {
  document.querySelectorAll('[data-scenario]').forEach((b) =>
    b.addEventListener('click', () => runScenario(b.dataset.scenario)));
  $('btn-random').addEventListener('click', () => addRandom(1));
  $('btn-batch').addEventListener('click', () => addRandom(10));
  $('btn-paste').addEventListener('click', openPaste);
  $('empty-paste').addEventListener('click', openPaste);
  $('paste-close').addEventListener('click', () => { $('paste-panel').hidden = true; });
  $('paste-sample').addEventListener('click', () => { $('paste-input').value = SAMPLE_PASTE; $('paste-input').focus(); });
  $('paste-run').addEventListener('click', runPaste);
  $('paste-input').addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) runPaste();
  });
  $('btn-llm').addEventListener('click', explainWithLLM);
  $('btn-export').addEventListener('click', exportCSV);
  $('btn-clear').addEventListener('click', () => { clearAll(); toast('Cleared'); });
  $('search').addEventListener('input', (e) => { state.query = e.target.value.trim().toLowerCase(); renderRows(); });
  document.querySelectorAll('.seg-btn').forEach((b) => b.addEventListener('click', () => {
    state.filter = b.dataset.sev;
    document.querySelectorAll('.seg-btn').forEach((x) => x.setAttribute('aria-pressed', String(x === b)));
    renderRows();
  }));
}

// ── Services ────────────────────────────────────────────────────────
async function checkServices() {
  let health = null;
  try {
    const res = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(4000) });
    if (res.ok) health = await res.json();
  } catch { /* offline */ }
  setSvc('svc-api', health ? 'up' : 'down');

  if (health) {
    try {
      const gen = await fetch(`${API_BASE}/scenarios`, { signal: AbortSignal.timeout(4000) });
      setSvc('svc-gen', gen.ok ? 'up' : 'down');
    } catch { setSvc('svc-gen', 'down'); }
  } else {
    setSvc('svc-gen', 'down');
  }

  state.llmAvailable = Boolean(health && health.llm_available);
  setSvc('svc-llm', state.llmAvailable ? 'up' : 'off');
  $('svc-llm-label').textContent = state.llmAvailable ? `LLM: ${health.llm_model}` : 'LLM off';
  $('btn-llm').disabled = !state.llmAvailable;
  $('btn-llm').title = state.llmAvailable ? '' : 'Set GROQ_API_KEY in .env and restart to enable';
}

function setSvc(id, s) { $(id).dataset.state = s; }

// ── Data loading ────────────────────────────────────────────────────
async function api(path, options) {
  let res;
  try {
    res = await fetch(`${API_BASE}${path}`, options);
  } catch {
    throw new Error('Cannot reach the explainer API on port 8000. Is ./run_local.sh running?');
  }
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.detail || `Request failed (${res.status})`);
  return body;
}

const post = (path, data) => api(path, {
  method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
});

async function withBusy(el, fn) {
  if (state.busy) return;
  state.busy = true;
  const controls = document.querySelectorAll('.scenario, .side-actions .btn, #paste-run, .empty-actions .btn');
  controls.forEach((c) => { c.disabled = true; });
  if (el) el.setAttribute('aria-busy', 'true');
  try { await fn(); } catch (e) { toast(e.message, 'err'); } finally {
    state.busy = false;
    controls.forEach((c) => { c.disabled = false; });
    if (el) el.removeAttribute('aria-busy');
  }
}

function runScenario(name) {
  const btn = document.querySelector(`.scenario[data-scenario="${name}"]`);
  return withBusy(btn, async () => {
    const data = await api(`/fetch-and-explain?scenario=${encodeURIComponent(name)}`);
    loadBatch(data, { kind: 'scenario', scenario: name });
    markScenario(name);
  });
}

function addRandom(count) {
  const btn = count > 1 ? $('btn-batch') : $('btn-random');
  return withBusy(btn, async () => {
    const data = await api(`/fetch-and-explain?count=${count}`);
    const fresh = data.explanations
      ? data.explanations.map((e) => ({ log: e.log, a: e.explanation }))
      : [{ log: data.log, a: data.explanation }];
    const keep = state.source && state.source.kind === 'random' ? state.entries : [];
    const all = keep.concat(fresh);
    const batch = await post('/explain-batch', { logs: all.map((e) => e.log) });
    loadBatch(batch, { kind: 'random' }, keep.length);
    markScenario(null);
  });
}

function openPaste() {
  $('paste-panel').hidden = false;
  $('paste-input').focus();
}

function runPaste() {
  const text = $('paste-input').value;
  if (!text.trim()) { toast('Paste at least one log line first', 'err'); return; }
  return withBusy($('paste-run'), async () => {
    const data = await post('/analyze-text', { text });
    loadBatch(data, { kind: 'paste' });
    markScenario(null);
    $('paste-panel').hidden = true;
  });
}

function loadBatch(data, source, newFrom = 0) {
  state.entries = data.explanations.map((e) => ({ log: e.log, a: e.explanation }));
  state.incident = data.incident;
  state.source = source;
  state.openIndex = null;
  state.keyLines = new Set();
  resetLLM();
  renderIncident();
  renderRows(newFrom);
}

function markScenario(name) {
  document.querySelectorAll('.scenario').forEach((b) =>
    b.setAttribute('aria-current', String(b.dataset.scenario === name)));
}

function clearAll() {
  state.entries = [];
  state.incident = null;
  state.source = null;
  state.keyLines = new Set();
  markScenario(null);
  resetLLM();
  renderIncident();
  renderRows();
}

// ── Incident panel ──────────────────────────────────────────────────
function incidentTitle() {
  const s = state.source;
  if (!s) return 'Incident';
  if (s.kind === 'scenario') return SCENARIO_NAMES[s.scenario] || s.scenario;
  if (s.kind === 'paste') return 'Pasted logs';
  return 'Random log sample';
}

function renderIncident() {
  const inc = state.incident;
  $('incident').hidden = !inc || !state.entries.length;
  if (!inc || !state.entries.length) return;

  $('inc-title').textContent = incidentTitle();
  const src = state.source.kind === 'paste' ? 'from pasted text' : 'generated by the log generator';
  $('inc-sub').textContent = `${state.entries.length} lines ${src}. Click any bar or row to see why it was rated that way.`;

  const pill = $('inc-status');
  pill.dataset.status = inc.status;
  pill.textContent = { critical: 'Critical', degraded: 'Degraded', stable: 'Stable' }[inc.status];

  $('inc-health').textContent = inc.health_score;
  $('inc-high').textContent = inc.severity_counts.HIGH;
  $('inc-med').textContent = inc.severity_counts.MEDIUM;
  $('inc-low').textContent = inc.severity_counts.LOW;
  $('inc-duration').textContent = formatDuration(inc.duration_seconds);
  $('inc-category').textContent = inc.category_label;
  $('inc-category').title = inc.category_label;
  $('inc-root').textContent = inc.root_cause;
  fillList($('inc-actions'), inc.recommended_actions);

  renderTimeline();
}

function renderTimeline() {
  const tl = $('timeline');
  tl.replaceChildren(...state.entries.map((e, i) => {
    const t = document.createElement('button');
    t.className = 'tick' + (state.keyLines.has(i) ? ' is-key' : '');
    t.dataset.sev = e.a.severity;
    t.setAttribute('role', 'listitem');
    t.title = `#${i + 1} ${e.a.severity}: ${e.log.message}`;
    t.setAttribute('aria-label', t.title);
    t.addEventListener('click', () => openRow(i));
    return t;
  }));
  const first = state.entries[0].log.timestamp;
  const last = state.entries[state.entries.length - 1].log.timestamp;
  const range = $('timeline-range');
  range.textContent = first && last ? `${formatTime(first)} to ${formatTime(last)}` : '';
  if (state.keyLines.size) range.append(el('span', 'key-legend', 'Key lines picked by the LLM'));
}

// ── LLM ─────────────────────────────────────────────────────────────
function resetLLM() {
  $('llm-model').textContent = '';
  $('llm-body').replaceChildren(Object.assign(document.createElement('p'), {
    className: 'muted',
    textContent: state.llmAvailable
      ? 'Ask the LLM to read these lines and explain the incident in plain language.'
      : 'LLM is off. Add GROQ_API_KEY to .env and restart to enable it. The rule-based result above works without it.',
  }));
  $('btn-llm').hidden = false;
}

async function explainWithLLM() {
  if (!state.entries.length) return;
  const btn = $('btn-llm');
  const body = $('llm-body');
  btn.disabled = true;
  btn.setAttribute('aria-busy', 'true');
  body.innerHTML = '<div class="skeleton" aria-label="Waiting for the LLM"><span></span><span></span><span></span></div>';
  try {
    const r = await post('/explain-incident-llm', {
      logs: state.entries.map((e) => e.log),
      scenario: state.source && state.source.scenario,
    });
    const title = el('p', 'llm-title', r.title);
    const summary = el('p', '', r.summary);
    const rc = el('p', '', `Root cause: ${r.root_cause}`);
    const list = document.createElement('ol');
    fillList(list, r.recommended_actions);
    body.replaceChildren(title, summary, rc, list);
    $('llm-model').textContent = r.model;
    state.keyLines = new Set(r.key_lines || []);
    renderTimeline();
    renderRows();
    btn.hidden = true;
  } catch (e) {
    body.replaceChildren(el('p', 'llm-error', e.message));
  } finally {
    btn.disabled = !state.llmAvailable;
    btn.removeAttribute('aria-busy');
  }
}

// ── Rows ────────────────────────────────────────────────────────────
function visible(e) {
  if (state.filter !== 'ALL' && e.a.severity !== state.filter) return false;
  return !state.query || (e.log.message || '').toLowerCase().includes(state.query);
}

function renderRows(newFrom = Infinity) {
  const rows = $('rows');
  const counts = { HIGH: 0, MEDIUM: 0, LOW: 0 };
  state.entries.forEach((e) => { counts[e.a.severity]++; });
  $('f-high').textContent = counts.HIGH;
  $('f-med').textContent = counts.MEDIUM;
  $('f-low').textContent = counts.LOW;

  const shown = state.entries.map((e, i) => [e, i]).filter(([e]) => visible(e));
  $('log-count').textContent = shown.length === state.entries.length
    ? state.entries.length : `${shown.length} of ${state.entries.length}`;
  document.querySelector('.logs').classList.toggle('has-rows', state.entries.length > 0);

  rows.replaceChildren(...shown.map(([e, i]) => buildRow(e, i, i >= newFrom)));
  if (state.entries.length && !shown.length) {
    rows.replaceChildren(el('p', 'muted', 'No lines match this filter.'));
    rows.firstChild.style.padding = '20px 16px';
  }
}

function buildRow(e, i, isNew) {
  const { log, a } = e;
  const row = document.createElement('div');
  row.className = 'row' + (isNew ? ' is-new' : '') + (state.keyLines.has(i) ? ' is-key' : '');
  row.id = `row-${i}`;
  row.dataset.open = String(state.openIndex === i);
  row.setAttribute('role', 'row');

  const main = document.createElement('button');
  main.className = 'tr row-main';
  main.setAttribute('aria-expanded', String(state.openIndex === i));
  main.innerHTML = `
    <span class="c-time" role="cell">${esc(formatTime(log.timestamp) || '--')}</span>
    <span class="c-level" role="cell" data-level="${esc(log.level)}">${esc(log.level)}</span>
    <span class="c-msg" role="cell"><svg class="ic"><use href="#i-chevron"/></svg><span>${esc(log.message)}</span></span>
    <span class="c-cat" role="cell">${esc(a.category_label)}</span>
    <span role="cell"><span class="sev" data-sev="${a.severity}">${titleCase(a.severity)}</span></span>
    <span class="conf" role="cell"><span class="conf-bar"><i style="width:${Math.round(a.confidence * 100)}%"></i></span>${Math.round(a.confidence * 100)}%</span>`;
  main.addEventListener('click', () => toggleRow(i));
  row.appendChild(main);

  if (state.openIndex === i) row.appendChild(buildDetail(log, a));
  return row;
}

function buildDetail(log, a) {
  const ctx = log.context || {};
  const d = document.createElement('div');
  d.className = 'detail';
  const signals = a.signals.length
    ? a.signals.map((s) => `<span class="chip">${esc(s)}</span>`).join('')
    : '<span class="muted">No known pattern words</span>';
  const meta = [
    ['Module', ctx.module], ['Line', ctx.line], ['PID', ctx.process_id], ['Thread', ctx.thread_id],
    ['Request', log.request_id], ['Risk score', a.risk_score],
  ].filter(([, v]) => v !== undefined && v !== null && v !== '');
  d.innerHTML = `
    <div>
      <p class="full-msg">${esc(log.message)}</p>
      <h4>Explanation</h4>
      <p>${esc(a.explanation)}</p>
      <h4 style="margin-top:10px">Suggested next step</h4>
      <p>${esc(a.suggestion)}</p>
    </div>
    <div class="detail-side">
      <div><h4>Matched signals</h4><div class="chips">${signals}</div></div>
      <dl class="meta">${meta.map(([k, v]) => `<dt>${k}</dt><dd>${esc(String(v))}</dd>`).join('')}</dl>
    </div>`;
  return d;
}

function toggleRow(i) {
  state.openIndex = state.openIndex === i ? null : i;
  renderRows();
}

function openRow(i) {
  if (!visible(state.entries[i])) {
    state.filter = 'ALL';
    state.query = '';
    $('search').value = '';
    document.querySelectorAll('.seg-btn').forEach((x) => x.setAttribute('aria-pressed', String(x.dataset.sev === 'ALL')));
  }
  state.openIndex = i;
  renderRows();
  const row = $(`row-${i}`);
  row.scrollIntoView({ behavior: 'smooth', block: 'center' });
  row.querySelector('.row-main').focus({ preventScroll: true });
}

// ── Export ──────────────────────────────────────────────────────────
function exportCSV() {
  if (!state.entries.length) { toast('Nothing to export yet'); return; }
  const head = ['Timestamp', 'Level', 'Message', 'Module', 'Category', 'Severity', 'Confidence', 'Signals', 'Explanation', 'Suggestion'];
  const lines = state.entries.map(({ log, a }) => [
    log.timestamp, log.level, log.message, (log.context || {}).module || '',
    a.category_label, a.severity, a.confidence, a.signals.join(' '), a.explanation, a.suggestion,
  ].map(csv).join(','));
  const blob = new Blob([[head.join(','), ...lines].join('\n')], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = Object.assign(document.createElement('a'), { href: url, download: `log-explainer-${new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-')}.csv` });
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
  toast(`Exported ${state.entries.length} lines`);
}

// ── Helpers ─────────────────────────────────────────────────────────
function el(tag, cls, text) {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  n.textContent = text;
  return n;
}

function fillList(list, items) {
  list.replaceChildren(...(items || []).map((t) => el('li', '', t)));
}

function esc(s) {
  return String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function csv(v) {
  const s = String(v ?? '');
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

function titleCase(s) { return s.charAt(0) + s.slice(1).toLowerCase(); }

function formatTime(ts) {
  if (!ts) return '';
  const m = String(ts).match(/T?(\d{2}:\d{2}:\d{2})/);
  return m ? m[1] : '';
}

function formatDuration(sec) {
  if (sec == null) return 'n/a';
  if (sec < 60) return `${Math.round(sec)}s`;
  const m = Math.floor(sec / 60);
  return `${m}m ${Math.round(sec % 60)}s`;
}

let toastTimer;
function toast(msg, type = 'ok') {
  const t = $('toast');
  t.textContent = msg;
  t.dataset.type = type;
  t.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { t.hidden = true; }, type === 'err' ? 6000 : 2500);
}
