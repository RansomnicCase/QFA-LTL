// Example presets
const EXAMPLES = {
  'ghz_eventually': { ltl: "F(prob(|11>) > 0.85)", target: '11', threshold: 0.85, run_circuit: true },
  'bounded_eventually': { ltl: "F<=5(prob(|11>) > 0.8)", target: '11', threshold: 0.8, run_circuit: true },
  'globally': { ltl: "G(prob(|00>) < 0.10)", target: '00', threshold: 0.10, run_circuit: false },
  'bv': { ltl: "F(prob(|10101>) > 0.5)", target: '10101', threshold: 0.5, run_circuit: false }
}

// API base URL — default to local backend, can be overridden with ?api=<url>
const _qs = new URLSearchParams(window.location.search)
const API_BASE = _qs.get('api') || 'http://127.0.0.1:8001/api/run'

document.getElementById('exampleSelect').addEventListener('change', (e) => {
  const val = e.target.value
  if (val === 'custom') {
    document.getElementById('ltlInput').disabled = false
    document.getElementById('targetInput').disabled = false
    document.getElementById('thresholdInput').disabled = false
    document.getElementById('circuitChk').disabled = false
    return
  }
  const ex = EXAMPLES[val]
  if (ex) {
    document.getElementById('ltlInput').value = ex.ltl
    document.getElementById('targetInput').value = ex.target
    document.getElementById('thresholdInput').value = ex.threshold
    document.getElementById('circuitChk').checked = !!ex.run_circuit
    document.getElementById('ltlInput').disabled = true
    document.getElementById('targetInput').disabled = true
    document.getElementById('thresholdInput').disabled = true
    document.getElementById('circuitChk').disabled = false
  }
})

document.getElementById('runBtn').addEventListener('click', async () => {
  const status = document.getElementById('status')
  status.textContent = 'Running demo...'
  document.getElementById('results').style.display = 'none'

  const ltl = document.getElementById('ltlInput').value
  const target = document.getElementById('targetInput').value
  const threshold = document.getElementById('thresholdInput').value
  const runCircuit = document.getElementById('circuitChk').checked

  try {
    const resp = await fetch(API_BASE, { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ ltl, target, threshold, run_circuit: runCircuit }) })
    if (!resp.ok) throw new Error('Server error: ' + resp.status)
    const data = await resp.json()

    document.getElementById('parsedSpec').textContent = JSON.stringify(data.parsed_spec, null, 2)
    document.getElementById('automaton').textContent = 'Operator: ' + data.operator + '\nStates: ' + (data.states||[]).join(', ') + '\nAccepting: ' + (data.accepting_states||[]).join(', ')
    document.getElementById('monitor').textContent = 'Result: ' + (data.monitor_result ? 'PASS' : 'FAIL') + '\nHistory length: ' + data.history_len

    document.getElementById('results').style.display = 'block'
    status.textContent = 'Demo complete'

    // If circuit probs are present, draw chart
    if (data.circuit_probabilities) {
      const labels = Object.keys(data.circuit_probabilities)
      const values = labels.map(k => data.circuit_probabilities[k])
      const ctx = document.getElementById('probChart').getContext('2d')
      if (window._probChart) window._probChart.destroy()
      window._probChart = new Chart(ctx, {
        type: 'bar',
        data: { labels, datasets: [{ label: 'Probability', data: values, backgroundColor: '#4f46e5' }] },
        options: { scales: { y: { beginAtZero: true, max: 1 } } }
      })
    } else {
      if (window._probChart) { window._probChart.destroy(); window._probChart = null }
    }
  } catch (e) {
    status.textContent = 'Error: ' + (e.message || e)
    document.getElementById('parsedSpec').textContent = ''
    document.getElementById('automaton').textContent = JSON.stringify(e, null, 2)
    document.getElementById('results').style.display = 'block'
  }
})
