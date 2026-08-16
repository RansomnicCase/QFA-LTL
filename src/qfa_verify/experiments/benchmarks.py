"""
Benchmark Suite: 6 Quantum Algorithms with 3 Bug Types Each
Generates the 24 circuits for empirical evaluation.
"""
from qiskit import QuantumCircuit
import numpy as np
from typing import Dict, List, Tuple, Optional

class BenchmarkSuite:
    """Generates benchmark circuits with injected faults and pairs them with LTL specs."""
    
    def __init__(self):
        # Generate the raw circuits using the internal class methods
        raw_suite = self.generate_all()
        self.circuits = []

        # Map each generated circuit to its LTL requirement
        for key, circuit in raw_suite.items():
            # Extract the base algorithm name (e.g., 'grover' from 'grover_correct')
            alg_base = key.split('_')[0]
            
            self.circuits.append({
                "name": key,
                "type": "correct" if "correct" in key else "buggy",
                "circuit": circuit,
                "ltl_spec": self._get_spec_for_alg(alg_base)
            })

    @staticmethod
    def _get_spec_for_alg(alg: str) -> str:
        """Returns the LTL safety property for each algorithm class."""
        specs = {
            "grover": "F(prob(|11>) > 0.5)",       
            "bv": "F(prob(|10101>) > 0.5)",       
            "dj": "G(prob(|00>) > 0.5)",           
            "ghz": "G(prob(|000000>) + prob(|111111>) > 0.7)", 
            "qft": "F(prob(|1010>) > 0.05)",        
            "qaoa": "F(prob(|0101>) + prob(|1010>) > 0.4)" 
        }
        return specs.get(alg, "F(prob('00') > 0.1)")

    @staticmethod
    def grover_2q(bug_type: Optional[str] = None) -> QuantumCircuit:
        """2-qubit Grover's algorithm searching for |11>"""
        qc = QuantumCircuit(2, 2)
        qc.h([0, 1])
        
        # Oracle
        if bug_type == 'wrong_oracle':
            qc.x([0, 1])
            qc.cz(0, 1)
            qc.x([0, 1])
        else:
            qc.cz(0, 1)
        
        # Diffusion
        if bug_type != 'missing_diffusion':
            qc.h([0, 1])
            qc.x([0, 1])
            if bug_type == 'wrong_angle':
                qc.rx(np.pi/4, 0)
            qc.cz(0, 1)
            qc.x([0, 1])
            qc.h([0, 1])
        
        qc.measure([0, 1], [0, 1])
        return qc
    
    @staticmethod
    def bernstein_vazirani_5q(secret: str = "10101", bug_type: Optional[str] = None) -> QuantumCircuit:
        """Bernstein-Vazirani for secret string '10101'"""
        n = 5
        qc = QuantumCircuit(n, n)
        if bug_type != 'missing_hadamard':
            qc.h(n-1)
            qc.z(n-1)
        qc.h(range(n-1))
        
        actual_secret = "01010" if bug_type == 'wrong_secret' else secret
        for i, bit in enumerate(actual_secret[:n-1]):
            if bit == '1':
                if bug_type == 'wrong_cnot' and i % 2 == 0:
                    qc.cx(i, (i+2) % (n-1))
                else:
                    qc.cx(i, n-1)
        
        if bug_type != 'missing_hadamard':
            qc.h(range(n-1))
        qc.measure(range(n-1), range(n-1))
        return qc
    
    @staticmethod
    def qft_4q(bug_type: Optional[str] = None) -> QuantumCircuit:
        """Quantum Fourier Transform on 4 qubits"""
        n = 4
        qc = QuantumCircuit(n, n)
        for i in range(n):
            if not (bug_type == 'missing_h' and i == 0):
                qc.h(i)
            for j in range(i+1, n):
                angle = np.pi / (2 ** (j-i+1)) if bug_type == 'wrong_phase' else np.pi / (2 ** (j-i))
                qc.cp(angle, j, i)
        if bug_type != 'missing_swap':
            for i in range(n//2):
                qc.swap(i, n-1-i)
        qc.measure(range(n), range(n))
        return qc
    
    @staticmethod
    def ghz_6q(bug_type: Optional[str] = None) -> QuantumCircuit:
        """GHZ State Preparation"""
        n = 6
        qc = QuantumCircuit(n, n)
        qc.h(0)
        if bug_type == 'wrong_entanglement':
            for i in range(n-1):
                qc.cx(i, i+1)
        else:
            for i in range(1, n):
                if not (bug_type == 'missing_cnot' and i > 3):
                    qc.cx(0, i)
        if bug_type == 'decoherence':
            for _ in range(100): qc.id(0)
        qc.measure(range(n), range(n))
        return qc
    
    @staticmethod
    def qaoa_4q(bug_type: Optional[str] = None) -> QuantumCircuit:
        """QAOA for MaxCut on 4-node ring"""
        n = 4
        qc = QuantumCircuit(n, n)
        qc.h(range(n))
        edges = [(0,1), (1,2), (2,3), (3,0)] if bug_type != 'wrong_problem' else [(0,2), (1,3)]
        gamma = 0.5 if bug_type != 'wrong_gamma' else 2.0
        for _ in range(1 if bug_type == 'insufficient_depth' else 2):
            for i, j in edges: qc.rzz(gamma, i, j)
            qc.rx(0.5, range(n))
        qc.measure(range(n), range(n))
        return qc
    
    @staticmethod
    def deutsch_jozsa_3q(bug_type: Optional[str] = None) -> QuantumCircuit:
        """Deutsch-Jozsa Algorithm"""
        n = 3
        qc = QuantumCircuit(n, n-1)
        qc.x(n-1)
        qc.h(range(n))
        if bug_type != 'constant_function':
            for i in range(n-1):
                if not (bug_type == 'incomplete_oracle' and i == n-2):
                    qc.cx(i, n-1)
        qc.h(range(n-1))
        if bug_type == 'wrong_measurement':
            qc.h(range(n-1))
        qc.measure(range(n-1), range(n-1))
        return qc
    
    @classmethod
    def generate_all(cls) -> Dict[str, QuantumCircuit]:
        """Generates 24 benchmark circuits (6 algorithms x 4 variations)."""
        suite = {}
        algorithms = [
            ('grover', cls.grover_2q), ('bv', cls.bernstein_vazirani_5q),
            ('qft', cls.qft_4q), ('ghz', cls.ghz_6q),
            ('qaoa', cls.qaoa_4q), ('dj', cls.deutsch_jozsa_3q)
        ]
        
        for name, func in algorithms:
            suite[f"{name}_correct"] = func()
            bugs = {
                'grover': ['missing_diffusion', 'wrong_oracle', 'wrong_angle'],
                'bv': ['wrong_secret', 'missing_hadamard', 'wrong_cnot'],
                'qft': ['missing_swap', 'wrong_phase', 'missing_h'],
                'ghz': ['missing_cnot', 'wrong_entanglement', 'decoherence'],
                'qaoa': ['wrong_gamma', 'insufficient_depth', 'wrong_problem'],
                'dj': ['constant_function', 'wrong_measurement', 'incomplete_oracle']
            }[name]
            for bug in bugs:
                suite[f"{name}_{bug}"] = func(bug_type=bug)
        return suite
