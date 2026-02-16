# examples/final_success.py
from qiskit import QuantumCircuit

# A simple 3-qubit identity circuit (No gates, should stay 000)
qc = QuantumCircuit(3)
qc.measure_all()
