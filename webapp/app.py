from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import traceback

app = FastAPI(title="QFA-LTL Demo")

# Allow local dev origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static UI
app.mount("/static", StaticFiles(directory="webapp/static"), name="static")


@app.get("/", response_class=HTMLResponse)
def index():
    return FileResponse("webapp/static/index.html")


@app.post("/api/run")
def run_demo(payload: dict):
    """Run the demo with user-supplied inputs.
    Expected JSON payload fields:
      - ltl: LTL spec string (default: "F(prob(|11>) > 0.85)")
      - target: basis string for monitoring (default: "11")
      - threshold: float threshold for predicate (default: 0.85)
      - run_circuit: bool whether to compile a small demo circuit (default: false)
    """
    try:
        ltl_str = payload.get('ltl', "F(prob(|11>) > 0.85)")
        target = payload.get('target', '11')
        threshold = float(payload.get('threshold', 0.85))
        run_circuit = bool(payload.get('run_circuit', False))

        from src.qfa_verify.ltl.parser import parse_ltl
        from src.qfa_verify.qfa.spec_automaton import SpecQFABuilder
        from src.qfa_verify.monitoring.temporal_monitor import TemporalMonitor

        spec = parse_ltl(ltl_str)
        spec_qfa = SpecQFABuilder.from_ltl(spec)

        # The spec is authoritative: derive the target basis set and the
        # comparison operator from the parsed predicate, not from the UI
        # defaults alone (this is what makes G(... < t) behave correctly).
        pred = spec.get('predicate', {})
        bases = pred.get('bases') or ([pred['basis']] if pred.get('basis') else [])
        comparison = pred.get('comparison', '>')
        threshold = float(pred.get('threshold', threshold))
        if not target or target == '11' and bases:
            target = bases[0]
        targets = bases if bases else [target]

        # Build a demo trace that actually satisfies the spec under windowed
        # Bernoulli semantics (window = 100 shots).
        #  - '>' / '>=': a burst of target shots fills the window.
        #  - '<' / '<=': targets sprinkled thinly so no window exceeds t.
        #  - Bounded ops (F<=k / G<=k): the burst must land within the bound.
        WINDOW = 100
        other = '0' * len(targets[0]) if targets else '00'
        other = '1' * len(targets[0]) if other == targets[0] else other
        op = spec.get('operator', 'F')
        bound = None
        if op.startswith('F<=') or op.startswith('G<='):
            bound = int(op.split('<=')[1])
        if comparison in ('<', '<='):
            trace = ([other] * 19 + [targets[0]]) * 50  # ~5% target, never trips t
        elif bound is not None:
            # The automaton advances per shot, so the bound is in shots, not
            # windows. The burst must land within `bound` shots; keep the
            # window fill time (WINDOW shots) well inside it.
            prefix = max(0, bound - WINDOW - 50)
            trace = [other] * prefix + [targets[0]] * 600
        else:
            trace = [other] * 500 + [targets[0]] * 600   # window fills to 100%

        monitor = TemporalMonitor(spec_qfa, targets, threshold,
                                  comparison=comparison, window_size=WINDOW)
        result, history = monitor.process_trace(trace)

        response = {
            'input': {'ltl': ltl_str, 'target': target, 'threshold': threshold, 'run_circuit': run_circuit},
            'parsed_spec': spec,
            'operator': getattr(spec_qfa, 'operator', None),
            'monitor_result': bool(result),
            'history_len': len(history),
            'states': list(spec_qfa.states) if hasattr(spec_qfa, 'states') else None,
            'accepting_states': list(spec_qfa.accepting_states) if hasattr(spec_qfa, 'accepting_states') else None,
        }

        if run_circuit:
            try:
                from src.qfa_verify.qfa.circuit_compiler import compile_circuit
                from qiskit import QuantumCircuit

                qc = QuantumCircuit(2, 2)
                qc.h([0, 1])
                qc.cz(0, 1)
                qc.h([0, 1])
                qc.measure([0, 1], [0, 1])

                qfa = compile_circuit(qc)
                probs = qfa.get_all_probabilities()
                response['circuit_probabilities'] = probs
            except Exception as e:
                response['circuit_probabilities'] = None
                response['circuit_error'] = str(e)

        return response
    except Exception as e:
        tb = traceback.format_exc()
        raise HTTPException(status_code=500, detail={"error": str(e), "trace": tb})
