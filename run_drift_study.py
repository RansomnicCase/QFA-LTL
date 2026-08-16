"""
WS-3B: Calibration-drift simulation.

Simulates device drift across 'days' by scaling the fake backend noise model.
The ZKC probe measures each day's actual noise; the derived anchor tracks it.
Shows: on high-drift days, a fixed 0.15 threshold false-fails correct circuits
while the adaptive anchor keeps them passing.

This is the honest no-token stand-in for the real-hardware drift study.
"""
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel
from qiskit_ibm_runtime.fake_provider import FakeBrisbane
from qiskit.quantum_info import Kraus, SuperOp

from qfa_verify.thresholds import DerivedAnchor, count_2q_gates
from qfa_verify.qfa.circuit_compiler import compile_circuit

OUT = Path("outputs/plots")
OUT.mkdir(parents=True, exist_ok=True)


def make_drift_noise_model(base_backend, factor: float) -> NoiseModel:
    """Build a noise model from the backend's calibration, scaled by `factor`.

    Reads real 1q/2q gate errors and readout errors from the fake backend,
    then builds a fresh NoiseModel with depolarizing channels scaled by the
    drift factor. This is the honest stand-in for a device whose calibration
    degrades over days.
    """
    from qiskit_aer.noise import depolarizing_error, ReadoutError
    props = base_backend.properties()
    config = base_backend.configuration()

    # Average 1q and 2q gate errors from the calibration
    err_1q, err_2q = 0.0005, 0.005
    count_1q = count_2q = 0
    for gate in props.gates:
        for param in gate.parameters:
            if param.name != 'gate_error':
                continue
            if gate.gate in ('cx', 'ecr', 'cz'):
                err_2q += param.value
                count_2q += 1
            elif gate.gate in ('x', 'sx', 'rx', 'rz', 'h', 'id'):
                err_1q += param.value
                count_1q += 1
    if count_1q:
        err_1q /= count_1q
    if count_2q:
        err_2q /= count_2q

    # Scale by the drift factor (cap at 0.5 to stay a valid channel)
    p1 = min(0.5, err_1q * factor * 4)  # depolarizing prob ~ 4x avg gate error
    p2 = min(0.5, err_2q * factor * 4)

    # Readout error scaled as well
    readout_err = min(0.5, 0.02 * factor)

    model = NoiseModel()
    model.add_all_qubit_quantum_error(depolarizing_error(p1, 1), ['x', 'sx', 'h', 'rz', 'rx'])
    model.add_all_qubit_quantum_error(depolarizing_error(p2, 2), ['cx', 'cz', 'ecr'])
    for q in range(config.n_qubits):
        model.add_readout_error(ReadoutError([[1 - readout_err, readout_err],
                                              [readout_err, 1 - readout_err]]), [q])
    return model


def measure_noise(noise_model, seed: int = 42):
    """Return ZKC probe loss for a given drift noise model."""
    sim = AerSimulator(noise_model=noise_model)
    sim.set_options(seed_simulator=seed)

    probe = QuantumCircuit(2)
    probe.h(0)
    probe.cx(0, 1)
    probe.measure_all()
    job = sim.run(probe, shots=8192)
    counts = job.result().get_counts()
    fidelity = (counts.get('00', 0) + counts.get('11', 0)) / 8192
    return 1.0 - fidelity


def run_circuit(noise_model, circuit, shots=8192, seed=42):
    sim = AerSimulator(noise_model=noise_model)
    sim.set_options(seed_simulator=seed)
    t = transpile(circuit, sim)
    job = sim.run(t, shots=shots)
    return job.result().get_counts()


def parity_metric(counts, n):
    """Fraction of shots in the GHZ parity class (000...0 / 111...1)."""
    zeros = '0' * n
    ones = '1' * n
    total = sum(counts.values())
    return (counts.get(zeros, 0) + counts.get(ones, 0)) / total if total else 0


def main():
    from qfa_verify.experiments.benchmarks import BenchmarkSuite
    suite = BenchmarkSuite()
    ghz = None
    for item in suite.circuits:
        if item['name'] == 'ghz_correct':
            ghz = item['circuit']
            break
    n = ghz.num_qubits

    backend = FakeBrisbane()
    factors = [1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0]
    fixed_threshold = 0.15

    rows = []
    for f in factors:
        noise_model = make_drift_noise_model(backend, f)
        eps = measure_noise(noise_model)
        counts = run_circuit(noise_model, ghz)
        metric = parity_metric(counts, n)

        # Derived anchor from the measured probe loss
        anchor = DerivedAnchor().compute_threshold(
            'ghz', [], ghz, noise_estimate=eps, p_ideal=1.0, n_shots=8192
        )
        fixed_verdict = 'PASS' if metric > fixed_threshold else 'FAIL'
        adaptive_verdict = 'PASS' if metric > anchor else 'FAIL'
        rows.append((f, metric, fixed_threshold, anchor, fixed_verdict, adaptive_verdict, eps))
        print(f"day={f:4.1f}x  eps={eps:.4f}  metric={metric:.4f}  "
              f"fixed={fixed_threshold:.3f}[{fixed_verdict}]  adaptive={anchor:.3f}[{adaptive_verdict}]")

    # Figure
    days = [r[0] for r in rows]
    metrics = [r[1] for r in rows]
    anchors = [r[3] for r in rows]
    fixed_line = [fixed_threshold] * len(rows)

    plt.figure(figsize=(10, 6))
    plt.plot(days, metrics, 'b-o', label='Measured parity fidelity (correct GHZ)')
    plt.plot(days, anchors, 'r--', label='Derived adaptive anchor (from ZKC probe)')
    plt.plot(days, fixed_line, 'g:', label='Fixed threshold (0.15)')
    # False failure zone: metric below fixed but above adaptive
    plt.fill_between(days, fixed_line, anchors,
                     where=[m < fixed_threshold and m >= a for m, a in zip(metrics, anchors)],
                     color='orange', alpha=0.3, label='False-failure zone (fixed only)')
    plt.xlabel('Simulated drift factor (noise multiplier)')
    plt.ylabel('Value')
    plt.title('Calibration Drift: Adaptive Anchor Tracks Device Noise, Fixed Threshold False-Fails')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUT / "fig4_drift_study.png", dpi=150)
    print(f"\n✅ Saved: {OUT / 'fig4_drift_study.png'}")
    print(f"   False failures avoided: {sum(1 for r in rows if r[4]=='FAIL' and r[5]=='PASS')} / {len(rows)} days")

    # LaTeX table
    print("\n% LaTeX drift table")
    print("\\begin{tabular}{|c|c|c|c|c|c|}")
    print("\\hline Drift & eps & Metric & Fixed & Adaptive & Status \\\\ \\hline")
    for r in rows:
        status = "RECOVERED" if r[4] == 'FAIL' and r[5] == 'PASS' else ("BOTH-PASS" if r[4] == 'PASS' else "BOTH-FAIL")
        print(f"{r[0]:.1f}x & {r[6]:.4f} & {r[1]:.4f} & {r[4]} & {r[5]} & {status} \\\\")
    print("\\hline \\end{tabular}")


if __name__ == "__main__":
    main()
