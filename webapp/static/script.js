// QFA-LTL Verification Console — vanilla JS, no framework.
// Calls the real backend (/api/verify -> UniversalVerifier.verify) for every
// run; nothing here is simulated or randomly generated.

const API_BASE = new URLSearchParams(location.search).get('api') || '/api/verify';

// Spec strings must match the real Lark grammar in src/qfa_verify/ltl/parser.py:
// F|G [<=k] ( prob(|BITS>) [+ prob(|BITS>) ...] COMPARISON NUMBER )
// The engine parses this spec and uses it as the authoritative source for the
// target basis state(s) and the verdict direction (see engine.py's
// _spec_to_target / _spec_direction) — it is not just descriptive text.
//
// NOTE: the "+" multi-basis sum (prob(|a>) + prob(|b>) > t) currently has a
// parser/transformer bug — parse_ltl() leaves the summed bases as an
// unflattened Lark Tree instead of a list of strings (confirmed empirically;
// not something to silently paper over here). Until that's fixed upstream in
// ltl/parser.py, the QPE example below uses a single-basis spec and instead
// passes both target states through the explicit `target` override, which
// bypasses spec-derived bases entirely (engine.py: target_params wins when set).
const EXAMPLES = [
  { id: 'ghz', name: 'GHZ state', qubits: 3, desc: 'Maximal 3-qubit entanglement — verifies eventual collapse to |111>.', spec: 'F(prob(|111>) > 0.7)', metric: 'probability', target: '111' },
  { id: 'bv10', name: 'Bernstein–Vazirani', qubits: 10, desc: '10-qubit oracle recovery of a hidden bitstring.', spec: 'G(prob(|1101101101>) > 0.5)', metric: 'probability', target: '1101101101' },
  { id: 'qpe', name: 'Phase estimation', qubits: 3, desc: '3-qubit QPE with inverse QFT — checks phase-readout stability.', spec: 'F(prob(|100>) > 0.1)', metric: 'parity', target: '100,010' },
  { id: 'stress7', name: 'Adversarial ansatz', qubits: 7, desc: 'Fully-entangled 7-qubit RealAmplitudes stress circuit.', spec: 'G(prob(|0000000>) > 0.1)', metric: 'expectation', target: '' },
];

const BACKENDS = ['fake_brisbane', 'fake_sherbrooke'];
const METRICS = [
  { id: 'probability', label: 'Probability' },
  { id: 'parity', label: 'Parity' },
  { id: 'expectation', label: 'Expectation' },
];

const PIPELINE_DEFS = [
  { label: 'Zero-Knowledge Calibration', detail: 'Probing hardware fidelity with a Bell-state circuit' },
  { label: 'Adaptive anchor', detail: 'Scaling threshold by circuit volume and probe loss' },
  { label: 'Circuit execution', detail: 'Running the target circuit on the selected backend' },
  { label: 'Verdict', detail: 'Comparing the measured metric against the anchor' },
];

const ICONS = {
  play: '<svg class="icon" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>',
  spinner: '<svg class="icon spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M12 3a9 9 0 1 0 9 9" opacity="0.9"/></svg>',
  check: '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M5 13l4 4 10-10"/></svg>',
  checkCircle: '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="9"/><path d="M8 12.5l2.5 2.5L16 9.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  xCircle: '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="9"/><path d="M9 9l6 6M15 9l-6 6" stroke-linecap="round"/></svg>',
  warning: '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3L2 20h20L12 3z"/><path d="M12 10v4"/><circle cx="12" cy="17" r="0.6" fill="currentColor"/></svg>',
  shield: '<svg class="icon icon-lg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M12 3l7 3v6c0 4.5-3 8-7 9-4-1-7-4.5-7-9V6z"/></svg>',
  info: '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8v.01"/></svg>',
  copy: '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/></svg>',
};

const state = {
  mode: 'example', // 'example' | 'custom'
  circuitId: 'ghz',
  customSpec: '',
  customMetric: '',
  customTarget: '',
  backend: 'fake_brisbane',
  noise: 0, // 0.0 - 0.30
  status: 'idle', // idle | running | error | done
  stepIndex: -1,
  report: null,
  errorMsg: '',
  copyLabel: 'Copy',
};

