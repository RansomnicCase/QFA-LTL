# examples/bv_10.py
from qiskit import QuantumCircuit

def create_bv_circuit(n, secret_string):
    qc = QuantumCircuit(n + 1, n)
    # Put auxiliary qubit in state |->
    qc.x(n)
    qc.h(n)
    
    # Superposition
    for i in range(n):
        qc.h(i)
        
    # Oracle for secret string (applying CX based on '1's in secret)
    for i, bit in enumerate(reversed(secret_string)):
        if bit == '1':
            qc.cx(i, n)
            
    # Measure
    for i in range(n):
        qc.h(i)
    
    qc.measure(range(n), range(n))
    return qc

# Target secret string: "1101101101" (10 bits)
qc = create_bv_circuit(10, "1101101101")
