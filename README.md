# QFA-LTL: Quantum Finite Automata and LTL Verification Framework

QFA-LTL is a hardware-aware verification framework designed to address the critical challenges of measurement collapse, state-space explosion, and stochastic noise in NISQ-era (Noisy Intermediate-Scale Quantum) computing. By integrating **Linear Temporal Logic (LTL)** with **Quantum Finite Automata (QFA)**, the system provides a robust test oracle that maintains high recall by adapting to real-time hardware conditions.

---

## Table of Contents

* [Introduction](#introduction)
* [Key Innovations](#key-innovations)
* [System Architecture](#system-architecture)
* [Project Structure](#project-structure)
* [Installation and Setup](#installation-and-setup)
* [Usage](#usage)

  * [Basic Verification](#1-basic-verification)
  * [Adversarial Stress Testing](#2-adversarial-stress-testing)
  * [Batch Benchmarking](#3-batch-benchmarking)
* [Experimental Validation](#experimental-validation)
* [Dependencies](#dependencies)
* [Configuration](#configuration)
* [Examples](#examples)
* [Troubleshooting](#troubleshooting)
* [Contributors](#contributors)
* [License](#license)
* [Citation](#citation)

---

## Introduction

QFA-LTL is designed to provide **hardware-aware temporal verification** for quantum circuits operating in noisy intermediate-scale quantum (NISQ) environments. Traditional verification methods often rely on static thresholds and idealized assumptions, leading to false failures or undetected drift in real hardware.

This framework dynamically adapts verification thresholds based on real-time calibration and circuit complexity, ensuring more reliable validation of quantum programs.

---

## Key Innovations

* **Adaptive Safety Anchor**
  A dynamic thresholding mechanism that adjusts pass/fail criteria based on real-time noise profiles rather than static benchmarks.

* **Zero-Knowledge Calibration (ZKC)**
  A pre-execution protocol that uses Bell-state probes to measure actual hardware fidelity on specific physical qubits before the target circuit runs.

* **Volume-Based Scaling Model**
  A noise-resilient model that scales verification thresholds according to:

  * Two-qubit gate density ($N_{2q}$)
  * Register width
    Following an exponential decay law.

* **Adversarial Noise Injection**
  A built-in stress-testing module that injects stochastic Pauli errors ($X$, $Z$) to validate robustness of safety anchors.

* **Temporal Property Enforcement**
  Support for verifying complex temporal properties including:

  * Reachability ($F$)
  * Invariance ($G$)
  * Persistence ($FG$)

---

## System Architecture

The framework operates through a modular and reproducible pipeline:

1. **Specification**
   LTL properties are defined as temporal constraints (e.g., `FG(p > t)`).

2. **Calibration**
   The ZKC module executes a probe circuit to detect gate drift and decoherence on the specific hardware layout.

3. **Thresholding**
   The engine calculates an **Adaptive Anchor** using the volume-based scaling model:

   ```
   Threshold = (1 - ε)^V × 0.98
   ```

4. **Execution**
   The `SafetyOrchestrator` manages execution flow via:

   * `SimulatorRunner` (Aer)
   * `IBMRunner` (Qiskit Runtime)

5. **Verdict**
   An automated report compares measured success metrics against the dynamic anchor to issue a **PASS/FAIL** verdict.

---

## Project Structure

```
qfa_ltl_project/
│
├── verify.py
├── stress_test.sh
├── outputs/
├── examples/
│   ├── ghz.qasm
│   └── ...
└── src/
    └── qfa_verify/
        ├── engine.py
        ├── experiments/
        │   └── orchestrator.py
        └── ibm/
            └── runner.py
```

### File Descriptions

* `verify.py` — Primary CLI entry point for running verification tasks.
* `src/qfa_verify/engine.py` — Core `UniversalVerifier`, ZKC implementation, and metric strategies.
* `src/qfa_verify/experiments/orchestrator.py` — `SafetyOrchestrator` for metrics, precision/recall tracking, and reporting.
* `src/qfa_verify/ibm/runner.py` — Execution interface for Aer simulators and IBM Quantum backends.
* `stress_test.sh` — Automation script for noise-boundary analysis.
* `examples/` — Benchmark circuits in `.qasm` and `.py` formats.

---

## Installation and Setup

### Requirements

* Python 3.9+
* Qiskit 1.0+
* Qiskit Aer

### Clone and Configure

```bash
git clone https://github.com/your-username/qfa_ltl_project.git
cd qfa_ltl_project
export PYTHONPATH=$PYTHONPATH:$(pwd)
mkdir -p outputs
```

---

## Usage

### 1. Basic Verification

Verify a GHZ state using the parity metric:

```bash
python3 verify.py \
    --circuit examples/ghz.qasm \
    --spec "F(p > t)" \
    --metric parity \
    --target "000, 111"
```

---

### 2. Adversarial Stress Testing

Inject 10% artificial noise to validate robustness:

```bash
python3 verify.py \
    --circuit examples/ghz.qasm \
    --spec "F(p > t)" \
    --metric parity \
    --target "000, 111" \
    --noise 0.1
```

---

### 3. Batch Benchmarking

Generate a robustness curve across the noise spectrum:

```bash
chmod +x stress_test.sh
./stress_test.sh
```

---

## Experimental Validation

The framework has been validated across standard quantum algorithms to demonstrate resilience against false failures:

* **GHZ State**
  Validated parity and entanglement stability under varying noise conditions.

* **Bernstein-Vazirani (10-qubit)**
  Demonstrated scalability and signal tracking in high-width registers.

* **Quantum Phase Estimation (QPE)**
  Validated temporal logic enforcement in high-depth, high-volume gate sequences.

---

## Dependencies

* Python ≥ 3.9
* Qiskit ≥ 1.0
* Qiskit Aer
* IBM Quantum Runtime (optional, for hardware execution)

---

## Configuration

Environment variables:

```bash
export PYTHONPATH=$PYTHONPATH:$(pwd)
```

Optional parameters:

* `--noise <float>` — Inject artificial stochastic noise.
* `--metric <type>` — Specify verification metric.
* `--spec "<LTL_formula>"` — Provide temporal property.
* `--target "<bitstrings>"` — Expected valid outcomes.

---

## Examples

Located in the `examples/` directory:

* `ghz.qasm`
* Benchmark circuits in both `.qasm` and `.py` formats.

---

## Troubleshooting

**ModuleNotFoundError**
Ensure `PYTHONPATH` includes the project root.

**Backend execution issues**
Confirm IBM Quantum credentials are properly configured.

**Unexpected FAIL verdicts**
Check:

* Noise injection parameter
* Hardware calibration drift
* Correct LTL specification

---

## Contributors

* Y. Agnihotri

---

## License

This project is currently part of an ongoing research submission.
License details will be updated upon publication.

---

## Citation

If you utilize this framework in your research, please cite:

> Agnihotri, Y. (2026). *QFA-LTL: Hardware-Aware Temporal Verification for NISQ Systems.*

---

**Note:** This project is part of an ongoing research submission for IEEE QCE 2026.