seedCustomFromCircuit(state.circuitId);

function seedCustomFromCircuit(id) {
  const base = EXAMPLES.find((e) => e.id === id) || EXAMPLES[0];
  state.customSpec = base.spec;
  state.customMetric = base.metric;
  // Left blank on purpose: the spec's own prob(|bits>) terms are authoritative
  // for the target unless the user deliberately types an override.
  state.customTarget = '';
}

function getActiveSpec() {
  const base = EXAMPLES.find((e) => e.id === state.circuitId) || EXAMPLES[0];
  if (state.mode === 'example') return { ...base };
  return {
    id: base.id,
    name: base.name,
    qubits: base.qubits,
    spec: (state.customSpec || '').trim() || base.spec,
    metric: state.customMetric || base.metric,
    target: (state.customTarget || '').trim(),
  };
}

function validate() {
  if (state.mode === 'custom') {
    const spec = getActiveSpec();
    // Target is optional — the spec's own prob(|bits>) term(s) always supply
    // at least one target basis; the field is only an explicit override.
    if (!spec.spec.trim()) return 'Provide an LTL specification, e.g. F(prob(|111>) > 0.7).';
  }
  return '';
}

async function run() {
  const err = validate();
  if (err) {
    state.status = 'error';
    state.errorMsg = err;
    render();
    return;
  }

  state.status = 'running';
  state.stepIndex = 0;
  state.errorMsg = '';
  render();

  const spec = getActiveSpec();
  const advance = setInterval(() => {
    if (state.stepIndex < 2) {
      state.stepIndex += 1;
      render();
    }
  }, 900);

  try {
    const resp = await fetch(API_BASE, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        circuit: spec.id,
        spec: spec.spec,
        metric: spec.metric,
        target: spec.target,
        backend: state.backend,
        noise: state.noise,
      }),
    });
    clearInterval(advance);

    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}));
      const detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail || body);
      throw new Error(detail || `Server error: ${resp.status}`);
    }

    const data = await resp.json();
    state.stepIndex = 3;
    state.report = buildReport(data);
    state.status = 'done';
  } catch (e) {
    clearInterval(advance);
    state.status = 'error';
    state.errorMsg = e.message || String(e);
  }
  render();
}

function buildReport(data) {
  const isPass = data.verdict === 'pass';
  const targets = (data.target || '').split(',').map((t) => t.trim()).filter(Boolean);

  const entries = Object.entries(data.counts || {}).sort((a, b) => b[1] - a[1]);
  const shots = entries.reduce((sum, [, c]) => sum + c, 0) || 1;
  const top = entries.slice(0, 5);
  const maxCount = top.length ? top[0][1] : 1;
  const counts = top.map(([bitstring, count]) => ({
    bitstring,
    isTarget: targets.includes(bitstring),
    pctStr: ((count / shots) * 100).toFixed(1) + '%',
    widthPct: (count / maxCount) * 100,
  }));

  return {
    raw: data,
    verdict: data.verdict,
    isPass,
    circuitName: data.circuit_name,
    backend: data.backend,
    metricLabel: data.metric.charAt(0).toUpperCase() + data.metric.slice(1),
    metricValue: data.metric_value,
    threshold: data.threshold,
    calLoss: data.calibration_loss,
    hasNoise: data.adversarial_noise > 0,
    noisePct: Math.round(data.adversarial_noise * 100),
    counts,
    bitWidth: data.num_qubits,
    jsonStr: JSON.stringify(data, null, 2),
  };
}

function copyJson() {
  const r = state.report;
  if (!r) return;
  const text = JSON.stringify(r.raw, null, 2);
  if (navigator.clipboard) navigator.clipboard.writeText(text).catch(() => {});
  state.copyLabel = 'Copied';
  render();
  clearTimeout(copyJson._t);
  copyJson._t = setTimeout(() => {
    state.copyLabel = 'Copy';
    render();
  }, 1400);
}

// ---- rendering ----

