# Paper Outline (IEEE QCE 2026 format — two-column IEEEtran)

Working title: **QFA-LTL: Noise-Adaptive Statistical Test Oracles for Temporal Verification of NISQ Circuit Executions**

## 1. Introduction
- The verification problem on NISQ: correct circuits fail static thresholds on noisy days; faulty circuits pass on clean ones. False failures burn expensive device time and erode trust in quantum results.
- Two existing lines of work and their blind spot:
  - Equivalence checking / decision diagrams (QCEC, MQT): verifies the *ideal unitary* — answers "is the circuit right?", not "is this noisy run acceptable?".
  - Statistical testing (shot-based, confidence bounds): tests single outcomes, not temporal properties over measurement streams.
- This work: oracle synthesis where the threshold is a function of measured device noise and circuit volume, and the property is temporal (LTL) over measurement windows.
- Contributions (summarize C1–C7).

## 2. Preliminaries and Related Work
- LTL and monitor automata (classical LTL3 monitoring line).
- Quantum noise models: depolarizing channels, readout error, calibration data (T1/T2, gate errors), randomized-benchmarking-style probes.
- Quantum program testing: metamorphic testing of quantum programs, the quantum oracle problem, statistical verification.
- QFAs: note the naming risk — our "QFA" is a classical weighted transition system (exact statevector tracking); disambiguate explicitly, or rename in the final version.
- Positioning table (adaptive oracle vs equivalence checking vs on-chip automata) — cite the practical penalties of on-chip verification (resource tax, noise catch-22, measurement collapse) as *motivation for classical-side oracle synthesis*.

## 3. Framework
### 3.1 Specification language
- Grammar: `F/G/F≤k/G≤k ( prob(|b1>)+...+prob(|bm>) ⋈ t )`.
- Semantics: windowed Bernoulli predicate; automaton states; F vs G acceptance rules; violating states.

### 3.2 Zero-Knowledge Calibration probe
- Bell-state probe on mapped physical qubits; fidelity estimate; ε = 1 − fidelity; 4096 shots.

### 3.3 Volume-based adaptive anchor
- `Anchor = max(0.10, (1−ε)^V × 0.98)`, `V = n₂q + 0.1·width`.
- [Phase 2] Derivation from a per-gate depolarizing model with readout error; soundness statement; why the 0.10 floor exists (never trust thresholds below noise floor of the estimator).

### 3.4 Circuit→automaton compiler
- Exact amplitude tracking; gate handlers; transition recording; truncation with tracked error.
- [Phase 2] Theorem: L2 truncation bound; complexity of product construction.

### 3.5 Verdict pipeline
- Metric strategies (probability/parity/expectation), direction from spec, seeded execution, structured report.

## 4. Benchmark Suite and Protocol
- 6 algorithms × (correct + 3 faults) = 24 circuits; fault catalog table (what each bug does to the state).
- Protocol: fake_brisbane noise model, 1024 shots, 5 reps, seed 42 (and N-seed protocol in final).
- Metrics defined on the *detection* convention (buggy = positive): recall, precision, false-failure rate.

## 5. Results
- R1: False-failure rate 0.0% (30/30 correct pass) — headline.
- R2: Alarm precision 100%; detection recall 77.8%; confusion matrix (fig1), pass rates (fig2).
- R3: Sensitivity analysis (fig3): operating point recall 0.778 / precision 1.000 / FF 0.000; wide plateau where recall = 1.0 under their definition (correct-circuit preservation).
- R4: Compiler validation vs Qiskit statevector: max |Δp| = 8.9e-16.
- R5: Temporal monitor behavior: windowed F/G/bounded cases (from tests) — include as a small table or figure of monitor traces.
- R6: [pending Phase 1] Multi-seed CIs, baseline comparisons, hold-out thresholds.
- R7: [pending Phase 3] Real-hardware ZKC drift study.

## 6. The Detectability Frontier
- Characterize the 20 missed faults: distribution-preserving unitary classes.
- Proposition sketch: if fault U satisfies `|⟨b|U|0⟩|² = |⟨b|I|0⟩|²` for all target-relevant b, no measurement-statistics oracle can detect it; proof sketch + empirical confirmation (QFT phase/swap, GHZ mutations).
- Implication: phase-sensitive verification (rotated bases, entanglement witnesses, interferometric probes) as future work; the suite doubles as a fault taxonomy dataset.

## 7. Discussion and Limitations
- Threshold learning in-sample → hold-out protocol required (Phase 1).
- Simulator-validated; real-device drift study is the decisive next experiment.
- Anchor floor behavior for high-volume circuits (comparison study honest note).
- Scope: not equivalence checking, not post-classical verification.

## 8. Conclusion
- What was built, what was measured, what is proven, what is next.

## Appendix
- Reproducibility: commands to regenerate every figure (README + scripts), seed policy, JSON schema.
- Bug catalog detail.
- [pending] Formal proofs.

---

## Figure plan
1. fig1_confusion_matrix.png — detection performance (regenerated, honest).
2. fig2_pass_rates.png — per-algorithm pass rates.
3. fig3_sensitivity.png — threshold multiplier sweep (standard metrics).
4. comparison_study.png — adaptive vs fixed (re-run with honest floor labeling; or replace with real noise sweep in Phase 1).
5. [new] Monitor trace figure — F/G/windowed verdicts over shot traces.
6. [new] Detectability frontier figure — fault classes vs detectable/invisible.

## Table plan
1. Fault catalog (24 circuits).
2. Results summary (metrics + CIs when available).
3. Per-algorithm breakdown.
4. Related-work positioning.

## Milestones to publication
- M1 (done): Phase-0 correctness fixes; honest baseline measured; docs.
- M2 (Phase 1): hold-out calibration, ≥30 seeds + CIs, baselines (fixed/Hoeffding/Wilson/no-ZKC), McNemar.
- M3 (Phase 2): formal semantics + anchor soundness + truncation bound theorems.
- M4 (Phase 3): real hardware (IBMRunner implementation) + ZKC drift study.
- M5 (Phase 4): reproducibility package + LaTeX draft.
