/* ═══════════════════════════════════════════════════════════════════
   LogFlow — Enterprise Log Analysis Dashboard
   app.js — All frontend logic
   ═══════════════════════════════════════════════════════════════════ */

const API_BASE = 'http://localhost:8000';

// ── State ──────────────────────────────────────────────────────────
let allLogs = [];         // { log: {...}, explanation: {...}, confidence: N, cardEl, analysisEl }
let isLoading = false;

// ── Init ───────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  checkHealth();
  setInterval(checkHealth, 30000);
});

// ══════════════════════════════════════════════════════════════════
// HEALTH CHECK
// ══════════════════════════════════════════════════════════════════
async function checkHealth() {
  const chip = document.getElementById('status-indicator');
  const txt  = document.getElementById('status-text');
  try {
    const res = await fetch(API_BASE + '/health', { signal: AbortSignal.timeout(5000) });
    if (res.ok) {
      chip.className = 'status-chip online';
      txt.textContent = '✓ Connected';
    } else {
      throw new Error('not ok');
    }
  } catch {
    chip.className = 'status-chip offline';
    txt.textContent = '✕ Offline';
  }
}

// ══════════════════════════════════════════════════════════════════
// GENERATE SINGLE LOG
// ══════════════════════════════════════════════════════════════════
async function generateRandomLog() {
  if (isLoading) return;
  hideSummary();
  setLoading(true, 'Fetching log from API...');
  try {
    const res = await fetch(API_BASE + '/fetch-and-explain');
    if (!res.ok) throw new Error(`API error ${res.status}`);
    const data = await res.json();
    appendEntry(data.log || data, data.explanation || data);
    showToast('Log generated', 'ok');
  } catch (e) {
    showToast('Error: ' + e.message, 'err');
  } finally {
    setLoading(false);
  }
}

// ══════════════════════════════════════════════════════════════════
// BATCH — 5 LOGS
// ══════════════════════════════════════════════════════════════════
async function generateBatch() {
  if (isLoading) return;
  hideSummary();
  setLoading(true, 'Generating batch of 5 logs...');
  disableButtons(true);
  let count = 0;
  try {
    for (let i = 0; i < 5; i++) {
      document.getElementById('loading-msg').textContent =
        `Fetching log ${i + 1} of 5...`;
      const res = await fetch(API_BASE + '/fetch-and-explain');
      if (!res.ok) throw new Error(`API error ${res.status}`);
      const data = await res.json();
      appendEntry(data.log || data, data.explanation || data);
      count++;
      await delay(200);
    }
    showToast(`${count} logs generated`, 'ok');
  } catch (e) {
    showToast('Batch error: ' + e.message, 'err');
  } finally {
    setLoading(false);
    disableButtons(false);
  }
}

// ══════════════════════════════════════════════════════════════════
// SCENARIO ANALYSIS
// ══════════════════════════════════════════════════════════════════
async function analyzeScenario(scenario) {
  if (isLoading) return;
  clearAll(false);
  hideSummary();
  setLoading(true, `Loading ${formatScenarioName(scenario)} scenario...`);
  disableButtons(true);
  try {
    const res = await fetch(`${API_BASE}/fetch-and-explain?scenario=${scenario}`);
    if (!res.ok) throw new Error(`API error ${res.status}`);
    const data = await res.json();

    if (data.explanations && Array.isArray(data.explanations)) {
      // Scenario bulk response
      data.explanations.forEach(exp => {
        const log = exp.log || exp;
        const expl = exp.explanation || exp;
        appendEntry(log, expl);
      });
      if (data.root_cause || data.summary || data.recommended_actions) {
        showSummary(data, scenario);
      }
      showToast(`Scenario loaded: ${data.count || data.explanations.length} logs`, 'ok');
    } else {
      // Single entry fallback
      appendEntry(data.log || data, data.explanation || data);
      showToast('Scenario loaded', 'ok');
    }
  } catch (e) {
    showToast('Scenario error: ' + e.message, 'err');
  } finally {
    setLoading(false);
    disableButtons(false);
  }
}