function renderConfigPanel() {
  const spec = getActiveSpec();
  const canRun = state.status !== 'running' && (state.mode === 'example' || !!spec.spec.trim());

  const exampleCards = EXAMPLES.map((ex) => {
    const selected = state.circuitId === ex.id;
    return `
      <div class="example-card ${selected ? 'is-selected' : ''}" data-action="select-circuit" data-id="${ex.id}">
        <div class="example-card-row">
          <span class="example-card-name">${ex.name}</span>
          <span class="tag tag-neutral">${ex.qubits}q</span>
        </div>
        <div class="example-card-desc">${ex.desc}</div>
        <code class="example-card-spec">${escapeHtml(ex.spec)}</code>
      </div>`;
  }).join('');

  const circuitOptions = EXAMPLES.map(
    (ex) => `<option value="${ex.id}" ${ex.id === state.circuitId ? 'selected' : ''}>${ex.name} (${ex.qubits}q)</option>`
  ).join('');

  const metricSeg = METRICS.map((m) => {
    const checked = spec.metric === m.id;
    return `
      <label class="seg-opt ${checked ? 'is-checked' : ''}">
        <input type="radio" name="metric" data-action="set-metric" data-id="${m.id}" ${checked ? 'checked' : ''}>
        <span>${m.label}</span>
      </label>`;
  }).join('');

  const backendOptions = BACKENDS.map(
    (b) => `<option value="${b}" ${b === state.backend ? 'selected' : ''}>${b}</option>`
  ).join('');

  return `
    <div class="card elev-sm" style="padding:20px;gap:18px">
      <div>
        <div class="card-kicker">Input</div>
        <h3 class="card-title" style="margin-top:2px">Verification setup</h3>
      </div>

      <div class="seg">
        <label class="seg-opt ${state.mode === 'example' ? 'is-checked' : ''}">
          <input type="radio" name="mode" data-action="set-mode" data-id="example" ${state.mode === 'example' ? 'checked' : ''}>
          <span>Example</span>
        </label>
        <label class="seg-opt ${state.mode === 'custom' ? 'is-checked' : ''}">
          <input type="radio" name="mode" data-action="set-mode" data-id="custom" ${state.mode === 'custom' ? 'checked' : ''}>
          <span>Custom</span>
        </label>
      </div>

      ${state.mode === 'example' ? `<div style="display:flex;flex-direction:column;gap:8px">${exampleCards}</div>` : ''}

      ${state.mode === 'custom' ? `
        <div style="display:flex;flex-direction:column;gap:14px">
          <div class="field">
            <label>Base circuit</label>
            <select class="input" data-action="select-circuit-dropdown">${circuitOptions}</select>
          </div>
          <div class="field">
            <label>LTL specification</label>
            <input class="input" type="text" placeholder="F(prob(|111&gt;) &gt; 0.7)" value="${escapeHtml(state.customSpec)}" data-action="set-spec">
          </div>
          <div class="field">
            <label>Success metric</label>
            <div class="seg">${metricSeg}</div>
          </div>
          <div class="field">
            <label>Target override (optional)</label>
            <input class="input" type="text" placeholder="Leave blank to use the spec's own |bits&gt; target(s)" value="${escapeHtml(state.customTarget)}" data-action="set-target" ${spec.metric === 'expectation' ? 'disabled' : ''}>
          </div>
          <p class="text-muted" style="font-size:11.5px;margin:0">The spec's own <code>prob(|bits&gt;)</code> term sets the target state and comparison direction unless you type an override above. For multiple target states, use the override field (comma-separated) rather than <code>+</code> inside the spec — that syntax is currently broken. Qubit count is fixed by the selected circuit (${spec.qubits}).</p>
        </div>` : ''}

      <div class="hr"></div>

      <div class="field">
        <label>Backend noise model</label>
        <select class="input" data-action="set-backend">${backendOptions}</select>
      </div>

      <div class="field">
        <label>Adversarial noise injection — ${Math.round(state.noise * 100)}%</label>
        <input class="input" type="range" min="0" max="30" step="1" value="${Math.round(state.noise * 100)}" data-action="set-noise">
      </div>

      <button class="btn btn-primary btn-block" ${canRun ? '' : 'disabled'} data-action="run">
        ${state.status === 'running' ? `${ICONS.spinner} Verifying…` : `${ICONS.play} Run verification`}
      </button>
      ${state.status === 'error' && !state.report && state.errorMsg ? `
        <div class="validation-msg">${ICONS.warning}${escapeHtml(state.errorMsg)}</div>` : ''}
    </div>`;
}

