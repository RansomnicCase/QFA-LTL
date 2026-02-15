# QFA-LTL: Quantum Finite Automata and LTL Verification Framework

QFA-LTL is a hardware-aware verification framework designed to address the critical challenges of measurement collapse, state-space explosion, and stochastic noise in NISQ-era quantum computing. By integrating Linear Temporal Logic (LTL) with Quantum Finite Automata (QFA), the system provides a robust test oracle that maintains high recall by adapting to real-time hardware conditions.

## Key Innovations

* **Adaptive Safety Anchor**: A dynamic thresholding mechanism that adjusts pass/fail criteria based on real-time noise profiles rather than static benchmarks.
* **Zero-Knowledge Calibration (ZKC)**: A pre-execution protocol that uses Bell-state probes to measure actual hardware fidelity on specific physical qubits.
* **Volume-Based Scaling Model**: A noise-resilient model that scales verification thresholds according to two-qubit gate density (N2q) and register width.
* **Temporal Property Enforcement**: Support for verifying complex temporal properties including Reachability (F), Invariance (G), and Persistence (FG).

## System Architecture

The framework operates through a modular pipeline:

1. **Specification**: LTL properties are defined as temporal constraints (e.g., "FG(p > t)").
2. **Calibration**: The ZKC module executes a probe circuit to detect gate drift and decoherence on the target backend.
3. **Thresholding**: The engine calculates an Adaptive Anchor using an exponential fidelity decay model based on circuit complexity.
4. **Execution**: The SafetyOrchestrator manages the execution flow via the SimulatorRunner or IBMRunner.
5. **Verdict**: An automated report is generated, providing an adaptive verdict based on hardware-aware performance.


## Experimental Results

Validation across multiple algorithms demonstrates that QFA-LTL significantly reduces false failure rates compared to legacy fixed-threshold methods.

* **GHZ State**: Validated parity and entanglement stability under varying noise.
* **Bernstein-Vazirani (10-qubit)**: Demonstrated scalability and signal tracking in high-width registers.
* **Quantum Phase Estimation (QPE)**: Validated logic enforcement in high-depth, high-volume gate sequences.


## Project Structure

* **src/qfa_verify/engine.py**: Core UniversalVerifier logic and ZKC implementation.
* **src/qfa_verify/experiments/orchestrator.py**: SafetyOrchestrator for managing metrics and reporting.
* **src/qfa_verify/ibm/runner.py**: Execution interface for Aer simulators and IBM Quantum backends.
* **verify.py**: Primary CLI entry point for running verification tasks.

## Installation and Usage

### Requirements
* Python 3.9+
* Qiskit 1.0+
* Qiskit Aer

### Environment Setup
```bash
export PYTHONPATH=$PYTHONPATH:$(pwd)
