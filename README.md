# QFA-LTL: Noise-Adaptive Statistical Verification for NISQ Executions

QFA-LTL is a research framework for **testing noisy quantum circuit executions against temporal statistical specifications**. It synthesizes adaptive pass/fail oracles from a calibration probe (ZKC), a volume-based noise anchor, and Linear Temporal Logic (LTL) properties evaluated over measurement windows — then characterizes which circuit faults are detectable from measurement statistics alone.

**Positioning note.** This is *not* on-chip verification (no ancilla automata, no mid-circuit measurement). All verification machinery runs classically: the automaton compiler is exact statevector tracking, and the LTL monitor consumes measurement histograms. The research contribution is the *noise-adaptive statistical oracle*: deciding whether a circuit's **measured behavior** satisfies a temporal specification under real device noise — the question classical equivalence checking (ideal unitary correctness) does not answer.

---

## Table of Contents

* [Key Innovations](#key-innovations)
* [System Architecture](#system-architecture)
* [Project Structure](#project-structure)
* [Installation and Setup](#installation-and-setup)
* [Usage](#usage)

  * [Basic Verification](#1-basic-verification)
  * [Adversarial Stress Testing](#2-adversarial-stress-testing)
  * [Batch Benchmarking](#3-batch-benchmarking)
* [Experimental Validation](#experimental-validation)
* [Known Limitations](#known-limitations)
* [Research Status](#research-status)
* [Dependencies](#dependencies)
* [Citation](#citation)

---

## Key Innovations

* **Zero-Knowledge Calibration (ZKC)**
  A pre-execution Bell-state probe on the *physical qubits* the circuit maps to. Measures actual device fidelity on the target layout before the circuit runs, and produces a per-run noise estimate ε.

* **Volume-Based Adaptive Anchor**
  A circuit-specific threshold derived from the probe:
  ```
  Anchor = (1 - ε)^V × 0.98,   V = (#2q gates) + 0.1 × (register width)
  ```
  The anchor is authoritative for the verdict: pass iff the measured success metric clears it (direction from the LTL predicate). No static thresholds, no per-algorithm hacks.

* **LTL as the Source of Truth**
  The spec is parsed and enforced: `F(prob(|b1> + |b2>) > t)`, `G(prob(|00>) < t)`, and bounded variants. The predicate supplies the target basis states, the comparison direction, and the semantic threshold. Multi-basis (parity-style) predicates are supported.

* **Windowed Temporal Monitoring**
  LTL properties are evaluated over measurement traces as *windowed Bernoulli estimates*: each time step is a window of shots, and the predicate is the empirical fraction of shots in the target bases compared per the spec operator. This gives `F`, `G`, `F<=k`, `G<=k` well-defined semantics on real histograms.

* **Exact Circuit→Automaton Compiler with Truncation Bound**
  The `CircuitQFA` compiler performs exact statevector tracking with per-gate amplitude transitions, validated against Qiskit's statevector simulator (max |Δp| ≈ 9e-16 over randomized circuits). State truncation is bounded and tracked (`truncation_error`), giving a provable handle on the approximation.

* **Adversarial Noise Injection**
  Controlled stochastic Pauli (X/Y/Z) error injection for robustness boundary analysis.

* **Fault Detectability Characterization**
  The benchmark suite is a taxonomy: for each algorithm class, we characterize which injected faults are detectable from measurement statistics and which are *measurement-invisible* (e.g., phase errors in QFT, distribution-preserving GHZ mutations). See [Known Limitations](#known-limitations).

---

## System Architecture

1. **Specification** — LTL properties define what "acceptable measured behavior" means.
2. **Calibration** — ZKC probe runs on the mapped physical qubits; estimates noise ε.
3. **Thresholding** — the volume-based anchor is computed from ε and circuit volume.
4. **Execution** — Aer simulator with fake-backend noise models (IBM Runtime path in progress).
5. **Verdict** — metric (probability / parity / expectation) vs anchor, direction from the spec; structured JSON report.

```
verify.py
├── UniversalVerifier (engine.py)
│   ├── ZKC probe (calibration)
│   ├── Adaptive anchor (volume scaling)
│   ├── Adversarial noise injection (optional)
│   └── LTL spec parsing (parser.py) → target/direction
├── SimulatorRunner (ibm/runner.py) — Aer + FakeBrisbane/FakeSherbrooke noise models
├── SafetyOrchestrator (experiments/orchestrator.py) — 24-circuit suite, thresholds, report
├── BenchmarkSuite (experiments/benchmarks.py) — 6 algorithms × (correct + 3 faults)
├── LTL machinery — parser → spec automaton → temporal monitor / product construction
└── analysis/ — visualizer (confusion matrix, pass rates), sensitivity (ROC-style), Streamlit dashboard
```

---

## Project Structure

```
qfa_ltl_project/
├── verify.py                 # CLI entry point (spec-driven verification)
├── run_benchmarks.py         # 24-circuit benchmark suite runner (seeded)
├── run_comparison_study.py   # Adaptive-vs-fixed threshold study
├── stress_test.sh            # Noise boundary sweep (seeded)
├── src/qfa_verify/
│   ├── engine.py             # UniversalVerifier: ZKC, anchor, verdict
│   ├── ltl/parser.py         # LTL grammar (Lark) incl. multi-basis predicates
│   ├── qfa/
│   │   ├── circuit_compiler.py    # Exact statevector-tracking automaton
│   │   ├── spec_automaton.py      # F/G/F<=k/G<=k automata + violating states
│   │   └── product_construction.py# Circuit × Spec product, reachability
│   ├── monitoring/temporal_monitor.py  # Windowed Bernoulli LTL monitoring
│   ├── oracle/generator.py   # Auto-generated deployable test oracles
│   ├── noise/ibm_backend.py  # Noise profiles + Wilson-score threshold calc
│   ├── ibm/runner.py         # Aer (fake backend) execution; IBM stub
│   └── experiments/          # BenchmarkSuite + SafetyOrchestrator
├── analysis/                 # visualizer.py, sensitivity.py, app.py (Streamlit)
├── tests/                    # test_week1/2/3.py (all green)
├── examples/                 # GHZ, BV-10, QPE, Ising, 7q variational, Grover oracle
└── paper/                    # Submission drafts (abstract, contributions, outline)
```

---

## Installation and Setup

### Requirements

* Python ≥ 3.10
* Qiskit ≥ 1.0, Qiskit Aer, Qiskit IBM Runtime
* lark, graphviz, matplotlib, seaborn, pandas

### Clone and Configure

```bash
git clone https://github.com/RansomnicCase/QFA-LTL-.git
cd qfa_ltl_project

# Recommended: editable install (makes `qfa_verify` importable everywhere)
pip install -e .

# Alternative: manual PYTHONPATH (project root for src.* imports,
# plus src/ for top-level qfa_verify imports)
export PYTHONPATH=$PYTHONPATH:$(pwd):$(pwd)/src
mkdir -p outputs
```

> Note: if your shell exports a global PYTHONPATH (e.g. from another tool's venv),
> unset it before running: `env -u PYTHONPATH .venv/bin/python ...`

---

## Usage

### 1. Basic Verification

The LTL spec is authoritative: it supplies the target basis state(s) and the comparison direction.

```bash
python3 verify.py \
    --circuit examples/ghz.qasm \
    --spec "F(prob(|000>) + prob(|111>) > 0.5)" \
    --metric parity \
    --target "000, 111"
```

(`--target` is optional — without it, basis states come from the spec predicate.)

### 2. Adversarial Stress Testing

```bash
python3 verify.py \
    --circuit examples/ghz.qasm \
    --spec "F(prob(|000>) + prob(|111>) > 0.5)" \
    --metric parity \
    --target "000, 111" \
    --noise 0.1 \
    --seed 42
```

### 3. Batch Benchmarking

The full 24-circuit suite (6 algorithms × correct + 3 injected faults), seeded and reproducible:

```bash
python3 run_benchmarks.py --seed 42 --shots 1024 --reps 5
```

Generates `outputs/experiments/*.json` plus a per-algorithm confusion report.

---

## Experimental Validation

Current honest baseline (seed 42, 24-circuit suite, 5 reps, fake_brisbane noise model, 120 tests):

| Metric | Value |
|---|---|
| False-failure rate (correct circuits failed) | **0.0%** (30/30 pass) |
| Bug-detection recall | 77.8% (70/90) |
| Alarm precision (FAIL ⇒ truly buggy) | **100.0%** |
| Compiler agreement vs Qiskit statevector | max \|Δp\| = 8.9e-16 (896 states) |
| Temporal monitor semantics | windowed Bernoulli, operator-aware |

The 20 missed faults are *measurement-invisible by construction* (see below) — the framework detects exactly the class that measurement statistics can detect, with zero false alarms.

---

## Known Limitations

1. **Measurement-invisible faults.** Faults that preserve the target-basis probability distribution cannot be detected from measurement statistics alone. Demonstrated classes: QFT phase errors and missing SWAPs (uniform magnitude spectrum preserved), GHZ entanglement-structure mutations (parity distribution preserved). Detection of these requires phase-sensitive probes (rotated bases, entanglement witnesses) — an open research direction.
2. **Simulator-validated, hardware pending.** All results use Aer with fake-backend calibration noise models. The IBM Runtime runner is a stub; real-device validation (esp. the ZKC drift study) is the next milestone.
3. **Threshold learning is in-sample.** `SafetyOrchestrator` currently derives thresholds from the correct circuits of the same run. A hold-out calibration protocol (thresholds from a separate calibration set) is required before publication.
4. **Single-shot statistics.** Runs are deterministic given a seed but reported without confidence intervals. Publication runs require ≥30 seeds with means ± CI (Wilson/Chernoff) and baselines (fixed, Hoeffding, Wilson-only, no-ZKC).
5. **No formal theory yet.** The automaton semantics, truncation bound, and anchor soundness need formal statements (paper Phase 2).

---

## Research Status

This is an active research project being prepared for submission (IEEE QCE 2026). The proposed contribution, stated honestly:

> **A noise-adaptive statistical test-oracle synthesis framework for NISQ executions** — ZKC calibration probes → volume-based anchors → LTL temporal monitoring over measurement windows — with a characterized fault-detectability frontier.

Not claimed: on-chip quantum automata verification, post-classical-scale verification, or equivalence checking. The framework targets the complementary question: *is the noisy measured behavior of this circuit acceptable?*

---

## Dependencies

* Python ≥ 3.10
* Qiskit ≥ 1.0, Qiskit Aer, Qiskit IBM Runtime
* lark, graphviz, matplotlib, seaborn, pandas
* (analysis dashboard) streamlit, plotly

---

## Citation

If you utilize this framework in your research, please cite:

> Agnihotri, Y. (2026). *QFA-LTL: Hardware-Aware Temporal Verification for NISQ Systems.*

---

**Note:** This project is part of an ongoing research submission for IEEE QCE 2026.
