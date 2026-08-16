"""
Week 2 Integration Test: Circuit → QFA → Product → Oracle
Tests the complete pipeline with Grover's algorithm.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from qiskit import QuantumCircuit
import numpy as np

from src.qfa_verify.qfa.circuit_compiler import compile_circuit
from src.qfa_verify.qfa.spec_automaton import SpecQFABuilder
from src.qfa_verify.qfa.product_construction import ProductAutomaton
from src.qfa_verify.ltl.parser import parse_ltl
from src.qfa_verify.noise.ibm_backend import NoiseAwareThresholdCalculator
from src.qfa_verify.oracle.generator import OracleGenerator

def create_grover_circuit() -> QuantumCircuit:
    """2-qubit Grover's algorithm searching for |11>"""
    qc = QuantumCircuit(2, 2)
    
    # Initialize superposition
    qc.h(0)
    qc.h(1)
    
    # Oracle: mark |11> with phase flip (CZ gate)
    qc.cz(0, 1)
    
    # Diffusion operator
    qc.h(0)
    qc.h(1)
    qc.x(0)
    qc.x(1)
    qc.cz(0, 1)  # Multi-controlled Z implemented as CZ in 2-qubit
    qc.x(0)
    qc.x(1)
    qc.h(0)
    qc.h(1)
    
    qc.measure([0, 1], [0, 1])
    return qc

def test_circuit_to_qfa():
    """Test Step 1: Circuit compilation"""
    print("=== Step 1: Circuit → QFA Compilation ===")
    qc = create_grover_circuit()
    print(f"Circuit:\n{qc}")
    
    qfa = compile_circuit(qc)
    print(f"\nCompiled QFA:")
    print(f"  Number of qubits: {qfa.num_qubits}")
    print(f"  Final superposition size: {len(qfa.superposition)} states")
    
    probs = qfa.get_all_probabilities()
    for state, prob in sorted(probs.items()):
        print(f"  |{state}>: {prob:.4f}")
    
    # Grover's should amplify |11> to ~97.7% for 2-qubit case
    prob_11 = qfa.get_probability('11')
    print(f"\n  Probability of |11>: {prob_11:.4f} (expected ~0.977)")
    
    assert prob_11 > 0.9, "Grover's algorithm not working correctly"
    return qfa, prob_11

def test_product_construction(qfa, ideal_prob):
    """Test Step 2: Product with Spec-QFA"""
    print("\n=== Step 2: Product Construction ===")
    
    # LTL spec: Eventually probability > 0.85
    ltl_str = "F(prob(|11>) > 0.85)"
    spec = parse_ltl(ltl_str)
    spec_qfa = SpecQFABuilder.from_ltl(spec)
    
    print(f"LTL Spec: {ltl_str}")
    print(f"Spec-QFA states: {spec_qfa.states}")
    
    # Build product
    constructor = ProductAutomaton(qfa, spec_qfa, '11', 0.85)
    constructor.construct()
    
    print(f"Product states: {len(constructor.states)}")
    print(f"Accepting states: {len(constructor.accepting_states)}")
    
    # Analyze reachability
    analysis = constructor.analyze_reachability()
    print(f"Reachability analysis:")
    for key, val in analysis.items():
        print(f"  {key}: {val}")
    
    return constructor, analysis

def test_threshold_calculation(ideal_prob):
    """Test Step 3: Noise-aware threshold"""
    print("\n=== Step 3: Threshold Calculation ===")
    
    calc = NoiseAwareThresholdCalculator(confidence=0.95)
    
    # Simulate IBM noise (in reality, fetch from backend)
    hardware_noise = 0.08  # 8% total error
    
    result = calc.calculate(ideal_prob, hardware_noise, num_shots=1024)
    
    print("Threshold components:")
    for key, val in result.items():
        print(f"  {key}: {val}")
    
    # Threshold should be lower than ideal due to noise
    assert result['final_threshold'] < ideal_prob
    return result

def test_oracle_generation(threshold_data, ideal_prob):
    """Test Step 4: Oracle generation"""
    print("\n=== Step 4: Oracle Generation ===")
    
    gen = OracleGenerator()
    metadata = {
        'timestamp': '2024-01-15T10:00:00',
        'backend': 'ibm_brisbane',
        'num_qubits': 2
    }
    
    oracle_code = gen.generate(
        circuit_name="grover_2q",
        ltl_spec="F(prob(|11>) > 0.85)",
        threshold_data=threshold_data,
        basis_state="11",
        metadata=metadata
    )
    
    print("Generated oracle code (first 30 lines):")
    lines = oracle_code.split('\n')[:30]
    for line in lines:
        print(line)
    print("...")
    
    # Save to file
    with open('outputs/grover_oracle.py', 'w') as f:
        f.write(oracle_code)
    print("\nSaved to: outputs/grover_oracle.py")
    
    # Test the oracle
    print("\n=== Testing Generated Oracle ===")
    exec(oracle_code, globals())
    
    # Correct circuit result (high |11>)
    correct_counts = {'00': 20, '01': 3, '10': 3, '11': 998}
    result = grover_2q_oracle(correct_counts, 1024)
    print(f"Correct circuit: {'PASS' if result else 'FAIL'}")
    
    # Buggy circuit result (missing diffusion)
    buggy_counts = {'00': 512, '01': 0, '10': 0, '11': 512}  # Only 50%
    result = grover_2q_oracle(buggy_counts, 1024)
    print(f"Buggy circuit: {'PASS' if result else 'FAIL'}")
    
    return oracle_code

def main():
    print("WEEK 2: Circuit-QFA Compilation & Product Construction")
    print("="*60)
    
    # Step 1
    qfa, ideal_prob = test_circuit_to_qfa()
    
    # Step 2  
    product, analysis = test_product_construction(qfa, ideal_prob)
    
    # Step 3
    threshold = test_threshold_calculation(ideal_prob)
    
    # Step 4
    oracle = test_oracle_generation(threshold, ideal_prob)
    
    print("\n" + "="*60)
    print("✅ Week 2 Complete!")
    print("Summary:")
    print(f"  - Circuit compiled to QFA with {len(qfa.superposition)} states")
    print(f"  - Product automaton has {len(product.states)} states")
    print(f"  - Generated oracle with threshold {threshold['final_threshold']:.4f}")
    print(f"  - Oracle saved to outputs/grover_oracle.py")

if __name__ == "__main__":
    main()
