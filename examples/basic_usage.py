# examples/basic_usage.py
import qfa_verify
from qiskit import QuantumCircuit

# 1. Create a simple GHZ circuit to verify
qc = QuantumCircuit(3)
qc.h(0)
qc.cx(0, 1)
qc.cx(1, 2)
qc.measure_all()

# 2. Define your safety requirement in LTL
# "Eventually, we must reach the '111' state with high probability"
ltl_specification = "F(prob('111') > 0.7)"

# 3. Use the one-line API we created in __init__.py
print("--- Starting QFA-LTL Verification ---")
try:
    # This runs the Adaptive Safety Anchor and checking logic
    verdict = qfa_verify.verify(qc, ltl_specification, backend="fake_brisbane")
    
    if verdict['is_safe']:
        print(f"SUCCESS: Circuit verified. Safety Score: {verdict['score']}")
    else:
        print(f"FAILURE: Potential bug detected. Confidence: {verdict['confidence']}")
        
except Exception as e:
    print(f"Verification Error: {e}")