function renderResultsPanel() {
  if (state.status === 'idle') {
    return `
      <div class="card elev-sm state-empty">
        ${ICONS.shield}
        <h4 style="margin:6px 0 2px;font-weight:500">No verification run yet</h4>
        <p class="text-muted" style="max-width:340px;font-size:13px;margin:0">Pick an example circuit — or define a custom one — then run verification to see the Adaptive Safety Anchor report.</p>
      </div>`;
  }

  if (state.status === 'running') {
    const steps = PIPELINE_DEFS.map((d, i) => {
      const done = state.stepIndex > i;
      const active = state.stepIndex === i;
      const color = state.stepIndex >= i ? 'var(--color-accent)' : 'var(--color-neutral-600)';
      return `
        <div class="pipeline-step" style="opacity:${state.stepIndex >= i ? 1 : 0.35}">
          <div class="pipeline-dot" style="color:${color};box-shadow:0 0 0 1px ${color}">
            ${done ? ICONS.check : ''}${active ? ICONS.spinner : ''}
          </div>
          <div>
            <div class="pipeline-label">${d.label}</div>
            <div class="pipeline-detail text-muted">${d.detail}</div>
          </div>
        </div>`;
    }).join('');
    return `<div class="card elev-sm pipeline">${steps}</div>`;
  }

  if (state.status === 'error' && !state.report) {
    return `
      <div class="card elev-sm error-card">
        <div style="display:flex;align-items:center;gap:8px;color:var(--color-accent-300)">
          ${ICONS.xCircle}<h4 style="margin:0;font-weight:500;color:var(--color-text)">Verification could not run</h4>
        </div>
        <p class="text-muted" style="font-size:13px;margin:0">${escapeHtml(state.errorMsg)}</p>
      </div>`;
  }

  if (state.status === 'done' && state.report) {
    const r = state.report;
    const distRows = r.counts.map((c) => `
      <div class="dist-row">
        <code class="dist-bitstring" style="width:${r.bitWidth}ch;color:${c.isTarget ? 'var(--color-accent-300)' : 'var(--color-neutral-400)'}">${c.bitstring}</code>
        <div class="dist-track"><div class="dist-fill" style="width:${c.widthPct}%;background:${c.isTarget ? 'var(--color-accent)' : 'var(--color-neutral-700)'}"></div></div>
        <span class="dist-pct text-muted">${c.pctStr}</span>
      </div>`).join('');

    return `
      <div class="result-wrap">
        <div class="card elev-md verdict-card">
          <div style="display:flex;align-items:center;gap:14px">
            <div class="verdict-badge ${r.isPass ? 'pass' : 'fail'}">${r.isPass ? ICONS.checkCircle : ICONS.xCircle}</div>
            <div>
              <div class="card-kicker" style="color:var(--color-neutral-500)">Verdict</div>
              <div class="verdict-title">${r.isPass ? 'PASS' : 'FAIL'}</div>
            </div>
          </div>
          <div style="display:flex;gap:8px;flex-wrap:wrap">
            <span class="tag tag-neutral">${r.circuitName}</span>
            <span class="tag tag-neutral">${r.backend}</span>
            ${r.hasNoise ? `<span class="tag tag-outline">${r.noisePct}% injected noise</span>` : ''}
          </div>
        </div>

        <div class="qfa-stats">
          <div class="card elev-sm stat-card">
            <div class="card-kicker">Measured value</div>
            <div class="stat-value">${r.metricValue.toFixed(4)}</div>
            <div class="stat-caption text-muted">${r.metricLabel}</div>
          </div>
          <div class="card elev-sm stat-card">
            <div class="card-kicker">Adaptive anchor</div>
            <div class="stat-value">${r.threshold.toFixed(4)}</div>
            <div class="stat-caption text-muted">Volume-scaled threshold</div>
          </div>
          <div class="card elev-sm stat-card">
            <div class="card-kicker">ZKC probe loss</div>
            <div class="stat-value">${r.calLoss.toFixed(4)}</div>
            <div class="stat-caption text-muted">Bell-state fidelity loss</div>
          </div>
        </div>

        <div class="card elev-sm" style="padding:18px 20px;gap:12px">
          <div style="display:flex;justify-content:space-between;align-items:baseline">
            <h5 style="font-weight:500">Measured vs. threshold</h5>
            <span class="text-muted" style="font-size:11.5px">metric: ${r.metricLabel}</span>
          </div>
          <div class="threshold-track">
            <div class="threshold-fill" style="width:${Math.min(100, r.metricValue * 100)}%;background:${r.isPass ? 'var(--color-accent)' : 'var(--color-neutral-500)'}"></div>
            <div class="threshold-marker" style="left:${Math.min(100, r.threshold * 100)}%" title="Adaptive anchor"></div>
          </div>
          <div class="threshold-scale"><span>0.0</span><span>1.0</span></div>
        </div>

        <div class="card elev-sm" style="padding:18px 20px;gap:14px">
          <h5 style="font-weight:500">Measurement distribution <span class="text-muted" style="font-weight:400;font-size:11.5px">— top outcomes</span></h5>
          <div style="display:flex;flex-direction:column;gap:9px">${distRows}</div>
        </div>

        <div class="card elev-sm" style="padding:18px 20px;gap:10px">
          <div style="display:flex;justify-content:space-between;align-items:center">
            <h5 style="font-weight:500">Structured report</h5>
            <button class="btn btn-ghost" data-action="copy-json">${ICONS.copy} ${state.copyLabel}</button>
          </div>
          <pre class="json-block">${escapeHtml(r.jsonStr)}</pre>
        </div>

        <p class="note text-muted">${ICONS.info}Live run: results come from UniversalVerifier.verify() on the server (ZKC probe + Adaptive Safety Anchor + Aer noise-model execution) — no data is mocked.</p>
      </div>`;
  }

  return '';
}