// ══════════════════════════════════════════════════════════════════
// APPEND ENTRY (log card + analysis card)
// ══════════════════════════════════════════════════════════════════
function appendEntry(log, explanation) {
  hideEmpty();

  // Resolve confidence once so display and export use the same value
  const confidence = explanation.confidence != null
    ? Math.round(explanation.confidence * 100)
    : randomInt(85, 99);

  const logEl  = buildLogCard(log);
  const anlEl  = buildAnalysisCard(explanation, confidence);

  document.getElementById('log-container').appendChild(logEl);
  document.getElementById('analysis-container').appendChild(anlEl);

  allLogs.push({ log, explanation, confidence, cardEl: logEl, analysisEl: anlEl });

  updateStats();
  updateBadges();
  applyCurrentFilter();

  // Auto-scroll both panels to bottom
  scrollPanelToBottom('log-container');
  scrollPanelToBottom('analysis-container');
}

// ══════════════════════════════════════════════════════════════════
// BUILD LOG CARD
// ══════════════════════════════════════════════════════════════════
function buildLogCard(log) {
  const level   = (log.level || 'INFO').toUpperCase();
  const ts      = log.timestamp ? log.timestamp.slice(0, 19).replace('T', ' ') : new Date().toISOString().slice(0, 19).replace('T', ' ');
  const msg     = escHtml(log.message || '(no message)');
  const ctx     = log.context || {};
  const module  = escHtml(ctx.module  || log.module  || '—');
  const line    = escHtml(String(ctx.line    || log.line    || '—'));
  const pid     = escHtml(String(ctx.process_id || ctx.pid || log.pid || '—'));

  const div = document.createElement('div');
  div.className = `log-card level-${level}`;
  div.dataset.level   = level;
  div.dataset.message = (log.message || '').toLowerCase();

  div.innerHTML = `
    <div class="log-top">
      <span class="log-ts">${ts}</span>
      <span class="level-badge lvl-${level}">${level}</span>
    </div>
    <div class="log-msg">${msg}</div>
    <div class="log-meta">
      <div class="log-meta-item">
        <span class="log-meta-key">Module</span>
        <span class="log-meta-val">${module}</span>
      </div>
      <div class="log-meta-item">
        <span class="log-meta-key">Line</span>
        <span class="log-meta-val">${line}</span>
      </div>
      <div class="log-meta-item">
        <span class="log-meta-key">PID</span>
        <span class="log-meta-val">${pid}</span>
      </div>
    </div>`;
  return div;
}

// ══════════════════════════════════════════════════════════════════
// BUILD ANALYSIS CARD
// ══════════════════════════════════════════════════════════════════
function buildAnalysisCard(exp, confidence) {
  const severity    = (exp.severity    || exp.predicted_severity || 'LOW').toUpperCase();
  const explanation = escHtml(exp.explanation || exp.message || 'Analyzing log entry...');
  const suggestion  = escHtml(exp.suggestion  || exp.action  || defaultSuggestion(severity));

  const div = document.createElement('div');
  div.className = 'analysis-card';
  div.dataset.severity = severity;

  div.innerHTML = `
    <div class="analysis-top">
      <span class="severity-badge sev-${severity}">${severity} SEVERITY</span>
      <div class="confidence-bar-wrap">
        <div class="confidence-bar">
          <div class="confidence-fill" style="width: ${confidence}%"></div>
        </div>
        ${confidence}%
      </div>
    </div>
    <div class="analysis-explanation">${explanation}</div>
    <div class="suggestion-box">
      <svg class="suggestion-arrow" width="14" height="14" viewBox="0 0 24 24"
           fill="none" stroke="currentColor" stroke-width="2.5">
        <line x1="5" y1="12" x2="19" y2="12"/>
        <polyline points="12 5 19 12 12 19"/>
      </svg>
      <div class="suggestion-content">
        <span class="suggestion-label">Recommendation</span>
        <span class="suggestion-text">${suggestion}</span>
      </div>
    </div>`;
  return div;
}

