# examples/stress_7q.py
import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import RealAmplitudes

num_qubits = 7
# 1. Create the parameterized circuit
ansatz = RealAmplitudes(num_qubits, entanglement='full', reps=2)

# 2. Generate random values for all parameters (theta)
# RealAmplitudes has (reps + 1) * num_qubits parameters
num_params = ansatz.num_parameters
random_weights = np.random.uniform(0, 2 * np.pi, num_params)

# 3. Bind the parameters to create a concrete circuit
qc = ansatz.assign_parameters(random_weights)

# 4. Decompose and add measurements
qc = qc.decompose()
qc.measure_all()
