from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
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

REPO_ROOT = Path(__file__).resolve().parent.parent

# Real example circuits backing the "Verification Console" UI. Each entry
# points at a file already used elsewhere in the repo (README's Experimental
# Validation section, run_comparison_study.py) so the console exercises the
# same circuits the project's own results are based on.
EXAMPLE_CIRCUITS = {
    "ghz": {
        "path": REPO_ROOT / "examples" / "ghz.qasm",
        "name": "GHZ state",
    },
    "bv10": {
        "path": REPO_ROOT / "examples" / "bv_10.py",
        "name": "Bernstein–Vazirani",
    },
    "qpe": {
        "path": REPO_ROOT / "examples" / "qpe_complex.qasm",
        "name": "Phase estimation",
    },
    "stress7": {
        "path": REPO_ROOT / "examples" / "stress_7q.py",
        "name": "Adversarial ansatz",
    },
}

SUPPORTED_BACKENDS = ("fake_brisbane", "fake_sherbrooke")

# UniversalVerifier instances are expensive to construct (they load fake
# backend calibration snapshots), so keep one per backend name for the life
# of the server process.
_verifier_cache = {}


def _get_verifier(backend_name: str):
    from src.qfa_verify.engine import UniversalVerifier

    if backend_name not in _verifier_cache:
        _verifier_cache[backend_name] = UniversalVerifier(backend_name=backend_name)
    return _verifier_cache[backend_name]


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


@app.post("/api/verify")
def api_verify(payload: dict):
    """Run the real UniversalVerifier pipeline (ZKC + Adaptive Safety Anchor +
    execution) for the "Verification Console" UI. This is the same engine
    verify.py drives from the CLI — no mocked/random data.

    Expected JSON payload fields:
      - circuit: one of EXAMPLE_CIRCUITS' keys ("ghz", "bv10", "qpe", "stress7")
      - spec: LTL specification string
      - metric: "probability" | "parity" | "expectation"
      - target: target basis state(s), comma-separated for multiple (e.g. "00,11")
      - backend: "fake_brisbane" | "fake_sherbrooke"
      - noise: adversarial noise injection probability, 0.0-1.0
    """
    try:
        circuit_id = payload.get("circuit")
        preset = EXAMPLE_CIRCUITS.get(circuit_id)
        if not preset:
            raise HTTPException(status_code=400, detail=f"Unknown circuit '{circuit_id}'")

        backend_name = payload.get("backend", "fake_brisbane")
        if backend_name not in SUPPORTED_BACKENDS:
            raise HTTPException(status_code=400, detail=f"Unsupported backend '{backend_name}'")

        spec = (payload.get("spec") or "").strip() or "F(p > t)"
        metric = payload.get("metric", "probability")
        target = (payload.get("target") or "").strip()
        noise = float(payload.get("noise", 0.0))

        from verify import load_circuit

        qc = load_circuit(str(preset["path"]))
        target_params = target.split(",") if "," in target else (target or None)

        verifier = _get_verifier(backend_name)
        report = verifier.verify(
            qc, spec, metric_type=metric, target_params=target_params, adversarial_noise=noise
        )

        counts = {k.replace(" ", ""): v for k, v in report["counts"].items()}

        # The spec is authoritative (see engine.py's _spec_to_target): when no
        # explicit target override was sent, report the basis/bases the spec
        # itself resolved to, so the UI can still highlight the right bars.
        if target:
            effective_target = target
        else:
            predicate = report.get("spec_parsed", {}).get("predicate", {})
            spec_bases = predicate.get("bases") or ([predicate["basis"]] if predicate.get("basis") else [])
            effective_target = ",".join(spec_bases)

        return {
            "circuit": circuit_id,
            "circuit_name": preset["name"],
            "num_qubits": qc.num_qubits,
            "backend": backend_name,
            "spec": spec,
            "metric": metric,
            "target": effective_target,
            "adversarial_noise": noise,
            "verdict": report["verdict"],
            "metric_value": report["metric_value"],
            "threshold": report["threshold"],
            "calibration_loss": report["calibration_loss"],
            "counts": counts,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
