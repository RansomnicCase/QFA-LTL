"""
Benchmark Suite: 6 Quantum Algorithms with 3 Bug Types Each
Generates the 54 circuits for empirical evaluation.
"""
from qiskit import QuantumCircuit
import numpy as np
from typing import Dict, List, Tuple, Optional

class BenchmarkSuite:
    """Generates benchmark circuits with injected faults"""
    
    @staticmethod
    def grover_2q(bug_type: Optional[str] = None) -> QuantumCircuit:
        """
        2-qubit Grover's algorithm searching for |11>
        
        Bug types:
        - 'missing_diffusion': Missing diffusion operator
        - 'wrong_oracle': Oracle marks |00> instead of |11>
        - 'wrong_angle': Wrong rotation angle
        """
        qc = QuantumCircuit(2, 2)
        
        # Initialize superposition
        qc.h([0, 1])
        
        # Oracle
        if bug_type == 'wrong_oracle':
            # Mark |00> instead of |11>
            qc.x([0, 1])
            qc.cz(0, 1)
            qc.x([0, 1])
        else:
            # Correct: mark |11>
            qc.cz(0, 1)
        
        # Diffusion operator
        if bug_type == 'missing_diffusion':
            pass  # Skip diffusion
        else:
            qc.h([0, 1])
            qc.x([0, 1])
            if bug_type == 'wrong_angle':
                qc.rx(np.pi/4, 0)  # Wrong rotation
            qc.cz(0, 1)
            qc.x([0, 1])
            qc.h([0, 1])
        
        qc.measure([0, 1], [0, 1])
        return qc
    
    @staticmethod
    def bernstein_vazirani_5q(secret: str = "10101", bug_type: Optional[str] = None) -> QuantumCircuit:
        """
        Bernstein-Vazirani: Finds secret string s in f(x) = s·x mod 2
        """
        n = 5
        qc = QuantumCircuit(n, n)
        
        # Initialize last qubit to |->
        if bug_type != 'missing_hadamard':
            qc.h(n-1)
            qc.z(n-1)
        
        # Hadamard on first n-1 qubits
        qc.h(range(n-1))
        
        # Oracle
        actual_secret = "01010" if bug_type == 'wrong_secret' else secret
        for i, bit in enumerate(actual_secret[:n-1]):  # FIX: Only use first n-1 qubits
            if bit == '1':
                if bug_type == 'wrong_cnot' and i % 2 == 0:
                    qc.cx(i, (i+2) % (n-1))  # Wrong connection
                else:
                    qc.cx(i, n-1)
        
        # Final Hadamard
        if bug_type != 'missing_hadamard':
            qc.h(range(n-1))
        
        qc.measure(range(n-1), range(n-1))
        return qc
    
    @staticmethod
    def qft_4q(bug_type: Optional[str] = None) -> QuantumCircuit:
        """
        Quantum Fourier Transform on 4 qubits
        """
        n = 4
        qc = QuantumCircuit(n, n)
        
        for i in range(n):
            if bug_type == 'missing_h' and i == 0:
                continue  # Skip first H
            qc.h(i)
            
            for j in range(i+1, n):
                if bug_type == 'wrong_phase':
                    angle = np.pi / (2 ** (j-i+1))  # Wrong angle
                else:
                    angle = np.pi / (2 ** (j-i))
                qc.cp(angle, j, i)
        
        # Swap qubits
        if bug_type != 'missing_swap':
            for i in range(n//2):
                qc.swap(i, n-1-i)
        
        qc.measure(range(n), range(n))
        return qc
    
    @staticmethod
    def ghz_6q(bug_type: Optional[str] = None) -> QuantumCircuit:
        """
        GHZ State Preparation: (|000000> + |111111>)/sqrt(2)
        """
        n = 6
        qc = QuantumCircuit(n, n)
        
        qc.h(0)
        
        if bug_type == 'wrong_entanglement':
            # Linear chain instead of star
            for i in range(n-1):
                qc.cx(i, i+1)
        else:
            # Star topology
            for i in range(1, n):
                if bug_type == 'missing_cnot' and i > 3:
                    continue
                qc.cx(0, i)
        
        if bug_type == 'decoherence':
            # Simulate T1 decay with identity gates
            for _ in range(100):
                qc.id(0)
        
        qc.measure(range(n), range(n))
        return qc
    
    @staticmethod
    def qaoa_4q(bug_type: Optional[str] = None) -> QuantumCircuit:
        """
        QAOA for MaxCut on 4-node ring
        """
        n = 4
        qc = QuantumCircuit(n, n)
        
        # Initial superposition
        qc.h(range(n))
        
        # Problem Hamiltonian (Cost)
        edges = [(0,1), (1,2), (2,3), (3,0)] if bug_type != 'wrong_problem' else [(0,2), (1,3)]
        gamma = 0.5 if bug_type != 'wrong_gamma' else 2.0
        
        for _ in range(1 if bug_type == 'insufficient_depth' else 2):
            for i, j in edges:
                qc.rzz(gamma, i, j)
            
            # Mixer Hamiltonian
            qc.rx(0.5, range(n))
        
        qc.measure(range(n), range(n))
        return qc
    
    @staticmethod
    def deutsch_jozsa_3q(bug_type: Optional[str] = None) -> QuantumCircuit:
        """
        Deutsch-Jozsa: Determine if function is constant or balanced
        """
        n = 3
        qc = QuantumCircuit(n, n-1)  # n-1 classical bits for measurement
        
        # Initialize ancilla in |1>
        qc.x(n-1)
        qc.h(range(n))
        
        # Oracle
        if bug_type == 'constant_function':
            pass  # Do nothing (constant)
        else:
            # Balanced oracle - FIX: Loop through first n-1 qubits
            for i in range(n-1):  # Only qubits 0 and 1 (not 2)
                if bug_type == 'incomplete_oracle' and i == n-2:
                    break  # Skip last CNOT for incomplete oracle
                qc.cx(i, n-1)
        
        qc.h(range(n-1))
        
        if bug_type == 'wrong_measurement':
            qc.h(range(n-1))  # Additional H changes basis
        
        qc.measure(range(n-1), range(n-1))
        return qc
    
    @classmethod
    def generate_all(cls) -> Dict[str, QuantumCircuit]:
        """
        Generate complete benchmark suite:
        6 algorithms × (1 correct + 3 bugs) = 24 circuits
        """
        suite = {}
        
        algorithms = [
            ('grover', cls.grover_2q),
            ('bv', cls.bernstein_vazirani_5q),
            ('qft', cls.qft_4q),
            ('ghz', cls.ghz_6q),
            ('qaoa', cls.qaoa_4q),
            ('dj', cls.deutsch_jozsa_3q),
        ]
        
        for name, func in algorithms:
            # Correct version (no bug_type parameter)
            suite[f"{name}_correct"] = func()
            
            # Buggy versions
            bugs = ['missing_diffusion', 'wrong_oracle', 'wrong_angle'] if name == 'grover' else \
                   ['wrong_secret', 'missing_hadamard', 'wrong_cnot'] if name == 'bv' else \
                   ['missing_swap', 'wrong_phase', 'missing_h'] if name == 'qft' else \
                   ['missing_cnot', 'wrong_entanglement', 'decoherence'] if name == 'ghz' else \
                   ['wrong_gamma', 'insufficient_depth', 'wrong_problem'] if name == 'qaoa' else \
                   ['constant_function', 'wrong_measurement', 'incomplete_oracle']
            
            for bug in bugs:
                suite[f"{name}_{bug}"] = func(bug_type=bug)
        
        return suite
