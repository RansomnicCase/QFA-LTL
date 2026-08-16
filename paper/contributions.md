# Contributions (mapped to evidence)

Each contribution below states exactly what is claimed and where the evidence lives in the repo. Claims not yet backed by data are marked **[pending]**.

## C1. Noise-adaptive anchor synthesis from calibration probes
- The verdict threshold is derived per-run from a Bell-state calibration probe on the circuit's mapped physical qubits and the circuit's gate volume: `Anchor = (1−ε)^V × 0.98`, `V = #2q + 0.1·width`.
- Evidence: `src/qfa_verify/engine.py` (`_calibrate_noise_floor`, `_calculate_adaptive_anchor`), `verify.py` CLI, `outputs/verification_report.json`.
- Honest caveat: the 0.98 factor and 0.1·width term are currently heuristic; Phase 2 must derive them from a depolarizing + readout noise model (soundness theorem).

## C2. LTL as the authoritative specification for measured behavior
- The spec is parsed and enforced end-to-end: predicate basis states → metric targets; comparison operator → verdict direction; threshold → semantics. Multi-basis predicates `prob(|a>)+prob(|b>) ⋈ t` supported.
- Evidence: `src/qfa_verify/ltl/parser.py` (grammar), `engine.verify()` target/direction derivation, `benchmarks.py` suite specs.
- Honest caveat: the orchestrator suite path still uses learned targets rather than parsed specs for metric selection — unify in Phase 1.

## C3. Windowed Bernoulli semantics for temporal monitoring
- F/G/F≤k/G≤k properties are evaluated over measurement traces as windowed empirical fractions vs the spec threshold, honoring the comparison operator; G-family requires acceptance at trace end; violating states are explicit in the automata.
- Evidence: `src/qfa_verify/monitoring/temporal_monitor.py` (rewritten), `src/qfa_verify/qfa/spec_automaton.py` (violating_states/operator), `tests/test_week1.py` (all green, including negative cases: sparse F-traces fail, bursts violate G).

## C4. Exact circuit→automaton compiler with validated correctness and bounded truncation
- Exact amplitude tracking with per-gate transitions; validated against Qiskit's statevector simulator: 60 randomized circuits (2–5 qubits, 5–35 gates from {h,x,z,cx,cz,ry,rz,rx,cp,rzz,swap}), 896 basis states, max |Δp| = 8.88e-16.
- Truncation (support cap) now accumulates `truncation_error` — the dropped probability mass — giving a formal handle for the approximation bound.
- Evidence: `src/qfa_verify/qfa/circuit_compiler.py`, validation runs documented in session history; reproducible via the harness pattern in tests.
- Honest caveat: the truncation bound is tracked but not yet stated as a theorem; support-cap behavior at scale (>16 qubits) needs the Phase 2 analysis.

## C5. Fault-detectability frontier for measurement-based verification
- Empirically characterized which fault classes are detectable from measurement statistics: all six algorithm classes achieve 100% alarm precision; 20/90 injected faults are missed, and every missed fault is measurement-invisible by construction:
  - QFT `wrong_phase` and `missing_swap`: preserve the uniform magnitude spectrum.
  - GHZ `missing_cnot`, `wrong_entanglement`, `decoherence` (idle): preserve the parity distribution.
- Evidence: `outputs/experiments/fake_brisbane_20260816_173410.json` (seed 42, 120 tests), `outputs/plots/fig1_confusion_matrix.png`, `fig2_pass_rates.png`, `fig3_sensitivity.png`, `analysis/sensitivity.py` operating point: recall 0.778, precision 1.000, false-failure 0.000.
- This is framed as a contribution (characterization + taxonomy), not a failure: it defines the space where phase-sensitive verification (rotated bases, entanglement witnesses) is needed. **[pending]** formal characterization of the invisible class in terms of distribution-preserving unitaries.

## C6. Reproducible seeded benchmark infrastructure
- Seeded end-to-end (Aer `seed_simulator`, Python/numpy seeds), per-entry thresholds persisted in result JSONs, per-algorithm confusion report printed by the suite runner, honest sensitivity analysis with standard detection metrics.
- Evidence: `run_benchmarks.py --seed`, `src/qfa_verify/ibm/runner.py`, `src/qfa_verify/experiments/orchestrator.py` (`_generate_report`), `analysis/sensitivity.py`.
- **[pending]** multi-seed sweeps with CIs (Phase 1).

## C7. Oracle generation for deployment
- The framework emits self-contained Python test oracles embedding the derived threshold and the spec's comparison operator, with a `temporal_oracle` for histogram streams.
- Evidence: `src/qfa_verify/oracle/generator.py`, `outputs/grover_oracle.py`, `tests/test_week2.py`.

---

## Explicit non-claims (protects against reviewer misreading)
- **Not** on-chip quantum automaton verification (no ancilla overhead, no mid-circuit measurement).
- **Not** verification beyond classical simulation scale (the compiler is classical statevector tracking).
- **Not** a substitute for equivalence checking (ideal-unitary correctness).
