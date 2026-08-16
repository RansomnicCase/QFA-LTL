"""MVP demo for QFA-LTL
Run with: py -3 mvp_demo.py
"""
import sys
from pathlib import Path

print("QFA-LTL MVP Demo")
print("Run with the Windows py launcher: py -3 mvp_demo.py")

# Basic smoke test
try:
    from run_smoke_checks import smoke_eventually
    print('\n-- Running smoke_eventually() --')
    smoke_eventually()
except Exception as e:
    print('Smoke check failed:', e)

# Optional: try Qiskit-based compilation if available
try:
    print('\n-- Attempting Qiskit Circuit -> CircuitQFA demo --')
    from src.qfa_verify.qfa.circuit_compiler import compile_circuit
    try:
        from qiskit import QuantumCircuit
        # build simple 2-qubit Grover-like circuit
        qc = QuantumCircuit(2, 2)
        qc.h([0,1])
        qc.cz(0,1)
        qc.h([0,1])
        qc.measure([0,1],[0,1])
        print('Built Qiskit circuit:')
        print(qc)

        qfa = compile_circuit(qc)
        probs = qfa.get_all_probabilities()
        print('\nCircuitQFA probabilities:')
        for s, p in probs.items():
            print(f'  |{s}>: {p:.6f}')
    except Exception as inner:
        print('Qiskit demo skipped (qiskit not available or error):', inner)
except Exception as e:
    print('Optional Qiskit demo import failed:', e)

print('\nMVP demo complete.')