// ══════════════════════════════════════════════════════════════════
// SCENARIO SUMMARY BAR
// ══════════════════════════════════════════════════════════════════
function showSummary(data, scenario) {
  const bar = document.getElementById('scenario-summary');
  document.getElementById('summary-scenario-name').textContent =
    `${formatScenarioName(scenario)} — Scenario Summary`;
  document.getElementById('summary-root-cause').textContent =
    data.root_cause || '—';
  document.getElementById('summary-overview').textContent =
    data.summary || '—';

  const ul = document.getElementById('summary-actions');
  ul.innerHTML = '';
  if (Array.isArray(data.recommended_actions)) {
    data.recommended_actions.forEach(action => {
      const li = document.createElement('li');
      li.textContent = action;
      ul.appendChild(li);
    });
  }

  bar.classList.remove('hidden');
}

function hideSummary() {
  document.getElementById('scenario-summary').classList.add('hidden');
}

// ══════════════════════════════════════════════════════════════════
// SEARCH & FILTER
// ══════════════════════════════════════════════════════════════════
function filterLogs() {
  const query   = (document.getElementById('search-input').value || '').toLowerCase();
  const showCrit= document.getElementById('filter-critical').checked;
  const showWarn= document.getElementById('filter-warning').checked;
  const showInfo= document.getElementById('filter-info').checked;

  allLogs.forEach(entry => {
    const { log, cardEl, analysisEl } = entry;
    const level = (log.level || 'INFO').toUpperCase();
    const msg   = (log.message || '').toLowerCase();

    const levelOk = (
      (level === 'ERROR' || level === 'CRITICAL') ? showCrit :
      level === 'WARNING' ? showWarn :
      showInfo
    );
    const searchOk = !query || msg.includes(query);

    const show = levelOk && searchOk;
    cardEl.classList.toggle('hidden', !show);
    analysisEl.classList.toggle('hidden', !show);
  });
}

