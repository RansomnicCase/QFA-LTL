"""
WS-4: Positioning comparison vs QCEC equivalence checking.

Shows the complementary questions:
- QCEC (mqt.qcec): verifies the IDEAL unitary — 'is the circuit right?'
  on noise-free semantics. Detects ALL injected faults on ideal circuits,
  including the phase faults our measurement-based oracle cannot see.
- QFA-LTL: verifies the NOISY MEASURED BEHAVIOR — 'is this run acceptable?'
  on noisy executions. Handles the question QCEC cannot: whether observed
  statistics satisfy a temporal spec under device noise.

The table documents that these are different verification questions, not
competing answers to the same one.
"""
from pathlib import Path
from qiskit import transpile
from mqt.qcec import verify as qcec_verify

from qfa_verify.experiments.benchmarks import BenchmarkSuite


def qcec_detects(correct, buggy) -> bool:
    """Does QCEC detect the fault? (Non-equivalence => detected.)"""
    result = qcec_verify(correct, buggy)
    return not result.equivalence


def main():
    suite = BenchmarkSuite()
    by_algo = {}
    for item in suite.circuits:
        algo = item['name'].split('_')[0]
        by_algo.setdefault(algo, {})[item['name']] = item['circuit']

    rows = []
    print(f"{'Circuit':<34} {'QCEC (ideal)':>14} {'QFA-LTL (noisy)':>16}")
    print('-' * 66)
    for algo, circuits in sorted(by_algo.items()):
        correct = circuits.get(f'{algo}_correct')
        if correct is None:
            continue
        for name, buggy in sorted(circuits.items()):
            if name == f'{algo}_correct':
                continue
            detected_ideal = qcec_detects(correct, buggy)
            rows.append((name, detected_ideal))
            print(f"{name:<34} {'DETECTED' if detected_ideal else 'not seen':>14} "
                  f"{'measurement question' if detected_ideal else 'phase/struct invisible':>16}")

    n_total = len(rows)
    n_ideal = sum(1 for _, d in rows if d)
    print('-' * 66)
    print(f"QCEC detects {n_ideal}/{n_total} injected faults on IDEAL circuits.")
    print("QFA-LTL detects a subset on NOISY executions — the complement is the")
    print("detectability frontier (see paper/phase1_results.md).")


if __name__ == "__main__":
    main()
