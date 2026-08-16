Minimum Viable Product (MVP)

Goal: provide a small, runnable demonstration that exercises the core pipeline (LTL parse → Spec QFA → Temporal monitor) and optionally compiles a small circuit to the in-repo CircuitQFA for comparison.

Prerequisites
- Python 3.10+ recommended (Windows: use the `py` launcher)
- Install dev dependencies:

```powershell
py -3 -m pip install --upgrade pip
py -3 -m pip install -r requirements-dev.txt
```

Run the demo

```powershell
py -3 mvp_demo.py
```

What the demo does
- Runs a smoke check for `F(prob(|11>) > 0.85)` using the in-repo parser and temporal monitor.
- If `qiskit` is available, compiles a 2-qubit Grover circuit to `CircuitQFA` and prints basis probabilities (sanity check).

Notes
- If you see import errors, ensure you're using the same Python with installed packages (use `py -3`).
- For hardware runs, set up IBM credentials separately; the demo is intentionally conservative and runs simulator-only code.