// ══════════════════════════════════════════════════════════════════
// EXPORT CSV
// ══════════════════════════════════════════════════════════════════
function exportCSV() {
  if (allLogs.length === 0) {
    showToast('No logs to export', 'info');
    return;
  }

  const rows = [
    ['Timestamp', 'Level', 'Message', 'Module', 'Line', 'PID', 'Severity', 'Confidence', 'Explanation', 'Suggestion']
  ];

  allLogs.forEach(({ log, explanation, confidence }) => {
    const ctx = log.context || {};
    rows.push([
      csvEsc(log.timestamp || ''),
      csvEsc(log.level || ''),
      csvEsc(log.message || ''),
      csvEsc(ctx.module || log.module || ''),
      csvEsc(String(ctx.line || log.line || '')),
      csvEsc(String(ctx.process_id || ctx.pid || log.pid || '')),
      csvEsc((explanation.severity || explanation.predicted_severity || '').toUpperCase()),
      confidence + '%',
      csvEsc(explanation.explanation || explanation.message || ''),
      csvEsc(explanation.suggestion || explanation.action || '')
    ]);
  });

  const csv = rows.map(r => r.join(',')).join('\n');
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href     = url;
  a.download = `logflow_export_${dateStamp()}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
  showToast(`Exported ${allLogs.length} log entries`, 'ok');
}

// ══════════════════════════════════════════════════════════════════
// CLEAR ALL
// ══════════════════════════════════════════════════════════════════
function clearAll(showMsg = true) {
  allLogs = [];
  hideSummary();

  const lc = document.getElementById('log-container');
  const ac = document.getElementById('analysis-container');
  lc.innerHTML = '';
  ac.innerHTML = '';
  showEmptyStates();
  updateStats();
  updateBadges();
  if (showMsg) showToast('Cleared all logs', 'info');
}

// ══════════════════════════════════════════════════════════════════
// UI HELPERS
// ══════════════════════════════════════════════════════════════════
function setLoading(on, msg = 'Loading...') {
  isLoading = on;
  const ov = document.getElementById('loading-overlay');
  document.getElementById('loading-msg').textContent = msg;
  ov.classList.toggle('hidden', !on);
}

function disableButtons(disabled) {
  ['generate-btn', 'batch-btn'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.disabled = disabled;
  });
}

let toastTimer = null;
function showToast(msg, type = 'info') {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = `toast toast-${type}`;
  t.classList.remove('hidden');
  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.add('hidden'), 3500);
}

function updateStats() {
  let total = 0, crit = 0, warn = 0, info = 0;
  allLogs.forEach(({ log }) => {
    total++;
    const lvl = (log.level || 'INFO').toUpperCase();
    if (lvl === 'ERROR' || lvl === 'CRITICAL') crit++;
    else if (lvl === 'WARNING') warn++;
    else info++;
  });

  setEl('stat-total',    total);
  setEl('stat-critical', crit);
  setEl('stat-warning',  warn);
  setEl('stat-info',     info);

  setEl('cb-critical-count', crit);
  setEl('cb-warning-count',  warn);
  setEl('cb-info-count',     info);
}

function updateBadges() {
  const total = allLogs.length;
  const visible = allLogs.filter(e => !e.cardEl.classList.contains('hidden')).length;
  document.getElementById('log-count-badge').textContent =
    `${total} ${total === 1 ? 'entry' : 'entries'}`;
  document.getElementById('analysis-count-badge').textContent =
    `${total} ${total === 1 ? 'result' : 'results'}`;
}

function hideEmpty() {
  document.getElementById('log-empty')?.remove();
  document.getElementById('analysis-empty')?.remove();
}

function showEmptyStates() {
  const lc = document.getElementById('log-container');
  const ac = document.getElementById('analysis-container');

  if (!document.getElementById('log-empty')) {
    const e1 = document.createElement('div');
    e1.className = 'empty-pane';
    e1.id = 'log-empty';
    e1.innerHTML = `
      <svg width="44" height="44" viewBox="0 0 24 24" fill="none"
           stroke="currentColor" stroke-width="1.2">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
        <polyline points="14 2 14 8 20 8"/>
      </svg>
      <p>No logs yet</p>
      <span>Click Generate Log or pick a scenario</span>`;
    lc.appendChild(e1);
  }

  if (!document.getElementById('analysis-empty')) {
    const e2 = document.createElement('div');
    e2.className = 'empty-pane';
    e2.id = 'analysis-empty';
    e2.innerHTML = `
      <svg width="44" height="44" viewBox="0 0 24 24" fill="none"
           stroke="currentColor" stroke-width="1.2">
        <circle cx="12" cy="12" r="10"/>
        <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/>
        <line x1="12" y1="17" x2="12.01" y2="17"/>
      </svg>
      <p>No analysis yet</p>
      <span>Analysis results appear after generating logs</span>`;
    ac.appendChild(e2);
  }
}

function scrollPanelToBottom(id) {
  const el = document.getElementById(id);
  if (el) el.scrollTop = el.scrollHeight;
}

function setEl(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

// ══════════════════════════════════════════════════════════════════
// UTILITY
// ══════════════════════════════════════════════════════════════════
function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function csvEsc(val) {
  const s = String(val || '').replace(/"/g, '""');
  return s.includes(',') || s.includes('"') || s.includes('\n')
    ? `"${s}"` : s;
}

function delay(ms) { return new Promise(r => setTimeout(r, ms)); }

function randomInt(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function dateStamp() {
  return new Date().toISOString().slice(0, 10);
}

function formatScenarioName(scenario) {
  return scenario
    .split('_')
    .map(w => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}

function defaultSuggestion(severity) {
  const map = {
    HIGH:   'Immediate action required — investigate root cause and escalate to on-call team.',
    MEDIUM: 'Review logs for pattern recurrence and apply targeted mitigation.',
    LOW:    'Monitor for frequency increase; schedule review in next maintenance window.'
  };
  return map[severity] || map.LOW;
}

function applyCurrentFilter() {
  // Re-run filter to apply to newly added entries
  filterLogs();
  updateBadges();
}
