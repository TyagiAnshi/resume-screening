/* ═══════════════════════════════════════════════════════════════════════════
   ResumeIQ — Frontend Application Logic
   API base: http://localhost:8000
═══════════════════════════════════════════════════════════════════════════ */

const API = 'http://localhost:8000';

// ── State ─────────────────────────────────────────────────────────────────────
const state = {
  dimensions: [],
  candidates: {},        // candidate_id → evaluation result
  activeCandidateId: null,
  noteTimers: {},        // candidate_id → debounce timer
};

// ── DOM helper ────────────────────────────────────────────────────────────────
const $ = id => document.getElementById(id);

// ── Step navigation ───────────────────────────────────────────────────────────
const panels = {
  1: $('panel-jd'),
  2: $('panel-cvs'),
  3: $('panel-results'),
};
const stepEls = [null, $('step-indicator-1'), $('step-indicator-2'), $('step-indicator-3')];

function goToStep(n) {
  Object.values(panels).forEach(p => p.style.display = 'none');
  panels[n].style.display = 'flex';
  stepEls.forEach((el, i) => {
    if (!el) return;
    el.classList.remove('active', 'completed');
    if (i < n) el.classList.add('completed');
    if (i === n) el.classList.add('active');
  });
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ── Toast notifications ───────────────────────────────────────────────────────
function toast(msg, type = 'info', ms = 3500) {
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.textContent = msg;
  $('toast-container').appendChild(el);
  setTimeout(() => el.remove(), ms);
}

// ── Upload zone wiring ────────────────────────────────────────────────────────
function wireUpload(zoneId, inputId, filenameId, btnId, onFile) {
  const zone  = $(zoneId);
  const input = $(inputId);
  const fname = $(filenameId);
  const btn   = $(btnId);

  const pick = file => {
    fname.textContent = `📄 ${file.name}`;
    fname.style.display = 'inline-block';
    zone.classList.add('has-file');
    btn.disabled = false;
    onFile(file);
  };

  zone.addEventListener('click', () => input.click());
  zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('drag-over'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
  zone.addEventListener('drop', e => {
    e.preventDefault(); zone.classList.remove('drag-over');
    if (e.dataTransfer.files[0]) pick(e.dataTransfer.files[0]);
  });
  input.addEventListener('change', () => { if (input.files[0]) pick(input.files[0]); });
}

// ── Utility ───────────────────────────────────────────────────────────────────
function esc(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}

function scoreColor(s) {
  return s >= 7.5 ? '#34d399' : s >= 5 ? '#fcd34d' : '#fb7185';
}

function scoreGrad(s) {
  return s >= 7.5
    ? 'linear-gradient(90deg,#10b981,#34d399)'
    : s >= 5
    ? 'linear-gradient(90deg,#f59e0b,#fcd34d)'
    : 'linear-gradient(90deg,#f43f5e,#fb7185)';
}

function recLabel(r) {
  return { STRONG_YES:'⭐ Strong Yes', YES:'✓ Yes', MAYBE:'~ Maybe', NO:'✗ No' }[r] || r || '—';
}

function setLoading(which, on) {
  const spinner = $(`${which}-loading`);
  const btn = $(which === 'jd' ? 'btn-analyze-jd' : 'btn-evaluate-cv');
  if (spinner) spinner.style.display = on ? 'flex' : 'none';
  if (btn) btn.disabled = on;
}

function showError(id, msg) {
  const el = $(id);
  el.textContent = `Error: ${msg}`;
  el.style.display = 'block';
}

// ═══════════════════════════════════════════════════════════════════════════
// STEP 1 — JD Analysis
// ═══════════════════════════════════════════════════════════════════════════

let jdFile = null;
wireUpload('jd-upload-zone', 'jd-file-input', 'jd-filename', 'btn-analyze-jd', f => {
  jdFile = f;
  $('jd-error').style.display = 'none';
});

$('btn-analyze-jd').addEventListener('click', async () => {
  if (!jdFile) return;
  setLoading('jd', true);
  $('jd-error').style.display = 'none';

  try {
    const fd = new FormData();
    fd.append('file', jdFile);
    const res = await fetch(`${API}/api/analyze-jd`, { method: 'POST', body: fd });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'JD analysis failed');

    state.dimensions = data.dimensions;
    renderDimensions(data.dimensions);
    $('dimensions-panel').style.display = 'flex';
    stepEls[1].classList.add('completed');
    toast(`✦ ${data.dimension_count} evaluation dimensions derived`, 'success');

  } catch (e) {
    showError('jd-error', e.message);
  } finally {
    setLoading('jd', false);
  }
});

$('btn-go-to-cvs').addEventListener('click', () => goToStep(2));
$('btn-download-ranking').addEventListener('click', () => window.open(`${API}/api/ranking-file`, '_blank'));

function renderDimensions(dims) {
  const grid = $('dimensions-grid');
  grid.innerHTML = '';
  dims.forEach((dim, i) => {
    const card = document.createElement('div');
    card.className = 'dim-card';
    card.style.animationDelay = `${i * 55}ms`;
    card.innerHTML = `
      <div class="dim-card-header">
        <span class="dim-name">${esc(dim.name)}</span>
        <div class="dim-badges">
          <span class="dim-weight weight-${Math.min(5,Math.max(1,dim.weight))}" title="Weight ${dim.weight}/5">W${dim.weight}</span>
          ${dim.disqualifying ? '<span class="dim-ko" title="Knockout criterion">KO</span>' : ''}
        </div>
      </div>
      <p class="dim-desc">${esc(dim.description)}</p>
      <div class="dim-signals"><strong>Look for:</strong>${esc(dim.what_to_look_for)}</div>
    `;
    grid.appendChild(card);
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// STEP 2 — CV Evaluation
// ═══════════════════════════════════════════════════════════════════════════

let cvFile = null;
wireUpload('cv-upload-zone', 'cv-file-input', 'cv-filename', 'btn-evaluate-cv', f => {
  cvFile = f;
  $('cv-error').style.display = 'none';
  $('cv-result-preview').style.display = 'none';
});

$('btn-evaluate-cv').addEventListener('click', async () => {
  if (!cvFile) return;
  if (!state.dimensions.length) { toast('Analyse a JD first.', 'error'); return; }

  setLoading('cv', true);
  $('cv-error').style.display = 'none';
  $('cv-result-preview').style.display = 'none';

  try {
    const fd = new FormData();
    fd.append('file', cvFile);
    const res = await fetch(`${API}/api/evaluate-cv`, { method: 'POST', body: fd });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'CV evaluation failed');

    const result = data.result;
    state.candidates[result.candidate_id] = result;

    renderPreview(result);
    updateScreenedCount();
    $('btn-view-results').style.display = 'inline-flex';
    stepEls[2].classList.add('completed');
    toast(`✓ ${result.candidate_id} — ${recLabel(result.recommendation)}`, 'success');

  } catch (e) {
    showError('cv-error', e.message);
  } finally {
    setLoading('cv', false);
  }
});

$('btn-view-results').addEventListener('click', () => {
  renderLeaderboard();
  goToStep(3);
});

function renderPreview(r) {
  const score = r.overall_weighted_score;
  const hl = r.highlights || {};
  $('cv-result-preview').innerHTML = `
    <div class="result-preview-card">
      <div class="detail-header">
        <div>
          <div class="detail-title">✓ ${esc(r.candidate_id)}</div>
          <div class="detail-meta">${r.pii_redactions} PII entities scrubbed locally · ${r.dimension_scores?.length || 0} dimensions scored</div>
        </div>
        <span class="recommendation-badge rec-${r.recommendation}">${recLabel(r.recommendation)}</span>
      </div>
      <div style="margin-bottom:18px">
        <div class="score-bar-label">
          <span style="color:var(--text-secondary)">Overall weighted score</span>
          <span style="color:${scoreColor(score)};font-weight:700">${score} / 10</span>
        </div>
        <div class="score-bar-track" style="height:8px">
          <div class="score-bar-fill" style="width:${score*10}%;background:${scoreGrad(score)}"></div>
        </div>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
        <div>
          <div class="detail-section-title">Strengths</div>
          ${(hl.strengths||[]).slice(0,3).map(s=>`<div style="font-size:12px;color:var(--text-secondary);margin-bottom:4px">✅ ${esc(s)}</div>`).join('')}
        </div>
        <div>
          <div class="detail-section-title">Gaps</div>
          ${(hl.gaps||[]).slice(0,3).map(g=>`<div style="font-size:12px;color:var(--text-secondary);margin-bottom:4px">⚠️ ${esc(g)}</div>`).join('')}
        </div>
      </div>
      ${r.recommendation_rationale ? `<p style="margin-top:16px;padding-top:16px;border-top:1px solid var(--border-glass);font-size:13px;color:var(--text-secondary)">${esc(r.recommendation_rationale)}</p>` : ''}
    </div>
  `;
  $('cv-result-preview').style.display = 'block';
}

function updateScreenedCount() {
  const n = Object.keys(state.candidates).length;
  $('screened-count').textContent = n;
  $('screened-indicator').style.display = n > 0 ? 'inline-block' : 'none';
}

// ═══════════════════════════════════════════════════════════════════════════
// STEP 3 — Results Dashboard
// ═══════════════════════════════════════════════════════════════════════════

$('btn-screen-more').addEventListener('click', () => goToStep(2));

$('btn-export').addEventListener('click', async () => {
  try {
    const res = await fetch(`${API}/api/export`);
    if (!res.ok) throw new Error('Export failed');
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'resumeiq_export.json'; a.click();
    URL.revokeObjectURL(url);
    toast('Session exported!', 'success');
  } catch (e) { toast(e.message, 'error'); }
});

function renderLeaderboard() {
  const sorted = Object.values(state.candidates).sort(
    (a, b) => b.overall_weighted_score - a.overall_weighted_score
  );
  const lb = $('leaderboard');
  lb.innerHTML = '';

  sorted.forEach((c, idx) => {
    const score = c.overall_weighted_score;
    const rankClass = ['rank-1','rank-2','rank-3'][idx] || 'rank-n';
    const rankLabel = ['🥇','🥈','🥉'][idx] || `#${idx+1}`;

    const row = document.createElement('div');
    row.className = 'candidate-row';
    row.dataset.cid = c.candidate_id;
    row.style.animationDelay = `${idx * 70}ms`;
    row.innerHTML = `
      <div class="candidate-rank ${rankClass}">${rankLabel}</div>
      <div>
        <div class="candidate-name">${esc(c.candidate_id)}</div>
        <div class="candidate-meta">${c.pii_redactions||0} PII redacted · ${c.dimension_scores?.length||0} dims scored</div>
      </div>
      <div class="score-bar-wrap">
        <div class="score-bar-label">
          <span>Score</span>
          <span style="color:${scoreColor(score)}">${score}/10</span>
        </div>
        <div class="score-bar-track">
          <div class="score-bar-fill" style="width:${score*10}%;background:${scoreGrad(score)}"></div>
        </div>
      </div>
      <span class="recommendation-badge rec-${c.recommendation}">${recLabel(c.recommendation)}</span>
    `;
    row.addEventListener('click', () => openDetail(c.candidate_id));
    lb.appendChild(row);
  });
}

function openDetail(cid) {
  state.activeCandidateId = cid;
  const c = state.candidates[cid];

  document.querySelectorAll('.candidate-row').forEach(r =>
    r.classList.toggle('active', r.dataset.cid === cid)
  );

  const detail = $('candidate-detail');
  detail.innerHTML = `
    <div class="detail-header">
      <div>
        <div class="detail-title">${esc(cid)}</div>
        <div class="detail-meta">
          Evaluated ${c.evaluated_at ? new Date(c.evaluated_at).toLocaleString() : '—'}
          &nbsp;·&nbsp; ${c.pii_redactions||0} PII entities scrubbed before LLM
        </div>
      </div>
      <div style="display:flex;align-items:center;gap:10px">
        <span class="recommendation-badge rec-${c.recommendation}">${recLabel(c.recommendation)}</span>
        <button class="detail-close" id="close-detail">✕</button>
      </div>
    </div>

    ${c.recommendation_rationale
      ? `<div class="rationale-bar">${esc(c.recommendation_rationale)}</div>`
      : ''}

    <div class="detail-grid">
      <div class="detail-section full-width">
        <div class="detail-section-title">📊 Dimension Scores</div>
        <div id="dim-scores"></div>
      </div>

      <div class="detail-section">
        <div class="detail-section-title">💪 Strengths</div>
        <div class="highlight-list" id="hl-strengths"></div>
      </div>

      <div class="detail-section">
        <div class="detail-section-title">⚠️ Gaps & Concerns</div>
        <div class="highlight-list" id="hl-gaps"></div>
      </div>

      <div class="detail-section full-width">
        <div class="detail-section-title">🎯 Interview Probes</div>
        <div class="highlight-list" id="hl-probes"></div>
      </div>

      <div class="detail-section full-width">
        <div class="notes-header">
          <div class="detail-section-title" style="margin-bottom:0">📝 HR Notes</div>
          <span class="notes-saved" id="notes-saved">✓ Saved</span>
        </div>
        <textarea class="notes-area" id="notes-ta" placeholder="Add your notes about this candidate…">${esc(c.notes||'')}</textarea>
      </div>
    </div>
  `;

  // Dimension scores
  const ds = document.getElementById('dim-scores');
  (c.dimension_scores||[]).forEach(d => {
    const row = document.createElement('div');
    row.className = 'dim-score-row';
    const ev = (d.evidence||[]).map(e=>`<span class="evidence-chip">${esc(e)}</span>`).join('');
    row.innerHTML = `
      <div>
        <div class="dim-score-name">${esc(d.dimension_name)}</div>
        <div class="dim-score-just">${esc(d.justification||'')}</div>
        ${ev ? `<div class="dim-score-evidence">${ev}</div>` : ''}
      </div>
      <div class="dim-score-num" style="color:${scoreColor(d.score)}">${d.score}</div>
    `;
    ds.appendChild(row);
  });

  // Highlights
  const hl = c.highlights || {};
  renderHL('hl-strengths', hl.strengths||[], '✅');
  renderHL('hl-gaps', [...(hl.gaps||[]), ...(hl.concerns||[])], '⚠️');
  renderHL('hl-probes', hl.interview_probes||[], '❓');

  // Notes autosave
  const ta = document.getElementById('notes-ta');
  const savedEl = document.getElementById('notes-saved');
  ta.addEventListener('input', () => {
    clearTimeout(state.noteTimers[cid]);
    state.noteTimers[cid] = setTimeout(async () => {
      try {
        await fetch(`${API}/api/notes/${encodeURIComponent(cid)}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ notes: ta.value }),
        });
        state.candidates[cid].notes = ta.value;
        savedEl.classList.add('visible');
        setTimeout(() => savedEl.classList.remove('visible'), 2000);
      } catch {}
    }, 700);
  });

  $('close-detail').addEventListener('click', () => {
    detail.style.display = 'none';
    document.querySelectorAll('.candidate-row').forEach(r => r.classList.remove('active'));
  });

  detail.style.display = 'block';
  detail.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function renderHL(id, items, icon) {
  const el = document.getElementById(id);
  if (!el) return;
  el.innerHTML = items.length
    ? items.map(t=>`<div class="highlight-item"><span class="highlight-icon">${icon}</span><span class="highlight-text">${esc(t)}</span></div>`).join('')
    : `<p style="font-size:12px;color:var(--text-muted);font-style:italic">None identified.</p>`;
}

// ═══════════════════════════════════════════════════════════════════════════
// Reset
// ═══════════════════════════════════════════════════════════════════════════
$('btn-reset').addEventListener('click', async () => {
  if (!confirm('Reset session? All evaluated CVs will be cleared.')) return;
  try {
    await fetch(`${API}/api/session`, { method: 'DELETE' });
  } catch {}

  Object.assign(state, { dimensions: [], candidates: {}, activeCandidateId: null });
  jdFile = null; cvFile = null;

  $('jd-filename').style.display = 'none';
  $('jd-upload-zone').classList.remove('has-file');
  $('btn-analyze-jd').disabled = true;
  $('dimensions-panel').style.display = 'none';
  $('jd-error').style.display = 'none';
  $('cv-result-preview').style.display = 'none';
  $('screened-indicator').style.display = 'none';
  $('btn-view-results').style.display = 'none';
  $('leaderboard').innerHTML = '';
  $('candidate-detail').style.display = 'none';

  stepEls.forEach(el => { if (el) el.classList.remove('active','completed'); });
  goToStep(1);
  toast('Session reset.', 'info');
});

// ── Init ──────────────────────────────────────────────────────────────────────
goToStep(1);