function render() {
  const app = document.getElementById('app');
  app.innerHTML = renderConfigPanel() + `<div style="display:flex;flex-direction:column;gap:20px;min-height:520px">${renderResultsPanel()}</div>`;
}

function escapeHtml(str) {
  return String(str).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

// ---- event delegation ----

document.addEventListener('DOMContentLoaded', () => {
  render();

  const app = document.getElementById('app');

  app.addEventListener('click', (e) => {
    const el = e.target.closest('[data-action]');
    if (!el) return;
    const action = el.dataset.action;
    if (action === 'select-circuit') {
      state.circuitId = el.dataset.id;
      seedCustomFromCircuit(state.circuitId);
      render();
    } else if (action === 'run') {
      run();
    } else if (action === 'copy-json') {
      copyJson();
    }
  });

  app.addEventListener('change', (e) => {
    const el = e.target.closest('[data-action]');
    if (!el) return;
    const action = el.dataset.action;
    if (action === 'set-mode') {
      state.mode = el.dataset.id;
      state.status = 'idle';
      state.report = null;
      render();
    } else if (action === 'select-circuit-dropdown') {
      state.circuitId = el.value;
      seedCustomFromCircuit(state.circuitId);
      render();
    } else if (action === 'set-metric') {
      state.customMetric = el.dataset.id;
      render();
    } else if (action === 'set-backend') {
      state.backend = el.value;
    } else if (action === 'set-noise') {
      state.noise = Number(el.value) / 100;
      render();
    }
  });

  app.addEventListener('input', (e) => {
    const el = e.target.closest('[data-action]');
    if (!el) return;
    const action = el.dataset.action;
    if (action === 'set-spec') {
      state.customSpec = el.value;
    } else if (action === 'set-target') {
      state.customTarget = el.value;
    } else if (action === 'set-noise') {
      state.noise = Number(el.value) / 100;
      render();
    }
  });
});
